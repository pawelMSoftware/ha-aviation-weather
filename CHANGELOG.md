# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Fixed

- `binary_sensor.<fir>_sigmet` (and the optional SIGMET detail sensors)
  now flip state exactly when a SIGMET's validity window ends, instead
  of staying stuck at the last polled value until the next scheduled
  refresh (up to the full poll interval later). Uses
  `async_track_point_in_utc_time` to wake up entities at the nearest
  upcoming expiry — no extra API calls, no shortened poll interval.
- A single malformed SIGMET record from the API (e.g. an unparseable or
  missing validity timestamp) no longer discards the entire batch for a
  FIR. It's now logged as a warning and skipped, while every other
  valid SIGMET in the same response is still processed normally.
- Every SIGMET was silently being skipped as "malformed" because the
  mapper parsed `validTimeFrom`/`validTimeTo` as ISO 8601 strings, but
  the isigmet API actually returns them as Unix timestamps (matching
  the TAF mapper's handling of the same field names). SIGMETs are now
  mapped correctly again.
- The continent step of "Add airport" showed a raw code (e.g. `EU`)
  instead of a translated name, because the translation files used
  lowercase option keys (`eu`) while the actual continent values are
  uppercase (`EU`) — the frontend's selector-label lookup is exact and
  case-sensitive, so the mismatch fell back to the raw code.

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
