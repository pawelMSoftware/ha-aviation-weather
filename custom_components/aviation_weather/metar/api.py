"""Aviation Weather API client."""

from __future__ import annotations

from aiohttp import ClientSession, ContentTypeError

from .mapper import MetarMapper
from .models import MetarData


class MetarApiClient:
    """Aviation Weather API client."""

    BASE_URL = "https://aviationweather.gov/api/data/metar"

    def __init__(
        self,
        session: ClientSession,
    ) -> None:
        self._session = session
        self._mapper = MetarMapper()

    async def get_metar(
        self,
        airport: str,
    ) -> MetarData:
        """Get METAR data."""
        params = {
            "ids": airport,
            "format": "json",
        }

        async with self._session.get(
            self.BASE_URL,
            params=params,
        ) as response:
            response.raise_for_status()

            # aviationweather.gov returns an empty 204 response (with no
            # JSON content-type) when an airport currently has no METAR
            # report available, even if it normally publishes one. This
            # is a transient "no data right now" condition, not an error.
            if response.status == 204:
                data = []
            else:
                try:
                    data = await response.json()
                except ContentTypeError:
                    data = []

        if not data:
            raise ValueError(
                f"No METAR data returned for airport {airport}",
            )

        return self._mapper.map(
            data[0],
            requested_airport=airport,
        )
