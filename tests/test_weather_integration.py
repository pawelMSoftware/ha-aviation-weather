"""Integration test for the weather entity: full config entry setup,
verifying the entity is created with a real, HA-managed state object
(including unit conversion handled by WeatherEntity itself).
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aviation_weather.const import CONF_AIRPORT, CONF_COUNTRY, DOMAIN

VALID_CONDITIONS = {
    "sunny",
    "clear-night",
    "cloudy",
    "partlycloudy",
    "rainy",
    "pouring",
    "snowy",
    "snowy-rainy",
    "lightning",
    "lightning-rainy",
    "fog",
    "windy",
    "windy-variant",
    "hail",
    "exceptional",
}


def _make_session() -> MagicMock:
    """Build a mock aiohttp session returning a realistic METAR payload
    with FEW clouds (so the resulting condition is deterministic:
    partlycloudy), plus a minimal TAF response."""

    metar_response = MagicMock()
    metar_response.status = 200
    metar_response.raise_for_status = MagicMock()
    metar_response.json = AsyncMock(
        return_value=[
            {
                "icaoId": "EPWA",
                "name": "Warsaw Chopin",
                "temp": 18.0,
                "dewp": 12.0,
                "altim": 1015.0,
                "wspd": 8,
                "wdir": 270,
                "fltCat": "VFR",
                "clouds": [{"cover": "FEW", "base": 2500}],
            },
        ],
    )

    taf_response = MagicMock()
    taf_response.status = 200
    taf_response.raise_for_status = MagicMock()
    taf_response.json = AsyncMock(
        return_value=[
            {"icaoId": "EPWA", "name": "Warsaw Chopin", "rawTAF": "TAF EPWA ..."},
        ],
    )

    def get(url, params=None, **kwargs):
        context_manager = MagicMock()
        if "taf" in url:
            context_manager.__aenter__ = AsyncMock(return_value=taf_response)
        else:
            context_manager.__aenter__ = AsyncMock(return_value=metar_response)
        context_manager.__aexit__ = AsyncMock(return_value=False)
        return context_manager

    session = MagicMock()
    session.get = MagicMock(side_effect=get)
    return session


async def test_weather_entity_loads_with_a_valid_condition_and_units(
    hass, enable_custom_integrations
) -> None:
    """Setting up the integration creates exactly one weather entity,
    with a recognized condition and HA-converted display units."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_COUNTRY: "PL", CONF_AIRPORT: "EPWA"},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.aviation_weather.async_get_clientsession",
        return_value=_make_session(),
    ):
        result = await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert result is True

    weather_states = hass.states.async_all("weather")
    assert len(weather_states) == 1

    state = weather_states[0]

    assert state.state in VALID_CONDITIONS
    assert state.state == "partlycloudy"  # FEW clouds, no precipitation

    assert state.attributes["temperature"] == 18.0
    assert state.attributes["pressure"] == 1015.0
    assert state.attributes["humidity"] is not None
    assert state.attributes["wind_bearing"] == 270.0

    # Native units are knots/hPa/Celsius; HA's default unit system
    # converts wind speed for display, so it should no longer be the
    # raw knots value (8) but a converted km/h figure.
    assert state.attributes["wind_speed"] != 8
    assert state.attributes["wind_speed_unit"] == "km/h"
