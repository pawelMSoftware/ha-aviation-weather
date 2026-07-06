"""Tests for the SIGMET data update coordinator."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp import ClientError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import UpdateFailed
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aviation_weather.const import CONF_FIR, DOMAIN
from custom_components.aviation_weather.sigmet.coordinator import SigmetCoordinator
from custom_components.aviation_weather.sigmet.models import Sigmet


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return a mock FIR config entry for EPWW."""
    return MockConfigEntry(domain=DOMAIN, data={CONF_FIR: "EPWW"})


def _make_sigmet(
    *,
    valid_from: datetime,
    valid_to: datetime,
    hazard: str | None = "TURB",
    sigmet_id: str = "sigmet-1",
) -> Sigmet:
    return Sigmet(
        id=sigmet_id,
        fir_id="EPWW",
        fir_name="WARSZAWA FIR",
        hazard=hazard,
        qualifier="SEV",
        base="FL180",
        top="FL360",
        valid_from=valid_from,
        valid_to=valid_to,
        coordinates=[],
        raw="WSPL31 EPWW",
        extra={},
    )


class TestAsyncUpdateData:
    """Tests for SigmetCoordinator._async_update_data."""

    async def test_returns_data_on_success(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        """A successful client call returns the SIGMET list unchanged."""
        client = AsyncMock()
        sigmets = [
            _make_sigmet(
                valid_from=datetime(2026, 7, 3, 10, tzinfo=UTC),
                valid_to=datetime(2026, 7, 3, 14, tzinfo=UTC),
            ),
        ]
        client.get_sigmets.return_value = sigmets

        coordinator = SigmetCoordinator(hass=hass, entry=config_entry, client=client)
        result = await coordinator._async_update_data()

        assert result is sigmets
        client.get_sigmets.assert_called_once_with("EPWW")

    async def test_empty_list_is_not_an_error(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        """An empty SIGMET list is a normal result, not UpdateFailed."""
        client = AsyncMock()
        client.get_sigmets.return_value = []

        coordinator = SigmetCoordinator(hass=hass, entry=config_entry, client=client)
        result = await coordinator._async_update_data()

        assert result == []

    async def test_client_error_becomes_update_failed(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        """A ClientError from the API client is wrapped in UpdateFailed."""
        client = AsyncMock()
        client.get_sigmets.side_effect = ClientError("connection reset")

        coordinator = SigmetCoordinator(hass=hass, entry=config_entry, client=client)

        with pytest.raises(UpdateFailed, match="Unable to fetch SIGMET data"):
            await coordinator._async_update_data()


class TestAsyncFirstRefresh:
    """Tests for SigmetCoordinator.async_first_refresh.

    Like TafCoordinator, this never raises ConfigEntryNotReady — a
    SIGMET connectivity blip shouldn't block the whole FIR device.
    """

    async def test_success_does_not_raise(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        client = AsyncMock()
        client.get_sigmets.return_value = []

        coordinator = SigmetCoordinator(hass=hass, entry=config_entry, client=client)

        await coordinator.async_first_refresh()

        assert coordinator.last_update_success is True

    async def test_connectivity_error_does_not_raise(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        """Unlike MetarCoordinator, a connectivity error here must not
        raise ConfigEntryNotReady — it should not block FIR setup."""
        client = AsyncMock()
        client.get_sigmets.side_effect = ClientError("connection reset")

        coordinator = SigmetCoordinator(hass=hass, entry=config_entry, client=client)

        await coordinator.async_first_refresh()

        assert coordinator.last_update_success is False


class TestActiveSigmets:
    """Tests for SigmetCoordinator.active_sigmets."""

    async def test_no_data_returns_empty_list(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        client = AsyncMock()
        coordinator = SigmetCoordinator(hass=hass, entry=config_entry, client=client)

        assert coordinator.active_sigmets == []

    async def test_filters_to_currently_active_sigmets(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        client = AsyncMock()
        coordinator = SigmetCoordinator(hass=hass, entry=config_entry, client=client)

        active = _make_sigmet(
            sigmet_id="active",
            valid_from=datetime(2026, 7, 3, 10, tzinfo=UTC),
            valid_to=datetime(2026, 7, 3, 14, tzinfo=UTC),
        )
        expired = _make_sigmet(
            sigmet_id="expired",
            valid_from=datetime(2020, 1, 1, tzinfo=UTC),
            valid_to=datetime(2020, 1, 1, 4, tzinfo=UTC),
        )
        coordinator.async_set_updated_data([active, expired])

        with patch(
            "custom_components.aviation_weather.sigmet.coordinator.dt_util.utcnow",
            return_value=datetime(2026, 7, 3, 12, tzinfo=UTC),
        ):
            result = coordinator.active_sigmets

        assert [sigmet.id for sigmet in result] == ["active"]

    async def test_reflects_expiry_between_polls(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        """A SIGMET that was active at fetch time but has since expired
        must no longer appear active — this is read-time filtering,
        not filtered-once-at-fetch-time."""
        client = AsyncMock()
        coordinator = SigmetCoordinator(hass=hass, entry=config_entry, client=client)

        sigmet = _make_sigmet(
            valid_from=datetime(2026, 7, 3, 10, tzinfo=UTC),
            valid_to=datetime(2026, 7, 3, 14, tzinfo=UTC),
        )
        coordinator.async_set_updated_data([sigmet])

        with patch(
            "custom_components.aviation_weather.sigmet.coordinator.dt_util.utcnow",
            return_value=datetime(2026, 7, 3, 12, tzinfo=UTC),
        ):
            assert len(coordinator.active_sigmets) == 1

        with patch(
            "custom_components.aviation_weather.sigmet.coordinator.dt_util.utcnow",
            return_value=datetime(2026, 7, 3, 15, tzinfo=UTC),
        ):
            assert coordinator.active_sigmets == []


class TestStaleDataRepairIssue:
    """Tests for the stale-SIGMET Repairs issue. Unlike METAR/TAF, an
    empty SIGMET list is a normal success — only a sustained run of
    ClientError failures (a real connectivity problem) triggers this."""

    async def test_repeated_failure_past_threshold_creates_issue(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        client = AsyncMock()
        client.get_sigmets.return_value = []

        coordinator = SigmetCoordinator(hass=hass, entry=config_entry, client=client)
        await coordinator.async_refresh()
        assert coordinator.last_update_success_time is not None

        coordinator.last_update_success_time -= timedelta(hours=7)

        client.get_sigmets.side_effect = ClientError("connection reset")
        await coordinator.async_refresh()

        issue_id = f"stale_sigmet_{config_entry.entry_id}"
        issue = ir.async_get(hass).async_get_issue(DOMAIN, issue_id)
        assert issue is not None
        assert issue.translation_placeholders == {"fir": "EPWW"}

    async def test_brief_failure_does_not_create_issue(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        client = AsyncMock()
        client.get_sigmets.return_value = []

        coordinator = SigmetCoordinator(hass=hass, entry=config_entry, client=client)
        await coordinator.async_refresh()

        client.get_sigmets.side_effect = ClientError("connection reset")
        await coordinator.async_refresh()

        issue_id = f"stale_sigmet_{config_entry.entry_id}"
        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None

    async def test_no_active_sigmets_does_not_create_issue(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        """An empty (successful) result, even repeated for a long time,
        must never be treated as "stale" — it's the normal state."""
        client = AsyncMock()
        client.get_sigmets.return_value = []

        coordinator = SigmetCoordinator(hass=hass, entry=config_entry, client=client)
        await coordinator.async_refresh()
        coordinator.last_update_success_time -= timedelta(hours=7)

        await coordinator.async_refresh()

        issue_id = f"stale_sigmet_{config_entry.entry_id}"
        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None

    async def test_recovery_clears_the_issue(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        client = AsyncMock()
        client.get_sigmets.return_value = []

        coordinator = SigmetCoordinator(hass=hass, entry=config_entry, client=client)
        await coordinator.async_refresh()
        coordinator.last_update_success_time -= timedelta(hours=7)

        client.get_sigmets.side_effect = ClientError("connection reset")
        await coordinator.async_refresh()

        issue_id = f"stale_sigmet_{config_entry.entry_id}"
        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None

        client.get_sigmets.side_effect = None
        client.get_sigmets.return_value = []
        await coordinator.async_refresh()

        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None
