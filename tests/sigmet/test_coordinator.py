"""Tests for the SIGMET data update coordinator."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientError
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import UpdateFailed
from homeassistant.util import dt as dt_util
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

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


class TestExpiryTimer:
    """Tests for the async_track_point_in_utc_time-based expiry wake-up.

    Real "now" (not a patched dt_util.utcnow) is used as the baseline
    here, with SIGMET windows offset by a few real seconds — the
    underlying scheduling (_TrackPointUTCTime) computes its delay from
    the real wall clock (time.time()), not from dt_util.utcnow, so
    mixing a frozen fake "now" with real timer firing would produce
    nonsensical delays. async_fire_time_changed still lets these fire
    deterministically without an actual sleep.
    """

    async def test_schedules_for_nearest_active_valid_to(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        """Given two active SIGMETs, the timer targets the sooner one,
        regardless of list order."""
        client = AsyncMock()
        now = dt_util.utcnow()
        sooner = _make_sigmet(
            sigmet_id="sooner",
            valid_from=now - timedelta(minutes=1),
            valid_to=now + timedelta(minutes=5),
        )
        later = _make_sigmet(
            sigmet_id="later",
            valid_from=now - timedelta(minutes=1),
            valid_to=now + timedelta(minutes=30),
        )
        client.get_sigmets.return_value = [later, sooner]

        coordinator = SigmetCoordinator(hass=hass, entry=config_entry, client=client)

        with patch(
            "custom_components.aviation_weather.sigmet.coordinator"
            ".async_track_point_in_utc_time",
        ) as mock_track:
            await coordinator.async_refresh()

        mock_track.assert_called_once()
        assert mock_track.call_args.args[2] == sooner.valid_to

    async def test_no_timer_when_nothing_active(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        client = AsyncMock()
        client.get_sigmets.return_value = []

        coordinator = SigmetCoordinator(hass=hass, entry=config_entry, client=client)
        await coordinator.async_refresh()

        assert coordinator._unsub_expiry is None

    async def test_no_timer_when_only_expired_sigmets(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        client = AsyncMock()
        now = dt_util.utcnow()
        expired = _make_sigmet(
            valid_from=now - timedelta(hours=2),
            valid_to=now - timedelta(hours=1),
        )
        client.get_sigmets.return_value = [expired]

        coordinator = SigmetCoordinator(hass=hass, entry=config_entry, client=client)
        await coordinator.async_refresh()

        assert coordinator._unsub_expiry is None

    async def test_previous_timer_cancelled_before_scheduling_new_one(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        """A fresh successful poll must cancel the old timer, not stack
        a second one alongside it."""
        client = AsyncMock()
        now = dt_util.utcnow()
        sigmet = _make_sigmet(
            valid_from=now - timedelta(minutes=1),
            valid_to=now + timedelta(minutes=5),
        )
        client.get_sigmets.return_value = [sigmet]

        coordinator = SigmetCoordinator(hass=hass, entry=config_entry, client=client)

        first_cancel = MagicMock()
        second_cancel = MagicMock()
        with patch(
            "custom_components.aviation_weather.sigmet.coordinator"
            ".async_track_point_in_utc_time",
            side_effect=[first_cancel, second_cancel],
        ):
            await coordinator.async_refresh()
            await coordinator.async_refresh()

        first_cancel.assert_called_once()
        second_cancel.assert_not_called()

    async def test_transport_failure_does_not_touch_existing_timer(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        """A failed poll must not cancel a still-valid pending timer —
        only a successful update reschedules."""
        client = AsyncMock()
        now = dt_util.utcnow()
        sigmet = _make_sigmet(
            valid_from=now - timedelta(minutes=1),
            valid_to=now + timedelta(minutes=5),
        )
        client.get_sigmets.return_value = [sigmet]

        coordinator = SigmetCoordinator(hass=hass, entry=config_entry, client=client)
        await coordinator.async_refresh()
        unsub_after_success = coordinator._unsub_expiry
        assert unsub_after_success is not None

        client.get_sigmets.side_effect = ClientError("connection reset")
        with pytest.raises(UpdateFailed):
            await coordinator._async_update_data()

        assert coordinator._unsub_expiry is unsub_after_success
        coordinator._cancel_expiry_timer()

    async def test_firing_at_expiry_notifies_listeners_and_reflects_expiry(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        """End-to-end: once real time passes valid_to, the scheduled
        callback actually fires, notifies listeners (what makes
        CoordinatorEntity re-read is_on/attributes), and active_sigmets
        reflects the expiry — all without any new API call."""
        client = AsyncMock()
        now = dt_util.utcnow()
        expiry = now + timedelta(seconds=2)
        sigmet = _make_sigmet(
            valid_from=now - timedelta(minutes=1),
            valid_to=expiry,
        )
        client.get_sigmets.return_value = [sigmet]

        coordinator = SigmetCoordinator(hass=hass, entry=config_entry, client=client)
        await coordinator.async_refresh()

        listener = MagicMock()
        coordinator.async_add_listener(listener)

        # dt_util.utcnow (used by active_advisories) is independent of
        # the real-time-based loop.call_at scheduling that
        # async_fire_time_changed simulates — it must be patched
        # separately so "is this SIGMET active" agrees with the
        # simulated fire time, not the real (barely-elapsed) wall clock.
        fired_at = expiry + timedelta(seconds=1)
        with patch(
            "custom_components.aviation_weather.sigmet.coordinator.dt_util.utcnow",
            return_value=fired_at,
        ):
            async_fire_time_changed(hass, fired_at)
            await hass.async_block_till_done()

            listener.assert_called()
            assert coordinator.active_sigmets == []
            assert coordinator._unsub_expiry is None

        client.get_sigmets.assert_called_once()
        # async_add_listener above schedules the coordinator's own
        # periodic refresh timer; shut it down so it doesn't linger
        # past this test.
        await coordinator.async_shutdown()

    async def test_reschedules_for_next_nearest_after_first_fires(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        """Two staggered SIGMETs: once the sooner one's timer fires,
        the coordinator reschedules for the still-active second one
        instead of leaving no timer at all."""
        client = AsyncMock()
        now = dt_util.utcnow()
        first_expiry = now + timedelta(seconds=2)
        second_expiry = now + timedelta(seconds=100)
        soon = _make_sigmet(
            sigmet_id="soon",
            valid_from=now - timedelta(minutes=1),
            valid_to=first_expiry,
        )
        later = _make_sigmet(
            sigmet_id="later",
            valid_from=now - timedelta(minutes=1),
            valid_to=second_expiry,
        )
        client.get_sigmets.return_value = [soon, later]

        coordinator = SigmetCoordinator(hass=hass, entry=config_entry, client=client)
        await coordinator.async_refresh()
        first_unsub = coordinator._unsub_expiry
        assert first_unsub is not None

        fired_at = first_expiry + timedelta(seconds=1)
        with patch(
            "custom_components.aviation_weather.sigmet.coordinator.dt_util.utcnow",
            return_value=fired_at,
        ):
            async_fire_time_changed(hass, fired_at)
            await hass.async_block_till_done()

            assert coordinator._unsub_expiry is not None
            assert coordinator._unsub_expiry is not first_unsub
            assert [sigmet.id for sigmet in coordinator.active_sigmets] == ["later"]

        coordinator._cancel_expiry_timer()

    async def test_unload_cancels_pending_timer(
        self, hass, config_entry: MockConfigEntry
    ) -> None:
        """The entry's async_on_unload hook must cancel a pending timer
        so it doesn't fire after the FIR device has been torn down."""
        client = AsyncMock()
        now = dt_util.utcnow()
        sigmet = _make_sigmet(
            valid_from=now - timedelta(minutes=1),
            valid_to=now + timedelta(minutes=5),
        )
        client.get_sigmets.return_value = [sigmet]
        config_entry.add_to_hass(hass)

        coordinator = SigmetCoordinator(hass=hass, entry=config_entry, client=client)
        await coordinator.async_refresh()
        assert coordinator._unsub_expiry is not None

        for unload_callback in list(config_entry._on_unload or []):
            unload_callback()

        assert coordinator._unsub_expiry is None
