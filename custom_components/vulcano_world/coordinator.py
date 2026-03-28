"""DataUpdateCoordinator for Volcano World."""
from __future__ import annotations

import asyncio
import logging
import re
from dataclasses import dataclass
from datetime import timedelta
from math import asin, cos, radians, sin, sqrt
from typing import Any

import aiohttp

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_LOCATION_MODE,
    CONF_RADIUS_KM,
    CONF_SOURCE_GVP,
    CONF_SOURCE_USGS,
    CONF_UPDATE_INTERVAL,
    DEFAULT_RADIUS_KM,
    DEFAULT_SOURCE_GVP,
    DEFAULT_SOURCE_USGS,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    GVP_CURRENT_ERUPTIONS_URL,
    GVP_WEEKLY_REPORT_URL,
    LOCATION_MODE_CUSTOM,
    LOCATION_MODE_HOME,
    LOCATION_MODE_WORLD,
    USGS_HANS_BASE_URL,
)
from .volcano_data import VOLCANO_ALIASES, VOLCANO_DATABASE, VOLCANO_NAME_LOOKUP

_LOGGER = logging.getLogger(__name__)
_HTTP_TIMEOUT = aiohttp.ClientTimeout(total=30)

# Max characters kept per volcano narrative (avoids bloated attributes)
_MAX_NARRATIVE_CHARS = 600


@dataclass
class VolcanoData:
    """Represents one active volcano with current activity data."""

    volcano_id:          str
    name:                str
    country:             str
    latitude:            float
    longitude:           float
    alert_level:         str        = "UNASSIGNED"
    aviation_color:      str | None = None
    eruption_start:      str | None = None
    last_activity:       str | None = None
    weekly_report_text:  str | None = None   # narrative from WVAR
    source:              str        = "gvp"
    distance_km:         float | None = None
    url:                 str | None = None
    volcano_type:        str | None = None
    in_weekly_report:    bool       = False
    gvp_number:          int | None = None
    has_coordinates:     bool       = True


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    φ1, λ1, φ2, λ2 = map(radians, (lat1, lon1, lat2, lon2))
    a = sin((φ2 - φ1) / 2) ** 2 + cos(φ1) * cos(φ2) * sin((λ2 - λ1) / 2) ** 2
    return 2 * r * asin(sqrt(a))


def _strip_html(text: str) -> str:
    """Remove HTML tags and normalise whitespace."""
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()


def _parse_wvar_narratives(html: str) -> dict[int, str]:
    """Extract per-volcano narrative text from the GVP Weekly Report page.

    The WVAR page has repeating blocks roughly like:
        <a ... href="/volcano.cfm?vn=XXXXXX">VolcanoName</a>
        ... (some header markup) ...
        <p>Narrative text about the volcano this week.</p>

    Returns a dict of {gvp_number: narrative_text}.
    """
    narratives: dict[int, str] = {}

    # Split page into per-volcano sections anchored on the profile link
    # Each section starts just before the volcano link and ends before the next
    sections = re.split(
        r'(?=href=["\'][^"\']*?/volcano\.cfm\?vn=\d{6})',
        html,
        flags=re.IGNORECASE,
    )

    for section in sections:
        # Find GVP number in this section
        vn_match = re.search(
            r'/volcano\.cfm\?vn=(\d{6})',
            section,
            re.IGNORECASE,
        )
        if not vn_match:
            continue
        gvp_num = int(vn_match.group(1))

        # Extract all <p> content within this section (take up to first 2 paragraphs)
        paragraphs = re.findall(r'<p[^>]*>(.*?)</p>', section, re.IGNORECASE | re.DOTALL)
        if not paragraphs:
            # Fallback: grab a chunk of plain text after the volcano link
            after = section[vn_match.end():]
            plain = _strip_html(after[:1200])
            if len(plain) > 80:
                narratives[gvp_num] = plain[:_MAX_NARRATIVE_CHARS]
            continue

        # Join first 2 non-empty paragraphs
        text_parts: list[str] = []
        for p in paragraphs[:2]:
            cleaned = _strip_html(p)
            if len(cleaned) > 40:          # skip tiny/empty paragraphs
                text_parts.append(cleaned)

        if text_parts:
            full = " ".join(text_parts)
            narratives[gvp_num] = full[:_MAX_NARRATIVE_CHARS]

    _LOGGER.debug("WVAR narratives extracted: %d volcanoes", len(narratives))
    return narratives


