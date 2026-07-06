"""TAF models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .enums import TafChangeType


@dataclass(slots=True)
class TafCloudLayer:
    """TAF cloud layer."""

    cover: str | None
    base: int | None
    cloud_type: str | None


@dataclass(slots=True)
class TafForecast:
    """Single TAF forecast period."""

    time_from: datetime
    time_to: datetime

    change_type: TafChangeType | str | None

    wind_direction: str | None
    wind_speed: int | None
    wind_gust: int | None

    visibility: str | None

    weather: str | None

    clouds: list[TafCloudLayer]


@dataclass(slots=True)
class TafData:
    """TAF data."""

    airport: str
    airport_name: str | None

    latitude: float | None
    longitude: float | None
    elevation: int | None

    issue_time: datetime | None

    valid_from: datetime | None
    valid_to: datetime | None

    raw_taf: str

    forecasts: list[TafForecast]
