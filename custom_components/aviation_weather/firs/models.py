"""FIR (Flight Information Region) data model."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Fir:
    """Flight Information Region definition.

    A FIR is an airspace designation defined by ICAO within which air
    traffic services are provided. Each airport belongs to exactly one
    FIR. SIGMETs and AIRMETs are issued per FIR, not per airport.

    Attributes:
        icao:    Four-letter ICAO FIR identifier (e.g. "EPWW").
        name:    Human-readable FIR name (e.g. "Warsaw FIR").
        country: ISO 3166-1 alpha-2 country code of the issuing authority
                 (e.g. "PL"). For oceanic FIRs covering multiple countries
                 this is the country of the controlling authority.
    """

    icao: str
    name: str
    country: str
