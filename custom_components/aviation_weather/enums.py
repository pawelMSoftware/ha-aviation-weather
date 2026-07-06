from __future__ import annotations

from enum import StrEnum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .airports.models import Airport


class AdditionalEntity(StrEnum):
    """Additional entities available in the integration."""

    METAR_SENSORS = "metar_sensors"
    TAF = "taf"

    @property
    def enabled_by_default(self) -> bool:
        """Return whether entity is enabled by default."""

        return False

    def is_available_for(
        self,
        airport: Airport,
    ) -> bool:
        """Return whether this entity makes sense for the given airport.

        METAR details are available for every airport in the database
        (METAR availability is a requirement for inclusion), but TAF
        forecasts are only published for a subset of airports.
        """

        match self:
            case AdditionalEntity.TAF:
                return airport.has_taf

            case _:
                return True

    @classmethod
    def options(
        cls,
        airport: Airport | None = None,
    ) -> list[AdditionalEntity]:
        """Return available additional entities.

        If `airport` is given, only entities that make sense for that
        airport are returned (e.g. TAF is omitted for airports that
        don't publish TAF forecasts).
        """

        all_entities = list(cls)

        if airport is None:
            return all_entities

        return [
            entity
            for entity in all_entities
            if entity.is_available_for(
                airport,
            )
        ]

    @classmethod
    def default_values(cls) -> list[str]:
        """Return default enabled entity values."""

        return [entity.value for entity in cls.options() if entity.enabled_by_default]


class FirAdditionalEntity(StrEnum):
    """Additional entities available for FIR entries.

    Mirrors AdditionalEntity's shape for airport entries. Kept as a
    separate enum (rather than adding members to AdditionalEntity)
    since it gates FIR-only entities and has no notion of per-airport
    availability — this also gives future AIRMET support a ready-made
    second member here.
    """

    SIGMET_SENSORS = "sigmet_sensors"

    @property
    def enabled_by_default(self) -> bool:
        """Return whether entity is enabled by default."""

        return False

    @classmethod
    def options(cls) -> list[FirAdditionalEntity]:
        """Return available additional entities for FIR entries."""

        return list(cls)

    @classmethod
    def default_values(cls) -> list[str]:
        """Return default enabled entity values."""

        return [entity.value for entity in cls.options() if entity.enabled_by_default]
