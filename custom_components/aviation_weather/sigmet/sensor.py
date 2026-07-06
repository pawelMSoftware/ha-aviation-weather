"""SIGMET detail sensors."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
)
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from ..entity import aviation_device_info
from .coordinator import SigmetCoordinator
from .models import Sigmet


@dataclass(frozen=True, kw_only=True)
class SigmetSensorEntityDescription(
    SensorEntityDescription,
):
    """SIGMET detail sensor description."""

    value_fn: Callable[[list[Sigmet]], object | None]
    extra_state_attributes_fn: Callable[[list[Sigmet]], dict[str, object]] | None = None


def _unique_hazards(active: list[Sigmet]) -> list[str]:
    """Return unique hazards among active SIGMETs, in first-seen order."""
    return list(dict.fromkeys(sigmet.hazard for sigmet in active if sigmet.hazard))


SIGMET_SENSORS: tuple[
    SigmetSensorEntityDescription,
    ...,
] = (
    SigmetSensorEntityDescription(
        key="sigmet_count",
        name="SIGMET Count",
        icon="mdi:counter",
        value_fn=len,
    ),
    SigmetSensorEntityDescription(
        key="sigmet_valid_until",
        name="SIGMET Valid Until",
        icon="mdi:clock-alert-outline",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda active: max(
            (sigmet.valid_to for sigmet in active),
            default=None,
        ),
    ),
    SigmetSensorEntityDescription(
        key="sigmet_hazards",
        name="SIGMET Hazards",
        icon="mdi:weather-lightning",
        value_fn=lambda active: ", ".join(_unique_hazards(active)) or None,
        extra_state_attributes_fn=lambda active: {"hazards": _unique_hazards(active)},
    ),
)


class FirSigmetSensor(
    CoordinatorEntity[SigmetCoordinator],
    SensorEntity,
):
    """SIGMET detail sensor."""

    entity_description: SigmetSensorEntityDescription

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: SigmetCoordinator,
        description: SigmetSensorEntityDescription,
        fir_icao: str,
    ) -> None:
        super().__init__(coordinator)

        self.entity_description = description
        self._fir_icao = fir_icao

        # unique_id must not depend on coordinator.data; see
        # FirSigmetBinarySensor.__init__ for why.
        self._attr_unique_id = f"{fir_icao}_{description.key}"

    @property
    def native_value(
        self,
    ) -> object | None:
        return self.entity_description.value_fn(
            self.coordinator.active_sigmets,
        )

    @property
    def extra_state_attributes(
        self,
    ) -> dict[str, object]:
        if self.entity_description.extra_state_attributes_fn is None:
            return {}

        return self.entity_description.extra_state_attributes_fn(
            self.coordinator.active_sigmets,
        )

    @property
    def device_info(
        self,
    ) -> DeviceInfo:
        return aviation_device_info(
            identifier=self._fir_icao,
            model="FIR",
        )
