from __future__ import annotations

from pathlib import Path

import defusedxml.ElementTree as ET

from ..models.station import Station


class StationLoader:
    """Load weather stations."""

    def load(
        self,
        xml_file: Path,
    ) -> dict[str, Station]:
        """Load weather stations."""

        tree = ET.parse(xml_file)
        root = tree.getroot()

        stations: dict[str, Station] = {}

        for station in root.findall("./data/Station"):
            icao = station.findtext("icao_id")

            if not icao:
                continue

            site_type = station.find("site_type")

            has_metar = False
            has_taf = False

            if site_type is not None:
                has_metar = site_type.find("METAR") is not None
                has_taf = site_type.find("TAF") is not None

            stations[icao] = Station(
                icao=icao,
                has_metar=has_metar,
                has_taf=has_taf,
            )

        return stations
