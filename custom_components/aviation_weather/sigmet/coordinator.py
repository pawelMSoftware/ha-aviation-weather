"""SIGMET update coordinator."""

from __future__ import annotations

import logging
from datetime import timedelta

from aiohttp import ClientError
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    TimestampDataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from ..airspace_advisory import active_advisories
from ..const import (
    CONF_FIR,
    DOMAIN,
    SIGMET_SCAN_INTERVAL,
    SIGMET_STALE_THRESHOLD_HOURS,
)
from ..helpers import (
    async_clear_stale_data_issue,
    async_maybe_create_stale_data_issue,
    get_entry_value,
)
from .api import SigmetApiClient
from .models import Sigmet

LOGGER = logging.getLogger(__name__)

SIGMET_STALE_THRESHOLD = timedelta(hours=SIGMET_STALE_THRESHOLD_HOURS)


class SigmetCoordinator(
    TimestampDataUpdateCoordinator[list[Sigmet]],
):
    """SIGMET coordinator."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: SigmetApiClient,
        update_interval: timedelta | None = None,
    ) -> None:
        super().__init__(
            hass,
            logger=LOGGER,
            name=f"{DOMAIN}_sigmet",
            update_interval=update_interval
            or timedelta(
                seconds=SIGMET_SCAN_INTERVAL,
            ),
        )

        self._entry = entry
        self._client = client
        self._stale_issue_id = f"stale_sigmet_{entry.entry_id}"

        entry.async_on_unload(
            lambda: async_clear_stale_data_issue(
                hass,
                issue_id=self._stale_issue_id,
            ),
        )

    async def async_first_refresh(self) -> None:
        """Perform the first refresh when the FIR config entry is set up.

        A SIGMET connectivity blip should never block the rest of the
        FIR device from loading, so — like TafCoordinator — this never
        raises ConfigEntryNotReady.
        """
        await self.async_refresh()

        if not self.last_update_success:
            LOGGER.debug(
                "Unable to fetch SIGMET data on first refresh for this "
                "FIR; the binary sensor will report unavailable until "
                "the next successful update.",
            )

    @property
    def active_sigmets(self) -> list[Sigmet]:
        """Return the currently active SIGMETs.

        The single call site for "is this SIGMET active" — computed at
        read time (using the current time, not the time of the last
        poll) so entities correctly reflect SIGMETs expiring between
        polls, and so binary_sensor/sensor entities never duplicate
        this filtering logic themselves.
        """
        return active_advisories(
            self.data or [],
            now=dt_util.utcnow(),
        )

    async def _async_update_data(
        self,
    ) -> list[Sigmet]:
        """Fetch SIGMET data."""
        fir_icao = get_entry_value(
            self._entry,
            CONF_FIR,
        )

        try:
            data = await self._client.get_sigmets(
                fir_icao,
            )
        except ClientError as ex:
            async_maybe_create_stale_data_issue(
                self.hass,
                self,
                issue_id=self._stale_issue_id,
                translation_key="stale_sigmet",
                translation_placeholders={"fir": fir_icao},
                threshold=SIGMET_STALE_THRESHOLD,
            )
            raise UpdateFailed(
                f"Unable to fetch SIGMET data: {ex}",
            ) from ex

        async_clear_stale_data_issue(
            self.hass,
            issue_id=self._stale_issue_id,
        )
        return data
