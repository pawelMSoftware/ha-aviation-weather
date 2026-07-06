"""SIGMET API client."""

from __future__ import annotations

from aiohttp import ClientSession, ContentTypeError

from .mapper import SigmetMapper
from .models import Sigmet


class SigmetApiClient:
    """SIGMET API client.

    Hits the international SIGMET endpoint (not /api/data/airsigmet,
    which is US-domestic-only) since this integration covers Europe.
    """

    BASE_URL = "https://aviationweather.gov/api/data/isigmet"

    def __init__(
        self,
        session: ClientSession,
    ) -> None:
        self._session = session
        self._mapper = SigmetMapper()

    async def get_sigmets(
        self,
        fir_icao: str,
    ) -> list[Sigmet]:
        """Get all current SIGMETs for the given FIR.

        Unlike METAR/TAF, an empty result is a normal, expected state
        (most FIRs have no active SIGMET most of the time) — it is
        never treated as an error here.
        """
        params = {
            "format": "json",
        }

        async with self._session.get(
            self.BASE_URL,
            params=params,
        ) as response:
            response.raise_for_status()

            if response.status == 204:
                data = []
            else:
                try:
                    data = await response.json()
                except ContentTypeError:
                    data = []

        return self._mapper.map(
            data or [],
            fir_id=fir_icao,
        )
