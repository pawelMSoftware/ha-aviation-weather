from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Station:
    """Weather station."""

    icao: str
    has_metar: bool
    has_taf: bool
