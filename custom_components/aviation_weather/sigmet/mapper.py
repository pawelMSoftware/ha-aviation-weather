"""SIGMET mapper."""

from __future__ import annotations

import hashlib
from datetime import datetime

from .models import Sigmet

# Raw API fields consumed explicitly by _map_one. Anything else present
# on a raw item is preserved verbatim in Sigmet.extra rather than
# dropped, per the "don't drop fields" requirement.
_KNOWN_FIELDS = frozenset(
    {
        "id",
        "firId",
        "firName",
        "hazard",
        "qualifier",
        "base",
        "top",
        "validTimeFrom",
        "validTimeTo",
        "coords",
        "rawSigmet",
    },
)


class SigmetMapper:
    """SIGMET mapper."""

    def map(
        self,
        raw_list: list[dict],
        *,
        fir_id: str,
    ) -> list[Sigmet]:
        """Map a raw isigmet API response to Sigmet objects for one FIR.

        The API is not known to reliably filter by FIR itself, so
        filtering by `firId` happens here, client-side.
        """
        return [self._map_one(item) for item in raw_list if item.get("firId") == fir_id]

    def _map_one(
        self,
        item: dict,
    ) -> Sigmet:
        """Map a single raw SIGMET item."""
        fir_id = item.get("firId", "")
        hazard = item.get("hazard")
        raw = item.get("rawSigmet", "")

        valid_from = self._from_iso_datetime(item.get("validTimeFrom"))
        valid_to = self._from_iso_datetime(item.get("validTimeTo"))

        advisory_id = item.get("id") or self._generate_id(
            fir_id=fir_id,
            valid_from=valid_from,
            valid_to=valid_to,
            hazard=hazard,
            raw=raw,
        )

        extra = {key: value for key, value in item.items() if key not in _KNOWN_FIELDS}

        return Sigmet(
            id=advisory_id,
            fir_id=fir_id,
            fir_name=item.get("firName"),
            hazard=hazard,
            qualifier=item.get("qualifier"),
            base=item.get("base"),
            top=item.get("top"),
            valid_from=valid_from,
            valid_to=valid_to,
            coordinates=item.get("coords", []),
            raw=raw,
            extra=extra,
        )

    def _generate_id(
        self,
        *,
        fir_id: str,
        valid_from: datetime,
        valid_to: datetime,
        hazard: str | None,
        raw: str,
    ) -> str:
        """Generate a deterministic ID when the API doesn't provide one.

        Hashes stable fields so the same SIGMET produces the same ID
        across successive polls (needed for stable entity attribute
        identity), without depending on any API-assigned identifier.
        """
        fingerprint = "|".join(
            [
                fir_id,
                valid_from.isoformat(),
                valid_to.isoformat(),
                hazard or "",
                raw,
            ],
        )

        return hashlib.sha256(fingerprint.encode()).hexdigest()[:16]

    def _from_iso_datetime(
        self,
        value: str | None,
    ) -> datetime:
        """Convert ISO datetime.

        SIGMET validity timestamps are required fields — a SIGMET
        without a validity window can't be evaluated for "is this
        active", so a missing/unparseable value is a genuine error
        rather than something to default away.
        """
        if value is None:
            raise ValueError("SIGMET item is missing a required validity timestamp")

        return datetime.fromisoformat(value.replace("Z", "+00:00"))
