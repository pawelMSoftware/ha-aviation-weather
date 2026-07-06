"""Shared airspace advisory model and helpers (SIGMET, future AIRMET)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from homeassistant.util import dt as dt_util


@dataclass(slots=True)
class AirspaceAdvisory:
    """Base model for FIR-scoped airspace hazard advisories.

    Shared by SIGMET today and AIRMET in the future, so both can reuse
    `active_advisories` below without duplicating the active-window
    check.
    """

    id: str
    fir_id: str
    fir_name: str | None
    hazard: str | None
    qualifier: str | None
    base: str | None
    top: str | None
    valid_from: datetime
    valid_to: datetime
    coordinates: list[Any]
    raw: str
    extra: dict[str, Any]


def active_advisories(
    advisories: list[AirspaceAdvisory],
    *,
    now: datetime | None = None,
) -> list[AirspaceAdvisory]:
    """Return advisories whose validity window covers `now`.

    The single shared helper for "is this advisory currently active" —
    entities must call this (or a coordinator property that wraps it)
    rather than re-implementing the `valid_from <= now <= valid_to`
    check themselves.
    """
    now = now or dt_util.utcnow()

    return [
        advisory
        for advisory in advisories
        if advisory.valid_from <= now <= advisory.valid_to
    ]
