from __future__ import annotations

from pathlib import Path

from ..groupers.airport_grouper import AirportGrouper
from ..models.airport import Airport
from ..models.generation_result import GenerationResult
from ..renderers.country_renderer import CountryRenderer
from .generated_file_writer import GeneratedFileWriter


class AirportWriter:
    """Generate airport country files."""

    def __init__(self) -> None:
        self._renderer = CountryRenderer()
        self._grouper = AirportGrouper()
        self._writer = GeneratedFileWriter()

    def write(
        self,
        output_directory: Path,
        airports: list[Airport],
    ) -> GenerationResult:
        """Write airport files."""

        countries = self._grouper.group(
            airports,
        )

        output_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

        for country, country_airports in countries.items():
            content = self._renderer.render(
                country_airports,
            )

            self._writer.write(
                output_directory / f"country_{country}.py",
                content,
            )

        return GenerationResult(
            countries=sorted(
                countries.keys(),
            ),
            airports=len(
                airports,
            ),
            metar=sum(airport.has_metar for airport in airports),
            taf=sum(airport.has_taf for airport in airports),
        )
