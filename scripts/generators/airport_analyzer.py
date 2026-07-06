from __future__ import annotations

from .models.airport import Airport
from .models.validation_result import ValidationResult

KNOWN_AIRPORT_TYPES = frozenset(
    {
        "small_airport",
        "medium_airport",
        "large_airport",
        "heliport",
        "seaplane_base",
        "balloonport",
        "closed",
    },
)


class AirportAnalyzer:
    """Compute validation metrics from loaded airport/station data."""

    def analyze(
        self,
        csv_airports: list[Airport],
        weather_stations: int,
        generated_airports: list[Airport],
    ) -> ValidationResult:
        """Compute a ValidationResult from the generation inputs/outputs."""

        return ValidationResult(
            csv_airports=len(csv_airports),
            weather_stations=weather_stations,
            generated_airports=len(generated_airports),
            duplicate_icao=self._count_duplicate_icao(
                csv_airports,
            ),
            missing_country=self._count_missing_country(
                csv_airports,
            ),
            missing_coordinates=self._count_missing_coordinates(
                csv_airports,
            ),
            unknown_airport_type=self._count_unknown_airport_type(
                csv_airports,
            ),
        )

    def _count_duplicate_icao(
        self,
        airports: list[Airport],
    ) -> int:
        """Count ICAO codes that appear more than once."""
        seen: set[str] = set()
        duplicates = 0

        for airport in airports:
            if airport.icao in seen:
                duplicates += 1
            else:
                seen.add(
                    airport.icao,
                )

        return duplicates

    def _count_missing_country(
        self,
        airports: list[Airport],
    ) -> int:
        """Count airports without a country code."""
        return sum(1 for airport in airports if not airport.country)

    def _count_missing_coordinates(
        self,
        airports: list[Airport],
    ) -> int:
        """Count airports with missing/zero coordinates.

        Note: latitude/longitude of exactly 0.0 is treated as "missing"
        here, matching the assumption already made by AirportFilter.
        This intentionally excludes the (very small) set of real airports
        located exactly on the equator or prime meridian.
        """
        return sum(
            1 for airport in airports if airport.latitude == 0 or airport.longitude == 0
        )

    def _count_unknown_airport_type(
        self,
        airports: list[Airport],
    ) -> int:
        """Count airports with a type not in the known set."""
        return sum(
            1 for airport in airports if airport.airport_type not in KNOWN_AIRPORT_TYPES
        )
