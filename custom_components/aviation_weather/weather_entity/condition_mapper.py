"""Map METAR data to Home Assistant's standard weather condition strings."""

from __future__ import annotations

from homeassistant.components.weather import (
    ATTR_CONDITION_CLEAR_NIGHT,
    ATTR_CONDITION_CLOUDY,
    ATTR_CONDITION_FOG,
    ATTR_CONDITION_LIGHTNING,
    ATTR_CONDITION_LIGHTNING_RAINY,
    ATTR_CONDITION_PARTLYCLOUDY,
    ATTR_CONDITION_POURING,
    ATTR_CONDITION_RAINY,
    ATTR_CONDITION_SNOWY,
    ATTR_CONDITION_SNOWY_RAINY,
    ATTR_CONDITION_SUNNY,
    ATTR_CONDITION_WINDY,
)

from ..metar.enums import CloudCover, WeatherIntensity, WeatherPhenomenon
from ..metar.models import MetarData

# Wind speed (knots) above which "windy" takes priority over a clear-sky
# reading, when no other phenomenon is reported. 20kt is a commonly used
# threshold for "noticeably windy" in aviation weather briefings.
WINDY_THRESHOLD_KT = 20

# Cloud cover codes that count as "overcast enough" to report `cloudy`
# rather than `partlycloudy`, ordered from least to most covered.
OVERCAST_COVERS = frozenset(
    {
        CloudCover.BROKEN,
        CloudCover.OVERCAST,
        CloudCover.VERTICAL_VISIBILITY,
    },
)

PARTLY_CLOUDY_COVERS = frozenset(
    {
        CloudCover.FEW,
        CloudCover.SCATTERED,
    },
)


def map_condition(
    metar: MetarData,
    *,
    is_daytime: bool,
) -> str:
    """Map METAR data to a Home Assistant weather condition string.

    Priority order (highest first): thunderstorms, then snow, then
    rain/drizzle, then fog/mist/haze, then strong wind, then cloud
    cover, finally a clear-sky reading based on time of day. This
    mirrors how a pilot would read a METAR: hazards and precipitation
    matter more than ambient cloud cover.

    Always returns a condition string: METAR omits the clouds array
    entirely far more often than it reports an explicit clear-sky code
    (CLR/SKC/NSC), so the absence of any reported phenomenon or cloud
    layer is treated as clear sky rather than "unknown".
    """

    phenomena = (
        set(
            metar.weather.phenomena,
        )
        if metar.weather
        else set()
    )

    is_heavy = bool(
        metar.weather and metar.weather.intensity == WeatherIntensity.HEAVY,
    )

    if WeatherPhenomenon.THUNDERSTORM in phenomena:
        has_rain = bool(
            phenomena
            & {
                WeatherPhenomenon.RAIN,
                WeatherPhenomenon.DRIZZLE,
                WeatherPhenomenon.FREEZING_RAIN,
            },
        )
        return ATTR_CONDITION_LIGHTNING_RAINY if has_rain else ATTR_CONDITION_LIGHTNING

    if WeatherPhenomenon.SNOW in phenomena:
        has_rain = bool(
            phenomena
            & {
                WeatherPhenomenon.RAIN,
                WeatherPhenomenon.DRIZZLE,
                WeatherPhenomenon.FREEZING_RAIN,
            },
        )
        return ATTR_CONDITION_SNOWY_RAINY if has_rain else ATTR_CONDITION_SNOWY

    if phenomena & {
        WeatherPhenomenon.RAIN,
        WeatherPhenomenon.DRIZZLE,
        WeatherPhenomenon.FREEZING_RAIN,
    }:
        return ATTR_CONDITION_POURING if is_heavy else ATTR_CONDITION_RAINY

    if phenomena & {
        WeatherPhenomenon.FOG,
        WeatherPhenomenon.MIST,
        WeatherPhenomenon.HAZE,
    }:
        return ATTR_CONDITION_FOG

    cloud_covers = {
        layer.cover
        for layer in metar.cloud_layers
        if isinstance(
            layer.cover,
            CloudCover,
        )
    }

    if (
        metar.wind_speed is not None
        and metar.wind_speed >= WINDY_THRESHOLD_KT
        and not (cloud_covers & OVERCAST_COVERS)
    ):
        return ATTR_CONDITION_WINDY

    if cloud_covers & OVERCAST_COVERS:
        return ATTR_CONDITION_CLOUDY

    if cloud_covers & PARTLY_CLOUDY_COVERS:
        return ATTR_CONDITION_PARTLYCLOUDY

    # Either an explicit "clear" cover code (CLR / SKC / NSC), or no
    # cloud layers reported at all. METAR omits the clouds array
    # entirely far more often than it reports an explicit clear-sky
    # code, so the absence of any layer also means clear sky here, not
    # "insufficient data".
    return ATTR_CONDITION_SUNNY if is_daytime else ATTR_CONDITION_CLEAR_NIGHT
