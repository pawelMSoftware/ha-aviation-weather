"""TAF mapper."""

from __future__ import annotations

from datetime import UTC, datetime

from .enums import TafChangeType
from .models import (
    TafCloudLayer,
    TafData,
    TafForecast,
)


class TafMapper:
    """TAF mapper."""

    def map(
        self,
        taf: dict,
        requested_airport: str | None = None,
    ) -> TafData:
        """Map API response to TAF data.

        `requested_airport` is used as a fallback for the airport ICAO
        code in case the API response is missing the "icaoId" field.
        """
        forecasts = [
            self._map_forecast(
                forecast,
            )
            for forecast in taf.get(
                "fcsts",
                [],
            )
        ]

        airport = taf.get(
            "icaoId",
            requested_airport,
        )

        if airport is None:
            raise ValueError(
                "TAF response is missing the airport ICAO code (icaoId)",
            )

        return TafData(
            airport=airport,
            airport_name=taf.get(
                "name",
            ),
            latitude=taf.get(
                "lat",
            ),
            longitude=taf.get(
                "lon",
            ),
            elevation=taf.get(
                "elev",
            ),
            issue_time=self._from_iso_datetime(
                taf.get(
                    "issueTime",
                ),
            ),
            valid_from=self._from_unix_timestamp(
                taf.get(
                    "validTimeFrom",
                ),
            ),
            valid_to=self._from_unix_timestamp(
                taf.get(
                    "validTimeTo",
                ),
            ),
            raw_taf=taf.get(
                "rawTAF",
                "",
            ),
            forecasts=forecasts,
        )

    def _map_forecast(
        self,
        forecast: dict,
    ) -> TafForecast:
        """Map forecast."""
        clouds = [
            self._map_cloud_layer(
                cloud,
            )
            for cloud in forecast.get(
                "clouds",
                [],
            )
        ]

        wind_direction = forecast.get(
            "wdir",
        )

        if wind_direction is not None:
            wind_direction = str(
                wind_direction,
            )

        return TafForecast(
            time_from=self._from_unix_timestamp(
                forecast.get(
                    "timeFrom",
                ),
            ),
            time_to=self._from_unix_timestamp(
                forecast.get(
                    "timeTo",
                ),
            ),
            change_type=self._map_change_type(
                forecast.get(
                    "fcstChange",
                ),
            ),
            wind_direction=wind_direction,
            wind_speed=forecast.get(
                "wspd",
            ),
            wind_gust=forecast.get(
                "wgst",
            ),
            visibility=(
                str(
                    forecast.get(
                        "visib",
                    ),
                )
                if forecast.get(
                    "visib",
                )
                is not None
                else None
            ),
            weather=forecast.get(
                "wxString",
            ),
            clouds=clouds,
        )

    def _map_cloud_layer(
        self,
        cloud: dict,
    ) -> TafCloudLayer:
        """Map cloud layer."""
        return TafCloudLayer(
            cover=cloud.get(
                "cover",
            ),
            base=cloud.get(
                "base",
            ),
            cloud_type=cloud.get(
                "type",
            ),
        )

    def _map_change_type(
        self,
        value: str | None,
    ) -> TafChangeType | str | None:
        """Map change type."""
        if value is None:
            return None

        try:
            return TafChangeType(
                value,
            )
        except ValueError:
            return value

    def _from_iso_datetime(
        self,
        value: str | None,
    ) -> datetime | None:
        """Convert ISO datetime."""
        if value is None:
            return None

        return datetime.fromisoformat(
            value.replace(
                "Z",
                "+00:00",
            ),
        )

    def _from_unix_timestamp(
        self,
        value: int | None,
    ) -> datetime | None:
        """Convert unix timestamp."""
        if value is None:
            return None

        return datetime.fromtimestamp(
            value,
            tz=UTC,
        )
