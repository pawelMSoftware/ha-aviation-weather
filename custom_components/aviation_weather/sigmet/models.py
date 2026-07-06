"""SIGMET models."""

from __future__ import annotations

from dataclasses import dataclass

from ..airspace_advisory import AirspaceAdvisory


@dataclass(slots=True)
class Sigmet(AirspaceAdvisory):
    """A single SIGMET (Significant Meteorological Information) advisory."""
