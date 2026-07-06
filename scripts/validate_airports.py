from __future__ import annotations

import sys
from pathlib import Path

from scripts.generators.airport_analyzer import AirportAnalyzer
from scripts.generators.airport_filter import AirportFilter
from scripts.generators.loaders.csv_airport_loader import CsvAirportLoader
from scripts.generators.loaders.station_loader import StationLoader
from scripts.generators.mergers.airport_merger import AirportMerger
from scripts.validators.airport_validator import AirportValidator


def main() -> int:
    """Validate airport data and report a summary.

    Returns a non-zero exit code when validation fails, so this can be
    wired into CI (e.g. run after `update_airports.py`, before
    `generate_airports.py`, to catch bad source data early).
    """

    root = Path(__file__).resolve().parent.parent

    csv_file = root / "scripts" / "data" / "airports.csv"
    stations_file = root / "scripts" / "data" / "stations.cache.xml"

    airports = CsvAirportLoader().load(
        csv_file,
    )

    stations = StationLoader().load(
        stations_file,
    )

    merged = AirportMerger().merge(
        airports,
        stations,
    )

    generated = AirportFilter().filter(
        merged,
    )

    result = AirportAnalyzer().analyze(
        csv_airports=airports,
        weather_stations=len(stations),
        generated_airports=generated,
    )

    success = AirportValidator().validate(
        result,
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
