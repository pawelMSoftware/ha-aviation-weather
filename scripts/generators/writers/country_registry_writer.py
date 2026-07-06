from __future__ import annotations

from pathlib import Path

from ..continents import CONTINENT_NAMES
from ..models.airport import Airport
from ..renderers.country_registry_renderer import CountryRegistryRenderer
from .generated_file_writer import GeneratedFileWriter


class CountryRegistryWriter:
    """Generate country registry."""

    def __init__(self) -> None:
        self._renderer = CountryRegistryRenderer()
        self._writer = GeneratedFileWriter()

    def write(
        self,
        output_directory: Path,
        airports: list[Airport],
    ) -> None:
        """Write country registry."""

        countries = {airport.country: airport.country_name for airport in airports}
        continents = {airport.country: airport.continent for airport in airports}

        content = self._renderer.render(
            countries=dict(
                sorted(countries.items()),
            ),
            continents=dict(
                sorted(continents.items()),
            ),
            continent_names=dict(
                sorted(CONTINENT_NAMES.items()),
            ),
        )

        self._writer.write(
            output_directory / "country_registry.py",
            content,
        )
