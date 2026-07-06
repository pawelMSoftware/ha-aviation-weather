"""Tests for AviationWeatherEntity (unique_id, availability, properties)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from custom_components.aviation_weather.metar.enums import CloudCover
from custom_components.aviation_weather.metar.models import CloudLayer, MetarData
from custom_components.aviation_weather.weather_entity.entity import (
    AviationWeatherEntity,
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
        temperature=18.0,
        dewpoint=12.0,
        pressure=1015.0,
        sea_level_pressure=1016.2,
        wind_speed=8,
        wind_gust=15,
        wind_direction="270",
        visibility_meters=10000,
        flight_category=None,
        metar_type=None,
        weather=None,
        snow_depth=None,
        vertical_visibility=None,
        cloud_layers=[],
        observation_time=None,
        raw_metar="",
    )


class TestUniqueIdAndAvailability:
    """unique_id must not depend on coordinator.data; availability does."""

    def test_unique_id_uses_airport_icao(self, full_metar_data: MetarData) -> None:
        coordinator = _make_coordinator(full_metar_data)
        entity = AviationWeatherEntity(
            coordinator=coordinator,
            airport_icao="EPWA",
        )

        assert entity.unique_id == "EPWA_weather"

    def test_unique_id_does_not_require_data(self) -> None:
        coordinator = _make_coordinator(None, last_update_success=False)
        entity = AviationWeatherEntity(
            coordinator=coordinator,
            airport_icao="EDFE",
        )

        assert entity.unique_id == "EDFE_weather"

    def test_available_when_data_present(self, full_metar_data: MetarData) -> None:
        coordinator = _make_coordinator(full_metar_data)
        entity = AviationWeatherEntity(
            coordinator=coordinator,
            airport_icao="EPWA",
        )

        assert entity.available is True

    def test_unavailable_when_data_is_none(self) -> None:
        coordinator = _make_coordinator(None, last_update_success=False)
        entity = AviationWeatherEntity(
            coordinator=coordinator,
            airport_icao="EDFE",
        )

        assert entity.available is False


class TestNativeProperties:
    """Properties read straight from MetarData, with None-safety."""

    def test_native_temperature(self, full_metar_data: MetarData) -> None:
        coordinator = _make_coordinator(full_metar_data)
        entity = AviationWeatherEntity(coordinator=coordinator, airport_icao="EPWA")

        assert entity.native_temperature == 18.0

    def test_native_pressure(self, full_metar_data: MetarData) -> None:
        coordinator = _make_coordinator(full_metar_data)
        entity = AviationWeatherEntity(coordinator=coordinator, airport_icao="EPWA")

        assert entity.native_pressure == 1015.0

    def test_native_dew_point(self, full_metar_data: MetarData) -> None:
        coordinator = _make_coordinator(full_metar_data)
        entity = AviationWeatherEntity(coordinator=coordinator, airport_icao="EPWA")

        assert entity.native_dew_point == 12.0

    def test_native_wind_speed(self, full_metar_data: MetarData) -> None:
        coordinator = _make_coordinator(full_metar_data)
        entity = AviationWeatherEntity(coordinator=coordinator, airport_icao="EPWA")

        assert entity.native_wind_speed == 8

    def test_native_wind_gust_speed(self, full_metar_data: MetarData) -> None:
        coordinator = _make_coordinator(full_metar_data)
        entity = AviationWeatherEntity(coordinator=coordinator, airport_icao="EPWA")

        assert entity.native_wind_gust_speed == 15

    def test_wind_bearing_parses_numeric_direction(
        self, full_metar_data: MetarData
    ) -> None:
        coordinator = _make_coordinator(full_metar_data)
        entity = AviationWeatherEntity(coordinator=coordinator, airport_icao="EPWA")

        assert entity.wind_bearing == 270.0

    def test_wind_bearing_handles_variable_direction(
        self, full_metar_data: MetarData
    ) -> None:
        """METAR sometimes reports "VRB" instead of a numeric bearing."""
        full_metar_data.wind_direction = "VRB"
        coordinator = _make_coordinator(full_metar_data)
        entity = AviationWeatherEntity(coordinator=coordinator, airport_icao="EPWA")

        assert entity.wind_bearing is None

    def test_all_native_properties_are_none_without_data(self) -> None:
        coordinator = _make_coordinator(None, last_update_success=False)
        entity = AviationWeatherEntity(coordinator=coordinator, airport_icao="EDFE")

        assert entity.native_temperature is None
        assert entity.native_pressure is None
        assert entity.native_dew_point is None
        assert entity.native_wind_speed is None
        assert entity.native_wind_gust_speed is None
        assert entity.wind_bearing is None
        assert entity.humidity is None
        assert entity.cloud_coverage is None
        assert entity.condition is None


class TestHumidity:
    """Humidity is derived from temperature/dew point via the
    August-Roche-Magnus approximation."""

    def test_saturated_air_is_100_percent(self) -> None:
        """When temperature equals dew point, relative humidity is 100%."""
        data = MetarData(
            airport="TEST",
            airport_name=None,
            latitude=None,
            longitude=None,
            elevation=None,
            temperature=15.0,
            dewpoint=15.0,
            pressure=None,
            sea_level_pressure=None,
            wind_speed=None,
            wind_gust=None,
            wind_direction=None,
            visibility_meters=None,
            flight_category=None,
            metar_type=None,
            weather=None,
            snow_depth=None,
            vertical_visibility=None,
            cloud_layers=[],
            observation_time=None,
            raw_metar="",
        )
        coordinator = _make_coordinator(data)
        entity = AviationWeatherEntity(coordinator=coordinator, airport_icao="TEST")

        assert entity.humidity == 100.0

    def test_returns_none_when_dewpoint_missing(
        self, full_metar_data: MetarData
    ) -> None:
        full_metar_data.dewpoint = None
        coordinator = _make_coordinator(full_metar_data)
        entity = AviationWeatherEntity(coordinator=coordinator, airport_icao="EPWA")

        assert entity.humidity is None

    def test_returns_a_value_between_zero_and_100(
        self, full_metar_data: MetarData
    ) -> None:
        coordinator = _make_coordinator(full_metar_data)
        entity = AviationWeatherEntity(coordinator=coordinator, airport_icao="EPWA")

        assert entity.humidity is not None
        assert 0.0 <= entity.humidity <= 100.0


class TestDeviceInfo:
    """device_info uses the airport name when available, ICAO otherwise."""

    def test_device_info_uses_airport_icao_as_name(
        self, full_metar_data: MetarData
    ) -> None:
        """device_info uses the airport ICAO code as the device name,
        not the full airport name from coordinator data."""
        coordinator = _make_coordinator(full_metar_data)
        entity = AviationWeatherEntity(coordinator=coordinator, airport_icao="EPWA")

        assert entity.device_info["name"] == "EPWA"

    def test_device_info_falls_back_to_icao_without_data(self) -> None:
        coordinator = _make_coordinator(None)
        entity = AviationWeatherEntity(coordinator=coordinator, airport_icao="EDFE")

        assert entity.device_info["name"] == "EDFE"


class TestCondition:
    """The `condition` property delegates to map_condition with the
    correct is_daytime flag from hass."""

    def test_condition_uses_is_up_for_daytime_flag(
        self, full_metar_data: MetarData
    ) -> None:
        coordinator = _make_coordinator(full_metar_data)
        entity = AviationWeatherEntity(coordinator=coordinator, airport_icao="EPWA")
        entity.hass = MagicMock()

        with patch(
            "custom_components.aviation_weather.weather_entity.entity.is_up",
            return_value=True,
        ) as mock_is_up:
            condition = entity.condition

        mock_is_up.assert_called_once_with(entity.hass)
        # full_metar_data has no clouds/weather, which the mapper treats
        # as clear sky; daytime=True (per the mocked is_up) means sunny.
        assert condition == "sunny"


class TestCloudCoverage:
    """The `cloud_coverage` property delegates to map_cloud_coverage."""

    def test_returns_percentage_for_known_cloud_layer(
        self, full_metar_data: MetarData
    ) -> None:
        full_metar_data.cloud_layers = [
            CloudLayer(cover=CloudCover.BROKEN, base=2000),
        ]
        coordinator = _make_coordinator(full_metar_data)
        entity = AviationWeatherEntity(coordinator=coordinator, airport_icao="EPWA")

        assert entity.cloud_coverage == 88

    def test_returns_none_when_no_cloud_layers_reported(
        self, full_metar_data: MetarData
    ) -> None:
        full_metar_data.cloud_layers = []
        coordinator = _make_coordinator(full_metar_data)
        entity = AviationWeatherEntity(coordinator=coordinator, airport_icao="EPWA")

        assert entity.cloud_coverage is None

    def test_returns_none_without_data(self) -> None:
        coordinator = _make_coordinator(None, last_update_success=False)
        entity = AviationWeatherEntity(coordinator=coordinator, airport_icao="EDFE")

        assert entity.cloud_coverage is None
