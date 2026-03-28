"""Config flow and Options flow for Volcano World."""
from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_LATITUDE,
    CONF_LONGITUDE,
    CONF_LOCATION_MODE,
    CONF_RADIUS_KM,
    CONF_SOURCE_GVP,
    CONF_SOURCE_USGS,
    CONF_UNIT,
    CONF_UPDATE_INTERVAL,
    DEFAULT_RADIUS_KM,
    DEFAULT_SOURCE_GVP,
    DEFAULT_SOURCE_USGS,
    DEFAULT_TITLE,
    DEFAULT_UNIT,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    KM_TO_MI,
    MI_TO_KM,
    LOCATION_MODE_CUSTOM,
    LOCATION_MODE_HOME,
    LOCATION_MODE_WORLD,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
    RADIUS_MAX_KM,
    RADIUS_MAX_MI,
    RADIUS_MIN_KM,
    RADIUS_MIN_MI,
    UNIT_KM,
    UNIT_MI,
)


def _radius_display(radius_km: float, unit: str) -> float:
    """Convert stored km radius to display value."""
    if unit == UNIT_MI:
        return round(radius_km * KM_TO_MI)
    return round(radius_km)


def _radius_to_km(value: float, unit: str) -> float:
    """Convert display radius back to km for storage."""
    if unit == UNIT_MI:
        return round(value * MI_TO_KM, 1)
    return float(value)


def _mode_schema(defaults: dict[str, Any]) -> vol.Schema:
    unit       = defaults.get(CONF_UNIT, DEFAULT_UNIT)
    radius_km  = defaults.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM)
    r_display  = _radius_display(radius_km, unit)
    r_min      = RADIUS_MIN_MI  if unit == UNIT_MI else RADIUS_MIN_KM
    r_max      = RADIUS_MAX_MI  if unit == UNIT_MI else RADIUS_MAX_KM
    r_step     = 50             if unit == UNIT_KM  else 31

    return vol.Schema({
        vol.Required(
            CONF_LOCATION_MODE,
            default=defaults.get(CONF_LOCATION_MODE, LOCATION_MODE_HOME),
        ): selector.SelectSelector(selector.SelectSelectorConfig(
            options=[
                {"value": LOCATION_MODE_HOME,   "label": "Home Assistant location"},
                {"value": LOCATION_MODE_CUSTOM, "label": "Custom location (pick on map)"},
                {"value": LOCATION_MODE_WORLD,  "label": "Entire world (no filter)"},
            ],
            mode=selector.SelectSelectorMode.LIST,
        )),
        vol.Required(
            CONF_UNIT,
            default=unit,
        ): selector.SelectSelector(selector.SelectSelectorConfig(
            options=[
                {"value": UNIT_KM, "label": "Kilometers (km)"},
                {"value": UNIT_MI, "label": "Miles (mi)"},
            ],
            mode=selector.SelectSelectorMode.LIST,
        )),
        vol.Required(
            CONF_RADIUS_KM,
            default=r_display,
        ): selector.NumberSelector(selector.NumberSelectorConfig(
            min=r_min,
            max=r_max,
            step=r_step,
            unit_of_measurement=unit,
            mode=selector.NumberSelectorMode.SLIDER,
        )),
        vol.Required(
            CONF_UPDATE_INTERVAL,
            default=defaults.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL),
        ): selector.NumberSelector(selector.NumberSelectorConfig(
            min=MIN_UPDATE_INTERVAL, max=MAX_UPDATE_INTERVAL, step=5,
            unit_of_measurement="min",
            mode=selector.NumberSelectorMode.BOX,
        )),
        vol.Required(
            CONF_SOURCE_GVP,
            default=defaults.get(CONF_SOURCE_GVP, DEFAULT_SOURCE_GVP),
        ): selector.BooleanSelector(),
        vol.Required(
            CONF_SOURCE_USGS,
            default=defaults.get(CONF_SOURCE_USGS, DEFAULT_SOURCE_USGS),
        ): selector.BooleanSelector(),
    })


def _location_schema(defaults: dict[str, Any], hass: HomeAssistant) -> vol.Schema:
    return vol.Schema({
        vol.Required(
            "location",
            default={
                "latitude":  defaults.get(CONF_LATITUDE,  hass.config.latitude),
                "longitude": defaults.get(CONF_LONGITUDE, hass.config.longitude),
            },
        ): selector.LocationSelector(
            selector.LocationSelectorConfig(radius=False, icon="mdi:volcano")
        ),
    })


# ── Config Flow ───────────────────────────────────────────────────────────────

class VolcanoWorldConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Volcano World."""

    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            # Convert displayed radius back to km for storage
            unit = user_input.get(CONF_UNIT, DEFAULT_UNIT)
            user_input[CONF_RADIUS_KM] = _radius_to_km(user_input[CONF_RADIUS_KM], unit)
            self._data.update(user_input)
            if user_input[CONF_LOCATION_MODE] == LOCATION_MODE_CUSTOM:
                return await self.async_step_custom_location()
            return self._create_entry()

        # Auto-detect HA unit system as default
        default_unit = UNIT_MI if self.hass.config.units.length_unit == "mi" else UNIT_KM
        return self.async_show_form(
            step_id="user",
            data_schema=_mode_schema({CONF_UNIT: default_unit}),
            description_placeholders={
                "gvp_url":  "https://volcano.si.edu",
                "usgs_url": "https://volcanoes.usgs.gov",
            },
        )

    async def async_step_custom_location(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            loc = user_input["location"]
            self._data[CONF_LATITUDE]  = loc["latitude"]
            self._data[CONF_LONGITUDE] = loc["longitude"]
            return self._create_entry()
        return self.async_show_form(
            step_id="custom_location",
            data_schema=_location_schema({}, self.hass),
        )

    def _create_entry(self) -> FlowResult:
        return self.async_create_entry(title=DEFAULT_TITLE, data=self._data)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> "VolcanoWorldOptionsFlow":
        return VolcanoWorldOptionsFlow()


# ── Options Flow (gear icon) ──────────────────────────────────────────────────

class VolcanoWorldOptionsFlow(OptionsFlow):
    """Options flow — self.config_entry injected automatically by HA 2024.4+."""

    def __init__(self) -> None:
        self._options: dict[str, Any] = {}

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        current = {**self.config_entry.data, **self.config_entry.options}

        if user_input is not None:
            unit = user_input.get(CONF_UNIT, DEFAULT_UNIT)
            user_input[CONF_RADIUS_KM] = _radius_to_km(user_input[CONF_RADIUS_KM], unit)
            self._options.update(user_input)
            if user_input[CONF_LOCATION_MODE] == LOCATION_MODE_CUSTOM:
                return await self.async_step_custom_location()
            return self.async_create_entry(data=self._options)

        return self.async_show_form(
            step_id="init",
            data_schema=_mode_schema(current),
            description_placeholders={
                "current_mode": current.get(CONF_LOCATION_MODE, LOCATION_MODE_HOME),
            },
        )

    async def async_step_custom_location(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        current = {**self.config_entry.data, **self.config_entry.options}
        if user_input is not None:
            loc = user_input["location"]
            self._options[CONF_LATITUDE]  = loc["latitude"]
            self._options[CONF_LONGITUDE] = loc["longitude"]
            return self.async_create_entry(data=self._options)
        return self.async_show_form(
            step_id="custom_location",
            data_schema=_location_schema(current, self.hass),
        )
