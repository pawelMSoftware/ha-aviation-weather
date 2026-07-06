"""Aviation Weather integration."""

from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    AIRPORT_PLATFORMS,
    CONF_ENTRY_TYPE,
    CONF_FIR,
    CONF_METAR_INTERVAL,
    CONF_SIGMET_INTERVAL,
    CONF_TAF_INTERVAL,
    DOMAIN,
    ENTRY_TYPE_AIRPORT,
    ENTRY_TYPE_FIR,
    FIR_PLATFORMS,
    METAR_INTERVAL_DEFAULT,
    SIGMET_INTERVAL_DEFAULT,
    TAF_INTERVAL_DEFAULT,
)
from .firs import get_fir
from .helpers import get_entry_value
from .metar import (
    MetarApiClient,
    MetarCoordinator,
)
from .sigmet import (
    SigmetApiClient,
    SigmetCoordinator,
)
from .taf import (
    TafApiClient,
    TafCoordinator,
)


async def async_setup(
    hass: HomeAssistant,
    config: dict,
) -> bool:
    """Set up Aviation Weather."""
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up Aviation Weather from a config entry.

    Dispatches to the appropriate setup function based on entry_type:
    - ENTRY_TYPE_AIRPORT: METAR/TAF coordinators + sensor/weather platforms
    - ENTRY_TYPE_FIR: SIGMET coordinator + binary_sensor/sensor platforms

    Entries created before CONF_ENTRY_TYPE was introduced default to
    ENTRY_TYPE_AIRPORT for backward compatibility.
    """
    hass.data.setdefault(
        DOMAIN,
        {},
    )

    entry_type = entry.data.get(
        CONF_ENTRY_TYPE,
        ENTRY_TYPE_AIRPORT,
    )

    if entry_type == ENTRY_TYPE_AIRPORT:
        return await _setup_airport_entry(hass, entry)

    if entry_type == ENTRY_TYPE_FIR:
        return await _setup_fir_entry(hass, entry)

    return False


async def _setup_airport_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up a single airport entry (METAR + TAF coordinators)."""
    entry.async_on_unload(
        entry.add_update_listener(
            update_listener,
        ),
    )

    session = async_get_clientsession(hass)

    metar_interval = timedelta(
        minutes=get_entry_value(
            entry,
            CONF_METAR_INTERVAL,
            METAR_INTERVAL_DEFAULT,
        ),
    )

    metar_coordinator = MetarCoordinator(
        hass=hass,
        entry=entry,
        client=MetarApiClient(session),
        update_interval=metar_interval,
    )

    await metar_coordinator.async_first_refresh()

    taf_interval = timedelta(
        minutes=get_entry_value(
            entry,
            CONF_TAF_INTERVAL,
            TAF_INTERVAL_DEFAULT,
        ),
    )

    taf_coordinator = TafCoordinator(
        hass=hass,
        entry=entry,
        client=TafApiClient(session),
        update_interval=taf_interval,
    )

    await taf_coordinator.async_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "entry_type": ENTRY_TYPE_AIRPORT,
        "metar_coordinator": metar_coordinator,
        "taf_coordinator": taf_coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(
        entry,
        AIRPORT_PLATFORMS,
    )

    return True


async def _setup_fir_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up a single FIR entry.

    Creates the FIR device in Home Assistant so it appears in the
    Devices list with model "FIR", sets up the SIGMET coordinator, and
    forwards to FIR_PLATFORMS (binary_sensor for the main SIGMET
    entity, sensor for the optional detail entities).
    """
    entry.async_on_unload(
        entry.add_update_listener(
            update_listener,
        ),
    )

    fir_icao = entry.data.get(CONF_FIR, "")
    fir = get_fir(fir_icao)

    device_registry = dr.async_get(hass)
    device_registry.async_get_or_create(
        config_entry_id=entry.entry_id,
        identifiers={(DOMAIN, fir_icao)},
        name=fir_icao,
        manufacturer="NOAA",
        model="FIR",
    )

    session = async_get_clientsession(hass)

    sigmet_interval = timedelta(
        minutes=get_entry_value(
            entry,
            CONF_SIGMET_INTERVAL,
            SIGMET_INTERVAL_DEFAULT,
        ),
    )

    sigmet_coordinator = SigmetCoordinator(
        hass=hass,
        entry=entry,
        client=SigmetApiClient(session),
        update_interval=sigmet_interval,
    )

    await sigmet_coordinator.async_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = {
        "entry_type": ENTRY_TYPE_FIR,
        "fir_icao": fir_icao,
        "fir_name": fir.name,
        "sigmet_coordinator": sigmet_coordinator,
    }

    await hass.config_entries.async_forward_entry_setups(
        entry,
        FIR_PLATFORMS,
    )

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload Aviation Weather."""
    entry_type = (
        hass.data.get(DOMAIN, {})
        .get(
            entry.entry_id,
            {},
        )
        .get(
            "entry_type",
            ENTRY_TYPE_AIRPORT,
        )
    )

    if entry_type == ENTRY_TYPE_AIRPORT:
        unload_ok = await hass.config_entries.async_unload_platforms(
            entry,
            AIRPORT_PLATFORMS,
        )
    else:
        unload_ok = await hass.config_entries.async_unload_platforms(
            entry,
            FIR_PLATFORMS,
        )

    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(
            entry.entry_id,
            None,
        )

    return unload_ok


async def update_listener(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Handle options update."""
    await hass.config_entries.async_reload(
        entry.entry_id,
    )


async def async_migrate_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Migrate config entry to the current version.

    Version 1.1 — normalise entry titles to "ICAO — Name" format for
    both airport and FIR entries so the integration list looks consistent.
    No data or options fields are changed.
    """
    from .airports import AIRPORTS  # noqa: PLC0415

    if entry.version == 1 and entry.minor_version == 0:
        entry_type = entry.data.get(CONF_ENTRY_TYPE, ENTRY_TYPE_AIRPORT)

        if entry_type == ENTRY_TYPE_AIRPORT:
            airport_icao = entry.data.get("airport", "")
            airport = AIRPORTS.get(airport_icao)
            if airport:
                new_title = f"{airport_icao} — {airport.name}"
                hass.config_entries.async_update_entry(
                    entry,
                    title=new_title,
                    minor_version=1,
                )

        elif entry_type == ENTRY_TYPE_FIR:
            fir_icao = entry.data.get(CONF_FIR, "")
            fir = get_fir(fir_icao)
            new_title = f"{fir_icao} — {fir.name}" if fir.name != fir_icao else fir_icao
            hass.config_entries.async_update_entry(
                entry,
                title=new_title,
                minor_version=1,
            )

    return True