class VolcanoWorldCoordinator(DataUpdateCoordinator[dict[str, VolcanoData]]):
    """Manages fetching and merging volcano data from GVP and USGS."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self._entry   = entry
        self._session = async_get_clientsession(hass)
        cfg = self._merged_config(entry)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(
                minutes=int(cfg.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL))
            ),
        )

    # ── Public properties ─────────────────────────────────────────────────────

    @property
    def location_mode(self) -> str:
        return self._merged_config(self._entry).get(CONF_LOCATION_MODE, LOCATION_MODE_WORLD)

    @property
    def radius_km(self) -> float:
        return float(self._merged_config(self._entry).get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM))

    @property
    def ref_lat(self) -> float | None:
        cfg  = self._merged_config(self._entry)
        mode = cfg.get(CONF_LOCATION_MODE, LOCATION_MODE_WORLD)
        if mode == LOCATION_MODE_HOME:
            return self.hass.config.latitude
        if mode == LOCATION_MODE_CUSTOM:
            return cfg.get(CONF_LATITUDE)
        return self.hass.config.latitude

    @property
    def ref_lon(self) -> float | None:
        cfg  = self._merged_config(self._entry)
        mode = cfg.get(CONF_LOCATION_MODE, LOCATION_MODE_WORLD)
        if mode == LOCATION_MODE_HOME:
            return self.hass.config.longitude
        if mode == LOCATION_MODE_CUSTOM:
            return cfg.get(CONF_LONGITUDE)
        return self.hass.config.longitude

    # ── Core update ───────────────────────────────────────────────────────────

    async def _async_update_data(self) -> dict[str, VolcanoData]:
        cfg      = self._merged_config(self._entry)
        use_gvp  = bool(cfg.get(CONF_SOURCE_GVP,  DEFAULT_SOURCE_GVP))
        use_usgs = bool(cfg.get(CONF_SOURCE_USGS, DEFAULT_SOURCE_USGS))

        if not use_gvp and not use_usgs:
            raise UpdateFailed("Both data sources are disabled.")

        tasks: list[Any] = []
        if use_gvp:
            tasks.append(self._fetch_gvp())
        if use_usgs:
            tasks.append(self._fetch_usgs())

        results = await asyncio.gather(*tasks, return_exceptions=True)

        gvp_list:  list[VolcanoData] = []
        usgs_list: list[VolcanoData] = []

        idx = 0
        if use_gvp:
            if isinstance(results[idx], Exception):
                _LOGGER.warning("GVP fetch failed: %s", results[idx])
            else:
                gvp_list = results[idx]
            idx += 1
        if use_usgs:
            if isinstance(results[idx], Exception):
                _LOGGER.warning("USGS fetch failed: %s", results[idx])
            else:
                usgs_list = results[idx]

        # Merge: GVP primary, USGS enriches alert data
        merged: dict[str, VolcanoData] = {}
        for v in gvp_list:
            merged[v.volcano_id] = v

        for v in usgs_list:
            if v.volcano_id in merged:
                existing = merged[v.volcano_id]
                existing.alert_level    = v.alert_level
                existing.aviation_color = v.aviation_color
            else:
                merged[v.volcano_id] = v

        if not merged:
            raise UpdateFailed("No active volcano data retrieved from any source.")

        # Calculate distances
        ref_lat, ref_lon = self.ref_lat, self.ref_lon
        for v in merged.values():
            if v.has_coordinates and ref_lat is not None and ref_lon is not None:
                v.distance_km = round(
                    _haversine_km(ref_lat, ref_lon, v.latitude, v.longitude), 1
                )

        _LOGGER.debug(
            "Volcano World updated: %d total (%d GVP + %d USGS)",
            len(merged), len(gvp_list), len(usgs_list),
        )
        return merged

    # ── GVP fetcher ───────────────────────────────────────────────────────────

    async def _fetch_gvp(self) -> list[VolcanoData]:
        """Fetch GVP current eruptions + weekly report (narratives)."""
        html_eruptions, html_weekly = await asyncio.gather(
            self._get_text(GVP_CURRENT_ERUPTIONS_URL),
            self._get_text(GVP_WEEKLY_REPORT_URL),
        )

        # Build WVAR number set and narrative dict in one pass
        wvar_numbers: set[int] = set()
        narratives:   dict[int, str] = {}

        if html_weekly:
            for m in re.finditer(r'/volcano\.cfm\?vn=(\d{6})', html_weekly):
                wvar_numbers.add(int(m.group(1)))
            narratives = _parse_wvar_narratives(html_weekly)

        if not html_eruptions:
            return []

        return self._parse_gvp_html(html_eruptions, wvar_numbers, narratives)

    async def _get_text(self, url: str) -> str | None:
        try:
            async with self._session.get(
                url,
                timeout=_HTTP_TIMEOUT,
                headers={"User-Agent": "HomeAssistant/VolcanoWorld/1.2"},
            ) as resp:
                resp.raise_for_status()
                return await resp.text(encoding="utf-8", errors="replace")
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("HTTP error fetching %s: %s", url, err)
            return None

    def _parse_gvp_html(
        self,
        html: str,
        wvar_numbers: set[int],
        narratives: dict[int, str],
    ) -> list[VolcanoData]:
        volcanoes: list[VolcanoData] = []
        seen: set[int] = set()

        link_re = re.compile(
            r'href=["\'](?:https?://volcano\.si\.edu)?/volcano\.cfm\?vn=(\d{6})["\'][^>]*>'
            r'\s*([^<]{2,60}?)\s*<',
            re.IGNORECASE,
        )

        for m in link_re.finditer(html):
            gvp_num  = int(m.group(1))
            raw_name = m.group(2).strip()

            if gvp_num in seen or len(raw_name) < 2 or re.match(r'^\d', raw_name):
                continue
            seen.add(gvp_num)

            db_entry = VOLCANO_DATABASE.get(gvp_num)
            if db_entry is None:
                norm      = raw_name.lower()
                alias_key = VOLCANO_ALIASES.get(norm) or VOLCANO_NAME_LOOKUP.get(norm)
                if alias_key:
                    db_entry = VOLCANO_DATABASE.get(alias_key)

            pos = m.start()
            ctx = html[max(0, pos - 60): pos + 600]
            date_match = re.search(
                r'(\d{4}\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*\d{1,2}'
                r'|\d{1,2}\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*\d{4}'
                r'|\d{4}-\d{2}-\d{2})',
                ctx,
                re.IGNORECASE,
            )
            eruption_start = date_match.group(0).strip() if date_match else None

            in_wvar   = gvp_num in wvar_numbers
            narrative = narratives.get(gvp_num)   # None if not in weekly report

            if db_entry:
                v = VolcanoData(
                    volcano_id         = f"vw_{gvp_num}",
                    name               = db_entry["name"],
                    country            = db_entry["country"],
                    latitude           = db_entry["lat"],
                    longitude          = db_entry["lon"],
                    source             = "gvp",
                    url                = f"https://volcano.si.edu/volcano.cfm?vn={gvp_num}",
                    volcano_type       = db_entry.get("type"),
                    in_weekly_report   = in_wvar,
                    weekly_report_text = narrative,
                    gvp_number         = gvp_num,
                    eruption_start     = eruption_start,
                    has_coordinates    = True,
                )
            else:
                _LOGGER.debug(
                    "GVP volcano '%s' (%d) not in bundled DB — no coordinates",
                    raw_name, gvp_num,
                )
                v = VolcanoData(
                    volcano_id         = f"vw_{gvp_num}",
                    name               = raw_name,
                    country            = "Unknown",
                    latitude           = 0.0,
                    longitude          = 0.0,
                    source             = "gvp",
                    url                = f"https://volcano.si.edu/volcano.cfm?vn={gvp_num}",
                    in_weekly_report   = in_wvar,
                    weekly_report_text = narrative,
                    gvp_number         = gvp_num,
                    eruption_start     = eruption_start,
                    has_coordinates    = False,
                )
            volcanoes.append(v)

        _LOGGER.debug("GVP: %d active volcanoes parsed", len(volcanoes))
        return volcanoes

    # ── USGS fetcher ──────────────────────────────────────────────────────────

    async def _fetch_usgs(self) -> list[VolcanoData]:
        async def _get_json(path: str) -> list[dict]:
            url = f"{USGS_HANS_BASE_URL}/{path}"
            try:
                async with self._session.get(
                    url,
                    timeout=_HTTP_TIMEOUT,
                    headers={"Accept": "application/json"},
                ) as resp:
                    resp.raise_for_status()
                    return await resp.json(content_type=None)
            except Exception as err:  # noqa: BLE001
                _LOGGER.debug("USGS %s failed: %s", path, err)
                return []

        monitored, elevated = await asyncio.gather(
            _get_json("getMonitoredVolcanoes"),
            _get_json("getElevatedVolcanoes"),
        )

        by_id: dict[int, dict] = {v.get("id", 0): v for v in monitored}
        for v in elevated:
            by_id[v.get("id", 0)] = v

        result: list[VolcanoData] = []
        for raw in by_id.values():
            lat = raw.get("latitude")
            lon = raw.get("longitude")
            if lat is None or lon is None:
                continue

            gvp_num: int | None = (
                raw.get("smithsonianVNum")
                or raw.get("smithsonianVnum")
                or raw.get("smithsonianVolcanoNumber")
            )

            color    = (raw.get("colorCode") or raw.get("backgroundColorCode") or "UNASSIGNED").upper()
            aviation = raw.get("aviationColorCode") or raw.get("aviationColor")
            name     = raw.get("volcanoName") or raw.get("name") or "Unknown"
            country  = raw.get("countryName") or raw.get("country") or "USA"
            db_entry = VOLCANO_DATABASE.get(gvp_num) if gvp_num else None

            result.append(VolcanoData(
                volcano_id      = f"vw_{gvp_num}" if gvp_num else f"usgs_{raw.get('id', 0)}",
                name            = db_entry["name"] if db_entry else name,
                country         = db_entry["country"] if db_entry else country,
                latitude        = float(lat),
                longitude       = float(lon),
                alert_level     = color,
                aviation_color  = aviation,
                source          = "usgs",
                gvp_number      = gvp_num,
                volcano_type    = db_entry.get("type") if db_entry else None,
                has_coordinates = True,
            ))

        _LOGGER.debug("USGS: %d volcanoes parsed", len(result))
        return result

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _merged_config(entry: ConfigEntry) -> dict[str, Any]:
        return {**entry.data, **entry.options}
