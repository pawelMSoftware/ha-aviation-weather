from __future__ import annotations

from scripts.config import (
    AIRPORTS_FILE,
    AIRPORTS_URL,
    STATIONS_GZIP_FILE,
    STATIONS_URL,
    STATIONS_XML_FILE,
)
from scripts.downloaders.file_downloader import FileDownloader
from scripts.downloaders.gzip_extractor import GzipExtractor


class AirportUpdater:
    """Update airport data files."""

    def __init__(self) -> None:
        self._downloader = FileDownloader()
        self._extractor = GzipExtractor()

    def update(self) -> None:
        """Update airport data."""

        self._download_airports()

        self._download_stations()

        self._extract_stations()

        self._cleanup()

        print(
            "Airport data updated.",
        )

    def _download_airports(self) -> None:
        """Download airport database."""

        print(
            "Downloading airports.csv...",
        )

        self._downloader.download(
            AIRPORTS_URL,
            AIRPORTS_FILE,
        )

    def _download_stations(self) -> None:
        """Download weather stations."""

        print(
            "Downloading stations.cache.xml.gz...",
        )

        self._downloader.download(
            STATIONS_URL,
            STATIONS_GZIP_FILE,
        )

    def _extract_stations(self) -> None:
        """Extract station database."""

        print(
            "Extracting stations.cache.xml...",
        )

        self._extractor.extract(
            STATIONS_GZIP_FILE,
            STATIONS_XML_FILE,
        )

    def _cleanup(self) -> None:
        """Cleanup temporary files."""

        STATIONS_GZIP_FILE.unlink(
            missing_ok=True,
        )
