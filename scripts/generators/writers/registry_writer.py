from __future__ import annotations

from pathlib import Path

from ..renderers.registry_renderer import RegistryRenderer
from .generated_file_writer import GeneratedFileWriter


class RegistryWriter:
    """Generate airport registry."""

    def __init__(self) -> None:
        self._renderer = RegistryRenderer()
        self._writer = GeneratedFileWriter()

    def write(
        self,
        output_directory: Path,
        countries: list[str],
    ) -> None:
        """Write registry."""

        content = self._renderer.render(
            sorted(countries),
        )

        self._writer.write(
            output_directory / "registry.py",
            content,
        )
