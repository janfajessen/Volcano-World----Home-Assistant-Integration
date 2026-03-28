"""GeoLocation platform for Volcano World.

Entity IDs: geo_location.volcano_world_etna, geo_location.volcano_world_stromboli, etc.
Distance shown in the unit chosen by the user (km or mi).
"""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.geo_location import GeolocationEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfLength
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import (
    ATTRIBUTION,
    CONF_LOCATION_MODE,
    CONF_RADIUS_KM,
    CONF_UNIT,
    DEFAULT_RADIUS_KM,
    DEFAULT_UNIT,
    DOMAIN,
    KM_TO_MI,
    LOCATION_MODE_WORLD,
    UNIT_MI,
)
from .coordinator import VolcanoWorldCoordinator, VolcanoData

_LOGGER = logging.getLogger(__name__)
GEO_SOURCE = DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: VolcanoWorldCoordinator = hass.data[DOMAIN][entry.entry_id]
    manager = _VolcanoEntityManager(hass, coordinator, entry, async_add_entities)
    await manager.async_init()
    entry.async_on_unload(manager.async_shutdown)


class _VolcanoEntityManager:
    def __init__(self, hass, coordinator, entry, async_add_entities):
        self._hass        = hass
        self._coordinator = coordinator
        self._entry       = entry
        self._add         = async_add_entities
        self._entities: dict[str, VolcanoGeolocationEvent] = {}
        self._remove_listener: Any = None

    async def async_init(self) -> None:
        self._remove_listener = self._coordinator.async_add_listener(
            self._async_coordinator_updated
        )
        self._async_coordinator_updated()

    @callback
    def async_shutdown(self) -> None:
        if self._remove_listener:
            self._remove_listener()

    @callback
    def _async_coordinator_updated(self) -> None:
        if self._coordinator.data is None:
            return

        config    = {**self._entry.data, **self._entry.options}
        mode      = config.get(CONF_LOCATION_MODE, LOCATION_MODE_WORLD)
        radius_km = float(config.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM))

        visible: set[str] = set()
        for vid, v in self._coordinator.data.items():
            if not v.has_coordinates or (v.latitude == 0.0 and v.longitude == 0.0):
                continue
            if mode == LOCATION_MODE_WORLD:
                visible.add(vid)
            elif v.distance_km is not None and v.distance_km <= radius_km:
                visible.add(vid)

        current_ids = set(self._entities)
        for vid in current_ids - visible:
            entity = self._entities.pop(vid)
            self._hass.async_create_task(entity.async_remove(force_remove=True))

        new_entities: list[VolcanoGeolocationEvent] = []
        for vid in visible - current_ids:
            entity = VolcanoGeolocationEvent(self._coordinator, self._entry, vid)
            self._entities[vid] = entity
            new_entities.append(entity)

        if new_entities:
            self._add(new_entities, update_before_add=False)

        for vid in current_ids & visible:
            if vid in self._entities:
                self._entities[vid].async_write_ha_state()


class VolcanoGeolocationEvent(
    CoordinatorEntity[VolcanoWorldCoordinator], GeolocationEvent
):
    """One active volcano as a geo_location entity on the HA map."""

    _attr_has_entity_name     = False
    _attr_attribution         = ATTRIBUTION
    _attr_should_poll         = False

    def __init__(
        self,
        coordinator: VolcanoWorldCoordinator,
        entry: ConfigEntry,
        volcano_id: str,
    ) -> None:
        super().__init__(coordinator)
        self._volcano_id = volcano_id
        self._entry      = entry

        v         = (coordinator.data or {}).get(volcano_id)
        name_slug = slugify(v.name) if v else slugify(volcano_id)

        self._attr_unique_id = f"{entry.entry_id}_{volcano_id}"
        self.entity_id       = f"geo_location.volcano_world_{name_slug}"

    # ── Unit helper ───────────────────────────────────────────────────────────

    @property
    def _use_miles(self) -> bool:
        cfg = {**self._entry.data, **self._entry.options}
        return cfg.get(CONF_UNIT, DEFAULT_UNIT) == UNIT_MI

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def _volcano(self) -> VolcanoData | None:
        return (self.coordinator.data or {}).get(self._volcano_id)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name="Volcano World",
            manufacturer="Smithsonian / USGS",
            model="GVP + HANS",
            entry_type=DeviceEntryType.SERVICE,
            configuration_url="https://volcano.si.edu",
        )

    @property
    def source(self) -> str:
        return GEO_SOURCE

    @property
    def name(self) -> str:  # type: ignore[override]
        v = self._volcano
        return v.name if v else "Unknown Volcano"

    @property
    def latitude(self) -> float | None:
        v = self._volcano
        return v.latitude if v and v.has_coordinates else None

    @property
    def longitude(self) -> float | None:
        v = self._volcano
        return v.longitude if v and v.has_coordinates else None

    @property
    def unit_of_measurement(self) -> str:
        return UnitOfLength.MILES if self._use_miles else UnitOfLength.KILOMETERS

    @property
    def distance(self) -> float | None:
        """Distance from reference point in the user's chosen unit."""
        v = self._volcano
        if not v or v.distance_km is None:
            return None
        if self._use_miles:
            return round(v.distance_km * KM_TO_MI, 1)
        return v.distance_km

    @property
    def icon(self) -> str:
        v     = self._volcano
        level = (v.alert_level if v else "UNASSIGNED").upper()
        if level in ("RED", "WARNING"):
            return "mdi:volcano"
        if level in ("ORANGE", "WATCH"):
            return "mdi:volcano-outline"
        if level in ("YELLOW", "ADVISORY"):
            return "mdi:alert-circle-outline"
        return "mdi:image-filter-hdr"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        v = self._volcano
        if not v:
            return {}
        use_mi = self._use_miles
        dist   = (round(v.distance_km * KM_TO_MI, 1) if use_mi else v.distance_km) if v.distance_km is not None else None
        unit   = UNIT_MI if use_mi else "km"
        return {
            "country":           v.country,
            "alert_level":       v.alert_level,
            "aviation_color":    v.aviation_color,
            "eruption_start":    v.eruption_start,
            "last_activity":     v.last_activity,
            "volcano_type":      v.volcano_type,
            "in_weekly_report":  v.in_weekly_report,
            "weekly_report_text": v.weekly_report_text,
            "data_source":       v.source,
            "gvp_number":        v.gvp_number,
            "url":               v.url,
            f"distance_{unit}":  dist,
            "attribution":       ATTRIBUTION,
        }

    @property
    def available(self) -> bool:
        return (
            self.coordinator.last_update_success
            and self._volcano_id in (self.coordinator.data or {})
        )
