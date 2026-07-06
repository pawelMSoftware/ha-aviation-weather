"""Tests for the AdditionalEntity enum (additional sensor availability)."""

from __future__ import annotations

from custom_components.aviation_weather.airports.models import Airport
from custom_components.aviation_weather.enums import AdditionalEntity

AIRPORT_WITH_TAF = Airport(
    icao="EPWA",
    country="PL",
    name="Warsaw Chopin Airport",
    latitude=52.1657,
    longitude=20.9671,
    has_metar=True,
    has_taf=True,
)

AIRPORT_WITHOUT_TAF = Airport(
    icao="EDFE",
    country="DE",
    name="Frankfurt-Egelsbach Airport",
    latitude=49.96,
    longitude=8.643043,
    has_metar=True,
    has_taf=False,
)


class TestIsAvailableFor:
    """Tests for AdditionalEntity.is_available_for."""

    def test_metar_sensors_available_for_any_airport(self) -> None:
        """METAR details are available regardless of TAF support."""
        assert AdditionalEntity.METAR_SENSORS.is_available_for(
            AIRPORT_WITH_TAF,
        )
        assert AdditionalEntity.METAR_SENSORS.is_available_for(
            AIRPORT_WITHOUT_TAF,
        )

    def test_taf_available_when_airport_has_taf(self) -> None:
        """TAF forecast is available for an airport that publishes TAF."""
        assert AdditionalEntity.TAF.is_available_for(
            AIRPORT_WITH_TAF,
        )

    def test_taf_unavailable_when_airport_has_no_taf(self) -> None:
        """TAF forecast is unavailable for an airport without TAF data."""
        assert not AdditionalEntity.TAF.is_available_for(
            AIRPORT_WITHOUT_TAF,
        )


class TestOptions:
    """Tests for AdditionalEntity.options."""

    def test_options_without_airport_returns_everything(self) -> None:
        """Without an airport argument, all entities are returned."""
        options = AdditionalEntity.options()

        assert AdditionalEntity.METAR_SENSORS in options
        assert AdditionalEntity.TAF in options

    def test_options_for_airport_with_taf_includes_taf(self) -> None:
        """For an airport with TAF data, TAF is included in the options."""
        options = AdditionalEntity.options(
            AIRPORT_WITH_TAF,
        )

        assert AdditionalEntity.TAF in options
        assert AdditionalEntity.METAR_SENSORS in options

    def test_options_for_airport_without_taf_excludes_taf(self) -> None:
        """For an airport without TAF data, TAF is excluded from options."""
        options = AdditionalEntity.options(
            AIRPORT_WITHOUT_TAF,
        )

        assert AdditionalEntity.TAF not in options
        # METAR details should still be offered.
        assert AdditionalEntity.METAR_SENSORS in options
