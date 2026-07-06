"""Tests for icons.json (per-state icon overrides)."""

from __future__ import annotations

import json
from pathlib import Path

from custom_components.aviation_weather.metar.enums import FlightCategory

ICONS_FILE = (
    Path(__file__).parent.parent
    / "custom_components"
    / "aviation_weather"
    / "icons.json"
)


def _load_icons() -> dict:
    with ICONS_FILE.open(encoding="utf-8") as file:
        return json.load(file)


class TestIconsFileIsValid:
    def test_is_valid_json(self) -> None:
        assert isinstance(_load_icons(), dict)


class TestMetarSummaryIcons:
    """Every FlightCategory value must have a per-state icon, or the
    frontend falls back to the generic default icon instead of a
    category-specific one.

    icons.json state keys must be lowercase — hassfest's icon schema
    requires `[a-z0-9-_]+` regardless of the entity's actual (uppercase)
    state value; the frontend lowercases the state before looking it up
    here, so `FlightCategory.VFR` ("VFR") still resolves against the
    "vfr" key at runtime.
    """

    def test_every_flight_category_has_an_icon(self) -> None:
        state_icons = _load_icons()["entity"]["sensor"]["metar_summary"]["state"]

        for category in FlightCategory:
            assert category.value.lower() in state_icons, (
                f"FlightCategory {category.value!r} is missing an icon"
            )

    def test_state_keys_are_lowercase(self) -> None:
        """Regression guard for the hassfest schema requirement."""
        state_icons = _load_icons()["entity"]["sensor"]["metar_summary"]["state"]

        for key in state_icons:
            assert key == key.lower(), f"icons.json state key {key!r} is not lowercase"

    def test_default_icon_is_set(self) -> None:
        icons = _load_icons()["entity"]["sensor"]["metar_summary"]

        assert icons["default"].startswith("mdi:")

    def test_no_icon_is_empty(self) -> None:
        state_icons = _load_icons()["entity"]["sensor"]["metar_summary"]["state"]

        for category, icon in state_icons.items():
            assert icon.startswith("mdi:"), f"{category!r} has a non-mdi icon"


class TestSigmetIcons:
    """The SIGMET binary sensor must have both on/off state icons."""

    def test_on_and_off_icons_are_set(self) -> None:
        state_icons = _load_icons()["entity"]["binary_sensor"]["sigmet"]["state"]

        assert state_icons["on"].startswith("mdi:")
        assert state_icons["off"].startswith("mdi:")

    def test_default_icon_is_set(self) -> None:
        icons = _load_icons()["entity"]["binary_sensor"]["sigmet"]

        assert icons["default"].startswith("mdi:")
