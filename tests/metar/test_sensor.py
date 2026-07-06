"""Tests for METAR sensor entities (unique_id, availability, attributes)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from custom_components.aviation_weather.metar.enums import (
    CloudCover,
    FlightCategory,
    WeatherIntensity,
    WeatherPhenomenon,
)
from custom_components.aviation_weather.metar.models import (
    CloudLayer,
    MetarData,
    WeatherCondition,
)
from custom_components.aviation_weather.metar.sensor import (
    METAR_SENSORS,
    MetarSensor,
    MetarSummarySensor,
)


def _make_coordinator(data: MetarData | None, *, last_update_success: bool = True):
    """Build a mock MetarCoordinator with the given data."""
    coordinator = MagicMock()
    coordinator.data = data
    coordinator.last_update_success = last_update_success
    return coordinator


@pytest.fixture
def full_metar_data() -> MetarData:
    """Return a fully populated MetarData instance."""
    return MetarData(
        airport="EPWA",
        airport_name="Warsaw Chopin Airport",
        latitude=52.1657,
        longitude=20.9671,
        elevation=110,
        temperature=15.0,
        dewpoint=10.0,
        pressure=1013.0,
        sea_level_pressure=1014.0,
        wind_speed=8,
        wind_gust=15,
        wind_direction="270",
        visibility_meters=10000,
        flight_category=FlightCategory.VFR,
        metar_type=None,
        weather=WeatherCondition(
            raw="-RA",
            intensity=WeatherIntensity.LIGHT,
            phenomena=[WeatherPhenomenon.RAIN],
        ),
        snow_depth=None,
        vertical_visibility=None,
        cloud_layers=[CloudLayer(cover=CloudCover.BROKEN, base=2000)],
        observation_time=datetime(2026, 6, 27, 12, 0, tzinfo=UTC),
        raw_metar="METAR EPWA 271200Z 27008KT 10SM -RA BKN020 15/10 Q1013",
    )


class TestMetarSummarySensorWithData:
    """Tests for MetarSummarySensor when coordinator data is available."""

    def test_unique_id_uses_airport_icao(self, full_metar_data: MetarData) -> None:
        """unique_id is derived from the airport ICAO, not coordinator data."""
        coordinator = _make_coordinator(full_metar_data)
        sensor = MetarSummarySensor(coordinator=coordinator, airport_icao="EPWA")

        assert sensor.unique_id == "EPWA_metar_summary"

    def test_translation_key_is_metar_summary(self, full_metar_data: MetarData) -> None:
        """translation_key must match the "metar_summary" key used in
        icons.json for this entity's per-flight-category icon; it must
        not also set a static _attr_icon, which would take priority
        over icons.json and silently defeat the per-state icons."""
        coordinator = _make_coordinator(full_metar_data)
        sensor = MetarSummarySensor(coordinator=coordinator, airport_icao="EPWA")

        assert sensor.translation_key == "metar_summary"
        assert not hasattr(sensor, "_attr_icon")

    def test_available_when_data_present(self, full_metar_data: MetarData) -> None:
        """Sensor is available when coordinator has data and last update succeeded."""
        coordinator = _make_coordinator(full_metar_data, last_update_success=True)
        sensor = MetarSummarySensor(coordinator=coordinator, airport_icao="EPWA")

        assert sensor.available is True

    def test_native_value_is_flight_category(self, full_metar_data: MetarData) -> None:
        """native_value returns the flight category's underlying value."""
        coordinator = _make_coordinator(full_metar_data)
        sensor = MetarSummarySensor(coordinator=coordinator, airport_icao="EPWA")

        assert sensor.native_value == "VFR"

    def test_device_info_uses_airport_icao_as_name(
        self, full_metar_data: MetarData
    ) -> None:
        """device_info uses the airport ICAO code as the device name,
        not the full airport name from coordinator data — this keeps
        derived entity_ids short and predictable (e.g. sensor.epwa_metar
        rather than sensor.warsaw_chopin_airport_metar)."""
        coordinator = _make_coordinator(full_metar_data)
        sensor = MetarSummarySensor(coordinator=coordinator, airport_icao="EPWA")

        assert sensor.device_info["name"] == "EPWA"

    def test_extra_state_attributes_includes_weather_details(
        self, full_metar_data: MetarData
    ) -> None:
        """extra_state_attributes surfaces weather, cloud layer, and raw data."""
        coordinator = _make_coordinator(full_metar_data)
        sensor = MetarSummarySensor(coordinator=coordinator, airport_icao="EPWA")

        attrs = sensor.extra_state_attributes

        assert attrs["airport"] == "EPWA"
        assert attrs["temperature"] == 15.0
        assert attrs["weather"] == "-RA"
        assert attrs["weather_intensity"] == "light"
        assert attrs["weather_phenomena"] == ["rain"]
        assert attrs["cloud_layers"] == [{"cover": "BKN", "base": 2000}]
        assert attrs["raw_metar"].startswith("METAR EPWA")


