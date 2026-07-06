"""Tests for the METAR -> Home Assistant weather condition mapper."""

from __future__ import annotations

import pytest

from custom_components.aviation_weather.metar.enums import (
    CloudCover,
    WeatherIntensity,
    WeatherPhenomenon,
)
from custom_components.aviation_weather.metar.models import (
    CloudLayer,
    MetarData,
    WeatherCondition,
)
from custom_components.aviation_weather.weather_entity.condition_mapper import (
    map_condition,
)


def _make_metar(
    *,
    wind_speed: int | None = None,
    cloud_layers: list[CloudLayer] | None = None,
    weather: WeatherCondition | None = None,
) -> MetarData:
    """Build a minimal MetarData for condition-mapping tests."""
    return MetarData(
        airport="TEST",
        airport_name=None,
        latitude=None,
        longitude=None,
        elevation=None,
        temperature=None,
        dewpoint=None,
        pressure=None,
        sea_level_pressure=None,
        wind_speed=wind_speed,
        wind_gust=None,
        wind_direction=None,
        visibility_meters=None,
        flight_category=None,
        metar_type=None,
        weather=weather,
        snow_depth=None,
        vertical_visibility=None,
        cloud_layers=cloud_layers or [],
        observation_time=None,
        raw_metar="",
    )


class TestNoDataFallback:
    """METAR very commonly omits the clouds array entirely when the sky
    is clear, rather than reporting an explicit CLR/SKC code. Treating
    "no cloud layers" as "unknown" would make most clear-sky airports
    show up as unknown — so the mapper treats it as clear sky instead.
    """

    def test_no_phenomena_and_no_clouds_is_treated_as_clear_sky(self) -> None:
        metar = _make_metar()

        assert map_condition(metar, is_daytime=True) == "sunny"
        assert map_condition(metar, is_daytime=False) == "clear-night"


class TestClearSky:
    """Explicitly reported clear sky maps to sunny/clear-night based on
    time of day."""

    def test_clear_sky_during_day_is_sunny(self) -> None:
        metar = _make_metar(
            cloud_layers=[CloudLayer(cover=CloudCover.CLEAR, base=None)],
        )

        assert map_condition(metar, is_daytime=True) == "sunny"

    def test_clear_sky_at_night_is_clear_night(self) -> None:
        metar = _make_metar(
            cloud_layers=[CloudLayer(cover=CloudCover.CLEAR, base=None)],
        )

        assert map_condition(metar, is_daytime=False) == "clear-night"

    def test_sky_clear_and_no_significant_clouds_also_count_as_clear(
        self,
    ) -> None:
        for cover in (CloudCover.SKY_CLEAR, CloudCover.NO_SIGNIFICANT_CLOUDS):
            metar = _make_metar(
                cloud_layers=[CloudLayer(cover=cover, base=None)],
            )

            assert map_condition(metar, is_daytime=True) == "sunny"


class TestCloudCover:
    """Cloud cover alone (no precipitation) maps to cloudy/partlycloudy."""

    def test_broken_clouds_is_cloudy(self) -> None:
        metar = _make_metar(
            cloud_layers=[CloudLayer(cover=CloudCover.BROKEN, base=2000)],
        )

        assert map_condition(metar, is_daytime=True) == "cloudy"

    def test_overcast_is_cloudy(self) -> None:
        metar = _make_metar(
            cloud_layers=[CloudLayer(cover=CloudCover.OVERCAST, base=1000)],
        )

        assert map_condition(metar, is_daytime=True) == "cloudy"

    def test_few_clouds_is_partlycloudy(self) -> None:
        metar = _make_metar(
            cloud_layers=[CloudLayer(cover=CloudCover.FEW, base=2500)],
        )

        assert map_condition(metar, is_daytime=True) == "partlycloudy"

    def test_scattered_clouds_is_partlycloudy(self) -> None:
        metar = _make_metar(
            cloud_layers=[CloudLayer(cover=CloudCover.SCATTERED, base=3000)],
        )

        assert map_condition(metar, is_daytime=True) == "partlycloudy"

    def test_multiple_layers_uses_the_most_covered_one(self) -> None:
        """FEW + OVC together should read as cloudy (overcast wins),
        matching how a pilot would summarize the sky condition."""
        metar = _make_metar(
            cloud_layers=[
                CloudLayer(cover=CloudCover.FEW, base=1500),
                CloudLayer(cover=CloudCover.OVERCAST, base=4000),
            ],
        )

        assert map_condition(metar, is_daytime=True) == "cloudy"


