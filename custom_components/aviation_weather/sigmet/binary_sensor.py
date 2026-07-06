"""SIGMET binary sensor."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..entity import aviation_device_info
from .coordinator import SigmetCoordinator
from .models import Sigmet


def _sigmet_to_dict(sigmet: Sigmet) -> dict[str, object]:
    """Serialize a Sigmet for entity attributes."""
    return {
        "id": sigmet.id,
        "fir_id": sigmet.fir_id,
        "fir_name": sigmet.fir_name,
        "hazard": sigmet.hazard,
        "qualifier": sigmet.qualifier,
        "base": sigmet.base,
        "top": sigmet.top,
        "valid_from": sigmet.valid_from,
        "valid_to": sigmet.valid_to,
        "coordinates": sigmet.coordinates,
        "raw": sigmet.raw,
    }


class FirSigmetBinarySensor(
    CoordinatorEntity[SigmetCoordinator],
    BinarySensorEntity,
):
    """Main SIGMET binary sensor for a FIR device.

    Always created (mirrors MetarSummarySensor for airports) — this is
    the primary automation entity for the FIR device: on when at least
    one active SIGMET exists for this FIR.
    """

    _attr_has_entity_name = True
    _attr_device_class = BinarySensorDeviceClass.SAFETY
    # No _attr_icon here on purpose: this entity's icon differs between
    # "on" (active SIGMET) and "off" via icons.json's per-state
    # overrides, keyed on this translation_key. A static _attr_icon
    # would take priority over icons.json and silently defeat that.
    _attr_translation_key = "sigmet"

    def __init__(
        self,
        coordinator: SigmetCoordinator,
        fir_icao: str,
    ) -> None:
        super().__init__(coordinator)

        self._attr_name = "SIGMET"
        self._fir_icao = fir_icao

        # unique_id must not depend on coordinator.data: the first
        # refresh may fail, in which case coordinator.data is still
        # None when this entity is constructed.
        self._attr_unique_id = f"{fir_icao}_sigmet"

    @property
    def active_sigmets(self) -> list[Sigmet]:
        return self.coordinator.active_sigmets

    @property
    def is_on(self) -> bool:
        return len(self.active_sigmets) > 0

    @property
    def device_info(
        self,
    ) -> DeviceInfo:
        return aviation_device_info(
            identifier=self._fir_icao,
            model="FIR",
        )

    @property
    def extra_state_attributes(
        self,
    ) -> dict[str, object]:
        active = self.active_sigmets

        return {
            "active_count": len(active),
            "hazards": list(
                dict.fromkeys(sigmet.hazard for sigmet in active if sigmet.hazard),
            ),
            "valid_until": max(
                (sigmet.valid_to for sigmet in active),
                default=None,
            ),
            "sigmets": [_sigmet_to_dict(sigmet) for sigmet in active],
        }
