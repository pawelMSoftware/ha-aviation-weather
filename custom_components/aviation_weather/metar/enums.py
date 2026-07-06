"""Aviation Weather enums."""

from __future__ import annotations

from enum import StrEnum


class FlightCategory(StrEnum):
    """METAR flight category."""

    VFR = "VFR"
    MVFR = "MVFR"
    IFR = "IFR"
    LIFR = "LIFR"


class CloudCover(StrEnum):
    """METAR cloud cover."""

    CLEAR = "CLR"
    SKY_CLEAR = "SKC"
    NO_SIGNIFICANT_CLOUDS = "NSC"
    FEW = "FEW"
    SCATTERED = "SCT"
    BROKEN = "BKN"
    OVERCAST = "OVC"
    VERTICAL_VISIBILITY = "VV"


class MetarType(StrEnum):
    """METAR report type."""

    METAR = "METAR"
    SPECI = "SPECI"
    SYNOP = "SYNOP"
    BUOY = "BUOY"
    CMAN = "CMAN"


class WeatherIntensity(StrEnum):
    """Weather intensity."""

    LIGHT = "light"
    MODERATE = "moderate"
    HEAVY = "heavy"


class WeatherPhenomenon(StrEnum):
    """Weather phenomenon."""

    RAIN = "rain"
    SNOW = "snow"
    DRIZZLE = "drizzle"
    FOG = "fog"
    MIST = "mist"
    HAZE = "haze"
    THUNDERSTORM = "thunderstorm"
    FREEZING_RAIN = "freezing_rain"
