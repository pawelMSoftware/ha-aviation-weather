"""Weather entity package."""

from __future__ import annotations

from .condition_mapper import map_condition
from .entity import AviationWeatherEntity

__all__ = [
    "AviationWeatherEntity",
    "map_condition",
]
