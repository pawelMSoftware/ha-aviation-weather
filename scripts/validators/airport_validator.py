from __future__ import annotations

from scripts.generators.models.validation_result import ValidationResult


class AirportValidator:
    """Validate generated airport data."""

    def validate(
        self,
        result: ValidationResult,
    ) -> bool:
        """Validate airport data."""

        print()

        print("Airport database")
        print("----------------")

        print(
            f"CSV airports.......... {result.csv_airports}",
        )

        print(
            f"Weather stations...... {result.weather_stations}",
        )

        print(
            f"Generated airports.... {result.generated_airports}",
        )

        print()

        print(
            f"Duplicate ICAO........ {result.duplicate_icao}",
        )

        print(
            f"Missing country....... {result.missing_country}",
        )

        print(
            f"Missing coordinates... {result.missing_coordinates}",
        )

        print(
            f"Unknown types......... {result.unknown_airport_type}",
        )

        print()

        success = (
            result.duplicate_icao == 0
            and result.missing_country == 0
            and result.missing_coordinates == 0
            and result.unknown_airport_type == 0
        )

        if success:
            print("✔ Validation passed")
        else:
            print("✘ Validation failed")

        return success
