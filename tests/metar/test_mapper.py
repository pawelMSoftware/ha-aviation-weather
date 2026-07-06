"""Tests for the METAR mapper."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from custom_components.aviation_weather.metar.enums import (
    CloudCover,
    FlightCategory,
    MetarType,
    WeatherIntensity,
    WeatherPhenomenon,
)
from custom_components.aviation_weather.metar.mapper import MetarMapper


@pytest.fixture
def mapper() -> MetarMapper:
    """Return a MetarMapper instance."""
    return MetarMapper()


class TestMapFullPayload:
    """Tests mapping a full, realistic API payload."""

    def test_basic_fields(self, mapper: MetarMapper, metar_payload_full: dict) -> None:
        """Basic scalar fields are mapped correctly."""
        result = mapper.map(metar_payload_full, requested_airport="EPWA")

        assert result.airport == "EPWA"
        assert result.airport_name == "Warszawa Chopina"
        assert result.latitude == 52.165
        assert result.longitude == 20.967
        assert result.elevation == 110
        assert result.temperature == 18.0
        assert result.dewpoint == 12.0
        assert result.pressure == 1015.0
        assert result.sea_level_pressure == 1016.2
        assert result.wind_speed == 8
        assert result.wind_gust == 15
        assert result.wind_direction == "270"
        assert result.visibility_meters == 10000

    def test_flight_category_is_mapped_to_enum(
        self, mapper: MetarMapper, metar_payload_full: dict
    ) -> None:
        """Known flight category strings map to the FlightCategory enum."""
        result = mapper.map(metar_payload_full)

        assert result.flight_category == FlightCategory.VFR
        assert isinstance(result.flight_category, FlightCategory)

    def test_metar_type_is_mapped_to_enum(
        self, mapper: MetarMapper, metar_payload_full: dict
    ) -> None:
        """Known METAR type strings map to the MetarType enum."""
        result = mapper.map(metar_payload_full)

        assert result.metar_type == MetarType.METAR

    def test_observation_time_is_parsed(
        self, mapper: MetarMapper, metar_payload_full: dict
    ) -> None:
        """reportTime is parsed into an aware UTC datetime."""
        result = mapper.map(metar_payload_full)

        assert result.observation_time == datetime(2026, 6, 27, 12, 0, 0, tzinfo=UTC)

    def test_cloud_layers_are_mapped(
        self, mapper: MetarMapper, metar_payload_full: dict
    ) -> None:
        """Cloud layers are mapped with known cover enums."""
        result = mapper.map(metar_payload_full)

        assert len(result.cloud_layers) == 2
        assert result.cloud_layers[0].cover == CloudCover.FEW
        assert result.cloud_layers[0].base == 2500
        assert result.cloud_layers[1].cover == CloudCover.BROKEN
        assert result.cloud_layers[1].base == 4000

    def test_weather_condition_is_parsed(
        self, mapper: MetarMapper, metar_payload_full: dict
    ) -> None:
        """wxString '-RA' maps to light intensity rain."""
        result = mapper.map(metar_payload_full)

        assert result.weather is not None
        assert result.weather.raw == "-RA"
        assert result.weather.intensity == WeatherIntensity.LIGHT
        assert result.weather.phenomena == [WeatherPhenomenon.RAIN]

    def test_raw_metar_is_preserved(
        self, mapper: MetarMapper, metar_payload_full: dict
    ) -> None:
        """The raw METAR string is preserved verbatim."""
        result = mapper.map(metar_payload_full)

        assert result.raw_metar.startswith("METAR EPWA")


class TestMapMinimalPayload:
    """Tests mapping a minimal payload, ensuring optional fields default safely."""

    def test_missing_optional_fields_default_to_none(
        self, mapper: MetarMapper, metar_payload_minimal: dict
    ) -> None:
        """All optional fields are None when absent from the payload."""
        result = mapper.map(metar_payload_minimal)

        assert result.airport == "EPKK"
        assert result.airport_name is None
        assert result.temperature is None
        assert result.wind_direction is None
        assert result.visibility_meters is None
        assert result.flight_category is None
        assert result.metar_type is None
        assert result.weather is None
        assert result.cloud_layers == []
        assert result.observation_time is None
        assert result.raw_metar == ""


class TestIcaoFallback:
    """Tests the icaoId fallback behavior described in the API client."""

    def test_uses_icao_from_payload_when_present(self, mapper: MetarMapper) -> None:
        """icaoId in the payload takes priority over requested_airport."""
        result = mapper.map({"icaoId": "EPWA"}, requested_airport="EPKK")

        assert result.airport == "EPWA"

    def test_falls_back_to_requested_airport_when_icao_missing(
        self, mapper: MetarMapper
    ) -> None:
        """requested_airport is used when icaoId is absent from the payload."""
        result = mapper.map({"name": "Some Airport"}, requested_airport="EPKK")

        assert result.airport == "EPKK"

    def test_raises_when_no_airport_can_be_determined(
        self, mapper: MetarMapper
    ) -> None:
        """A ValueError is raised when neither icaoId nor a fallback exist."""
        with pytest.raises(ValueError, match="icaoId"):
            mapper.map({}, requested_airport=None)


class TestUnknownEnumValues:
    """Tests that unrecognized enum-like strings fall back gracefully."""

    def test_unknown_flight_category_falls_back_to_string(
        self, mapper: MetarMapper
    ) -> None:
        """An unrecognized flight category string is returned as-is."""
        result = mapper.map({"icaoId": "EPWA", "fltCat": "WEIRD"})

        assert result.flight_category == "WEIRD"
        assert not isinstance(result.flight_category, FlightCategory)

    def test_unknown_cloud_cover_falls_back_to_string(
        self, mapper: MetarMapper
    ) -> None:
        """An unrecognized cloud cover string is returned as-is."""
        result = mapper.map(
            {
                "icaoId": "EPWA",
                "clouds": [{"cover": "XXX", "base": 1000}],
            }
        )

        assert result.cloud_layers[0].cover == "XXX"

    def test_unknown_metar_type_falls_back_to_string(self, mapper: MetarMapper) -> None:
        """An unrecognized METAR type string is returned as-is."""
        result = mapper.map({"icaoId": "EPWA", "metarType": "WEIRD"})

        assert result.metar_type == "WEIRD"

    def test_cloud_entry_without_cover_is_skipped(self, mapper: MetarMapper) -> None:
        """Cloud entries with a falsy cover value are skipped entirely."""
        result = mapper.map(
            {
                "icaoId": "EPWA",
                "clouds": [
                    {"cover": None, "base": 1000},
                    {"cover": "", "base": 2000},
                    {"cover": "SCT", "base": 3000},
                ],
            }
        )

        assert len(result.cloud_layers) == 1
        assert result.cloud_layers[0].cover == CloudCover.SCATTERED


class TestWeatherStringParsing:
    """Tests various wxString combinations for the weather condition mapper."""

    @pytest.mark.parametrize(
        ("wx_string", "expected_intensity", "expected_phenomena"),
        [
            ("RA", None, [WeatherPhenomenon.RAIN]),
            ("-SN", WeatherIntensity.LIGHT, [WeatherPhenomenon.SNOW]),
            (
                "+TSRA",
                WeatherIntensity.HEAVY,
                [
                    WeatherPhenomenon.THUNDERSTORM,
                    WeatherPhenomenon.RAIN,
                ],
            ),
            ("BR", None, [WeatherPhenomenon.MIST]),
            # "RA" is a substring of "FZRA", so the mapper (correctly,
            # given its simple substring-matching approach) reports both
            # FREEZING_RAIN and RAIN for this code.
            (
                "FZRA",
                None,
                [
                    WeatherPhenomenon.FREEZING_RAIN,
                    WeatherPhenomenon.RAIN,
                ],
            ),
        ],
    )
    def test_wx_string_variants(
        self,
        mapper: MetarMapper,
        wx_string: str,
        expected_intensity: WeatherIntensity | None,
        expected_phenomena: list[WeatherPhenomenon],
    ) -> None:
        """Different wxString codes map to the expected intensity/phenomena."""
        result = mapper.map({"icaoId": "EPWA", "wxString": wx_string})

        assert result.weather is not None
        assert result.weather.intensity == expected_intensity
        assert result.weather.phenomena == expected_phenomena

    def test_empty_wx_string_returns_no_weather(self, mapper: MetarMapper) -> None:
        """An empty or missing wxString results in weather being None."""
        result = mapper.map({"icaoId": "EPWA", "wxString": ""})

        assert result.weather is None


class TestParseVisibilityMeters:
    """Tests for _parse_visibility_meters — the rawOb visibility parser.

    This covers the three ICAO formats (metric group, 9999, CAVOK) and
    the US statute-mile format that must be left as None rather than
    converted.
    """

    @pytest.mark.parametrize(
        ("raw_ob", "expected"),
        [
            # ICAO metric group — 4 digits read directly as metres
            (
                "METAR EPGD 021200Z 27010KT 0500 FG BKN002 12/11 Q1008",
                500,
            ),
            (
                "METAR EPWA 021200Z 27008KT 0800 BR OVC004 10/09 Q1005",
                800,
            ),
            (
                "METAR EDDF 021200Z 26012KT 3500 -RA BKN015 16/12 Q1010",
                3500,
            ),
            (
                "METAR EGLL 021200Z 28010KT 7000 SCT025 19/12 Q1008",
                7000,
            ),
            # 9999 → sentinel 10000
            (
                "METAR EPWA 021200Z 27010KT 9999 FEW030 18/10 Q1015",
                10000,
            ),
            # CAVOK → sentinel 10000 (replaces visibility group entirely)
            (
                "METAR EHAM 021200Z 24015KT CAVOK 22/14 Q1012",
                10000,
            ),
            # SPECI format — same parsing rules apply
            (
                "SPECI EPWA 021145Z 26018G30KT 0800 +RA OVC006 14/13 Q1005",
                800,
            ),
            # Variable wind suffix before visibility must be skipped
            (
                "METAR EPWA 021200Z 27010G20KT 240V310 7000 SCT025 17/11 Q1012",
                7000,
            ),
            # MPS wind unit (e.g. Russia)
            (
                "METAR UUEE 021200Z 25005MPS 9999 FEW040 21/10 Q1015",
                10000,
            ),
        ],
    )
    def test_metric_visibility_parsed_correctly(
        self,
        mapper: MetarMapper,
        raw_ob: str,
        expected: int,
    ) -> None:
        result = mapper.map({"icaoId": "EPWA", "rawOb": raw_ob})
        assert result.visibility_meters == expected

    @pytest.mark.parametrize(
        "raw_ob",
        [
            # US statute-mile format — not converted, returned as None
            "METAR KJFK 021200Z 27012KT 10SM FEW025 22/14 A2995",
            "METAR KORD 021200Z 26015KT 1SM BR OVC002 14/13 A3001",
            "METAR KBOS 021200Z 28008KT 1/4SM FG OVC002 12/11 A2998",
        ],
    )
    def test_us_statute_miles_returns_none(
        self,
        mapper: MetarMapper,
        raw_ob: str,
    ) -> None:
        """US statute-mile visibility must not be converted to metres."""
        result = mapper.map({"icaoId": "EPWA", "rawOb": raw_ob})
        assert result.visibility_meters is None

    def test_empty_raw_ob_returns_none(self, mapper: MetarMapper) -> None:
        result = mapper.map({"icaoId": "EPWA"})
        assert result.visibility_meters is None

    def test_no_wind_group_returns_none(self, mapper: MetarMapper) -> None:
        """If the wind group is absent the parser cannot locate visibility."""
        result = mapper.map(
            {"icaoId": "EPWA", "rawOb": "METAR EPWA 021200Z 9999 18/12 Q1015"}
        )
        assert result.visibility_meters is None

    def test_non_visibility_token_after_wind_returns_none(
        self, mapper: MetarMapper
    ) -> None:
        """When the token after the wind group is not a visibility group
        (e.g. it starts with a letter and isn't CAVOK), the parser stops
        and returns None rather than scanning further."""
        # RMK (remark) immediately after wind — no visibility group
        result = mapper.map(
            {
                "icaoId": "EPWA",
                "rawOb": "METAR EPWA 021200Z 27010KT RMK NOSIG 18/12 Q1015",
            }
        )
        assert result.visibility_meters is None

    def test_wind_is_last_token_returns_none(self, mapper: MetarMapper) -> None:
        """When the wind group is the last token in rawOb (no visibility
        group follows it), the for-loop has nothing to iterate and
        falls through to return None."""
        result = mapper.map(
            {
                "icaoId": "EPWA",
                "rawOb": "METAR EPWA 021200Z 27010KT",
            }
        )
        assert result.visibility_meters is None
