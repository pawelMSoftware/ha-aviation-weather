from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "aviation_weather"

CONF_COUNTRY = "country"
CONF_AIRPORT = "airport"
CONF_ENABLED_ENTITIES = "enabled_entities"
CONF_METAR_INTERVAL = "metar_interval"
CONF_TAF_INTERVAL = "taf_interval"

# Used only as a form field key during the config flow (continent ->
# country -> airport navigation). It is not stored on the config entry,
# since the integration only needs `country` and `airport` to operate.
CONF_CONTINENT = "continent"

# Distinguishes airport entries from FIR entries in config_entries.
# Stored in entry.data[CONF_ENTRY_TYPE]. Defaults to ENTRY_TYPE_AIRPORT
# for backward compatibility with existing entries that predate this field.
CONF_ENTRY_TYPE = "entry_type"
ENTRY_TYPE_AIRPORT = "airport"
ENTRY_TYPE_FIR = "fir"

# Key for the FIR ICAO code stored in FIR config entries.
CONF_FIR = "fir"

# METAR reports are issued every 30 minutes (routine) or more often
# when conditions change rapidly (SPECI). 10 minutes ensures we catch
# any SPECI quickly without hammering the API.
METAR_SCAN_INTERVAL = 600
METAR_INTERVAL_MIN = 5  # minutes
METAR_INTERVAL_MAX = 60  # minutes
METAR_INTERVAL_DEFAULT = 10  # minutes

# TAF forecasts are issued every 6 hours and cover 24-30 hours ahead.
# 30 minutes is more than sufficient to catch any amended TAF.
TAF_SCAN_INTERVAL = 1800
TAF_INTERVAL_MIN = 15  # minutes
TAF_INTERVAL_MAX = 120  # minutes
TAF_INTERVAL_DEFAULT = 30  # minutes

# SIGMETs are issued as needed (not on a fixed schedule) and are valid
# for a few hours; 15 minutes catches new/amended SIGMETs promptly
# without hammering the API.
CONF_SIGMET_INTERVAL = "sigmet_interval"
SIGMET_SCAN_INTERVAL = 900
SIGMET_INTERVAL_MIN = 5  # minutes
SIGMET_INTERVAL_MAX = 60  # minutes
SIGMET_INTERVAL_DEFAULT = 15  # minutes

# How long METAR/SIGMET must fail continuously before it's surfaced as
# a Repairs issue. A brief outage (a poll or two) is normal; several
# hours of continuous failure usually means a real connectivity
# problem or that an airport has stopped reporting. TAF is deliberately
# excluded — most airports never publish TAF at all, so a persistently
# failing TafCoordinator is normal, not anomalous, for most entries.
METAR_STALE_THRESHOLD_HOURS = 6
SIGMET_STALE_THRESHOLD_HOURS = 6

AIRPORT_PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.WEATHER,
]

FIR_PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.SENSOR,
]
