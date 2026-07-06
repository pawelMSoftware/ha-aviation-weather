from __future__ import annotations

from pathlib import Path


class GeneratedFileWriter:
    """Write generated files."""

    def write(
        self,
        path: Path,
        content: str,
    ) -> None:
        """Write file."""

        path.write_text(
            content.rstrip() + "\n",
            encoding="utf-8",
        )
