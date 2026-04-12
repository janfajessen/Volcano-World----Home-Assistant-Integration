<div align="center">
    
# 🌋 Volcano World 🌋 <br> Home Assistant Integration

<img src="https://github.com/janfajessen/Volcano-World/blob/76daa9ee24ca0d4b9e27bff34318d01607362da9/brands/logo%402x.png" alt="Volcano World" width="400">

![Version](https://img.shields.io/badge/version-1.5.24-blue?style=for-the-badge)
![HA](https://img.shields.io/badge/Home%20Assistant-2024.1+-orange?style=for-the-badge&logo=home-assistant)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python)
![HACS](https://img.shields.io/badge/HACS-Custom-41bdf5?style=for-the-badge)
[![Ko-Fi](https://img.shields.io/badge/Ko--Fi-Support-teal?style=for-the-badge&logo=ko-fi)](https://ko-fi.com/janfajessen)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Donate-yellow?style=for-the-badge&logo=buymeacoffee)](https://www.buymeacoffee.com/janfajessen)
[![Patreon](https://img.shields.io/badge/Patreon-Support-red?style=for-the-badge&logo=patreon)](https://www.patreon.com/janfajessen)
[![GitHub Sponsors](https://img.shields.io/badge/GitHub%20Sponsors-Support-pink?style=for-the-badge&logo=githubsponsors)](https://github.com/sponsors/janfajessen)


<!--[![PayPal](https://img.shields.io/badge/PayPal-Donate-blue?style=for-the-badge&logo=paypal)](https://paypal.me/janfajessen)-->

A Home Assistant integration that tracks active and erupting volcanoes worldwide. Every active volcano appears as a pin on the HA map. Sensors and binary sensors enable automations and dashboards.

</div>

**Data sources — no API key required:**
- 🏛️ [Smithsonian Global Volcanism Program (GVP)](https://volcano.si.edu) — global eruption database (~45 continuously active volcanoes)
- 🇺🇸 [USGS Volcano Hazards HANS API](https://volcanoes.usgs.gov) — official US alert levels (GREEN / YELLOW / ORANGE / RED)
---

## Features

| Feature | Detail |
|---|---|
| 🗺️ Map (GeoLocation) | Each active volcano as a `geo_location` entity, visible on the HA map card |
| 📍 Location filter | Home location, custom map point, or entire world |
| 📏 km / miles | Distance unit selectable during setup and in options |
| 📰 Weekly report text | Narrative description of activity for volcanoes in the weekly report |
| 🔄 Live data | Configurable update interval (15 min minimum) |
| ⚙️ Reconfigure | Gear icon changes all settings without restarting HA |
| 🌍 Built-in database | ~100 volcanoes with coordinates, country, and type |
| 🌐 Multilingual | CA · DE · EN · ES · FR · IT · PT · ... |

---

## Installation via HACS

1. Open HACS → **Integrations** → ⋮ → **Custom Repositories**
2. Add `https://github.com/janfajessen/volcano_world` as type **Integration**
3. Search **Volcano World** and install
4. Restart Home Assistant (first time only)
5. **Settings → Devices & Services → Add Integration → "Volcano World"**

<img src="https://raw.githubusercontent.com/janfajessen/Volcano-World----Home-Assistant-Integration/e884d2b81a68b9b99160982edcb07f35a255420c/Volcano_World.png" alt="Volcano World" width="100">

## Manual Installation

Copy the `volcano_world` folder into your `custom_components` directory:

```
config/
└── custom_components/
    └── volcano_world/
        ├── __init__.py
        ├── binary_sensor.py
        ├── config_flow.py
        ├── const.py
        ├── coordinator.py
        ├── geo_location.py
        ├── manifest.json
        ├── sensor.py
        ├── strings.json
        ├── volcano_data.py
        └── translations/
            ├── en.json
            ├── es.json
            ├── ca.json
            ├── de.json
            └── ...
```

---

## Configuration

### Step 1 — Location filter

| Mode | Description |
|---|---|
| **Home Assistant location** | Filters volcanoes within a radius of your HA `zone.home` coordinates |
| **Custom location** | Opens an interactive map — click anywhere to set the filter center |
| **Entire world** | Shows all ~45 currently active volcanoes worldwide, no filter |

### Step 2 — Advanced options

| Option | Default | Description |
|---|---|---|
| Distance unit | km | Choose **km** or **miles (mi)** — affects all distances in entities and attributes |
| Radius | 500 km / 311 mi | Maximum distance from the reference point (Home / Custom modes only) |
| Update interval | 60 min | How often data is fetched. Minimum 15 min |
| Smithsonian GVP | ✅ | Fetches the global current eruptions list |
| USGS HANS | ✅ | Enriches data with official US alert levels |

> All options are available from the **gear icon** after installation — no restart needed.

---

## Entities Created

### GeoLocation — Map entities

Each active volcano generates one `geo_location` entity visible on the HA map.

**Entity ID format:** `geo_location.volcano_world_etna`, `geo_location.volcano_world_stromboli`, etc.

To display them on a map card, add this to your dashboard:

```yaml
type: map
geo_location_sources:
  - volcano_world
```

**Available attributes on each geo_location entity:**

| Attribute | Example | Description |
|---|---|---|
| `country` | `Italy` | Country where the volcano is located |
| `alert_level` | `ORANGE` | USGS alert level: RED / ORANGE / YELLOW / GREEN / UNASSIGNED |
| `aviation_color` | `ORANGE` | Aviation color code from USGS |
| `eruption_start` | `2022 Nov 27` | Date the current eruption began (GVP data) |
| `volcano_type` | `Shield volcano` | Geological type |
| `in_weekly_report` | `true` | Appears in this week's GVP/USGS Weekly Volcanic Activity Report |
| `weekly_report_text` | `"Explosive activity continued..."` | Narrative description from the weekly report (English only, up to 600 chars). `null` if not in report |
| `data_source` | `gvp` | Which source provided this entry (`gvp` or `usgs`) |
| `gvp_number` | `211060` | Smithsonian GVP identifier |
| `url` | `https://volcano.si.edu/...` | Direct link to volcano profile page |
| `distance_km` or `distance_mi` | `1257.5` | Distance from your reference location in your chosen unit |

**Icon by alert level:**

| Alert | Icon | Meaning |
|---|---|---|
| 🔴 RED / WARNING | `mdi:volcano` | Major eruption, lava flows or strong explosions |
| 🟠 ORANGE / WATCH | `mdi:volcano-outline` | Eruption with moderate activity or elevated unrest |
| 🟡 YELLOW / ADVISORY | `mdi:alert-circle-outline` | Elevated unrest, gas emissions, minor activity |
| 🟢 GREEN / NORMAL / UNASSIGNED | `mdi:image-filter-hdr` | Background activity or no USGS alert assigned |

> **Note on UNASSIGNED:** USGS alert levels only cover volcanoes monitored by USGS (mainly US territory). Most GVP-sourced volcanoes (Etna, Stromboli, Indonesian volcanoes, etc.) show `UNASSIGNED` — this does **not** mean they are inactive. Use `in_weekly_report` and `weekly_report_text` to assess real-time activity for non-US volcanoes.

---

### Sensors

All sensor entity IDs follow the pattern `sensor.volcano_world_*`.

| Entity | Example state | Description |
|---|---|---|
| `sensor.volcano_world_active_volcanoes` | `45` | Total active volcanoes in the current dataset. Attribute `volcanoes` lists all with name, country, alert level, distance, and weekly report status |
| `sensor.volcano_world_in_weekly_report` | `26` | Volcanoes featured in the current Smithsonian/USGS Weekly Volcanic Activity Report (updated every Thursday) |
| `sensor.volcano_world_elevated_alert_volcanoes` | `3` | Volcanoes with alert level YELLOW or higher |
| `sensor.volcano_world_highest_alert_level` | `ORANGE` | Highest current alert level globally. Useful for conditional cards and automations |
| `sensor.volcano_world_nearby_active_volcanoes` | `0` | Active volcanoes within your configured radius. Attribute `nearby_volcanoes` lists them sorted by distance |
| `sensor.volcano_world_closest_active_volcano` | `Etna` | Name of the closest active volcano to your reference location. Attributes include distance, alert level, eruption start, and URL |
| `sensor.volcano_world_most_dangerous_volcano` | `Kilauea` | Name of the volcano with the highest current alert level. Attributes include alert level, country, distance, and URL |

---

### Binary Sensors

All binary sensor entity IDs follow the pattern `binary_sensor.volcano_world_*`.

| Entity | ON when... | Attributes |
|---|---|---|
| `binary_sensor.volcano_world_volcanic_activity_nearby` | Any active volcano is within your configured radius | `nearby_volcanoes` list sorted by distance, `radius_km` or `radius_mi` |
| `binary_sensor.volcano_world_elevated_volcano_nearby` | Any volcano with YELLOW+ alert is within your radius | Same as above, filtered to elevated only |
| `binary_sensor.volcano_world_global_volcano_warning` | Any volcano anywhere has RED or WARNING alert | `warning_volcanoes` list with name, country, alert level, distance |

All binary sensors use `device_class: safety`.

---

## Example Automations

### 1 — Alert for Spanish volcanoes (Teide / Cumbre Vieja)

```yaml
- alias: "Volcano World — Spanish volcano alert"
  triggers:
    - trigger: state
      entity_id:
        - geo_location.volcano_world_teide
        - geo_location.volcano_world_cumbre_vieja
  actions:
    - action: notify.telegram_jan
      data:
        title: "🌋 Spanish Volcano Alert"
        message: >
          {{ trigger.to_state.name }}
          — Alert: {{ state_attr(trigger.entity_id, 'alert_level') | default('UNASSIGNED') }}
          {% if state_attr(trigger.entity_id, 'in_weekly_report') %}| In weekly report ✅{% endif %}
          {% if state_attr(trigger.entity_id, 'weekly_report_text') %}
          {{ state_attr(trigger.entity_id, 'weekly_report_text') }}
          {% endif %}
          | {{ state_attr(trigger.entity_id, 'url') }}
```

### 2 — New volcano appears in active list

```yaml
- alias: "Volcano World — Active count increased (new activity)"
  triggers:
    - trigger: state
      entity_id: sensor.volcano_world_active_volcanoes
  conditions:
    - condition: template
      value_template: >
        {{ trigger.to_state.state | int(0) > trigger.from_state.state | int(0) }}
  actions:
    - action: notify.telegram_jan
      data:
        title: "🌋 New Volcanic Activity (+{{ trigger.to_state.state | int(0) - trigger.from_state.state | int(0) }})"
        message: >
          Active volcanoes: {{ trigger.from_state.state }} → {{ trigger.to_state.state }}
          {% set vlist = state_attr('sensor.volcano_world_active_volcanoes', 'volcanoes') %}
          {% if vlist %}
          {% for v in vlist[:5] %}• {{ v.name }} ({{ v.country }}) — {{ v.alert_level }}
          {% endfor %}
          {% if vlist | length > 5 %}...and {{ vlist | length - 5 }} more{% endif %}
          {% endif %}
```

### 3 — Volcanic activity within configured radius

```yaml
- alias: "Volcano World — Activity within radius"
  triggers:
    - trigger: state
      entity_id: binary_sensor.volcano_world_volcanic_activity_nearby
      to: "on"
  actions:
    - action: notify.telegram_jan
      data:
        title: "⚠️ Volcanic Activity Nearby"
        message: >
          {% set volcanoes = state_attr('binary_sensor.volcano_world_volcanic_activity_nearby', 'nearby_volcanoes') %}
          {% for v in volcanoes %}
          • {{ v.name }} ({{ v.country }}) — {{ v.distance_km }} km — {{ v.alert_level }}
          {% endfor %}
```

### 4 — Volcano within hardcoded 3000 km (template, any radius)

```yaml
- alias: "Volcano World — Volcano within 3000 km"
  triggers:
    - trigger: template
      value_template: >
        {% set ns = namespace(found=false) %}
        {% set vlist = state_attr('sensor.volcano_world_active_volcanoes', 'volcanoes') %}
        {% if vlist %}
          {% for v in vlist %}
            {% if v.distance_km is not none and v.distance_km | float(99999) <= 3000 %}
              {% set ns.found = true %}
            {% endif %}
          {% endfor %}
        {% endif %}
        {{ ns.found }}
  actions:
    - action: notify.telegram_jan
      data:
        title: "⚠️ Volcano within 3000 km"
        message: >
          {% set vlist = state_attr('sensor.volcano_world_active_volcanoes', 'volcanoes') %}
          {% for v in vlist if v.distance_km is not none and v.distance_km | float(99999) <= 3000 %}
          • {{ v.name }} ({{ v.country }}) — {{ v.distance_km }} km — {{ v.alert_level }}
          {% endfor %}
```

### 5 — Global RED / WARNING alert

```yaml
- alias: "Volcano World — Global RED alert"
  triggers:
    - trigger: state
      entity_id: binary_sensor.volcano_world_global_volcano_warning
      to: "on"
  actions:
    - action: notify.telegram_jan
      data:
        title: "🔴 GLOBAL VOLCANO WARNING"
        message: >
          {% set v = state_attr('binary_sensor.volcano_world_global_volcano_warning', 'warning_volcanoes') %}
          {% for vol in v %}
          🌋 {{ vol.name }} ({{ vol.country }}) — {{ vol.alert_level }}
          {% if vol.distance_km %}| {{ vol.distance_km }} km from home{% endif %}
          {% endfor %}
```

---


---

## Recommended Logger

Add to `configuration.yaml` to debug:

```yaml
logger:
  default: warning
  logs:
    custom_components.volcano_world: debug
```

---

## Translations

The integration UI is available in multiple languages.


[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Donate-yellow.svg?style=for-the-badge)](https://www.buymeacoffee.com/janfajessen)
[![Patreon](https://img.shields.io/badge/Patreon-Support-red.svg?style=for-the-badge)](https://www.patreon.com/janfajessen)

---

## Data & License

Eruption data provided by the [Smithsonian Institution Global Volcanism Program](https://volcano.si.edu) and the [USGS Volcano Hazards Program](https://volcanoes.usgs.gov). Both are US government / public-domain sources with no usage restrictions.

Integration code licensed under **MIT**. See [LICENSE](LICENSE).

---

*Volcano World is an independent community integration and is not affiliated with Smithsonian Institution or USGS.*
