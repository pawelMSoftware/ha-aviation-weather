"""Weather platform."""

from __future__ import annotations

from homeassistant.components.weather import WeatherEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_AIRPORT,
    DOMAIN,
)
from .helpers import get_entry_value
from .metar import MetarCoordinator
from .weather_entity import AviationWeatherEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the weather entity.

    Unlike the optional detail sensors, the weather entity is always
    created: it complements the existing METAR/TAF sensors rather than
    requiring an explicit opt-in, since it has no equivalent today and
    is what lets this airport show up in Home Assistant's native
    weather card.
    """

    metar_coordinator: MetarCoordinator = hass.data[DOMAIN][entry.entry_id][
        "metar_coordinator"
    ]

    airport_icao = get_entry_value(
        entry,
        CONF_AIRPORT,
    )

    entities: list[WeatherEntity] = [
        AviationWeatherEntity(
            coordinator=metar_coordinator,
            airport_icao=airport_icao,
        ),
    ]

    async_add_entities(
        entities,
    )
