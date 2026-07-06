"""Shared entity helpers for Aviation Weather."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN


def enum_value(value: Any) -> Any:
    """Return the underlying value of an enum, or the value itself.

    Several fields in the API responses are mapped to enums when the
    value is recognized, but fall back to a plain string otherwise.
    This helper normalizes both cases for sensor state/attributes.
    """
    if hasattr(value, "value"):
        return value.value

    return value


def aviation_device_info(
    *,
    identifier: str,
    model: str,
) -> DeviceInfo:
    """Build DeviceInfo for any aviation object (Airport, FIR, etc.).

    Uses `identifier` (e.g. ICAO code) as both the device name and the
    unique identifier within this integration's domain. `model` describes
    the type of aviation object (e.g. "Airport" or "FIR") and is shown
    in the HA device list alongside the manufacturer.

    Using the ICAO code as the device name keeps entity_ids short and
    predictable (e.g. sensor.epgd_metar, sensor.epww_sigmet) rather
    than deriving them from long, comma-separated API names.
    """
    return DeviceInfo(
        identifiers={
            (
                DOMAIN,
                identifier,
            ),
        },
        name=identifier,
        manufacturer="NOAA",
        model=model,
    )


def airport_device_info(
    *,
    airport_icao: str,
    airport_name: str | None,
) -> DeviceInfo:
    """Build DeviceInfo for an airport device.

    Thin wrapper around aviation_device_info kept for backward
    compatibility with existing call sites in metar/sensor.py,
    taf/sensor.py, and weather_entity/entity.py. The airport_name
    parameter is intentionally unused — see aviation_device_info for
    the rationale.
    """
    return aviation_device_info(
        identifier=airport_icao,
        model="Airport",
    )
