"""Binary sensor platform for Volcano World."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ALERT_SEVERITY,
    ATTRIBUTION,
    BINARY_SENSOR_ACTIVITY_NEARBY,
    BINARY_SENSOR_ELEVATED_NEARBY,
    BINARY_SENSOR_WARNING_GLOBAL,
    CONF_RADIUS_KM,
    CONF_UNIT,
    DEFAULT_RADIUS_KM,
    DEFAULT_UNIT,
    DOMAIN,
    KM_TO_MI,
    UNIT_MI,
)
from .coordinator import VolcanoWorldCoordinator, VolcanoData


@dataclass(frozen=True, kw_only=True)
class VolcanoBinarySensorDescription(BinarySensorEntityDescription):
    is_on_fn:      Callable[[dict[str, VolcanoData], dict[str, Any]], bool]
    attributes_fn: Callable[[dict[str, VolcanoData], dict[str, Any]], dict[str, Any]] | None = None


def _radius_km(cfg: dict) -> float:
    return float(cfg.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM))

def _use_mi(cfg: dict) -> bool:
    return cfg.get(CONF_UNIT, DEFAULT_UNIT) == UNIT_MI

def _unit_label(cfg: dict) -> str:
    return UNIT_MI if _use_mi(cfg) else "km"

def _dist(v: VolcanoData, use_mi: bool) -> float | None:
    if v.distance_km is None:
        return None
    return round(v.distance_km * KM_TO_MI, 1) if use_mi else v.distance_km


def _activity_nearby(data, cfg) -> bool:
    r = _radius_km(cfg)
    return any(v.has_coordinates and v.distance_km is not None and v.distance_km <= r for v in data.values())

def _elevated_nearby(data, cfg) -> bool:
    r = _radius_km(cfg)
    return any(
        v.has_coordinates and v.distance_km is not None and v.distance_km <= r
        and ALERT_SEVERITY.get((v.alert_level or "").upper(), 0) >= 2
        for v in data.values()
    )

def _warning_global(data, cfg) -> bool:
    return any(ALERT_SEVERITY.get((v.alert_level or "").upper(), 0) >= 4 for v in data.values())


def _nearby_attrs(data, cfg):
    r    = _radius_km(cfg)
    mi   = _use_mi(cfg)
    unit = _unit_label(cfg)
    r_d  = round(r * KM_TO_MI, 1) if mi else r
    return {
        "nearby_volcanoes": [
            {"name": v.name, "country": v.country, f"distance_{unit}": _dist(v, mi), "alert_level": v.alert_level, "url": v.url}
            for v in sorted(
                (v for v in data.values() if v.has_coordinates and v.distance_km is not None and v.distance_km <= r),
                key=lambda x: x.distance_km or 9999,
            )
        ],
        f"radius_{unit}": r_d,
    }

def _warning_attrs(data, cfg):
    mi   = _use_mi(cfg)
    unit = _unit_label(cfg)
    return {
        "warning_volcanoes": [
            {"name": v.name, "country": v.country, "alert_level": v.alert_level, f"distance_{unit}": _dist(v, mi), "url": v.url}
            for v in data.values()
            if ALERT_SEVERITY.get((v.alert_level or "").upper(), 0) >= 4
        ]
    }


BINARY_SENSOR_DESCRIPTIONS: tuple[VolcanoBinarySensorDescription, ...] = (
    VolcanoBinarySensorDescription(
        key=BINARY_SENSOR_ACTIVITY_NEARBY, translation_key=BINARY_SENSOR_ACTIVITY_NEARBY,
        icon="mdi:volcano", device_class=BinarySensorDeviceClass.SAFETY,
        is_on_fn=_activity_nearby, attributes_fn=_nearby_attrs,
    ),
    VolcanoBinarySensorDescription(
        key=BINARY_SENSOR_ELEVATED_NEARBY, translation_key=BINARY_SENSOR_ELEVATED_NEARBY,
        icon="mdi:volcano-outline", device_class=BinarySensorDeviceClass.SAFETY,
        is_on_fn=_elevated_nearby, attributes_fn=_nearby_attrs,
    ),
    VolcanoBinarySensorDescription(
        key=BINARY_SENSOR_WARNING_GLOBAL, translation_key=BINARY_SENSOR_WARNING_GLOBAL,
        icon="mdi:alert", device_class=BinarySensorDeviceClass.SAFETY,
        is_on_fn=_warning_global, attributes_fn=_warning_attrs,
    ),
)


async def async_setup_entry(hass, entry, async_add_entities):
    coordinator: VolcanoWorldCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(VolcanoBinarySensor(coordinator, entry, d) for d in BINARY_SENSOR_DESCRIPTIONS)


class VolcanoBinarySensor(CoordinatorEntity[VolcanoWorldCoordinator], BinarySensorEntity):
    _attr_has_entity_name = True
    _attr_attribution     = ATTRIBUTION
    entity_description: VolcanoBinarySensorDescription

    def __init__(self, coordinator, entry, description):
        super().__init__(coordinator)
        self.entity_description = description
        self._entry             = entry
        self._attr_unique_id    = f"{entry.entry_id}_{description.key}"

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
    def is_on(self) -> bool | None:
        if not self.coordinator.data:
            return None
        return self.entity_description.is_on_fn(
            self.coordinator.data, {**self._entry.data, **self._entry.options}
        )

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        attrs: dict[str, Any] = {"attribution": ATTRIBUTION}
        if not self.coordinator.data or not self.entity_description.attributes_fn:
            return attrs
        attrs.update(self.entity_description.attributes_fn(
            self.coordinator.data, {**self._entry.data, **self._entry.options}
        ))
        return attrs
