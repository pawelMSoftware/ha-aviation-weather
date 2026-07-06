from __future__ import annotations

import csv
from pathlib import Path

import pycountry

from ..continents import continent_for_country
from ..models.airport import Airport

# Manual overrides for country names that are missing, ambiguous, or
# unhelpful when sourced from pycountry:
# - "XK" (Kosovo): ISO 3166-1 has no assigned code for Kosovo at all.
# - "CD"/"CG": both are named "Congo" in some form, and neither has a
#   pycountry `common_name`, so they're indistinguishable in a dropdown
#   without these overrides.
COUNTRY_NAME_OVERRIDES = {
    "XK": "Kosovo",
    "CD": "DR Congo",
    "CG": "Republic of the Congo",
}


class CsvAirportLoader:
    """Load airports from OurAirports CSV."""

    REQUIRED_COLUMNS = {
        "ident",
        "type",
        "name",
        "latitude_deg",
        "longitude_deg",
        "iso_country",
    }

    def load(
        self,
        csv_file: Path,
    ) -> list[Airport]:
        """Load airports from CSV."""

        with csv_file.open(
            encoding="utf-8",
            newline="",
        ) as file:
            reader = csv.DictReader(file)

            self._validate_columns(
                reader.fieldnames,
            )

            airports: list[Airport] = []

            for row in reader:
                airport = self._parse_row(
                    row,
                )

                if airport is not None:
                    airports.append(
                        airport,
                    )

        return airports

    def _validate_columns(
        self,
        columns: list[str] | None,
    ) -> None:
        """Validate CSV columns."""

        if columns is None:
            raise ValueError(
                "CSV file is empty.",
            )

        missing = self.REQUIRED_COLUMNS.difference(
            columns,
        )

        if missing:
            raise ValueError(
                f"Missing required columns: {', '.join(sorted(missing))}",
            )

    def _parse_float(
        self,
        value: str,
    ) -> float | None:
        """Parse a float value, returning None if invalid or empty."""

        value = value.strip()

        if not value:
            return None

        try:
            return float(value)
        except ValueError:
            return None

    def _country_name(
        self,
        country_code: str,
    ) -> str:
        """Return country name.

        Prefers pycountry's `common_name` (e.g. "North Korea", "Vietnam")
        over the formal ISO 3166-1 `name` (e.g. "Korea, Democratic
        People's Republic of", "Viet Nam") where available, since the
        common name reads better in a dropdown aimed at end users.
        """

        if country_code in COUNTRY_NAME_OVERRIDES:
            return COUNTRY_NAME_OVERRIDES[country_code]

        country = pycountry.countries.get(
            alpha_2=country_code,
        )

        if country is None:
            return country_code

        return (
            getattr(
                country,
                "common_name",
                None,
            )
            or country.name
        )

    def _parse_row(
        self,
        row: dict[str, str],
    ) -> Airport | None:
        """Parse CSV row.

        Returns None (skipping the row) if the ident is missing or the
        coordinates cannot be parsed as floats. OurAirports is a
        community-maintained dataset, so a handful of malformed rows
        should not abort the whole import.
        """

        if not row["ident"]:
            return None

        latitude = self._parse_float(
            row["latitude_deg"],
        )
        longitude = self._parse_float(
            row["longitude_deg"],
        )

        if latitude is None or longitude is None:
            print(
                f"Skipping {row['ident']!r}: invalid coordinates "
                f"(lat={row['latitude_deg']!r}, lon={row['longitude_deg']!r})",
            )
            return None

        country = row["iso_country"].strip().upper()

        return Airport(
            icao=row["ident"].strip().upper(),
            country=country,
            country_name=self._country_name(
                country,
            ),
            continent=continent_for_country(
                country,
            ),
            name=row["name"].strip(),
            latitude=latitude,
            longitude=longitude,
            airport_type=row["type"].strip(),
        )
