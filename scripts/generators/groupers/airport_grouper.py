from __future__ import annotations

from collections import defaultdict

from ..models.airport import Airport


class AirportGrouper:
    """Group airports by country."""

    def group(
        self,
        airports: list[Airport],
    ) -> dict[str, list[Airport]]:
        """Group airports."""

        countries: dict[str, list[Airport]] = defaultdict(
            list,
        )

        for airport in airports:
            countries[airport.country.lower()].append(
                airport,
            )

        return {
            country: sorted(
                country_airports,
                key=lambda airport: airport.icao,
            )
            for country, country_airports in sorted(
                countries.items(),
            )
        }
