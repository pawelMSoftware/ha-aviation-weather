"""Tests for the TAF data update coordinator."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from aiohttp import ClientError
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aviation_weather.const import CONF_AIRPORT, DOMAIN
from custom_components.aviation_weather.taf.coordinator import TafCoordinator
from custom_components.aviation_weather.taf.models import TafData


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return a mock config entry configured for EPWA."""
    return MockConfigEntry(domain=DOMAIN, data={CONF_AIRPORT: "EPWA"})


@pytest.fixture
def sample_taf_data() -> TafData:
    """Return a minimal valid TafData instance."""
    return TafData(
        airport="EPWA",
        airport_name="Warszawa Chopina",
        latitude=52.16,
        longitude=20.96,
        elevation=110,
        issue_time=None,
        valid_from=None,
        valid_to=None,
        raw_taf="",
        forecasts=[],
    )


class TestAsyncUpdateData:
    """Tests for TafCoordinator._async_update_data."""

    async def test_returns_data_on_success(
        self, hass, config_entry: MockConfigEntry, sample_taf_data: TafData
    ) -> None:
        """A successful client call returns the TAF data unchanged."""
        client = AsyncMock()
        client.get_taf.return_value = sample_taf_data

        coordinator = TafCoordinator(hass=hass, entry=config_entry, client=client)
        result = await coordinator._async_update_data()

        assert result is sample_taf_data
        client.get_taf.assert_called_once_with("EPWA")

    async def test_client_error_becomes_update_failed(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        """A ClientError from the API client is wrapped in UpdateFailed."""
        client = AsyncMock()
        client.get_taf.side_effect = ClientError("connection reset")

        coordinator = TafCoordinator(hass=hass, entry=config_entry, client=client)

        with pytest.raises(UpdateFailed, match="Unable to fetch TAF data"):
            await coordinator._async_update_data()

    async def test_value_error_becomes_update_failed(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        """A ValueError (e.g. missing icaoId) is wrapped in UpdateFailed."""
        client = AsyncMock()
        client.get_taf.side_effect = ValueError("No TAF data returned")

        coordinator = TafCoordinator(hass=hass, entry=config_entry, client=client)

        with pytest.raises(UpdateFailed, match="No current TAF data"):
            await coordinator._async_update_data()

    async def test_unexpected_exception_is_not_swallowed(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        """An unrelated bug (e.g. TypeError) is NOT masked as UpdateFailed.

        This guards against regressing to a broad `except Exception` in the
        coordinator, which would hide programming errors as ordinary
        connectivity failures.
        """
        client = AsyncMock()
        client.get_taf.side_effect = TypeError("unexpected bug")

        coordinator = TafCoordinator(hass=hass, entry=config_entry, client=client)

        with pytest.raises(TypeError):
            await coordinator._async_update_data()


class TestAsyncFirstRefresh:
    """Tests for TafCoordinator.async_first_refresh.

    TAF is published for only a subset of airports, so a failed first
    refresh should NEVER block integration setup, regardless of the
    failure reason. The TAF sensor simply starts as unavailable.
    """

    async def test_success_does_not_raise(
        self, hass, config_entry: MockConfigEntry, sample_taf_data: TafData
    ) -> None:
        """A successful first refresh does not raise."""
        client = AsyncMock()
        client.get_taf.return_value = sample_taf_data

        coordinator = TafCoordinator(hass=hass, entry=config_entry, client=client)

        await coordinator.async_first_refresh()

        assert coordinator.last_update_success is True

    async def test_connectivity_error_does_not_raise(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        """Even a connectivity error does not block setup for TAF.

        Unlike METAR, TAF is a secondary/optional data source, so its
        coordinator never raises ConfigEntryNotReady.
        """
        client = AsyncMock()
        client.get_taf.side_effect = ClientError("connection reset")

        coordinator = TafCoordinator(hass=hass, entry=config_entry, client=client)

        await coordinator.async_first_refresh()

        assert coordinator.last_update_success is False

    async def test_no_data_does_not_raise(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        """An airport with no TAF data does not block setup."""
        client = AsyncMock()
        client.get_taf.side_effect = ValueError("No TAF data returned")

        coordinator = TafCoordinator(hass=hass, entry=config_entry, client=client)

        await coordinator.async_first_refresh()

        assert coordinator.last_update_success is False
