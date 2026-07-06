from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class ValidationResult:
    """Validation result."""

    csv_airports: int = 0
    weather_stations: int = 0
    generated_airports: int = 0

    duplicate_icao: int = 0
    missing_country: int = 0
    missing_coordinates: int = 0
    unknown_airport_type: int = 0
