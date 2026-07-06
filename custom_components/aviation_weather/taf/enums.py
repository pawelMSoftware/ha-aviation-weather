"""TAF enums."""

from __future__ import annotations

from enum import StrEnum


class TafChangeType(StrEnum):
    """TAF forecast change type."""

    TEMPO = "TEMPO"
    FM = "FM"
    BECMG = "BECMG"
    PROB = "PROB"
