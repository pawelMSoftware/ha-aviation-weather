# Aviation Weather

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-orange.svg?style=for-the-badge)](https://github.com/hacs/integration)

A Home Assistant integration providing real-time METAR, TAF, and SIGMET
weather data for European airports and their Flight Information Regions
(FIRs). Designed for pilots, aviation enthusiasts, or anyone living near an
airport who wants professional-grade weather observations.

## Features

### Weather entity (`weather.*`)

A native HA weather entity driven by live METAR data, with day/night
condition awareness — `clear-night` automatically replaces `sunny` after
sunset based on your Home Assistant location:

- Condition (sunny / clear-night / cloudy / rainy / snowy / etc.)
- Temperature and dew point
- Atmospheric pressure
- Wind speed, gust speed, and bearing
- Humidity (derived from temperature and dew point)
- Cloud coverage (%)

Works with the built-in weather card, voice assistants, and any automation
that uses a `weather.*` entity.

### Airport device — sensors always created

Every configured airport creates a device with the following sensors:

- **METAR** — flight category (`VFR` / `MVFR` / `IFR` / `LIFR`) and full raw
  report as entity state and attributes

### Airport device — optional sensors

Enabled per-airport in the integration's options:

- **METAR details** — individual sensors for temperature, dew point, pressure,
  sea-level pressure, wind speed, wind gust, wind direction, visibility,
  weather phenomena, cloud layers, METAR type, snow depth, vertical
  visibility, observation time
- **TAF forecast** — full TAF in entity attributes (raw text + parsed forecast
  periods)

### FIR device (Flight Information Region)

When you add an airport, the integration detects its FIR and offers to create
a separate FIR device. For example, adding Warsaw Chopin (EPWA) offers to
also create a device for **EPWW — Warszawa FIR**.

If you later add more airports from the same FIR (e.g. Gdańsk EPGD, Kraków
EPKK), the existing FIR device is reused automatically — no duplicates. If
you declined the FIR device when adding the airport, you can add it later
from that airport's **Configure** options without having to remove and
re-add it.

### FIR device — sensor always created

- **SIGMET** (`binary_sensor.<fir>_sigmet`) — `on` when there is at least
  one active SIGMET for the FIR, `off` otherwise. Attributes: `active_count`,
  `hazards` (unique hazard codes among active SIGMETs, e.g. `TURB`, `ICE`,
  `TS`, `MTW`, `DS`, `SS`, `VA`), `valid_until` (latest expiry among active
  SIGMETs), and `sigmets` (full details of every active SIGMET — hazard,
  qualifier, base/top altitude, validity window, coordinates, raw text).
  This is the entity to use in automations.

### FIR device — optional sensors

Enabled per-FIR in the integration's options:

- **SIGMET details** — individual sensors for the active SIGMET count
  (`sensor.<fir>_sigmet_count`), the latest valid-until time
  (`sensor.<fir>_sigmet_valid_until`), and the active hazards
  (`sensor.<fir>_sigmet_hazards`)

### General

- 863 European airports across 45 countries
- Short, predictable entity IDs based on ICAO code:
  `sensor.epgd_metar`, `weather.epgd`, `binary_sensor.epww_sigmet`
- Nearest-airport suggestion on first setup, based on your HA location
- Configurable polling intervals per airport/FIR (5–60 min for METAR,
  15–120 min for TAF, 5–60 min for SIGMET)

## Installation

### HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=pawelMSoftware&repository=ha-aviation-weather&category=integration)

1. Open HACS → **Custom repositories**
2. Add this repository URL, category **Integration**
3. Find "Aviation Weather" and install it
4. Restart Home Assistant

### Manual

Copy `custom_components/aviation_weather/` to your `config/custom_components/`
folder and restart Home Assistant.

## Configuration

1. **Settings → Devices & Services → Add Integration → Aviation Weather**
2. Select a continent (currently Europe only), then a country, then an airport.
   Your nearest airport is pre-selected.
3. If the selected airport has a mapped FIR, you will be asked whether to also
   create a FIR device. This is checked by default — uncheck only if you
   deliberately do not want SIGMET alerts for that FIR.

After setup, click **Configure** on any airport entry to adjust its options:

| Option | Default | Description |
|---|---|---|
| METAR details | off | Enable individual METAR parameter sensors |
| TAF forecast | off | Enable the TAF forecast sensor |
| METAR refresh interval | 10 min | How often to fetch current conditions (5–60 min) |
| TAF refresh interval | 30 min | How often to fetch the forecast (15–120 min) |

> The TAF option only appears for airports that publish TAF reports.
> 10 minutes is a good METAR default to catch unscheduled SPECI updates
> without hammering the API. If you declined the FIR device earlier, an
> **Add FIR device** checkbox appears here too.

Click **Configure** on any FIR entry to adjust its options:

| Option | Default | Description |
|---|---|---|
| SIGMET details | off | Enable the SIGMET count / valid-until / hazards sensors |
| SIGMET refresh interval | 15 min | How often to fetch SIGMET data (5–60 min) |

> The main SIGMET binary sensor (`binary_sensor.<fir>_sigmet`) is always
> created — SIGMET details only add extra, individually-addressable
> sensors on top of it.

### Changing an airport

Picked the wrong airport, or moved? Click **Reconfigure** on the airport
entry (the same three-dot menu as **Configure**) to pick a different
country/airport without deleting and re-adding the entry — its options
(enabled sensors, refresh intervals) and entity history are preserved.

## Troubleshooting

If an airport's METAR, or a FIR's SIGMET data, hasn't updated for several
hours, Aviation Weather raises a **Repair** (Settings → System → **Repairs**)
explaining the likely cause and pointing you at the logs. This is separate
from an airport simply having no current METAR report, or a FIR having no
active SIGMET — both of those are normal and don't raise a repair. The
issue clears itself automatically once data starts flowing again.

## Visibility

Visibility is read from the raw METAR string (not from the API's `visib`
field, which uses inconsistent units). The stored value is always in metres:

| METAR group | Stored value | Displayed as |
|---|---|---|
| `0500` | 500 m | `500 m` |
| `3500` | 3 500 m | `3.5 km` |
| `9999` | 10 000 m | `10+ km` |
| `CAVOK` | 10 000 m | `10+ km` |
| US statute miles | `None` | unavailable |

## Data sources

METAR, TAF, and SIGMET data is fetched from
[aviationweather.gov](https://aviationweather.gov/) (NOAA Aviation Weather
Center) — a free, public API with no key required.

The airport and FIR databases are generated from public data and committed to
the repository. See [`scripts/README.md`](scripts/README.md) for details.

## Roadmap

- **AIRMET alerts** on FIR devices, alongside SIGMET — the underlying data
  model (`AirspaceAdvisory`) and active-advisory filtering were built to be
  shared between SIGMET and AIRMET, so this is additive rather than a
  rewrite.
- **Forecast support** in `weather.*` entity (hourly/daily from TAF) —
  implementation exists but is disabled pending investigation of a
  discrepancy between tests and one real-world deployment.
- **Per-period TAF sensors** — individual sensors for each TAF forecast period.

## Automations

Every automation below is also available as a ready-to-import
[blueprint](blueprints/automation/aviation_weather/) — no copy-pasting YAML
required.

### Importing a blueprint

1. **Settings → Automations & Scenes → Blueprints → Import Blueprint**
2. Paste the blueprint's raw GitHub URL, e.g.
   `https://raw.githubusercontent.com/pawelMSoftware/ha-aviation-weather/main/blueprints/automation/aviation_weather/speci_alert.yaml`
3. **Preview** → **Import Blueprint**, then create an automation from it and
   fill in your entities (Settings → Automations & Scenes → **+ Add
   Automation** → pick the imported blueprint).

Blueprints ask for the relevant entities directly (via dropdowns) and a
`notify` target entity, instead of the ICAO-code templating the raw YAML
examples below use — pick whichever fits how you like to work.

### Alert on SPECI report

*Blueprint: [`speci_alert.yaml`](blueprints/automation/aviation_weather/speci_alert.yaml)*

When conditions change rapidly, the airport issues an unscheduled SPECI
instead of waiting for the next routine METAR (every 30 minutes).
`sensor.<icao>_metar_type` switches from `METAR` to `SPECI`.

> **Prerequisite:** enable **METAR details** in options — `metar_type` is
> part of that group.

```yaml
alias: "EPGD — Alert on SPECI report"
triggers:
  - trigger: state
    entity_id: sensor.epgd_metar_type
    to: "SPECI"
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: "⚠️ EPGD — Rapid weather change"
      message: >
        SPECI issued at {{ now().strftime('%H:%M') }}.
        Conditions: {{ states('weather.epgd') }},
        visibility {{ state_attr('sensor.epgd_metar', 'visibility') }},
        wind {{ state_attr('sensor.epgd_metar', 'wind_speed') }} kt
        {{ state_attr('sensor.epgd_metar', 'wind_direction') }}°.
        Raw: {{ state_attr('sensor.epgd_metar', 'raw_metar') }}
```

Replace `epgd` with your airport's ICAO code (lowercase).

### Alert on flight category change

*Blueprint: [`flight_category_alert.yaml`](blueprints/automation/aviation_weather/flight_category_alert.yaml)*

`sensor.<icao>_metar` always reports the current flight category. This
automation triggers when conditions drop below VFR — no extra sensors needed.

```yaml
alias: "EPGD — Alert on IFR / LIFR conditions"
triggers:
  - trigger: state
    entity_id: sensor.epgd_metar
    to:
      - "IFR"
      - "LIFR"
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: "🔴 EPGD — {{ states('sensor.epgd_metar') }} conditions"
      message: >
        Flight category dropped to {{ states('sensor.epgd_metar') }}
        at {{ now().strftime('%H:%M') }}.
        Raw: {{ state_attr('sensor.epgd_metar', 'raw_metar') }}
```

Flight category definitions:

| Category | Ceiling | Visibility |
|---|---|---|
| VFR | > 3 000 ft | > 5 sm |
| MVFR | 1 000–3 000 ft | 3–5 sm |
| IFR | 500–999 ft | 1–3 sm |
| LIFR | < 500 ft | < 1 sm |

### Alert on strong wind or gusts

*Blueprint: [`wind_gust_alert.yaml`](blueprints/automation/aviation_weather/wind_gust_alert.yaml)*

> **Prerequisite:** enable **METAR details** in options.

```yaml
alias: "EPGD — Alert on strong gusts"
triggers:
  - trigger: numeric_state
    entity_id: sensor.epgd_wind_gust
    above: 25
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: "💨 EPGD — Strong gusts"
      message: >
        Wind gust {{ states('sensor.epgd_wind_gust') }} kt
        (wind {{ states('sensor.epgd_wind_speed') }} kt
        from {{ states('sensor.epgd_wind_direction') }}°)
        at {{ now().strftime('%H:%M') }}.
```

Values are in knots. 25 kt ≈ 46 km/h, 30 kt ≈ 56 km/h.

### Alert on active SIGMET

*Blueprint: [`sigmet_active_alert.yaml`](blueprints/automation/aviation_weather/sigmet_active_alert.yaml)*

`binary_sensor.<fir>_sigmet` turns `on` when a FIR has at least one active
SIGMET. The `hazards` attribute lists the unique hazard codes currently in
effect (e.g. `TURB`, `ICE`, `TS`, `MTW`, `DS`, `SS`, `VA`).

```yaml
alias: "EPWW — Alert on active SIGMET"
triggers:
  - trigger: state
    entity_id: binary_sensor.epww_sigmet
    to: "on"
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: "⚠️ EPWW — Active SIGMET"
      message: >
        {{ state_attr('binary_sensor.epww_sigmet', 'active_count') }}
        active SIGMET(s): {{ state_attr('binary_sensor.epww_sigmet', 'hazards')
        | join(', ') }}.
        Valid until {{ state_attr('binary_sensor.epww_sigmet', 'valid_until') }}.
```

Replace `epww` with your FIR's ICAO code (lowercase).

### Alert on a specific SIGMET hazard (e.g. icing)

*Blueprint: [`sigmet_hazard_alert.yaml`](blueprints/automation/aviation_weather/sigmet_hazard_alert.yaml)*

If you only care about certain hazards — icing before a flight, say — match
against the `hazards` attribute with a template trigger instead of reacting
to every SIGMET.

```yaml
alias: "EPWW — Alert on icing SIGMET"
triggers:
  - trigger: template
    value_template: >
      {{ "ICE" in (state_attr("binary_sensor.epww_sigmet", "hazards") or []) }}
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: "🧊 EPWW — Icing SIGMET"
      message: >
        Icing SIGMET active for EPWW.
        Valid until {{ state_attr('binary_sensor.epww_sigmet', 'valid_until') }}.
```

Common hazard codes: `TS` (thunderstorm), `TURB` (turbulence), `ICE` (icing),
`VA` (volcanic ash), `MTW` (mountain wave), `DS`/`SS` (dust/sand storm).

### Notify when a SIGMET clears

*Blueprint: [`sigmet_cleared_alert.yaml`](blueprints/automation/aviation_weather/sigmet_cleared_alert.yaml)*

The counterpart to "Alert on active SIGMET" — trigger on the binary sensor
turning back `off` to know when the airspace is clear again.

```yaml
alias: "EPWW — SIGMET cleared"
triggers:
  - trigger: state
    entity_id: binary_sensor.epww_sigmet
    to: "off"
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: "✅ EPWW — SIGMET cleared"
      message: "No active SIGMET for EPWW anymore."
```

### Alert when multiple SIGMETs are active

*Blueprint: [`sigmet_count_alert.yaml`](blueprints/automation/aviation_weather/sigmet_count_alert.yaml)*

> **Prerequisite:** enable **SIGMET details** in the FIR's options —
> `sigmet_count` and `sigmet_hazards` are part of that group.

```yaml
alias: "EPWW — Multiple active SIGMETs"
triggers:
  - trigger: numeric_state
    entity_id: sensor.epww_sigmet_count
    above: 1
actions:
  - action: notify.mobile_app_your_phone
    data:
      title: "⚠️ EPWW — Multiple SIGMETs active"
      message: >
        {{ states('sensor.epww_sigmet_count') }} SIGMETs currently active
        for EPWW: {{ states('sensor.epww_sigmet_hazards') }}.
```

## Contributing

Issues and pull requests are welcome — see [`CONTRIBUTING.md`](CONTRIBUTING.md)
for dev setup, test/lint commands, and PR expectations. See
[`CHANGELOG.md`](CHANGELOG.md) for release history, and
[`RELEASING.md`](RELEASING.md) for the maintainer release process.

## License

[MIT](LICENSE)