class TestThunderstorms:
    """Thunderstorms take priority over everything except not being
    reported at all."""

    def test_thunderstorm_alone_is_lightning(self) -> None:
        metar = _make_metar(
            weather=WeatherCondition(
                raw="TS",
                intensity=None,
                phenomena=[WeatherPhenomenon.THUNDERSTORM],
            ),
        )

        assert map_condition(metar, is_daytime=True) == "lightning"

    def test_thunderstorm_with_rain_is_lightning_rainy(self) -> None:
        metar = _make_metar(
            weather=WeatherCondition(
                raw="TSRA",
                intensity=None,
                phenomena=[
                    WeatherPhenomenon.THUNDERSTORM,
                    WeatherPhenomenon.RAIN,
                ],
            ),
        )

        assert map_condition(metar, is_daytime=True) == "lightning-rainy"

    def test_thunderstorm_takes_priority_over_heavy_cloud_cover(self) -> None:
        metar = _make_metar(
            cloud_layers=[CloudLayer(cover=CloudCover.OVERCAST, base=500)],
            weather=WeatherCondition(
                raw="TS",
                intensity=None,
                phenomena=[WeatherPhenomenon.THUNDERSTORM],
            ),
        )

        assert map_condition(metar, is_daytime=True) == "lightning"


class TestSnow:
    """Snow takes priority over plain rain/cloud cover."""

    def test_snow_alone_is_snowy(self) -> None:
        metar = _make_metar(
            weather=WeatherCondition(
                raw="-SN",
                intensity=WeatherIntensity.LIGHT,
                phenomena=[WeatherPhenomenon.SNOW],
            ),
        )

        assert map_condition(metar, is_daytime=True) == "snowy"

    def test_snow_with_rain_is_snowy_rainy(self) -> None:
        metar = _make_metar(
            weather=WeatherCondition(
                raw="SNRA",
                intensity=None,
                phenomena=[WeatherPhenomenon.SNOW, WeatherPhenomenon.RAIN],
            ),
        )

        assert map_condition(metar, is_daytime=True) == "snowy-rainy"


class TestRain:
    """Rain/drizzle map to rainy, or pouring if reported as heavy."""

    def test_moderate_rain_is_rainy(self) -> None:
        metar = _make_metar(
            weather=WeatherCondition(
                raw="RA",
                intensity=None,
                phenomena=[WeatherPhenomenon.RAIN],
            ),
        )

        assert map_condition(metar, is_daytime=True) == "rainy"

    def test_heavy_rain_is_pouring(self) -> None:
        metar = _make_metar(
            weather=WeatherCondition(
                raw="+RA",
                intensity=WeatherIntensity.HEAVY,
                phenomena=[WeatherPhenomenon.RAIN],
            ),
        )

        assert map_condition(metar, is_daytime=True) == "pouring"

    def test_drizzle_is_rainy(self) -> None:
        metar = _make_metar(
            weather=WeatherCondition(
                raw="DZ",
                intensity=None,
                phenomena=[WeatherPhenomenon.DRIZZLE],
            ),
        )

        assert map_condition(metar, is_daytime=True) == "rainy"


class TestFogMistHaze:
    """Fog, mist, and haze all map to the single `fog` condition."""

    @pytest.mark.parametrize(
        "phenomenon",
        [WeatherPhenomenon.FOG, WeatherPhenomenon.MIST, WeatherPhenomenon.HAZE],
    )
    def test_each_obscuration_maps_to_fog(self, phenomenon: WeatherPhenomenon) -> None:
        metar = _make_metar(
            weather=WeatherCondition(
                raw="x",
                intensity=None,
                phenomena=[phenomenon],
            ),
        )

        assert map_condition(metar, is_daytime=True) == "fog"


class TestWind:
    """Strong wind is reported as `windy` only when there's no
    significant cloud cover to take priority instead."""

    def test_strong_wind_with_clear_sky_is_windy(self) -> None:
        metar = _make_metar(
            wind_speed=25,
            cloud_layers=[CloudLayer(cover=CloudCover.FEW, base=2000)],
        )

        assert map_condition(metar, is_daytime=True) == "windy"

    def test_strong_wind_with_overcast_is_cloudy_not_windy(self) -> None:
        """Overcast skies are visually more salient than wind, so cloud
        cover wins over a windy reading."""
        metar = _make_metar(
            wind_speed=25,
            cloud_layers=[CloudLayer(cover=CloudCover.OVERCAST, base=1000)],
        )

        assert map_condition(metar, is_daytime=True) == "cloudy"

    def test_light_wind_does_not_trigger_windy(self) -> None:
        metar = _make_metar(
            wind_speed=5,
            cloud_layers=[CloudLayer(cover=CloudCover.FEW, base=2000)],
        )

        assert map_condition(metar, is_daytime=True) == "partlycloudy"
