# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-07-06

First release.

### Added

- METAR sensor (`sensor.<icao>_metar`) — flight category and full raw
  report, always created for every configured airport.
- Optional METAR detail sensors (temperature, dew point, pressure,
  wind, visibility, weather phenomena, cloud layers, and more).
- Optional TAF forecast sensor (`sensor.<icao>_taf`).
- Native `weather.*` entity driven by live METAR data, with day/night
  condition awareness.
- Config flow: continent → country → airport selection, with
  nearest-airport suggestion based on Home Assistant's configured
  location.
- FIR (Flight Information Region) device creation, offered automatically
  when adding an airport with a mapped FIR.
- 863 European airports across 45 countries, generated from public
  OurAirports/aviationweather.gov/Eurocontrol data.
- **SIGMET support for FIR devices**: `binary_sensor.<fir>_sigmet` — on
  when at least one SIGMET is currently active for the FIR, with
  `active_count`, `hazards`, `valid_until`, and full per-SIGMET details
  (hazard, qualifier, base/top altitude, validity window, coordinates,
  raw text) as attributes.
- Optional SIGMET detail sensors, enabled per-FIR in options:
  `sensor.<fir>_sigmet_count`, `sensor.<fir>_sigmet_valid_until`,
  `sensor.<fir>_sigmet_hazards`.
- Configurable SIGMET refresh interval per FIR (5–60 min, default 15 min).
- FIR entries have their own **Configure** options, including
  retroactively adding a FIR device to an airport that declined it at
  setup time.
- `AirspaceAdvisory` shared base model and `active_advisories()` helper,
  laying the groundwork for future AIRMET support without reworking
  SIGMET.
- Airport entries can be **reconfigured** (change country/airport) from
  the entry's menu, without deleting and re-adding it.
- A **Repairs** issue is raised when METAR or SIGMET data has failed to
  update for several continuous hours (a real connectivity problem),
  separate from — and not confused with — an airport simply having no
  current report or a FIR having no active SIGMET, both of which are
  normal.
- Ready-to-import **automation blueprints** for every example in the
  README's "Automations" section (`blueprints/automation/aviation_weather/`).
- Per-flight-category icon on the METAR sensor, and on/off icons on the
  SIGMET binary sensor (`icons.json`).

### Changed

- Config-entry title normalization (`ICAO — Name`) applies uniformly to
  both airport and FIR entries (schema migration v1.0 → v1.1).

[1.0.0]: https://github.com/pawelMSoftware/ha-aviation-weather/releases/tag/v1.0.0
