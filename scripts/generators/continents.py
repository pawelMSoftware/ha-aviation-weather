from __future__ import annotations

import pycountry_convert as pc

# pycountry_convert (which wraps a continent dataset) doesn't recognize
# every code our airport data uses. These are mapped by hand:
# - AQ (Antarctica): not part of any continent grouping in the library.
#   Treated as its own pseudo-continent since it genuinely isn't part
#   of any other one.
# - EH (Western Sahara): disputed territory, not in the library's data.
# - SX (Sint Maarten): Dutch Caribbean territory, missing from the data.
# - TL (Timor-Leste): missing from the data despite being a UN member.
# - UM (US Minor Outlying Islands): scattered Pacific territories.
CONTINENT_OVERRIDES = {
    "AQ": "AN",
    "EH": "AF",
    "SX": "NA",
    "TL": "AS",
    "UM": "OC",
}

CONTINENT_NAMES = {
    "AF": "Africa",
    "AN": "Antarctica",
    "AS": "Asia",
    "EU": "Europe",
    "NA": "North America",
    "OC": "Oceania",
    "SA": "South America",
}


def continent_for_country(
    country_code: str,
) -> str:
    """Return the continent code for a given ISO 3166-1 country code."""

    if country_code in CONTINENT_OVERRIDES:
        return CONTINENT_OVERRIDES[country_code]

    try:
        return pc.country_alpha2_to_continent_code(
            country_code,
        )
    except KeyError:
        return "OTHER"
