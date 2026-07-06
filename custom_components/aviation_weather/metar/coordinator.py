"""Data update coordinator."""

from __future__ import annotations

import logging
from datetime import timedelta

from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.update_coordinator import (
    TimestampDataUpdateCoordinator,
    UpdateFailed,
)

from ..const import (
    CONF_AIRPORT,
    DOMAIN,
    METAR_SCAN_INTERVAL,
    METAR_STALE_THRESHOLD_HOURS,
)
from ..helpers import (
    async_clear_stale_data_issue,
    async_maybe_create_stale_data_issue,
    get_entry_value,
)
from .api import MetarApiClient
from .models import MetarData

LOGGER = logging.getLogger(__name__)

METAR_STALE_THRESHOLD = timedelta(hours=METAR_STALE_THRESHOLD_HOURS)


class MetarCoordinator(
    TimestampDataUpdateCoordinator[MetarData],
):
    """Aviation Weather coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: MetarApiClient,
        update_interval: timedelta | None = None,
    ) -> None:
        super().__init__(
            hass,
            logger=LOGGER,
            name=DOMAIN,
            update_interval=update_interval
            or timedelta(
                seconds=METAR_SCAN_INTERVAL,
            ),
        )

        self._entry = entry
        self._client = client
        self._airport_had_no_data = False
        self._stale_issue_id = f"stale_metar_{entry.entry_id}"

        entry.async_on_unload(
            lambda: async_clear_stale_data_issue(
                hass,
                issue_id=self._stale_issue_id,
            ),
        )

    async def async_first_refresh(self) -> None:
        """Perform the first refresh when the config entry is set up.

        Unlike `async_config_entry_first_refresh`, this only raises
        `ConfigEntryNotReady` (blocking setup, triggering HA's retry)
        when the failure looks like a connectivity problem. If the
        airport simply has no current METAR report (e.g. a temporary
        gap in reporting), setup proceeds and the sensor starts as
        unavailable until the next successful update.
        """
        await self.async_refresh()

        if self.last_update_success:
            return

        if self._airport_had_no_data:
            LOGGER.warning(
                "No current METAR data available yet for this airport; "
                "the sensor will become available once a report is "
                "published.",
            )
            return

        ex = ConfigEntryNotReady()
        ex.__cause__ = self.last_exception
        raise ex

    async def _async_update_data(
        self,
    ) -> MetarData:
        """Fetch data."""
        airport = get_entry_value(
            self._entry,
            CONF_AIRPORT,
        )

        self._airport_had_no_data = False

        try:
            data = await self._client.get_metar(
                airport,
            )
        except ClientError as ex:
            async_maybe_create_stale_data_issue(
                self.hass,
                self,
                issue_id=self._stale_issue_id,
                translation_key="stale_metar",
                translation_placeholders={"airport": airport},
                threshold=METAR_STALE_THRESHOLD,
            )
            raise UpdateFailed(
                f"Unable to fetch METAR data: {ex}",
            ) from ex
        except ValueError as ex:
            self._airport_had_no_data = True
            async_maybe_create_stale_data_issue(
                self.hass,
                self,
                issue_id=self._stale_issue_id,
                translation_key="stale_metar",
                translation_placeholders={"airport": airport},
                threshold=METAR_STALE_THRESHOLD,
            )
            raise UpdateFailed(
                f"No current METAR data for {airport}: {ex}",
            ) from ex

        async_clear_stale_data_issue(
            self.hass,
            issue_id=self._stale_issue_id,
        )
        return data
