"""Integration test for the exact failure scenario reported in production:

An airport (EDFE) returns an empty/204 response from aviationweather.gov
for both METAR and TAF. The integration must still load successfully,
with its sensors starting in an "unavailable" state, rather than
crashing the whole config entry setup.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aviation_weather.const import CONF_AIRPORT, CONF_COUNTRY, DOMAIN


def _make_204_session() -> MagicMock:
    """Build a mock aiohttp session that always returns 204 No Content."""
    response = MagicMock()
    response.status = 204
    response.raise_for_status = MagicMock()
    response.json = AsyncMock(return_value=None)

    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=response)
    context_manager.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock()
    session.get = MagicMock(return_value=context_manager)

    return session


async def test_airport_with_no_current_data_still_loads(
    hass, enable_custom_integrations
) -> None:
    """Setup succeeds and sensors are created (as unavailable) even when
    the airport has no current METAR/TAF report from the API."""

    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_COUNTRY: "DE", CONF_AIRPORT: "EDFE"},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.aviation_weather.async_get_clientsession",
        return_value=_make_204_session(),
    ):
        result = await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    assert result is True
    assert entry.state.value == "loaded"

    state = hass.states.get("sensor.edfe_metar")

    assert state is not None
    assert state.state == "unavailable"
