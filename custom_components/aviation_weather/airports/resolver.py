from __future__ import annotations

from math import asin, cos, radians, sin, sqrt

from .country_registry import (
    CONTINENTS,
    COUNTRIES,
    COUNTRY_NAMES,
)
from .models import Airport


def continent_options() -> list[str]:
    """Return the list of continent codes that have at least one airport.

    Labels are not included here: the SelectSelector this feeds into
    uses `translation_key="continent"`, so the frontend resolves and
    sorts the displayed names from the integration's translation files
    instead of a hardcoded English name.
    """

    return sorted(
        set(
            CONTINENTS.values(),
        ),
    )


def countries_for_continent(
    continent: str,
) -> set[str]:
    """Return the set of country codes belonging to a continent."""

    return {
        country
        for country, country_continent in CONTINENTS.items()
        if country_continent == continent
    }


def country_options(
    continent: str,
) -> dict[str, str]:
    """Return country options for a continent, sorted by name."""

    codes = countries_for_continent(
        continent,
    )

    return {
        code: COUNTRY_NAMES[code]
        for code in sorted(
            codes,
            key=lambda code: COUNTRY_NAMES[code],
        )
    }


def airport_options(
    country: str,
    suggested_airport: str | None = None,
) -> dict[str, str]:
    """Return airport options for a country, sorted by name.

    Returns a dict of {icao: label} pairs. The suggested_airport
    parameter is kept for backward compatibility but no longer affects
    the label — SelectSelector highlights the default value visually
    without needing a prefix in the label text.
    """

    airports = COUNTRIES[country]

    return {
        airport.icao: f"{airport.icao} — {airport.name}"
        for airport in sorted(
            airports.values(),
            key=lambda airport: airport.name,
        )
    }


def _distance_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:
    """Calculate distance in kilometers."""

    earth_radius = 6371

    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)

    lat1 = radians(lat1)
    lat2 = radians(lat2)

    a = sin(d_lat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(d_lon / 2) ** 2

    c = 2 * asin(
        sqrt(a),
    )

    return earth_radius * c


def find_nearest_airport(
    latitude: float,
    longitude: float,
    country: str | None = None,
    continent: str | None = None,
) -> Airport:
    """Find nearest airport.

    If `country` is given, search is restricted to that country.
    Otherwise, if `continent` is given, search is restricted to all
    countries in that continent. If neither is given, search spans
    every airport in the registry.
    """

    if country is not None:
        country_airports = COUNTRIES.get(
            country,
        )

        if country_airports is None:
            raise ValueError(
                f"Unsupported country: {country}",
            )

        airports = country_airports.values()
    elif continent is not None:
        country_codes = countries_for_continent(
            continent,
        )

        if not country_codes:
            raise ValueError(
                f"Unsupported continent: {continent}",
            )

        airports = [
            airport for code in country_codes for airport in COUNTRIES[code].values()
        ]
    else:
        airports = [
            airport
            for country_airports in COUNTRIES.values()
            for airport in country_airports.values()
        ]

    return min(
        airports,
        key=lambda airport: _distance_km(
            latitude,
            longitude,
            airport.latitude,
            airport.longitude,
        ),
    )


def distance_to_airport(
    latitude: float,
    longitude: float,
    airport: Airport,
) -> float:
    """Calculate distance to airport."""

    return _distance_km(
        latitude,
        longitude,
        airport.latitude,
        airport.longitude,
    )
