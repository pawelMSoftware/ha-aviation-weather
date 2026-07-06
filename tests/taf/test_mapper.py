"""Tests for the TAF mapper."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from custom_components.aviation_weather.taf.enums import TafChangeType
from custom_components.aviation_weather.taf.mapper import TafMapper


@pytest.fixture
def mapper() -> TafMapper:
    """Return a TafMapper instance."""
    return TafMapper()


class TestMapFullPayload:
    """Tests mapping a full, realistic TAF API payload."""

    def test_basic_fields(self, mapper: TafMapper, taf_payload_full: dict) -> None:
        """Basic scalar fields are mapped correctly."""
        result = mapper.map(taf_payload_full, requested_airport="EPWA")

        assert result.airport == "EPWA"
        assert result.airport_name == "Warszawa Chopina"
        assert result.latitude == 52.165
        assert result.longitude == 20.967
        assert result.elevation == 110
        assert result.raw_taf.startswith("TAF EPWA")

    def test_issue_time_is_parsed_from_iso(
        self, mapper: TafMapper, taf_payload_full: dict
    ) -> None:
        """issueTime (ISO 8601) is parsed into an aware UTC datetime."""
        result = mapper.map(taf_payload_full)

        assert result.issue_time == datetime(2026, 6, 27, 11, 0, 0, tzinfo=UTC)

    def test_valid_from_to_are_parsed_from_unix_timestamp(
        self, mapper: TafMapper, taf_payload_full: dict
    ) -> None:
        """validTimeFrom/To (unix timestamps) are parsed into datetimes."""
        result = mapper.map(taf_payload_full)

        assert result.valid_from is not None
        assert result.valid_to is not None
        assert result.valid_from.tzinfo == UTC
        assert result.valid_to > result.valid_from

    def test_forecasts_are_mapped(
        self, mapper: TafMapper, taf_payload_full: dict
    ) -> None:
        """All forecast periods are mapped with correct field values."""
        result = mapper.map(taf_payload_full)

        assert len(result.forecasts) == 2

        first, second = result.forecasts

        assert first.change_type is None
        assert first.wind_direction == "270"
        assert first.wind_speed == 10
        assert first.wind_gust is None
        assert first.visibility == "9999"
        assert first.weather is None
        assert len(first.clouds) == 1
        assert first.clouds[0].cover == "FEW"
        assert first.clouds[0].base == 3000

        assert second.change_type == TafChangeType.TEMPO
        assert second.wind_direction == "280"
        assert second.wind_gust == 28
        assert second.weather == "TSRA"
        assert second.clouds[0].cloud_type == "CB"


class TestMapMinimalPayload:
    """Tests mapping a minimal payload, ensuring optional fields default safely."""

    def test_missing_optional_fields_default_to_none(
        self, mapper: TafMapper, taf_payload_minimal: dict
    ) -> None:
        """All optional fields are None/empty when absent from the payload."""
        result = mapper.map(taf_payload_minimal)

        assert result.airport == "EPKK"
        assert result.airport_name is None
        assert result.issue_time is None
        assert result.valid_from is None
        assert result.valid_to is None
        assert result.raw_taf == ""
        assert result.forecasts == []


class TestIcaoFallback:
    """Tests the icaoId fallback behavior described in the API client."""

    def test_uses_icao_from_payload_when_present(self, mapper: TafMapper) -> None:
        """icaoId in the payload takes priority over requested_airport."""
        result = mapper.map({"icaoId": "EPWA"}, requested_airport="EPKK")

        assert result.airport == "EPWA"

    def test_falls_back_to_requested_airport_when_icao_missing(
        self, mapper: TafMapper
    ) -> None:
        """requested_airport is used when icaoId is absent from the payload."""
        result = mapper.map({"rawTAF": "x"}, requested_airport="EPKK")

        assert result.airport == "EPKK"

    def test_raises_when_no_airport_can_be_determined(self, mapper: TafMapper) -> None:
        """A ValueError is raised when neither icaoId nor a fallback exist."""
        with pytest.raises(ValueError, match="icaoId"):
            mapper.map({}, requested_airport=None)


class TestUnknownChangeType:
    """Tests that unrecognized change type strings fall back gracefully."""

    def test_unknown_change_type_falls_back_to_string(self, mapper: TafMapper) -> None:
        """An unrecognized fcstChange string is returned as-is."""
        result = mapper.map(
            {
                "icaoId": "EPWA",
                "fcsts": [{"fcstChange": "WEIRD"}],
            }
        )

        assert result.forecasts[0].change_type == "WEIRD"
        assert not isinstance(result.forecasts[0].change_type, TafChangeType)


class TestTimestampHelpers:
    """Tests for the internal datetime conversion helpers."""

    def test_from_iso_datetime_handles_z_suffix(self, mapper: TafMapper) -> None:
        """Zulu-suffixed ISO datetimes are parsed as UTC."""
        result = mapper._from_iso_datetime("2026-01-01T00:00:00Z")

        assert result == datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)

    def test_from_iso_datetime_handles_none(self, mapper: TafMapper) -> None:
        """None input returns None."""
        assert mapper._from_iso_datetime(None) is None

    def test_from_unix_timestamp_handles_none(self, mapper: TafMapper) -> None:
        """None input returns None."""
        assert mapper._from_unix_timestamp(None) is None

    def test_from_unix_timestamp_returns_utc(self, mapper: TafMapper) -> None:
        """Unix timestamps are converted to UTC-aware datetimes."""
        result = mapper._from_unix_timestamp(0)

        assert result == datetime(1970, 1, 1, 0, 0, 0, tzinfo=UTC)
