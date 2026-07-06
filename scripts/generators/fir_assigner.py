"""FIR assigner — assigns each airport to its Flight Information Region.

This module uses `traffic.data.eurofirs` (which in turn depends on
geopandas and shapely) to perform point-in-polygon lookups. It is
intentionally isolated in the generator layer: nothing in the
custom_components package imports from here. That keeps the HA
integration free of heavy geospatial dependencies.

The algorithm:
1. Load all European FIR polygons from traffic.data.eurofirs once.
2. For each airport, create a shapely Point(longitude, latitude).
3. Find the FIR polygon that contains the point.
4. If found: set airport.fir_icao = fir.designator.
5. If not found: set airport.fir_icao = "" and log a warning.
"""

from __future__ import annotations

import warnings
from dataclasses import replace

from .models.airport import Airport


class FirAssigner:
    """Assign airports to FIRs using point-in-polygon geometry.

    Uses traffic.data.eurofirs as the polygon source. Importing
    traffic is done lazily inside assign() so that merely importing
    this module (e.g. during a test that stubs it out) does not pull
    in geopandas/shapely.
    """

    def assign(
        self,
        airports: list[Airport],
    ) -> list[Airport]:
        """Return a new list of airports with fir_icao populated.

        For each airport a shapely Point is tested against every FIR
        polygon. The first containing polygon wins (FIRs in the dataset
        do not overlap in practice). Airports not contained in any FIR
        receive fir_icao="" and are logged as warnings.

        Args:
            airports: List of Airport objects to process.  Usually the
                      already-filtered European-only list, but the method
                      handles non-European airports gracefully by leaving
                      their fir_icao as "".

        Returns:
            New list of Airport dataclass instances with fir_icao set.
        """
        fir_polygons = self._load_fir_polygons()

        assigned: list[Airport] = []
        unmatched: list[str] = []

        for airport in airports:
            fir_icao = self._find_fir(
                airport.latitude,
                airport.longitude,
                fir_polygons,
            )

            if fir_icao:
                assigned.append(
                    replace(
                        airport,
                        fir_icao=fir_icao,
                    ),
                )
            else:
                unmatched.append(airport.icao)
                assigned.append(airport)

        if unmatched:
            print(  # noqa: T201
                f"\nWarning: {len(unmatched)} airport(s) could not be matched "
                f"to any FIR polygon:",
            )
            for icao in sorted(unmatched):
                print(f"  {icao}")  # noqa: T201

        return assigned

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load_fir_polygons(
        self,
    ) -> list[tuple[str, object]]:
        """Load FIR polygons from traffic.data.eurofirs.

        Returns a list of (designator, polygon) tuples sorted by
        designator for deterministic iteration order.

        The `object` type for polygon is intentional — we avoid
        importing shapely types at the module level to keep the
        import side-effect-free.
        """
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from traffic.data import eurofirs  # noqa: PLC0415

        data = eurofirs.data

        polygons: list[tuple[str, object]] = []
        for _, row in data.iterrows():
            designator = str(row.get("designator", "")).strip()
            geometry = row.get("geometry")

            if not designator or geometry is None:
                continue

            polygons.append((designator, geometry))

        return sorted(polygons, key=lambda t: t[0])

    def _find_fir(
        self,
        latitude: float,
        longitude: float,
        fir_polygons: list[tuple[str, object]],
    ) -> str:
        """Return the designator of the FIR that contains (lat, lon).

        Uses shapely Point.within(polygon) as the primary test, with a
        fallback to intersects(point.buffer(0.02)) for airports that lie
        exactly on a FIR boundary (within() is strict and excludes the
        boundary itself). The buffer of ~2 km handles rounding in airport
        coordinates without risk of false-positives between adjacent FIRs.

        Returns an empty string if no polygon contains the point (typically
        means the airport's FIR is not present in traffic.data.eurofirs —
        e.g. Iceland BIRD, Russian FIRs beyond ECAC coverage).

        Note: shapely uses (x, y) = (longitude, latitude) convention,
        which is the reverse of the ICAO/human lat/lon convention.
        """
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            from shapely.geometry import Point  # noqa: PLC0415

        point = Point(longitude, latitude)

        # Primary pass: strict containment.
        for designator, polygon in fir_polygons:
            try:
                if point.within(polygon):
                    return designator
            except Exception:  # noqa: BLE001
                continue

        # Fallback pass: boundary tolerance (~2 km buffer).
        # Catches airports whose coordinates sit exactly on a FIR edge.
        buffered = point.buffer(0.02)
        for designator, polygon in fir_polygons:
            try:
                if buffered.intersects(polygon):
                    return designator
            except Exception:  # noqa: BLE001
                continue

        return ""
