from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Airport:
    """Airport used by the generator."""

    icao: str
    country: str
    country_name: str
    continent: str
    name: str
    latitude: float
    longitude: float
    airport_type: str

    has_metar: bool = False
    has_taf: bool = False
    fir_icao: str = ""
