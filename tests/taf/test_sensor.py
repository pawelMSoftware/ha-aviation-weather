"""Tests for TAF sensor entities (unique_id, availability, attributes)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from custom_components.aviation_weather.taf.enums import TafChangeType
from custom_components.aviation_weather.taf.models import (
    TafCloudLayer,
    TafData,
    TafForecast,
)
from custom_components.aviation_weather.taf.sensor import TafSummarySensor


def _make_coordinator(data: TafData | None, *, last_update_success: bool = True):
    """Build a mock TafCoordinator with the given data."""
    coordinator = MagicMock()
    coordinator.data = data
    coordinator.last_update_success = last_update_success
    return coordinator


@pytest.fixture
def full_taf_data() -> TafData:
    """Return a fully populated TafData instance with one forecast period."""
    return TafData(
        airport="EPWA",
        airport_name="Warsaw Chopin Airport",
        latitude=52.1657,
        longitude=20.9671,
        elevation=110,
        issue_time=datetime(2026, 6, 27, 11, 0, tzinfo=UTC),
        valid_from=datetime(2026, 6, 27, 12, 0, tzinfo=UTC),
        valid_to=datetime(2026, 6, 28, 18, 0, tzinfo=UTC),
        raw_taf="TAF EPWA 271100Z 2712/2818 27010KT 9999 FEW030",
        forecasts=[
            TafForecast(
                time_from=datetime(2026, 6, 27, 12, 0, tzinfo=UTC),
                time_to=datetime(2026, 6, 27, 18, 0, tzinfo=UTC),
                change_type=TafChangeType.TEMPO,
                wind_direction="280",
                wind_speed=18,
                wind_gust=28,
                visibility="5000",
                weather="TSRA",
                clouds=[TafCloudLayer(cover="BKN", base=1500, cloud_type="CB")],
            ),
        ],
    )


class TestTafSummarySensorWithData:
    """Tests for TafSummarySensor when coordinator data is available."""

    def test_unique_id_uses_airport_icao(self, full_taf_data: TafData) -> None:
        """unique_id is derived from the airport ICAO, not coordinator data."""
        coordinator = _make_coordinator(full_taf_data)
        sensor = TafSummarySensor(coordinator=coordinator, airport_icao="EPWA")

        assert sensor.unique_id == "EPWA_taf_summary"

    def test_available_when_data_present(self, full_taf_data: TafData) -> None:
        """Sensor is available when coordinator has data."""
        coordinator = _make_coordinator(full_taf_data, last_update_success=True)
        sensor = TafSummarySensor(coordinator=coordinator, airport_icao="EPWA")

        assert sensor.available is True

    def test_native_value_is_forecast(self, full_taf_data: TafData) -> None:
        """native_value is the literal 'Forecast' state when data exists."""
        coordinator = _make_coordinator(full_taf_data)
        sensor = TafSummarySensor(coordinator=coordinator, airport_icao="EPWA")

        assert sensor.native_value == "Forecast"

    def test_device_info_uses_airport_icao_as_name(
        self, full_taf_data: TafData
    ) -> None:
        """device_info uses the airport ICAO code as the device name,
        not the full airport name from coordinator data."""
        coordinator = _make_coordinator(full_taf_data)
        sensor = TafSummarySensor(coordinator=coordinator, airport_icao="EPWA")

        assert sensor.device_info["name"] == "EPWA"

    def test_extra_state_attributes_includes_forecast_details(
        self, full_taf_data: TafData
    ) -> None:
        """extra_state_attributes surfaces forecast periods and cloud data."""
        coordinator = _make_coordinator(full_taf_data)
        sensor = TafSummarySensor(coordinator=coordinator, airport_icao="EPWA")

        attrs = sensor.extra_state_attributes

        assert attrs["airport"] == "EPWA"
        assert attrs["forecast_count"] == 1
        assert attrs["raw_taf"].startswith("TAF EPWA")

        forecast = attrs["forecasts"][0]
        assert forecast["change_type"] == "TEMPO"
        assert forecast["wind_direction"] == "280"
        assert forecast["weather"] == "TSRA"
        assert forecast["clouds"] == [
            {"cover": "BKN", "base": 1500, "type": "CB"},
        ]


class TestTafSummarySensorWithoutData:
    """Tests for TafSummarySensor when the coordinator has no data.

    This is the common case for airports that simply don't publish TAF
    at all, in addition to the transient "no current report" case.
    """

    def test_unique_id_does_not_require_data(self) -> None:
        """unique_id can be constructed even when coordinator.data is None."""
        coordinator = _make_coordinator(None, last_update_success=False)
        sensor = TafSummarySensor(coordinator=coordinator, airport_icao="EDFE")

        assert sensor.unique_id == "EDFE_taf_summary"

    def test_unavailable_when_data_is_none(self) -> None:
        """Sensor is unavailable when coordinator.data is None."""
        coordinator = _make_coordinator(None, last_update_success=False)
        sensor = TafSummarySensor(coordinator=coordinator, airport_icao="EDFE")

        assert sensor.available is False

    def test_native_value_is_none(self) -> None:
        """native_value is None (not the literal 'Forecast') without data."""
        coordinator = _make_coordinator(None)
        sensor = TafSummarySensor(coordinator=coordinator, airport_icao="EDFE")

        assert sensor.native_value is None

    def test_device_info_falls_back_to_icao(self) -> None:
        """device_info falls back to the ICAO code when no airport name is
        available from coordinator data."""
        coordinator = _make_coordinator(None)
        sensor = TafSummarySensor(coordinator=coordinator, airport_icao="EDFE")

        assert sensor.device_info["name"] == "EDFE"

    def test_extra_state_attributes_is_empty_dict(self) -> None:
        """extra_state_attributes returns an empty dict, not a crash."""
        coordinator = _make_coordinator(None)
        sensor = TafSummarySensor(coordinator=coordinator, airport_icao="EDFE")

        assert sensor.extra_state_attributes == {}
