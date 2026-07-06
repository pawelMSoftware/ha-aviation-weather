from __future__ import annotations

from pathlib import Path


class AirportCleaner:
    """Clean generated airport files."""

    def clean(
        self,
        countries_directory: Path,
    ) -> None:
        """Remove generated country files."""

        if not countries_directory.exists():
            return

        for file in countries_directory.glob(
            "country_*.py",
        ):
            file.unlink()
