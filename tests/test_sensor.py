"""Tests for the sensor platform setup (sensor.py: async_setup_entry)."""

from __future__ import annotations

from unittest.mock import MagicMock

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aviation_weather.const import (
    CONF_AIRPORT,
    CONF_ENABLED_ENTITIES,
    DOMAIN,
)
from custom_components.aviation_weather.enums import AdditionalEntity
from custom_components.aviation_weather.metar.sensor import (
    METAR_SENSORS,
    MetarSensor,
    MetarSummarySensor,
)
from custom_components.aviation_weather.sensor import async_setup_entry
from custom_components.aviation_weather.taf.sensor import TafSummarySensor


def _make_entry(hass, *, enabled_entities: list[str] | None = None) -> MockConfigEntry:
    """Build a config entry wired up with mock coordinators in hass.data."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_AIRPORT: "EPWA"},
        options={CONF_ENABLED_ENTITIES: enabled_entities or []},
    )
    entry.add_to_hass(hass)

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "metar_coordinator": MagicMock(),
        "taf_coordinator": MagicMock(),
    }

    return entry


class TestAsyncSetupEntry:
    """Tests for the sensor platform's async_setup_entry."""

    async def test_always_creates_metar_summary_sensor(self, hass) -> None:
        """The METAR summary sensor is always created, regardless of options."""
        entry = _make_entry(hass)
        async_add_entities = MagicMock()

        await async_setup_entry(hass, entry, async_add_entities)

        entities = async_add_entities.call_args[0][0]
        summary_sensors = [e for e in entities if isinstance(e, MetarSummarySensor)]
        assert len(summary_sensors) == 1

    async def test_no_detail_sensors_by_default(self, hass) -> None:
        """Without any enabled_entities, only the summary sensor is created."""
        entry = _make_entry(hass, enabled_entities=[])
        async_add_entities = MagicMock()

        await async_setup_entry(hass, entry, async_add_entities)

        entities = async_add_entities.call_args[0][0]
        assert len(entities) == 1
        assert isinstance(entities[0], MetarSummarySensor)

    async def test_metar_sensors_option_creates_all_detail_sensors(self, hass) -> None:
        """Enabling METAR_SENSORS creates one detail sensor per description."""
        entry = _make_entry(
            hass,
            enabled_entities=[AdditionalEntity.METAR_SENSORS.value],
        )
        async_add_entities = MagicMock()

        await async_setup_entry(hass, entry, async_add_entities)

        entities = async_add_entities.call_args[0][0]
        detail_sensors = [e for e in entities if isinstance(e, MetarSensor)]
        assert len(detail_sensors) == len(METAR_SENSORS)

        # No TAF sensor should be present, since it wasn't enabled.
        assert not any(isinstance(e, TafSummarySensor) for e in entities)

    async def test_taf_option_creates_taf_summary_sensor(self, hass) -> None:
        """Enabling TAF creates the TAF summary sensor."""
        entry = _make_entry(
            hass,
            enabled_entities=[AdditionalEntity.TAF.value],
        )
        async_add_entities = MagicMock()

        await async_setup_entry(hass, entry, async_add_entities)

        entities = async_add_entities.call_args[0][0]
        taf_sensors = [e for e in entities if isinstance(e, TafSummarySensor)]
        assert len(taf_sensors) == 1

    async def test_both_options_enabled_creates_everything(self, hass) -> None:
        """Enabling both options creates the summary, all detail sensors,
        and the TAF summary sensor."""
        entry = _make_entry(
            hass,
            enabled_entities=[
                AdditionalEntity.METAR_SENSORS.value,
                AdditionalEntity.TAF.value,
            ],
        )
        async_add_entities = MagicMock()

        await async_setup_entry(hass, entry, async_add_entities)

        entities = async_add_entities.call_args[0][0]

        assert sum(isinstance(e, MetarSummarySensor) for e in entities) == 1
        assert sum(isinstance(e, MetarSensor) for e in entities) == len(
            METAR_SENSORS,
        )
        assert sum(isinstance(e, TafSummarySensor) for e in entities) == 1
        assert len(entities) == 1 + len(METAR_SENSORS) + 1

    async def test_entities_are_created_for_the_configured_airport(self, hass) -> None:
        """All created entities reference the airport ICAO from the config
        entry, not a hardcoded or mismatched value."""
        entry = _make_entry(
            hass,
            enabled_entities=[
                AdditionalEntity.METAR_SENSORS.value,
                AdditionalEntity.TAF.value,
            ],
        )
        async_add_entities = MagicMock()

        await async_setup_entry(hass, entry, async_add_entities)

        entities = async_add_entities.call_args[0][0]

        for entity in entities:
            assert entity.unique_id.startswith("EPWA_")
