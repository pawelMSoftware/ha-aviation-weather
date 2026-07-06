"""Tests for FirSigmetBinarySensor (unique_id, on/off, attributes, device_info)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from custom_components.aviation_weather.sigmet.binary_sensor import (
    FirSigmetBinarySensor,
)
from custom_components.aviation_weather.sigmet.models import Sigmet


def _make_coordinator(active_sigmets: list[Sigmet]):
    """Build a mock SigmetCoordinator exposing the given active SIGMETs."""
    coordinator = MagicMock()
    coordinator.active_sigmets = active_sigmets
    coordinator.last_update_success = True
    return coordinator


def _make_sigmet(
    *,
    sigmet_id: str = "sigmet-1",
    hazard: str | None = "TURB",
    valid_from: datetime | None = None,
    valid_to: datetime | None = None,
) -> Sigmet:
    return Sigmet(
        id=sigmet_id,
        fir_id="EPWW",
        fir_name="WARSZAWA FIR",
        hazard=hazard,
        qualifier="SEV",
        base="FL180",
        top="FL360",
        valid_from=valid_from or datetime(2026, 7, 3, 10, tzinfo=UTC),
        valid_to=valid_to or datetime(2026, 7, 3, 14, tzinfo=UTC),
        coordinates=[],
        raw="WSPL31 EPWW",
        extra={},
    )


@pytest.fixture
def active_sigmet() -> Sigmet:
    return _make_sigmet()


class TestOn:
    """Binary sensor is on when active SIGMETs exist."""

    def test_is_on_when_active_sigmet_exists(self, active_sigmet: Sigmet) -> None:
        coordinator = _make_coordinator([active_sigmet])
        sensor = FirSigmetBinarySensor(coordinator=coordinator, fir_icao="EPWW")

        assert sensor.is_on is True

    def test_unique_id(self, active_sigmet: Sigmet) -> None:
        coordinator = _make_coordinator([active_sigmet])
        sensor = FirSigmetBinarySensor(coordinator=coordinator, fir_icao="EPWW")

        assert sensor.unique_id == "EPWW_sigmet"

    def test_translation_key_is_sigmet(self, active_sigmet: Sigmet) -> None:
        """translation_key must match the "sigmet" key used in
        icons.json for this entity's on/off icon; it must not also set
        a static _attr_icon, which would take priority over icons.json
        and silently defeat the per-state icons."""
        coordinator = _make_coordinator([active_sigmet])
        sensor = FirSigmetBinarySensor(coordinator=coordinator, fir_icao="EPWW")

        assert sensor.translation_key == "sigmet"
        assert not hasattr(sensor, "_attr_icon")

    def test_device_info_attaches_to_fir_device_not_airport(
        self, active_sigmet: Sigmet
    ) -> None:
        coordinator = _make_coordinator([active_sigmet])
        sensor = FirSigmetBinarySensor(coordinator=coordinator, fir_icao="EPWW")

        device_info = sensor.device_info

        assert device_info["name"] == "EPWW"
        assert device_info["model"] == "FIR"
        assert device_info["identifiers"] == {("aviation_weather", "EPWW")}

    def test_attributes_include_active_count_hazards_valid_until_sigmets(
        self, active_sigmet: Sigmet
    ) -> None:
        coordinator = _make_coordinator([active_sigmet])
        sensor = FirSigmetBinarySensor(coordinator=coordinator, fir_icao="EPWW")

        attrs = sensor.extra_state_attributes

        assert attrs["active_count"] == 1
        assert attrs["hazards"] == ["TURB"]
        assert attrs["valid_until"] == datetime(2026, 7, 3, 14, tzinfo=UTC)
        assert len(attrs["sigmets"]) == 1
        assert attrs["sigmets"][0]["id"] == "sigmet-1"
        assert attrs["sigmets"][0]["fir_id"] == "EPWW"
        assert attrs["sigmets"][0]["hazard"] == "TURB"

    def test_hazards_are_unique_and_ordered(self) -> None:
        sigmets = [
            _make_sigmet(sigmet_id="a", hazard="TURB"),
            _make_sigmet(sigmet_id="b", hazard="ICE"),
            _make_sigmet(sigmet_id="c", hazard="TURB"),
        ]
        coordinator = _make_coordinator(sigmets)
        sensor = FirSigmetBinarySensor(coordinator=coordinator, fir_icao="EPWW")

        assert sensor.extra_state_attributes["hazards"] == ["TURB", "ICE"]

    def test_valid_until_is_latest_among_active(self) -> None:
        sigmets = [
            _make_sigmet(
                sigmet_id="a",
                valid_to=datetime(2026, 7, 3, 12, tzinfo=UTC),
            ),
            _make_sigmet(
                sigmet_id="b",
                valid_to=datetime(2026, 7, 3, 18, tzinfo=UTC),
            ),
        ]
        coordinator = _make_coordinator(sigmets)
        sensor = FirSigmetBinarySensor(coordinator=coordinator, fir_icao="EPWW")

        assert sensor.extra_state_attributes["valid_until"] == datetime(
            2026, 7, 3, 18, tzinfo=UTC
        )

    def test_sigmets_attribute_is_not_capped(self) -> None:
        sigmets = [_make_sigmet(sigmet_id=str(i)) for i in range(10)]
        coordinator = _make_coordinator(sigmets)
        sensor = FirSigmetBinarySensor(coordinator=coordinator, fir_icao="EPWW")

        assert len(sensor.extra_state_attributes["sigmets"]) == 10


class TestOff:
    """Binary sensor is off when there are no active SIGMETs."""

    def test_is_off_when_no_active_sigmets(self) -> None:
        coordinator = _make_coordinator([])
        sensor = FirSigmetBinarySensor(coordinator=coordinator, fir_icao="EPWW")

        assert sensor.is_on is False

    def test_attributes_when_no_active_sigmets(self) -> None:
        coordinator = _make_coordinator([])
        sensor = FirSigmetBinarySensor(coordinator=coordinator, fir_icao="EPWW")

        attrs = sensor.extra_state_attributes

        assert attrs["active_count"] == 0
        assert attrs["hazards"] == []
        assert attrs["valid_until"] is None
        assert attrs["sigmets"] == []

    def test_unique_id_does_not_require_data(self) -> None:
        coordinator = _make_coordinator([])
        sensor = FirSigmetBinarySensor(coordinator=coordinator, fir_icao="EDFE")

        assert sensor.unique_id == "EDFE_sigmet"
