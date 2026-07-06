from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Airport:
    """Airport definition."""

    icao: str
    country: str
    name: str
    latitude: float
    longitude: float
    has_metar: bool = True
    has_taf: bool = False
    fir_icao: str = ""
    """Four-letter ICAO identifier of the FIR that covers this airport
    (e.g. "EPWW" for Warsaw FIR, which covers EPGD, EPWA, EPKK etc.).

    Used to:
    - suggest the related FIR device in the config flow after airport
      selection ("Detected related objects: EPWW — Warsaw FIR")
    - avoid duplicate FIR devices when the user adds multiple airports
      from the same FIR
    - route SIGMET/AIRMET data to the correct FIR device

    An empty string means the FIR mapping for this airport hasn't been
    populated yet in the airport database. The integration still works
    fully for METAR/TAF — only the FIR suggestion step in the config
    flow is skipped.
    """
