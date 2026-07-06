from __future__ import annotations

from dataclasses import replace

from ..models.airport import Airport
from ..models.station import Station


class AirportMerger:
    """Merge airport and weather station data."""

    def merge(
        self,
        airports: list[Airport],
        stations: dict[str, Station],
    ) -> list[Airport]:
        """Merge airport data with station data."""

        merged: list[Airport] = []

        for airport in airports:
            station = stations.get(
                airport.icao,
            )

            if station is None:
                merged.append(
                    airport,
                )
                continue

            merged.append(
                replace(
                    airport,
                    has_metar=station.has_metar,
                    has_taf=station.has_taf,
                ),
            )

        return merged
