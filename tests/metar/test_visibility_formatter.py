"""Tests for format_visibility — the visibility display formatter."""

from __future__ import annotations

import pytest

from custom_components.aviation_weather.metar.sensor import format_visibility


class TestFormatVisibility:
    """format_visibility converts stored metre values to display strings.

    Key rules:
    - None         → None (sensor shows as unavailable)
    - < 1000 m     → "X m"
    - >= 1000 m    → "X.X km" (trailing .0 stripped)
    - 10000        → "10+ km" (CAVOK / 9999 sentinel)
    """

    @pytest.mark.parametrize(
        ("meters", "expected"),
        [
            # Below 1 km — display in metres
            (100, "100 m"),
            (500, "500 m"),
            (800, "800 m"),
            (999, "999 m"),
            # Exactly 1 km and above — display in km, no trailing zero
            (1000, "1 km"),
            (1500, "1.5 km"),
            (2000, "2 km"),
            (3500, "3.5 km"),
            (5000, "5 km"),
            (7000, "7 km"),
            (8000, "8 km"),
            (9000, "9 km"),
            # CAVOK / 9999 sentinel — always "10+ km"
            (10000, "10+ km"),
        ],
    )
    def test_formatting(self, meters: int, expected: str) -> None:
        assert format_visibility(meters) == expected

    def test_none_returns_none(self) -> None:
        """None input (visibility not available) must return None,
        not a string like "None m", so the sensor shows as unavailable."""
        assert format_visibility(None) is None

    def test_10000_always_shows_plus(self) -> None:
        """10000 is a sentinel meaning 'at least 10 km' (CAVOK or 9999),
        not exactly 10 km — so it must always render as '10+ km'."""
        assert format_visibility(10000) == "10+ km"
        assert "+" in format_visibility(10000)

    def test_km_values_have_no_trailing_zero(self) -> None:
        """'7.0 km' must be simplified to '7 km'."""
        assert format_visibility(7000) == "7 km"
        assert format_visibility(2000) == "2 km"

    def test_subkm_values_stay_in_metres(self) -> None:
        """Values below 1000 must never be displayed in km."""
        result = format_visibility(800)
        assert "km" not in result
        assert "m" in result
