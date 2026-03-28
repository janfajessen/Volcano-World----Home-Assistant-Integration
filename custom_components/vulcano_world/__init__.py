"""Volcano World – Home Assistant Integration.

Displays currently active/erupting volcanoes worldwide as GeoLocation
entities on the HA map, plus sensors and binary sensors.

Data sources (no API key required):
  - Smithsonian Global Volcanism Program (GVP): https://volcano.si.edu
  - USGS Volcano Hazards HANS API: https://volcanoes.usgs.gov
"""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import VolcanoWorldCoordinator

PLATFORMS: list[Platform] = [
    Platform.GEO_LOCATION,
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Volcano World from a config entry (no HA restart required)."""
    coordinator = VolcanoWorldCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload integration when options change via gear icon — no restart needed
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok


async def _async_options_updated(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload when options are updated via the gear icon."""
    await hass.config_entries.async_reload(entry.entry_id)
