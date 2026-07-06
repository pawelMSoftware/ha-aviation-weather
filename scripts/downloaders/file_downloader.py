from __future__ import annotations

from pathlib import Path

import httpx


class FileDownloader:
    """Download files from HTTP."""

    def download(
        self,
        url: str,
        destination: Path,
    ) -> None:
        """Download file."""

        destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        with httpx.Client(
            follow_redirects=True,
            timeout=60,
        ) as client:
            response = client.get(
                url,
            )

            response.raise_for_status()

            destination.write_bytes(
                response.content,
            )
