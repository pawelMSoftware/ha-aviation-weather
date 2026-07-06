from __future__ import annotations

from homeassistant.components import system_health
from homeassistant.core import HomeAssistant, callback

from .const import CONF_ENTRY_TYPE, DOMAIN, ENTRY_TYPE_AIRPORT, ENTRY_TYPE_FIR


@callback
def async_register(
    hass: HomeAssistant,
    register: system_health.SystemHealthRegistration,
) -> None:
    """Register system health callbacks.

    Must be a plain, synchronous function decorated with @callback, not
    `async def`: Home Assistant core's integration platform loader
    (homeassistant.components.system_health._register_system_health_platform)
    calls this without awaiting it. An `async def` version here returns
    an un-awaited coroutine object that never actually runs, silently
    skipping registration and raising
    "RuntimeWarning: coroutine 'async_register' was never awaited" at
    startup — this mirrors the synchronous pattern used by every
    built-in HA integration's system_health.py (e.g. accuweather).
    """

    register.async_register_info(
        system_health_info,
    )


async def system_health_info(
    hass: HomeAssistant,
) -> dict[str, object]:
    """Return system health information."""

    entries = hass.config_entries.async_entries(DOMAIN)

    metar = 0
    taf = 0
    sigmet = 0
    airports = 0
    firs = 0

    for entry in entries:
        # entry.data (the entry's own stored type) is used for the
        # configured_* counts so they reflect what's configured even
        # before/without a successful setup — matching the pre-SIGMET
        # behavior for airport entries, where configured_airports
        # counted entries regardless of runtime state.
        entry_type = entry.data.get(CONF_ENTRY_TYPE, ENTRY_TYPE_AIRPORT)

        if entry_type == ENTRY_TYPE_AIRPORT:
            airports += 1
        elif entry_type == ENTRY_TYPE_FIR:
            firs += 1

        data = hass.data.get(DOMAIN, {}).get(entry.entry_id)

        if not data:
            continue

        if entry_type == ENTRY_TYPE_AIRPORT:
            # metar_coordinator and taf_coordinator are always created
            # together in _setup_airport_entry, so a single presence
            # check on `data` is sufficient — there's no real state
            # where one exists without the other.
            metar += 1
            taf += 1
        elif entry_type == ENTRY_TYPE_FIR:
            sigmet += 1

    return {
        "configured_airports": airports,
        "metar_coordinators": metar,
        "taf_coordinators": taf,
        "configured_firs": firs,
        "sigmet_coordinators": sigmet,
    }
