"""TAF API client."""

from __future__ import annotations

from aiohttp import ClientSession, ContentTypeError

from .mapper import TafMapper
from .models import TafData


class TafApiClient:
    """TAF API client."""

    BASE_URL = "https://aviationweather.gov/api/data/taf"

    def __init__(
        self,
        session: ClientSession,
    ) -> None:
        self._session = session
        self._mapper = TafMapper()

    async def get_taf(
        self,
        airport: str,
    ) -> TafData:
        """Get TAF data."""
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
            # JSON content-type) when an airport currently has no TAF
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
                f"No TAF data returned for airport {airport}",
            )

        return self._mapper.map(
            data[0],
            requested_airport=airport,
        )
