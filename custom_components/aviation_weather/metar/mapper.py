"""METAR mapper."""

from __future__ import annotations

import re
from datetime import datetime

from .enums import (
    CloudCover,
    FlightCategory,
    MetarType,
    WeatherIntensity,
    WeatherPhenomenon,
)
from .models import (
    CloudLayer,
    MetarData,
    WeatherCondition,
)


class MetarMapper:
    """METAR mapper."""

    def map(
        self,
        metar: dict,
        requested_airport: str | None = None,
    ) -> MetarData:
        """Map API response to METAR data.

        `requested_airport` is used as a fallback for the airport ICAO
        code in case the API response is missing the "icaoId" field.
        """
        cloud_layers: list[CloudLayer] = []

        for cloud in metar.get(
            "clouds",
            [],
        ):
            cover = cloud.get(
                "cover",
            )

            if not cover:
                continue

            cloud_layers.append(
                CloudLayer(
                    cover=self._map_cloud_cover(
                        cover,
                    ),
                    base=cloud.get(
                        "base",
                    ),
                ),
            )

        observation_time = None

        if report_time := metar.get(
            "reportTime",
        ):
            observation_time = datetime.fromisoformat(
                report_time.replace(
                    "Z",
                    "+00:00",
                ),
            )

        wind_direction = metar.get(
            "wdir",
        )

        if wind_direction is not None:
            wind_direction = str(
                wind_direction,
            )

        airport = metar.get(
            "icaoId",
            requested_airport,
        )

        if airport is None:
            raise ValueError(
                "METAR response is missing the airport ICAO code (icaoId)",
            )

        return MetarData(
            airport=airport,
            airport_name=metar.get(
                "name",
            ),
            latitude=metar.get(
                "lat",
            ),
            longitude=metar.get(
                "lon",
            ),
            elevation=metar.get(
                "elev",
            ),
            temperature=metar.get(
                "temp",
            ),
            dewpoint=metar.get(
                "dewp",
            ),
            pressure=metar.get(
                "altim",
            ),
            sea_level_pressure=metar.get(
                "slp",
            ),
            wind_speed=metar.get(
                "wspd",
            ),
            wind_gust=metar.get(
                "wgst",
            ),
            wind_direction=wind_direction,
            visibility_meters=self._parse_visibility_meters(
                metar.get(
                    "rawOb",
                    "",
                ),
            ),
            flight_category=self._map_flight_category(
                metar.get(
                    "fltCat",
                ),
            ),
            metar_type=self._map_metar_type(
                metar.get(
                    "metarType",
                ),
            ),
            weather=self._map_weather(
                metar.get(
                    "wxString",
                ),
            ),
            snow_depth=metar.get(
                "snow",
            ),
            vertical_visibility=metar.get(
                "vertVis",
            ),
            cloud_layers=cloud_layers,
            observation_time=observation_time,
            raw_metar=metar.get(
                "rawOb",
                "",
            ),
        )

    def _parse_visibility_meters(
        self,
        raw_ob: str,
    ) -> int | None:
        """Parse prevailing visibility in metres from a raw METAR string.

        Reads from the standard ICAO visibility group that appears after
        the wind group. Handles three cases:

        - CAVOK or 9999 → 10000 (meaning "10 km or more")
        - Four-digit metric group (e.g. "0500", "3500") → that value
        - US statute-mile format (e.g. "10SM", "1/4SM") → None
          (not converted; callers treat None as "not available")

        Returns None when the raw string is empty, malformed, or uses a
        format that cannot be unambiguously parsed as metres.
        """
        if not raw_ob:
            return None

        tokens = raw_ob.split()

        # CAVOK can appear anywhere after the header; check first because
        # it replaces the visibility group entirely.
        if "CAVOK" in tokens:
            return 10000

        # Find the wind group — visibility immediately follows it.
        # Wind groups end with KT, MPS, or KMH (ICAO Doc 4444 §11.4.5).
        wind_index = None
        for i, token in enumerate(tokens):
            if token.endswith(("KT", "MPS", "KMH")):
                wind_index = i
                break

        if wind_index is None:
            return None

        # The token right after the wind group is the visibility group
        # (or a variable-wind suffix like "270V360", which we skip).
        for token in tokens[wind_index + 1 :]:
            # Skip variable wind direction suffix (e.g. "270V360").
            if re.match(r"^\d{3}V\d{3}$", token):
                continue

            if token == "9999":
                return 10000

            # Standard ICAO four-digit metric group.
            if re.match(r"^\d{4}$", token):
                return int(token)

            # US statute-mile format — not converted.
            if "SM" in token:
                return None

            # Any other token means the visibility group is absent
            # (e.g. METAR skipped it) — stop looking.
            break

        return None

    def _map_flight_category(
        self,
        value: str | None,
    ) -> FlightCategory | str | None:
        """Map flight category."""
        if value is None:
            return None

        try:
            return FlightCategory(
                value,
            )
        except ValueError:
            return value

    def _map_cloud_cover(
        self,
        value: str,
    ) -> CloudCover | str:
        """Map cloud cover."""
        try:
            return CloudCover(
                value,
            )
        except ValueError:
            return value

    def _map_metar_type(
        self,
        value: str | None,
    ) -> MetarType | str | None:
        """Map METAR type."""
        if value is None:
            return None

        try:
            return MetarType(
                value,
            )
        except ValueError:
            return value

    def _map_weather(
        self,
        value: str | None,
    ) -> WeatherCondition | None:
        """Map weather condition."""
        if not value:
            return None

        intensity = None

        if value.startswith(
            "+",
        ):
            intensity = WeatherIntensity.HEAVY
        elif value.startswith(
            "-",
        ):
            intensity = WeatherIntensity.LIGHT

        phenomena: list[WeatherPhenomenon] = []

        mappings = {
            "FZRA": WeatherPhenomenon.FREEZING_RAIN,
            "TS": WeatherPhenomenon.THUNDERSTORM,
            "RA": WeatherPhenomenon.RAIN,
            "SN": WeatherPhenomenon.SNOW,
            "DZ": WeatherPhenomenon.DRIZZLE,
            "FG": WeatherPhenomenon.FOG,
            "BR": WeatherPhenomenon.MIST,
            "HZ": WeatherPhenomenon.HAZE,
        }

        for (
            code,
            phenomenon,
        ) in mappings.items():
            if code in value:
                phenomena.append(
                    phenomenon,
                )

        return WeatherCondition(
            raw=value,
            intensity=intensity,
            phenomena=phenomena,
        )
