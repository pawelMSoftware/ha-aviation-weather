"""Tests for the METAR data update coordinator."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock

import pytest
from aiohttp import ClientError
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aviation_weather.const import CONF_AIRPORT, DOMAIN
from custom_components.aviation_weather.metar.coordinator import MetarCoordinator
from custom_components.aviation_weather.metar.models import MetarData


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return a mock config entry configured for EPWA."""
    return MockConfigEntry(domain=DOMAIN, data={CONF_AIRPORT: "EPWA"})


@pytest.fixture
def sample_metar_data() -> MetarData:
    """Return a minimal valid MetarData instance."""
    return MetarData(
        airport="EPWA",
        airport_name="Warszawa Chopina",
        latitude=52.16,
        longitude=20.96,
        elevation=110,
        temperature=15.0,
        dewpoint=10.0,
        pressure=1013.0,
        sea_level_pressure=1014.0,
        wind_speed=5,
        wind_gust=None,
        wind_direction="270",
        visibility_meters=10000,
        flight_category=None,
        metar_type=None,
        weather=None,
        snow_depth=None,
        vertical_visibility=None,
        cloud_layers=[],
        observation_time=None,
        raw_metar="",
    )


class TestAsyncUpdateData:
    """Tests for MetarCoordinator._async_update_data."""

    async def test_returns_data_on_success(
        self, hass, config_entry: MockConfigEntry, sample_metar_data: MetarData
    ) -> None:
        """A successful client call returns the METAR data unchanged."""
        client = AsyncMock()
        client.get_metar.return_value = sample_metar_data

        coordinator = MetarCoordinator(hass=hass, entry=config_entry, client=client)
        result = await coordinator._async_update_data()

        assert result is sample_metar_data
        client.get_metar.assert_called_once_with("EPWA")

    async def test_client_error_becomes_update_failed(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        """A ClientError from the API client is wrapped in UpdateFailed."""
        client = AsyncMock()
        client.get_metar.side_effect = ClientError("connection reset")

        coordinator = MetarCoordinator(hass=hass, entry=config_entry, client=client)

        with pytest.raises(UpdateFailed, match="Unable to fetch METAR data"):
            await coordinator._async_update_data()

    async def test_value_error_becomes_update_failed(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        """A ValueError (e.g. missing icaoId) is wrapped in UpdateFailed."""
        client = AsyncMock()
        client.get_metar.side_effect = ValueError("No METAR data returned")

        coordinator = MetarCoordinator(hass=hass, entry=config_entry, client=client)

        with pytest.raises(UpdateFailed, match="No current METAR data"):
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
        client.get_metar.side_effect = TypeError("unexpected bug")

        coordinator = MetarCoordinator(hass=hass, entry=config_entry, client=client)

        with pytest.raises(TypeError):
            await coordinator._async_update_data()


class TestAsyncFirstRefresh:
    """Tests for MetarCoordinator.async_first_refresh.

    METAR is the integration's core data source, so a real connectivity
    problem should still block setup (ConfigEntryNotReady, triggering
    HA's retry). But if the airport simply has no current METAR report
    (e.g. a temporary reporting gap), setup should proceed instead of
    failing outright.
    """

    async def test_success_does_not_raise(
        self, hass, config_entry: MockConfigEntry, sample_metar_data: MetarData
    ) -> None:
        """A successful first refresh does not raise."""
        client = AsyncMock()
        client.get_metar.return_value = sample_metar_data

        coordinator = MetarCoordinator(hass=hass, entry=config_entry, client=client)

        await coordinator.async_first_refresh()

        assert coordinator.last_update_success is True

    async def test_connectivity_error_raises_config_entry_not_ready(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        """A connectivity error (ClientError) blocks setup, so HA retries."""
        client = AsyncMock()
        client.get_metar.side_effect = ClientError("connection reset")

        coordinator = MetarCoordinator(hass=hass, entry=config_entry, client=client)

        with pytest.raises(ConfigEntryNotReady):
            await coordinator.async_first_refresh()

    async def test_no_data_does_not_raise(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        """An airport with no current METAR report does NOT block setup.

        The coordinator's last_update_success stays False (so the sensor
        starts as unavailable), but the integration still loads.
        """
        client = AsyncMock()
        client.get_metar.side_effect = ValueError("No METAR data returned")

        coordinator = MetarCoordinator(hass=hass, entry=config_entry, client=client)

        await coordinator.async_first_refresh()

        assert coordinator.last_update_success is False


class TestStaleDataRepairIssue:
    """Tests for the stale-METAR Repairs issue (helpers.py's
    async_maybe_create_stale_data_issue / async_clear_stale_data_issue,
    wired into MetarCoordinator._async_update_data)."""

    async def test_repeated_failure_past_threshold_creates_issue(
        self, hass, config_entry: MockConfigEntry, sample_metar_data: MetarData
    ) -> None:
        client = AsyncMock()
        client.get_metar.return_value = sample_metar_data

        coordinator = MetarCoordinator(hass=hass, entry=config_entry, client=client)
        await coordinator.async_refresh()
        assert coordinator.last_update_success_time is not None

        # Simulate several hours passing since the last success.
        coordinator.last_update_success_time -= timedelta(hours=7)

        client.get_metar.side_effect = ClientError("connection reset")
        await coordinator.async_refresh()

        issue_id = f"stale_metar_{config_entry.entry_id}"
        issue = ir.async_get(hass).async_get_issue(DOMAIN, issue_id)
        assert issue is not None
        assert issue.translation_placeholders == {"airport": "EPWA"}

    async def test_brief_failure_does_not_create_issue(
        self, hass, config_entry: MockConfigEntry, sample_metar_data: MetarData
    ) -> None:
        """A single failed poll shortly after success must not create
        an issue — only sustained failure past the threshold does."""
        client = AsyncMock()
        client.get_metar.return_value = sample_metar_data

        coordinator = MetarCoordinator(hass=hass, entry=config_entry, client=client)
        await coordinator.async_refresh()

        client.get_metar.side_effect = ClientError("connection reset")
        await coordinator.async_refresh()

        issue_id = f"stale_metar_{config_entry.entry_id}"
        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None

    async def test_recovery_clears_the_issue(
        self, hass, config_entry: MockConfigEntry, sample_metar_data: MetarData
    ) -> None:
        client = AsyncMock()
        client.get_metar.return_value = sample_metar_data

        coordinator = MetarCoordinator(hass=hass, entry=config_entry, client=client)
        await coordinator.async_refresh()
        coordinator.last_update_success_time -= timedelta(hours=7)

        client.get_metar.side_effect = ClientError("connection reset")
        await coordinator.async_refresh()

        issue_id = f"stale_metar_{config_entry.entry_id}"
        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None

        client.get_metar.side_effect = None
        client.get_metar.return_value = sample_metar_data
        await coordinator.async_refresh()

        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None
