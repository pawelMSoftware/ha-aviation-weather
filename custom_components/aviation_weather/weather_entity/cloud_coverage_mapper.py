"""Map METAR cloud layers to Home Assistant's `cloud_coverage` (%).

METAR reports cloud cover per layer using WMO/ICAO okta-based codes
(FEW/SCT/BKN/OVC), not a direct percentage. This maps each code to a
representative percentage using the upper bound of its okta range
(8 oktas = 100% sky coverage):

    FEW (1-2 oktas)  -> 25%
    SCT (3-4 oktas)  -> 50%
    BKN (5-7 oktas)  -> 88%  (7/8, rounded)
    OVC (8 oktas)    -> 100%

Layers are cumulative in METAR (an OVC layer above a FEW layer still
means the sky is 100% covered overall), so the maximum coverage across
all reported layers is used — matching how `condition_mapper` already
treats cloud cover as "whichever layer is most significant".
"""

from __future__ import annotations

from ..metar.enums import CloudCover
from ..metar.models import MetarData

# Representative percentage for each cover code, using the upper bound
# of its WMO okta range (an okta is 1/8 of the sky, so 8 oktas = 100%).
_COVERAGE_PERCENT: dict[CloudCover, float] = {
    CloudCover.CLEAR: 0,
    CloudCover.SKY_CLEAR: 0,
    CloudCover.NO_SIGNIFICANT_CLOUDS: 0,
    CloudCover.FEW: 25,  # 2/8
    CloudCover.SCATTERED: 50,  # 4/8
    CloudCover.BROKEN: 88,  # 7/8, rounded
    CloudCover.OVERCAST: 100,  # 8/8
    CloudCover.VERTICAL_VISIBILITY: 100,  # sky obscured: treated as fully covered
}


def map_cloud_coverage(
    metar: MetarData,
) -> float | None:
    """Return the most significant cloud layer's coverage, as a percentage.

    Returns None if there's no usable cloud layer data at all (neither
    an explicit clear-sky code nor any reported layer) — matching
    map_condition's distinction between "no data" and "clear sky",
    except here a missing clouds array is genuinely ambiguous for a
    numeric percentage (unlike condition, which can safely default to
    sunny/clear-night), so this intentionally returns None rather than
    guessing 0%.
    """

    known_covers = [
        layer.cover
        for layer in metar.cloud_layers
        if isinstance(layer.cover, CloudCover)
    ]

    if not known_covers:
        return None

    return max(_COVERAGE_PERCENT[cover] for cover in known_covers)
