"""Tests for map_cloud_coverage (METAR cloud cover -> percentage)."""

from __future__ import annotations

import pytest

from custom_components.aviation_weather.metar.enums import CloudCover
from custom_components.aviation_weather.metar.models import CloudLayer, MetarData
from custom_components.aviation_weather.weather_entity.cloud_coverage_mapper import (
    map_cloud_coverage,
)


def _make_metar(
    cloud_layers: list[CloudLayer],
) -> MetarData:
    """Build a minimal MetarData for cloud coverage tests."""
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
        wind_speed=None,
        wind_gust=None,
        wind_direction=None,
        visibility_meters=None,
        flight_category=None,
        metar_type=None,
        weather=None,
        snow_depth=None,
        vertical_visibility=None,
        cloud_layers=cloud_layers,
        observation_time=None,
        raw_metar="",
    )


class TestNoData:
    """No cloud layer data at all returns None, not 0%."""

    def test_empty_cloud_layers_returns_none(self) -> None:
        metar = _make_metar([])

        assert map_cloud_coverage(metar) is None


class TestSingleLayer:
    """Each cover code maps to its representative percentage."""

    @pytest.mark.parametrize(
        ("cover", "expected_percent"),
        [
            (CloudCover.CLEAR, 0),
            (CloudCover.SKY_CLEAR, 0),
            (CloudCover.NO_SIGNIFICANT_CLOUDS, 0),
            (CloudCover.FEW, 25),
            (CloudCover.SCATTERED, 50),
            (CloudCover.BROKEN, 88),
            (CloudCover.OVERCAST, 100),
            (CloudCover.VERTICAL_VISIBILITY, 100),
        ],
    )
    def test_each_cover_code(self, cover: CloudCover, expected_percent: float) -> None:
        metar = _make_metar(
            [CloudLayer(cover=cover, base=1000)],
        )

        assert map_cloud_coverage(metar) == expected_percent


class TestMultipleLayers:
    """Layers are cumulative: the maximum coverage across all layers
    wins, matching how METAR layers stack (a higher OVC layer means
    the sky is 100% covered overall, even with a FEW layer below it).
    """

    def test_higher_layer_with_more_coverage_wins(self) -> None:
        metar = _make_metar(
            [
                CloudLayer(cover=CloudCover.FEW, base=1500),
                CloudLayer(cover=CloudCover.OVERCAST, base=4000),
            ],
        )

        assert map_cloud_coverage(metar) == 100

    def test_order_does_not_matter(self) -> None:
        metar = _make_metar(
            [
                CloudLayer(cover=CloudCover.OVERCAST, base=4000),
                CloudLayer(cover=CloudCover.FEW, base=1500),
            ],
        )

        assert map_cloud_coverage(metar) == 100

    def test_two_partial_layers_takes_the_larger(self) -> None:
        metar = _make_metar(
            [
                CloudLayer(cover=CloudCover.FEW, base=1500),
                CloudLayer(cover=CloudCover.SCATTERED, base=3000),
            ],
        )

        assert map_cloud_coverage(metar) == 50


class TestUnrecognizedCoverCode:
    """A cloud layer with a cover value that isn't a recognized
    CloudCover enum member (e.g. an unmapped/unexpected string from the
    API) is ignored, rather than raising a KeyError."""

    def test_unrecognized_cover_is_ignored(self) -> None:
        metar = _make_metar(
            [CloudLayer(cover="XYZ", base=1000)],
        )

        assert map_cloud_coverage(metar) is None

    def test_unrecognized_cover_mixed_with_known_cover(self) -> None:
        metar = _make_metar(
            [
                CloudLayer(cover="XYZ", base=1000),
                CloudLayer(cover=CloudCover.SCATTERED, base=3000),
            ],
        )

        assert map_cloud_coverage(metar) == 50