class TestMetarSummarySensorWithoutData:
    """Tests for MetarSummarySensor when the coordinator has no data yet.

    This is the scenario that previously crashed entity setup: an airport
    with no current METAR report, where coordinator.data stays None.
    """

    def test_unique_id_does_not_require_data(self) -> None:
        """unique_id can be constructed even when coordinator.data is None."""
        coordinator = _make_coordinator(None, last_update_success=False)
        sensor = MetarSummarySensor(coordinator=coordinator, airport_icao="EDFE")

        assert sensor.unique_id == "EDFE_metar_summary"

    def test_unavailable_when_data_is_none(self) -> None:
        """Sensor is unavailable when coordinator.data is None."""
        coordinator = _make_coordinator(None, last_update_success=False)
        sensor = MetarSummarySensor(coordinator=coordinator, airport_icao="EDFE")

        assert sensor.available is False

    def test_unavailable_even_if_last_update_success_is_stale_true(self) -> None:
        """Sensor is unavailable based on data presence, regardless of the
        coordinator's last_update_success flag in isolation."""
        coordinator = _make_coordinator(None, last_update_success=True)
        sensor = MetarSummarySensor(coordinator=coordinator, airport_icao="EDFE")

        assert sensor.available is False

    def test_native_value_is_none(self) -> None:
        """native_value is None when there is no data to read from."""
        coordinator = _make_coordinator(None)
        sensor = MetarSummarySensor(coordinator=coordinator, airport_icao="EDFE")

        assert sensor.native_value is None

    def test_device_info_falls_back_to_icao(self) -> None:
        """device_info falls back to the ICAO code as the name when no
        airport name is available from coordinator data."""
        coordinator = _make_coordinator(None)
        sensor = MetarSummarySensor(coordinator=coordinator, airport_icao="EDFE")

        assert sensor.device_info["name"] == "EDFE"

    def test_extra_state_attributes_is_empty_dict(self) -> None:
        """extra_state_attributes returns an empty dict, not a crash."""
        coordinator = _make_coordinator(None)
        sensor = MetarSummarySensor(coordinator=coordinator, airport_icao="EDFE")

        assert sensor.extra_state_attributes == {}


class TestMetarSensorDetail:
    """Tests for the MetarSensor (detail sensor) class."""

    def test_unique_id_includes_description_key(
        self, full_metar_data: MetarData
    ) -> None:
        """unique_id combines the airport ICAO and the sensor description key."""
        coordinator = _make_coordinator(full_metar_data)
        description = METAR_SENSORS[0]  # temperature
        sensor = MetarSensor(
            coordinator=coordinator,
            description=description,
            airport_icao="EPWA",
        )

        assert sensor.unique_id == f"EPWA_{description.key}"

    def test_device_info_uses_airport_icao_as_name(
        self, full_metar_data: MetarData
    ) -> None:
        """Detail sensors share the same device-naming rule as the
        summary sensor: the device name is always the ICAO code."""
        coordinator = _make_coordinator(full_metar_data)
        description = METAR_SENSORS[0]
        sensor = MetarSensor(
            coordinator=coordinator,
            description=description,
            airport_icao="EPWA",
        )

        assert sensor.device_info["name"] == "EPWA"

    def test_device_info_falls_back_to_icao_without_data(self) -> None:
        coordinator = _make_coordinator(None)
        description = METAR_SENSORS[0]
        sensor = MetarSensor(
            coordinator=coordinator,
            description=description,
            airport_icao="EDFE",
        )

        assert sensor.device_info["name"] == "EDFE"

    def test_native_value_uses_description_value_fn(
        self, full_metar_data: MetarData
    ) -> None:
        """native_value delegates to the description's value_fn."""
        coordinator = _make_coordinator(full_metar_data)
        temperature_description = next(
            d for d in METAR_SENSORS if d.key == "temperature"
        )
        sensor = MetarSensor(
            coordinator=coordinator,
            description=temperature_description,
            airport_icao="EPWA",
        )

        assert sensor.native_value == 15.0

    def test_native_value_is_none_without_data(self) -> None:
        """native_value is None (not a crash) when coordinator.data is None."""
        coordinator = _make_coordinator(None)
        description = METAR_SENSORS[0]
        sensor = MetarSensor(
            coordinator=coordinator,
            description=description,
            airport_icao="EDFE",
        )

        assert sensor.native_value is None

    def test_available_is_false_without_data(self) -> None:
        """Detail sensors are unavailable when coordinator.data is None."""
        coordinator = _make_coordinator(None, last_update_success=False)
        description = METAR_SENSORS[0]
        sensor = MetarSensor(
            coordinator=coordinator,
            description=description,
            airport_icao="EDFE",
        )

        assert sensor.available is False

    @pytest.mark.parametrize("description", METAR_SENSORS, ids=lambda d: d.key)
    def test_every_description_value_fn_runs_without_error(
        self, full_metar_data: MetarData, description
    ) -> None:
        """Every METAR_SENSORS description's value_fn runs without raising,
        against a fully populated MetarData."""
        coordinator = _make_coordinator(full_metar_data)
        sensor = MetarSensor(
            coordinator=coordinator,
            description=description,
            airport_icao="EPWA",
        )

        # Just confirm it doesn't raise; the actual value depends on the
        # specific field being exercised.
        _ = sensor.native_value
