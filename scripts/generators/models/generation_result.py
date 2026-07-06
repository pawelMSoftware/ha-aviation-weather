from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class GenerationResult:
    """Airport generation result."""

    countries: list[str]
    airports: int
    metar: int
    taf: int
