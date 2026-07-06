"""Data models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .enums import (
    CloudCover,
    FlightCategory,
    MetarType,
    WeatherIntensity,
    WeatherPhenomenon,
)


@dataclass(slots=True)
class CloudLayer:
    """Cloud layer."""

    cover: CloudCover | str
    base: int | None


@dataclass(slots=True)
class WeatherCondition:
    """Weather condition."""

    raw: str

    intensity: WeatherIntensity | None

    phenomena: list[WeatherPhenomenon]


@dataclass(slots=True)
class MetarData:
    """METAR data."""

    airport: str
    airport_name: str | None

    latitude: float | None
    longitude: float | None
    elevation: int | None

    temperature: float | None
    dewpoint: float | None

    pressure: float | None
    sea_level_pressure: float | None

    wind_speed: int | None
    wind_gust: int | None
    wind_direction: str | None

    visibility_meters: int | None
    """Prevailing visibility in metres, parsed from the raw METAR (rawOb).

    Values:
    - None:  visibility not reported or could not be parsed (e.g. US
             statute-mile format — not converted, left as None).
    - 10000: CAVOK or 9999, meaning "10 km or more".
    - other: value exactly as reported in the METAR group (e.g. 800
             for "0800", 3500 for "3500").

    Stored in metres throughout the model; conversion to km for display
    happens only at the sensor layer via format_visibility().
    """

    flight_category: FlightCategory | str | None

    metar_type: MetarType | str | None

    weather: WeatherCondition | None

    snow_depth: float | None
    vertical_visibility: int | None

    cloud_layers: list[CloudLayer]

    observation_time: datetime | None

    raw_metar: str
