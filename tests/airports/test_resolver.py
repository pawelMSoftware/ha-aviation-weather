"""Tests for the airport resolver (distance calculations, lookups)."""

from __future__ import annotations

import math

import pytest

from custom_components.aviation_weather.airports import resolver
from custom_components.aviation_weather.airports.models import Airport

# Fixed, hand-built test fixtures so these tests stay stable regardless
# of how many real airports get added to the registry over time.
WARSAW = Airport(
    icao="TEST_WAW",
    country="XX",
    name="Test Warsaw",
    latitude=52.2297,
    longitude=21.0122,
)
KRAKOW = Airport(
    icao="TEST_KRK",
    country="XX",
    name="Test Krakow",
    latitude=50.0647,
    longitude=19.9450,
)
BERLIN = Airport(
    icao="TEST_BER",
    country="YY",
    name="Test Berlin",
    latitude=52.5200,
    longitude=13.4050,
)

TEST_REGISTRY = {
    "XX": {
        "TEST_WAW": WARSAW,
        "TEST_KRK": KRAKOW,
    },
    "YY": {
        "TEST_BER": BERLIN,
    },
}

TEST_CONTINENTS = {
    "XX": "EU",
    "YY": "NA",
}


@pytest.fixture(autouse=True)
def patched_registry(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace COUNTRIES and CONTINENTS with small, fixed test registries."""
    monkeypatch.setattr(resolver, "COUNTRIES", TEST_REGISTRY)
    monkeypatch.setattr(resolver, "CONTINENTS", TEST_CONTINENTS)


class TestDistanceKm:
    """Tests for the internal haversine distance calculation."""

    def test_distance_to_self_is_zero(self) -> None:
        """The distance between a point and itself is zero."""
        distance = resolver._distance_km(52.0, 21.0, 52.0, 21.0)

        assert distance == pytest.approx(0.0, abs=1e-6)

    def test_known_distance_warsaw_krakow(self) -> None:
        """Warsaw-Krakow straight-line distance is roughly 250-260 km."""
        distance = resolver._distance_km(
            WARSAW.latitude, WARSAW.longitude, KRAKOW.latitude, KRAKOW.longitude
        )

        assert 250 <= distance <= 260

    def test_distance_is_symmetric(self) -> None:
        """Distance from A to B equals distance from B to A."""
        a_to_b = resolver._distance_km(
            WARSAW.latitude, WARSAW.longitude, BERLIN.latitude, BERLIN.longitude
        )
        b_to_a = resolver._distance_km(
            BERLIN.latitude, BERLIN.longitude, WARSAW.latitude, WARSAW.longitude
        )

        assert a_to_b == pytest.approx(b_to_a, abs=1e-9)

    def test_antipodal_points_is_half_earth_circumference(self) -> None:
        """Distance between antipodal points equals pi * earth radius."""
        distance = resolver._distance_km(0.0, 0.0, 0.0, 180.0)

        assert distance == pytest.approx(6371 * math.pi, abs=1.0)


class TestFindNearestAirport:
    """Tests for find_nearest_airport across and within countries."""

    def test_finds_nearest_within_same_country(self) -> None:
        """A point near Warsaw resolves to the Warsaw test airport."""
        result = resolver.find_nearest_airport(52.23, 21.01)

        assert result.icao == "TEST_WAW"

    def test_finds_nearest_across_countries(self) -> None:
        """Nearest-airport search spans all countries when none is given."""
        # Closer to Berlin than to any Polish test airport.
        result = resolver.find_nearest_airport(52.5, 13.5)

        assert result.icao == "TEST_BER"

    def test_restricts_search_to_given_country(self) -> None:
        """Passing a country restricts the search even if another is closer."""
        # Geographically closer to Berlin, but we force country="XX".
        result = resolver.find_nearest_airport(52.5, 13.5, country="XX")

        assert result.icao in {"TEST_WAW", "TEST_KRK"}
        assert result.country == "XX"

    def test_unsupported_country_raises(self) -> None:
        """An unsupported country code raises a ValueError."""
        with pytest.raises(ValueError, match="Unsupported country"):
            resolver.find_nearest_airport(52.0, 21.0, country="ZZ")


class TestDistanceToAirport:
    """Tests for the public distance_to_airport helper."""

    def test_matches_internal_distance_calculation(self) -> None:
        """distance_to_airport matches _distance_km for the same inputs."""
        expected = resolver._distance_km(
            WARSAW.latitude, WARSAW.longitude, KRAKOW.latitude, KRAKOW.longitude
        )

        result = resolver.distance_to_airport(WARSAW.latitude, WARSAW.longitude, KRAKOW)

        assert result == pytest.approx(expected)


class TestAirportOptions:
    """Tests for the airport_options used by the config flow UI."""

    def test_returns_all_airports_sorted_by_name(self) -> None:
        """Options are sorted alphabetically by airport name."""
        options = resolver.airport_options("XX")

        names = list(options.values())
        # "Test Krakow" sorts before "Test Warsaw" alphabetically.
        assert names == ["TEST_KRK — Test Krakow", "TEST_WAW — Test Warsaw"]

    def test_suggested_airport_does_not_change_the_label(self) -> None:
        """suggested_airport is kept for backward compatibility but no
        longer affects the label — SelectSelector highlights the
        default value visually, so no text marker is needed."""
        options = resolver.airport_options("XX", suggested_airport="TEST_WAW")

        assert options["TEST_WAW"] == "TEST_WAW — Test Warsaw"
        assert options["TEST_KRK"] == "TEST_KRK — Test Krakow"

    def test_no_suggestion_means_same_labels(self) -> None:
        """Without a suggested airport, labels are identical to the
        suggested-airport case — the parameter never affects output."""
        options = resolver.airport_options("XX")

        assert options == {
            "TEST_KRK": "TEST_KRK — Test Krakow",
            "TEST_WAW": "TEST_WAW — Test Warsaw",
        }

    def test_unknown_country_raises_key_error(self) -> None:
        """An unsupported country code raises a KeyError (direct dict access)."""
        with pytest.raises(KeyError):
            resolver.airport_options("ZZ")


class TestContinentOptions:
    """Tests for continent_options used by the config flow's continent step.

    continent_options() intentionally returns plain continent codes
    (not a code -> English name mapping): the SelectSelector consuming
    this list resolves and sorts the displayed labels itself from the
    integration's translation files (translation_key="continent"), so
    this function isn't responsible for naming or English sort order.
    """

    def test_returns_a_sorted_list_of_codes(self) -> None:
        """Returns the distinct continent codes present in the registry,
        sorted by code (not by any English name)."""
        options = resolver.continent_options()

        assert options == ["EU", "NA"]

    def test_does_not_duplicate_continents_shared_by_multiple_countries(
        self,
    ) -> None:
        """A continent appears once even if multiple countries map to it."""
        options = resolver.continent_options()

        assert options.count("EU") == 1

    def test_return_type_is_a_list_not_a_dict(self) -> None:
        """Returns a plain list of codes, not a code -> name dict.

        This is the exact shape required by SelectSelectorConfig's
        `options` field when paired with `translation_key`.
        """
        options = resolver.continent_options()

        assert isinstance(options, list)
        assert all(isinstance(code, str) for code in options)


class TestCountryOptions:
    """Tests for country_options, used by the airport-database-only
    code paths (the config flow itself now uses CountrySelector, but
    this remains public API for diagnostics, tests, or future use)."""

    TEST_COUNTRY_NAMES = {
        "XX": "Testland",
        "YY": "Yetherlands",
    }

    @pytest.fixture(autouse=True)
    def patched_country_names(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """country_options() reads COUNTRY_NAMES directly, which isn't
        covered by the module-level patched_registry fixture (that one
        only patches COUNTRIES/CONTINENTS)."""
        monkeypatch.setattr(
            resolver,
            "COUNTRY_NAMES",
            self.TEST_COUNTRY_NAMES,
        )

    def test_returns_only_countries_in_the_given_continent(self) -> None:
        options = resolver.country_options("EU")

        assert options == {"XX": "Testland"}

    def test_different_continent_returns_different_countries(self) -> None:
        options = resolver.country_options("NA")

        assert options == {"YY": "Yetherlands"}

    def test_continent_with_no_countries_returns_empty_dict(self) -> None:
        options = resolver.country_options("AF")

        assert options == {}

    def test_return_type_is_a_code_to_name_dict(self) -> None:
        """Unlike continent_options(), country_options() does return a
        code -> name mapping: there's no equivalent CountrySelector for
        a continent-scoped, English-labeled dropdown elsewhere in the
        codebase to delegate naming to."""
        options = resolver.country_options("EU")

        assert isinstance(options, dict)
        assert options["XX"] == "Testland"


class TestFindNearestAirportByContinent:
    """Tests for find_nearest_airport with continent= (no country=) —
    the lookup used by the config flow's first step, before the user
    has picked a specific country."""

    def test_restricts_search_to_the_given_continent(self) -> None:
        """Even though TEST_BER (Berlin, continent NA) might be
        geographically closer to some coordinates, only airports in
        the requested continent (EU, containing only Warsaw/Krakow)
        are considered."""
        result = resolver.find_nearest_airport(
            52.5,
            13.5,  # Closest to Berlin geographically
            continent="EU",
        )

        assert result.country == "XX"

    def test_unsupported_continent_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unsupported continent"):
            resolver.find_nearest_airport(
                52.0,
                21.0,
                continent="ZZ",
            )

    def test_country_takes_priority_over_continent_when_both_given(self) -> None:
        """If both country and continent are given, country wins (the
        continent argument is silently ignored) — this matches the
        function's own docstring precedence order."""
        result = resolver.find_nearest_airport(
            52.5,
            13.5,
            country="XX",
            continent="NA",
        )

        assert result.country == "XX"
