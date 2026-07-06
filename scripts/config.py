from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).parent

DATA_DIRECTORY = ROOT / "data"

AIRPORTS_URL = "https://ourairports.com/data/airports.csv"

STATIONS_URL = "https://aviationweather.gov/data/cache/stations.cache.xml.gz"

AIRPORTS_FILE = DATA_DIRECTORY / "airports.csv"

STATIONS_GZIP_FILE = DATA_DIRECTORY / "stations.cache.xml.gz"

STATIONS_XML_FILE = DATA_DIRECTORY / "stations.cache.xml"

FIR_FILE = DATA_DIRECTORY / "firs.csv"
