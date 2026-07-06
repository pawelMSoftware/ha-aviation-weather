"""Tests for the weather platform setup (weather.py: async_setup_entry)."""

from __future__ import annotations

from unittest.mock import MagicMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aviation_weather.const import CONF_AIRPORT, DOMAIN
from custom_components.aviation_weather.weather import async_setup_entry
from custom_components.aviation_weather.weather_entity import AviationWeatherEntity


async def test_creates_a_single_weather_entity_for_the_airport(hass) -> None:
    """async_setup_entry always creates exactly one weather entity,
    unlike the optional detail sensors which require opting in."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_AIRPORT: "EPWA"},
    )
    entry.add_to_hass(hass)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "metar_coordinator": MagicMock(),
    }

    async_add_entities = MagicMock()

    await async_setup_entry(hass, entry, async_add_entities)

    entities = async_add_entities.call_args[0][0]

    assert len(entities) == 1
    assert isinstance(entities[0], AviationWeatherEntity)
    assert entities[0].unique_id == "EPWA_weather"
