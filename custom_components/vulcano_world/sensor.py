"""Sensor platform for Volcano World.

Sensors:
  sensor.volcano_world_active_volcanoes
  sensor.volcano_world_in_weekly_report
  sensor.volcano_world_elevated_alert_volcanoes
  sensor.volcano_world_highest_alert_level
  sensor.volcano_world_nearby_active_volcanoes
  sensor.volcano_world_closest_active_volcano
  sensor.volcano_world_most_dangerous_volcano
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    ALERT_SEVERITY,
    ATTRIBUTION,
    CONF_LOCATION_MODE,
    CONF_RADIUS_KM,
    CONF_UNIT,
    DEFAULT_RADIUS_KM,
    DEFAULT_UNIT,
    DOMAIN,
    KM_TO_MI,
    LOCATION_MODE_WORLD,
    SENSOR_ACTIVE_COUNT,
    SENSOR_CLOSEST_VOLCANO,
    SENSOR_ELEVATED_COUNT,
    SENSOR_HIGHEST_ALERT,
    SENSOR_MOST_DANGEROUS,
    SENSOR_NEARBY_COUNT,
    SENSOR_WEEKLY_REPORT_COUNT,
    UNIT_MI,
)
from .coordinator import VolcanoWorldCoordinator, VolcanoData


@dataclass(frozen=True, kw_only=True)
class VolcanoSensorDescription(SensorEntityDescription):
    value_fn:      Callable[[dict[str, VolcanoData], dict[str, Any]], Any]
    attributes_fn: Callable[[dict[str, VolcanoData], dict[str, Any]], dict[str, Any]] | None = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _dist(v: VolcanoData, use_mi: bool) -> float | None:
    if v.distance_km is None:
        return None
    return round(v.distance_km * KM_TO_MI, 1) if use_mi else v.distance_km

def _unit_label(cfg: dict) -> str:
    return UNIT_MI if cfg.get(CONF_UNIT, DEFAULT_UNIT) == UNIT_MI else "km"

def _radius_km(cfg: dict) -> float:
    return float(cfg.get(CONF_RADIUS_KM, DEFAULT_RADIUS_KM))


# ── Value functions ───────────────────────────────────────────────────────────

def _active_count(data, cfg):    return len(data)
def _weekly_count(data, cfg):    return sum(1 for v in data.values() if v.in_weekly_report)
def _elevated_count(data, cfg):  return sum(1 for v in data.values() if ALERT_SEVERITY.get((v.alert_level or "").upper(), 0) >= 2)

def _highest_alert(data, cfg):
    if not data:
        return "NONE"
    return max(data.values(), key=lambda v: ALERT_SEVERITY.get((v.alert_level or "").upper(), 0)).alert_level or "UNASSIGNED"

def _nearby_count(data, cfg):
    radius_km = _radius_km(cfg)
    return sum(1 for v in data.values() if v.has_coordinates and v.distance_km is not None and v.distance_km <= radius_km)

def _closest_name(data, cfg):
    c = [v for v in data.values() if v.has_coordinates and v.distance_km is not None]
    return min(c, key=lambda v: v.distance_km).name if c else None   # type: ignore[arg-type]

def _most_dangerous_name(data, cfg):
    if not data:
        return None
    return max(data.values(), key=lambda v: ALERT_SEVERITY.get((v.alert_level or "").upper(), 0)).name


# ── Attribute functions ───────────────────────────────────────────────────────

def _active_attrs(data, cfg):
    use_mi = cfg.get(CONF_UNIT, DEFAULT_UNIT) == UNIT_MI
    unit   = _unit_label(cfg)
    return {
        "volcanoes": [
            {
                "name":             v.name,
                "country":          v.country,
                "alert_level":      v.alert_level,
                "in_weekly_report": v.in_weekly_report,
                f"distance_{unit}": _dist(v, use_mi),
            }
            for v in sorted(data.values(), key=lambda x: ALERT_SEVERITY.get((x.alert_level or "").upper(), 0), reverse=True)
        ],
        "location_mode": cfg.get(CONF_LOCATION_MODE, LOCATION_MODE_WORLD),
    }

def _nearby_attrs(data, cfg):
    use_mi    = cfg.get(CONF_UNIT, DEFAULT_UNIT) == UNIT_MI
    unit      = _unit_label(cfg)
    radius_km = _radius_km(cfg)
    radius_d  = round(radius_km * KM_TO_MI, 1) if use_mi else radius_km
    return {
        "nearby_volcanoes": [
            {
                "name":             v.name,
                "country":          v.country,
                f"distance_{unit}": _dist(v, use_mi),
                "alert_level":      v.alert_level,
                "url":              v.url,
            }
            for v in sorted(
                (v for v in data.values() if v.has_coordinates and v.distance_km is not None and v.distance_km <= radius_km),
                key=lambda x: x.distance_km or 9999,
            )
        ],
        f"radius_{unit}": radius_d,
    }

def _closest_attrs(data, cfg):
    use_mi = cfg.get(CONF_UNIT, DEFAULT_UNIT) == UNIT_MI
    unit   = _unit_label(cfg)
    c      = [v for v in data.values() if v.has_coordinates and v.distance_km is not None]
    if not c:
        return {}
    v = min(c, key=lambda x: x.distance_km)   # type: ignore[arg-type]
    return {
        f"distance_{unit}": _dist(v, use_mi),
        "country":          v.country,
        "alert_level":      v.alert_level,
        "aviation_color":   v.aviation_color,
        "volcano_type":     v.volcano_type,
        "eruption_start":   v.eruption_start,
        "in_weekly_report": v.in_weekly_report,
        "url":              v.url,
    }

def _dangerous_attrs(data, cfg):
    if not data:
        return {}
    use_mi = cfg.get(CONF_UNIT, DEFAULT_UNIT) == UNIT_MI
    unit   = _unit_label(cfg)
    v = max(data.values(), key=lambda x: ALERT_SEVERITY.get((x.alert_level or "").upper(), 0))
    return {
        "alert_level":      v.alert_level,
        "aviation_color":   v.aviation_color,
        "country":          v.country,
        f"distance_{unit}": _dist(v, use_mi),
        "volcano_type":     v.volcano_type,
        "eruption_start":   v.eruption_start,
        "in_weekly_report": v.in_weekly_report,
        "url":              v.url,
    }


# ── Descriptions ──────────────────────────────────────────────────────────────

SENSOR_DESCRIPTIONS: tuple[VolcanoSensorDescription, ...] = (
    VolcanoSensorDescription(
        key=SENSOR_ACTIVE_COUNT,        translation_key=SENSOR_ACTIVE_COUNT,
        icon="mdi:volcano",             native_unit_of_measurement="volcanoes",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_active_count,         attributes_fn=_active_attrs,
    ),
    VolcanoSensorDescription(
        key=SENSOR_WEEKLY_REPORT_COUNT, translation_key=SENSOR_WEEKLY_REPORT_COUNT,
        icon="mdi:clipboard-text-clock", native_unit_of_measurement="volcanoes",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_weekly_count,
    ),
    VolcanoSensorDescription(
        key=SENSOR_ELEVATED_COUNT,      translation_key=SENSOR_ELEVATED_COUNT,
        icon="mdi:alert-rhombus",       native_unit_of_measurement="volcanoes",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_elevated_count,
    ),
    VolcanoSensorDescription(
        key=SENSOR_HIGHEST_ALERT,       translation_key=SENSOR_HIGHEST_ALERT,
        icon="mdi:shield-alert",
        value_fn=_highest_alert,
    ),
    VolcanoSensorDescription(
        key=SENSOR_NEARBY_COUNT,        translation_key=SENSOR_NEARBY_COUNT,
        icon="mdi:map-marker-radius",   native_unit_of_measurement="volcanoes",
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=_nearby_count,         attributes_fn=_nearby_attrs,
    ),
    VolcanoSensorDescription(
        key=SENSOR_CLOSEST_VOLCANO,     translation_key=SENSOR_CLOSEST_VOLCANO,
        icon="mdi:map-marker-distance",
        value_fn=_closest_name,         attributes_fn=_closest_attrs,
    ),
    VolcanoSensorDescription(
        key=SENSOR_MOST_DANGEROUS,      translation_key=SENSOR_MOST_DANGEROUS,
        icon="mdi:skull-outline",
        value_fn=_most_dangerous_name,  attributes_fn=_dangerous_attrs,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: VolcanoWorldCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(VolcanoSensor(coordinator, entry, d) for d in SENSOR_DESCRIPTIONS)


class VolcanoSensor(CoordinatorEntity[VolcanoWorldCoordinator], SensorEntity):
    _attr_has_entity_name = True
    _attr_attribution     = ATTRIBUTION
    entity_description: VolcanoSensorDescription

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
    def native_value(self) -> Any:
        if not self.coordinator.data:
            return None
        return self.entity_description.value_fn(
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
