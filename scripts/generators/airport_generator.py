from __future__ import annotations

import subprocess
import sys
from pathlib import Path

from .airport_filter import AirportFilter
from .cleaners.airport_cleaner import AirportCleaner
from .fir_assigner import FirAssigner
from .loaders.csv_airport_loader import CsvAirportLoader
from .loaders.station_loader import StationLoader
from .mergers.airport_merger import AirportMerger
from .models.airport import Airport
from .writers.airport_writer import AirportWriter
from .writers.country_registry_writer import CountryRegistryWriter
from .writers.registry_writer import RegistryWriter


class AirportGenerator:
    """Generate airport resources."""

    def __init__(
        self,
        root: Path,
    ) -> None:
        self._root = root

    def generate(self) -> None:
        """Generate airport resources."""

        airports = self._load_airports()

        stations = StationLoader().load(
            self._stations_file,
        )

        print(
            f"Loaded {len(airports)} airports",
        )

        print(
            f"Loaded {len(stations)} weather stations",
        )

        airports = AirportMerger().merge(
            airports,
            stations,
        )

        airports = AirportFilter().filter(
            airports,
        )

        print(
            f"Filtered to {len(airports)} airports",
        )

        print("Assigning FIR designators...")

        airports = FirAssigner().assign(
            airports,
        )

        fir_assigned = sum(1 for a in airports if a.fir_icao)
        print(
            f"FIR assigned: {fir_assigned}/{len(airports)}",
        )

        AirportCleaner().clean(
            self._countries_directory,
        )

        result = AirportWriter().write(
            self._countries_directory,
            airports,
        )

        RegistryWriter().write(
            self._airports_directory,
            result.countries,
        )

        CountryRegistryWriter().write(
            self._airports_directory,
            airports,
        )

        self._format_generated_files()

        print()

        print(
            "Generation summary",
        )

        print(
            "------------------",
        )

        print(
            f"Countries............. {len(result.countries)}",
        )

        print(
            f"Airports.............. {result.airports}",
        )

        print(
            f"METAR................. {result.metar}",
        )

        print(
            f"TAF................... {result.taf}",
        )

        print()

        print(
            "Airport files generated.",
        )

    def _format_generated_files(self) -> None:
        """Run ruff format on the generated files.

        The Jinja templates aim for ruff-compatible output, but text
        wrapping for long airport names doesn't always match ruff's own
        line-length decisions exactly. Running `ruff format` here keeps
        the generated files consistent with the rest of the codebase
        without needing a separate manual step after every generation.
        """

        try:
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "ruff",
                    "format",
                    str(self._airports_directory),
                ],
                check=True,
                capture_output=True,
                text=True,
            )
        except FileNotFoundError:
            print(
                "ruff not found, skipping auto-formatting of generated files. "
                "Run `ruff format` manually, or install dev dependencies.",
            )
        except subprocess.CalledProcessError as error:
            print(
                f"ruff format failed (exit {error.returncode}): {error.stderr}",
            )

    @property
    def _csv_file(self) -> Path:
        """Return CSV file path."""

        return self._root / "scripts" / "data" / "airports.csv"

    @property
    def _airports_directory(self) -> Path:
        """Return airports directory."""

        return self._root / "custom_components" / "aviation_weather" / "airports"

    @property
    def _countries_directory(self) -> Path:
        """Return countries directory."""

        return self._airports_directory / "countries"

    @property
    def _stations_file(self) -> Path:
        """Return stations XML path."""

        return self._root / "scripts" / "data" / "stations.cache.xml"

    def _load_airports(
        self,
    ) -> list[Airport]:
        """Load airports."""

        return CsvAirportLoader().load(
            self._csv_file,
        )
