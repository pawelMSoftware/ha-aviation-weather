from __future__ import annotations

import gzip
import shutil
from pathlib import Path


class GzipExtractor:
    """Extract gzip archives."""

    def extract(
        self,
        source: Path,
        destination: Path,
    ) -> None:
        """Extract gzip file."""

        with (
            gzip.open(
                source,
                "rb",
            ) as compressed,
            destination.open(
                "wb",
            ) as extracted,
        ):
            shutil.copyfileobj(
                compressed,
                extracted,
            )
