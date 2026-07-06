"""TAF update coordinator."""

from __future__ import annotations

import logging
from datetime import timedelta

from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)

from ..const import (
    CONF_AIRPORT,
    DOMAIN,
    TAF_SCAN_INTERVAL,
)
from ..helpers import get_entry_value
from .api import TafApiClient
from .models import TafData

LOGGER = logging.getLogger(__name__)


class TafCoordinator(
    DataUpdateCoordinator[TafData],
):
    """TAF coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: TafApiClient,
        update_interval: timedelta | None = None,
    ) -> None:
        super().__init__(
            hass,
            logger=LOGGER,
            name=f"{DOMAIN}_taf",
            update_interval=update_interval
            or timedelta(
                seconds=TAF_SCAN_INTERVAL,
            ),
        )

        self._entry = entry
        self._client = client

    async def async_first_refresh(self) -> None:
        """Perform the first refresh when the config entry is set up.

        TAF is published for only a subset of airports, and even where
        it is normally published, a report may be temporarily
        unavailable. Either way, this should never block the rest of
        the integration from loading. This intentionally never raises
        `ConfigEntryNotReady`, unlike `async_config_entry_first_refresh`.
        The TAF sensor simply starts as unavailable until the first
        successful update.
        """
        await self.async_refresh()

        if not self.last_update_success:
            LOGGER.debug(
                "No current TAF data available yet for this airport; "
                "the sensor will become available once a forecast is "
                "published, if this airport publishes TAF at all.",
            )

    async def _async_update_data(
        self,
    ) -> TafData:
        """Fetch TAF data."""
        airport = get_entry_value(
            self._entry,
            CONF_AIRPORT,
        )

        try:
            return await self._client.get_taf(
                airport,
            )
        except ClientError as ex:
            raise UpdateFailed(
                f"Unable to fetch TAF data: {ex}",
            ) from ex
        except ValueError as ex:
            raise UpdateFailed(
                f"No current TAF data for {airport}: {ex}",
            ) from ex
