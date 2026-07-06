"""Shared pytest fixtures for the Aviation Weather test suite."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable loading custom_components/* as real integrations in tests.

    Without this, hass.config_entries.flow.async_init(DOMAIN, ...) raises
    IntegrationNotFound for any custom component, since Home Assistant's
    integration loader only looks at built-in integrations by default.
    """
    return enable_custom_integrations


@pytest.fixture
def metar_payload_full() -> dict:
    """Return a full, realistic METAR API payload for EPWA."""
    return {
        "icaoId": "EPWA",
        "name": "Warszawa Chopina",
        "lat": 52.165,
        "lon": 20.967,
        "elev": 110,
        "temp": 18.0,
        "dewp": 12.0,
        "altim": 1015.0,
        "slp": 1016.2,
        "wspd": 8,
        "wgst": 15,
        "wdir": 270,
        "visib": "10+",
        "fltCat": "VFR",
        "metarType": "METAR",
        "wxString": "-RA",
        "snow": None,
        "vertVis": None,
        "clouds": [
            {"cover": "FEW", "base": 2500},
            {"cover": "BKN", "base": 4000},
        ],
        "reportTime": "2026-06-27T12:00:00Z",
        "rawOb": "METAR EPWA 271200Z 27008KT 9999 -RA FEW025 BKN040 18/12 Q1015",
    }


@pytest.fixture
def metar_payload_minimal() -> dict:
    """Return a minimal METAR payload with most optional fields missing."""
    return {
        "icaoId": "EPKK",
    }


@pytest.fixture
def taf_payload_full() -> dict:
    """Return a full, realistic TAF API payload for EPWA."""
    return {
        "icaoId": "EPWA",
        "name": "Warszawa Chopina",
        "lat": 52.165,
        "lon": 20.967,
        "elev": 110,
        "issueTime": "2026-06-27T11:00:00Z",
        "validTimeFrom": 1782900000,
        "validTimeTo": 1782986400,
        "rawTAF": "TAF EPWA 271100Z 2712/2818 27010KT 9999 FEW030",
        "fcsts": [
            {
                "timeFrom": 1782900000,
                "timeTo": 1782936000,
                "fcstChange": None,
                "wdir": 270,
                "wspd": 10,
                "wgst": None,
                "visib": "9999",
                "wxString": None,
                "clouds": [
                    {"cover": "FEW", "base": 3000, "type": None},
                ],
            },
            {
                "timeFrom": 1782936000,
                "timeTo": 1782986400,
                "fcstChange": "TEMPO",
                "wdir": 280,
                "wspd": 18,
                "wgst": 28,
                "visib": "5000",
                "wxString": "TSRA",
                "clouds": [
                    {"cover": "BKN", "base": 1500, "type": "CB"},
                ],
            },
        ],
    }


@pytest.fixture
def taf_payload_minimal() -> dict:
    """Return a minimal TAF payload with most optional fields missing."""
    return {
        "icaoId": "EPKK",
    }
