"""Binary sensor platform."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_FIR, DOMAIN
from .sigmet import FirSigmetBinarySensor, SigmetCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the SIGMET binary sensor for a FIR entry.

    Only FIR entries forward to this platform (see FIR_PLATFORMS in
    const.py) — always created, mirroring the always-created METAR
    summary sensor for airport entries.
    """

    sigmet_coordinator: SigmetCoordinator = hass.data[DOMAIN][entry.entry_id][
        "sigmet_coordinator"
    ]

    fir_icao = entry.data.get(CONF_FIR, "")

    entities: list[BinarySensorEntity] = [
        FirSigmetBinarySensor(
            coordinator=sigmet_coordinator,
            fir_icao=fir_icao,
        ),
    ]

    async_add_entities(
        entities,
    )
