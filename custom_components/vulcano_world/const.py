"""Constants for Volcano World integration."""
from __future__ import annotations

DOMAIN = "volcano_world"
ATTRIBUTION = "Data from Smithsonian GVP & USGS Volcano Hazards Program"
DEFAULT_TITLE = "Volcano World"

# ── Config keys ───────────────────────────────────────────────────────────────
CONF_LOCATION_MODE    = "location_mode"
CONF_LATITUDE         = "latitude"
CONF_LONGITUDE        = "longitude"
CONF_RADIUS_KM        = "radius_km"        # always stored in km internally
CONF_UPDATE_INTERVAL  = "update_interval"
CONF_SOURCE_GVP       = "source_gvp"
CONF_SOURCE_USGS      = "source_usgs"
CONF_UNIT             = "unit"             # "km" or "mi"

# ── Location modes ────────────────────────────────────────────────────────────
LOCATION_MODE_HOME   = "home"
LOCATION_MODE_CUSTOM = "custom"
LOCATION_MODE_WORLD  = "world"

LOCATION_MODES: list[str] = [
    LOCATION_MODE_HOME,
    LOCATION_MODE_CUSTOM,
    LOCATION_MODE_WORLD,
]

# ── Units ─────────────────────────────────────────────────────────────────────
UNIT_KM   = "km"
UNIT_MI   = "mi"
KM_TO_MI  : float = 0.621371
MI_TO_KM  : float = 1.609344

# ── Defaults ──────────────────────────────────────────────────────────────────
DEFAULT_RADIUS_KM       : float = 500.0
DEFAULT_UPDATE_INTERVAL : int   = 60
MIN_UPDATE_INTERVAL     : int   = 15
MAX_UPDATE_INTERVAL     : int   = 1440
DEFAULT_SOURCE_GVP      : bool  = True
DEFAULT_SOURCE_USGS     : bool  = True
DEFAULT_UNIT            : str   = UNIT_KM

# Radius slider limits in each unit
RADIUS_MIN_KM : float = 50.0
RADIUS_MAX_KM : float = 20000.0
RADIUS_MIN_MI : float = 31.0
RADIUS_MAX_MI : float = 12500.0

# ── External URLs ─────────────────────────────────────────────────────────────
GVP_CURRENT_ERUPTIONS_URL = "https://volcano.si.edu/gvp_currenteruptions.cfm"
GVP_WEEKLY_REPORT_URL     = "https://volcano.si.edu/reports_weekly.cfm"
GVP_VOLCANO_URL           = "https://volcano.si.edu/volcano.cfm?vn={gvp_number}"
USGS_HANS_BASE_URL        = "https://volcanoes.usgs.gov/hans-public/api/volcano"

# ── Alert severity (higher = more dangerous) ──────────────────────────────────
ALERT_SEVERITY: dict[str, int] = {
    "RED":        4,
    "WARNING":    4,
    "ORANGE":     3,
    "WATCH":      3,
    "YELLOW":     2,
    "ADVISORY":   2,
    "GREEN":      1,
    "NORMAL":     1,
    "UNASSIGNED": 0,
    "":           0,
}

# ── Sensor keys ───────────────────────────────────────────────────────────────
SENSOR_ACTIVE_COUNT        = "active_count"
SENSOR_WEEKLY_REPORT_COUNT = "weekly_report_count"
SENSOR_ELEVATED_COUNT      = "elevated_count"
SENSOR_HIGHEST_ALERT       = "highest_alert"
SENSOR_NEARBY_COUNT        = "nearby_count"
SENSOR_CLOSEST_VOLCANO     = "closest_volcano"
SENSOR_MOST_DANGEROUS      = "most_dangerous_volcano"

# ── Binary sensor keys ────────────────────────────────────────────────────────
BINARY_SENSOR_ACTIVITY_NEARBY = "activity_nearby"
BINARY_SENSOR_ELEVATED_NEARBY = "elevated_nearby"
BINARY_SENSOR_WARNING_GLOBAL  = "warning_global"
