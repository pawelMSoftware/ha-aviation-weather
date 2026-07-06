"""Tests for FirSigmetSensor (the optional SIGMET detail sensors)."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from custom_components.aviation_weather.sigmet.models import Sigmet
from custom_components.aviation_weather.sigmet.sensor import (
    SIGMET_SENSORS,
    FirSigmetSensor,
)


def _make_coordinator(active_sigmets: list[Sigmet]):
    coordinator = MagicMock()
    coordinator.active_sigmets = active_sigmets
    coordinator.last_update_success = True
    return coordinator


def _make_sigmet(
    *,
    sigmet_id: str = "sigmet-1",
    hazard: str | None = "TURB",
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
        valid_from=datetime(2026, 7, 3, 10, tzinfo=UTC),
        valid_to=valid_to or datetime(2026, 7, 3, 14, tzinfo=UTC),
        coordinates=[],
        raw="WSPL31 EPWW",
        extra={},
    )


def _description(key: str):
    return next(d for d in SIGMET_SENSORS if d.key == key)


class TestSigmetCountSensor:
    def test_state_is_active_count(self) -> None:
        coordinator = _make_coordinator([_make_sigmet(), _make_sigmet(sigmet_id="2")])
        sensor = FirSigmetSensor(
            coordinator=coordinator,
            description=_description("sigmet_count"),
            fir_icao="EPWW",
        )

        assert sensor.native_value == 2

    def test_state_is_zero_when_no_active(self) -> None:
        coordinator = _make_coordinator([])
        sensor = FirSigmetSensor(
            coordinator=coordinator,
            description=_description("sigmet_count"),
            fir_icao="EPWW",
        )

        assert sensor.native_value == 0

    def test_unique_id(self) -> None:
        coordinator = _make_coordinator([])
        sensor = FirSigmetSensor(
            coordinator=coordinator,
            description=_description("sigmet_count"),
            fir_icao="EPWW",
        )

        assert sensor.unique_id == "EPWW_sigmet_count"


class TestSigmetValidUntilSensor:
    def test_state_is_latest_valid_to(self) -> None:
        coordinator = _make_coordinator(
            [
                _make_sigmet(
                    sigmet_id="a", valid_to=datetime(2026, 7, 3, 12, tzinfo=UTC)
                ),
                _make_sigmet(
                    sigmet_id="b", valid_to=datetime(2026, 7, 3, 18, tzinfo=UTC)
                ),
            ],
        )
        sensor = FirSigmetSensor(
            coordinator=coordinator,
            description=_description("sigmet_valid_until"),
            fir_icao="EPWW",
        )

        assert sensor.native_value == datetime(2026, 7, 3, 18, tzinfo=UTC)

    def test_state_is_none_when_no_active(self) -> None:
        coordinator = _make_coordinator([])
        sensor = FirSigmetSensor(
            coordinator=coordinator,
            description=_description("sigmet_valid_until"),
            fir_icao="EPWW",
        )

        assert sensor.native_value is None


class TestSigmetHazardsSensor:
    def test_state_is_joined_unique_hazards(self) -> None:
        coordinator = _make_coordinator(
            [
                _make_sigmet(sigmet_id="a", hazard="TURB"),
                _make_sigmet(sigmet_id="b", hazard="ICE"),
                _make_sigmet(sigmet_id="c", hazard="TURB"),
            ],
        )
        sensor = FirSigmetSensor(
            coordinator=coordinator,
            description=_description("sigmet_hazards"),
            fir_icao="EPWW",
        )

        assert sensor.native_value == "TURB, ICE"
        assert sensor.extra_state_attributes == {"hazards": ["TURB", "ICE"]}

    def test_state_is_none_when_no_active(self) -> None:
        coordinator = _make_coordinator([])
        sensor = FirSigmetSensor(
            coordinator=coordinator,
            description=_description("sigmet_hazards"),
            fir_icao="EPWW",
        )

        assert sensor.native_value is None
        assert sensor.extra_state_attributes == {"hazards": []}


class TestDeviceInfo:
    def test_device_info_attaches_to_fir_device(self) -> None:
        coordinator = _make_coordinator([])
        sensor = FirSigmetSensor(
            coordinator=coordinator,
            description=_description("sigmet_count"),
            fir_icao="EPWW",
        )

        device_info = sensor.device_info

        assert device_info["name"] == "EPWW"
        assert device_info["model"] == "FIR"


class TestEveryDescriptionRunsWithoutError:
    @pytest.mark.parametrize("description", SIGMET_SENSORS, ids=lambda d: d.key)
    def test_value_fn_runs_without_error(self, description) -> None:
        coordinator = _make_coordinator([_make_sigmet()])
        sensor = FirSigmetSensor(
            coordinator=coordinator,
            description=description,
            fir_icao="EPWW",
        )

        _ = sensor.native_value
