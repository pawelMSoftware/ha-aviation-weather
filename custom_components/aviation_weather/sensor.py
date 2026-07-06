"""Sensor platform."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_AIRPORT,
    CONF_ENABLED_ENTITIES,
    CONF_FIR,
    DOMAIN,
    ENTRY_TYPE_FIR,
)
from .enums import AdditionalEntity, FirAdditionalEntity
from .helpers import get_entry_value
from .metar import (
    METAR_SENSORS,
    MetarCoordinator,
    MetarSensor,
    MetarSummarySensor,
)
from .sigmet import (
    SIGMET_SENSORS,
    FirSigmetSensor,
    SigmetCoordinator,
)
from .taf import (
    TafCoordinator,
    TafSummarySensor,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up sensors."""

    entry_data = hass.data[DOMAIN][entry.entry_id]

    if entry_data.get("entry_type") == ENTRY_TYPE_FIR:
        entities = _setup_fir_entities(entry, entry_data)
    else:
        entities = _setup_airport_entities(entry, entry_data)

    async_add_entities(
        entities,
    )


def _setup_airport_entities(
    entry: ConfigEntry,
    entry_data: dict,
) -> list[SensorEntity]:
    """Build sensor entities for an airport entry."""

    metar_coordinator: MetarCoordinator = entry_data["metar_coordinator"]
    taf_coordinator: TafCoordinator = entry_data["taf_coordinator"]

    airport_icao = get_entry_value(
        entry,
        CONF_AIRPORT,
    )

    entities: list[SensorEntity] = []

    enabled_entities: list[str] = get_entry_value(
        entry,
        CONF_ENABLED_ENTITIES,
        [],
    )

    entities.append(
        MetarSummarySensor(
            coordinator=metar_coordinator,
            airport_icao=airport_icao,
        ),
    )

    if AdditionalEntity.METAR_SENSORS.value in enabled_entities:
        for description in METAR_SENSORS:
            entities.append(
                MetarSensor(
                    coordinator=metar_coordinator,
                    description=description,
                    airport_icao=airport_icao,
                ),
            )

    if AdditionalEntity.TAF.value in enabled_entities:
        entities.append(
            TafSummarySensor(
                coordinator=taf_coordinator,
                airport_icao=airport_icao,
            ),
        )

    return entities


def _setup_fir_entities(
    entry: ConfigEntry,
    entry_data: dict,
) -> list[SensorEntity]:
    """Build sensor entities for a FIR entry.

    The main SIGMET entity is a binary_sensor (see binary_sensor.py);
    these are only the optional detail sensors, gated behind the
    sigmet_sensors option — same convention as METAR/TAF detail
    sensors for airports.
    """

    sigmet_coordinator: SigmetCoordinator = entry_data["sigmet_coordinator"]

    fir_icao = entry.data.get(CONF_FIR, "")

    enabled_entities: list[str] = get_entry_value(
        entry,
        CONF_ENABLED_ENTITIES,
        [],
    )

    entities: list[SensorEntity] = []

    if FirAdditionalEntity.SIGMET_SENSORS.value in enabled_entities:
        for description in SIGMET_SENSORS:
            entities.append(
                FirSigmetSensor(
                    coordinator=sigmet_coordinator,
                    description=description,
                    fir_icao=fir_icao,
                ),
            )

    return entities
