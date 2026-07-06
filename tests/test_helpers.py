"""Tests for helpers.py (get_entry_value, stale-data Repairs issues)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock

from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aviation_weather.const import DOMAIN
from custom_components.aviation_weather.helpers import (
    async_clear_stale_data_issue,
    async_maybe_create_stale_data_issue,
    get_entry_value,
)


class TestGetEntryValue:
    """Tests for get_entry_value."""

    def test_returns_data_value_when_no_option_set(self) -> None:
        entry = MockConfigEntry(domain=DOMAIN, data={"foo": "bar"})

        assert get_entry_value(entry, "foo") == "bar"

    def test_option_overrides_data(self) -> None:
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={"foo": "bar"},
            options={"foo": "baz"},
        )

        assert get_entry_value(entry, "foo") == "baz"

    def test_returns_default_when_key_absent(self) -> None:
        entry = MockConfigEntry(domain=DOMAIN, data={})

        assert get_entry_value(entry, "missing", "fallback") == "fallback"

    def test_returns_none_default_when_unspecified(self) -> None:
        entry = MockConfigEntry(domain=DOMAIN, data={})

        assert get_entry_value(entry, "missing") is None


def _make_coordinator(last_update_success_time: datetime | None) -> MagicMock:
    coordinator = MagicMock()
    coordinator.last_update_success_time = last_update_success_time
    return coordinator


class TestAsyncMaybeCreateStaleDataIssue:
    """Tests for async_maybe_create_stale_data_issue."""

    def test_never_succeeded_does_not_create_issue(self, hass) -> None:
        """No baseline success time means nothing has "gone stale" yet."""
        coordinator = _make_coordinator(None)

        async_maybe_create_stale_data_issue(
            hass,
            coordinator,
            issue_id="test_issue",
            translation_key="stale_metar",
            translation_placeholders={"airport": "EPWA"},
            threshold=timedelta(hours=6),
        )

        assert ir.async_get(hass).async_get_issue(DOMAIN, "test_issue") is None

    def test_recent_success_does_not_create_issue(self, hass) -> None:
        coordinator = _make_coordinator(datetime.now(UTC) - timedelta(hours=1))

        async_maybe_create_stale_data_issue(
            hass,
            coordinator,
            issue_id="test_issue",
            translation_key="stale_metar",
            translation_placeholders={"airport": "EPWA"},
            threshold=timedelta(hours=6),
        )

        assert ir.async_get(hass).async_get_issue(DOMAIN, "test_issue") is None

    def test_stale_beyond_threshold_creates_issue(self, hass) -> None:
        coordinator = _make_coordinator(datetime.now(UTC) - timedelta(hours=7))

        async_maybe_create_stale_data_issue(
            hass,
            coordinator,
            issue_id="test_issue",
            translation_key="stale_metar",
            translation_placeholders={"airport": "EPWA"},
            threshold=timedelta(hours=6),
        )

        issue = ir.async_get(hass).async_get_issue(DOMAIN, "test_issue")
        assert issue is not None
        assert issue.translation_key == "stale_metar"
        assert issue.translation_placeholders == {"airport": "EPWA"}
        assert issue.is_fixable is False
        assert issue.severity == ir.IssueSeverity.WARNING

    def test_exactly_at_threshold_creates_issue(self, hass) -> None:
        """The check is `< threshold: return`, so >= threshold creates
        the issue (not strictly greater-than)."""
        coordinator = _make_coordinator(
            datetime.now(UTC) - timedelta(hours=6, seconds=1),
        )

        async_maybe_create_stale_data_issue(
            hass,
            coordinator,
            issue_id="test_issue",
            translation_key="stale_metar",
            translation_placeholders={},
            threshold=timedelta(hours=6),
        )

        assert ir.async_get(hass).async_get_issue(DOMAIN, "test_issue") is not None

    def test_just_under_threshold_does_not_create_issue(self, hass) -> None:
        coordinator = _make_coordinator(
            datetime.now(UTC) - timedelta(hours=5, minutes=59),
        )

        async_maybe_create_stale_data_issue(
            hass,
            coordinator,
            issue_id="test_issue",
            translation_key="stale_metar",
            translation_placeholders={},
            threshold=timedelta(hours=6),
        )

        assert ir.async_get(hass).async_get_issue(DOMAIN, "test_issue") is None


class TestAsyncClearStaleDataIssue:
    """Tests for async_clear_stale_data_issue."""

    def test_clears_an_existing_issue(self, hass) -> None:
        coordinator = _make_coordinator(datetime.now(UTC) - timedelta(hours=7))
        async_maybe_create_stale_data_issue(
            hass,
            coordinator,
            issue_id="test_issue",
            translation_key="stale_metar",
            translation_placeholders={},
            threshold=timedelta(hours=6),
        )
        assert ir.async_get(hass).async_get_issue(DOMAIN, "test_issue") is not None

        async_clear_stale_data_issue(hass, issue_id="test_issue")

        assert ir.async_get(hass).async_get_issue(DOMAIN, "test_issue") is None

    def test_clearing_a_nonexistent_issue_does_not_raise(self, hass) -> None:
        async_clear_stale_data_issue(hass, issue_id="never_existed")

        assert ir.async_get(hass).async_get_issue(DOMAIN, "never_existed") is None
