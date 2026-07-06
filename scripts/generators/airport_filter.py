from __future__ import annotations

from .continents import continent_for_country
from .models.airport import Airport


class AirportFilter:
    """Filter airport list."""

    ALLOWED_TYPES = frozenset(
        {
            "large_airport",
            "medium_airport",
        },
    )

    # Only airports in these continents are included in the generated
    # database. Keeping this list small reduces the package size and
    # focuses the integration on the regions where METAR/TAF coverage
    # is most complete and where SIGMET data (future) will be most useful.
    # Add continent codes here when you want to expand coverage.
    ALLOWED_CONTINENTS = frozenset({"EU"})

    def filter(
        self,
        airports: list[Airport],
    ) -> list[Airport]:
        """Return filtered airports."""

        filtered: list[Airport] = []
        seen: set[str] = set()

        for airport in airports:
            if not self._is_valid(
                airport,
                seen,
            ):
                continue

            filtered.append(
                airport,
            )

        return sorted(
            filtered,
            key=lambda airport: airport.icao,
        )

    def _is_valid(
        self,
        airport: Airport,
        seen: set[str],
    ) -> bool:
        """Return whether airport should be included."""

        if not airport.has_metar:
            return False

        if airport.airport_type not in self.ALLOWED_TYPES:
            return False

        if len(airport.icao) != 4:
            return False

        if not airport.country:
            return False

        if airport.latitude == 0:
            return False

        if airport.longitude == 0:
            return False

        if airport.icao in seen:
            return False

        if continent_for_country(airport.country) not in self.ALLOWED_CONTINENTS:
            return False

        seen.add(
            airport.icao,
        )

        return True
