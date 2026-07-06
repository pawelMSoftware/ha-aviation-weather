from __future__ import annotations

from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import issue_registry as ir
from homeassistant.helpers.update_coordinator import TimestampDataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import DOMAIN


def get_entry_value(
    entry: ConfigEntry,
    key: str,
    default: object | None = None,
):
    """Return config entry value."""
    return entry.options.get(
        key,
        entry.data.get(
            key,
            default,
        ),
    )


def async_clear_stale_data_issue(
    hass: HomeAssistant,
    *,
    issue_id: str,
) -> None:
    """Clear a stale-data Repairs issue.

    Call this from a coordinator's success path. Deleting an issue that
    doesn't currently exist is a harmless no-op, so callers don't need
    to track whether one was actually created first.
    """
    ir.async_delete_issue(hass, DOMAIN, issue_id)


def async_maybe_create_stale_data_issue(
    hass: HomeAssistant,
    coordinator: TimestampDataUpdateCoordinator,
    *,
    issue_id: str,
    translation_key: str,
    translation_placeholders: dict[str, str],
    threshold: timedelta,
) -> None:
    """Create a stale-data Repairs issue after sustained coordinator failure.

    Call this from a coordinator's failure path (inside the except
    branch, before re-raising as UpdateFailed) — deliberately not
    inferred from `coordinator.last_update_success`, since that flag is
    only updated by the base DataUpdateCoordinator *after*
    `_async_update_data` returns, so it still reflects the *previous*
    attempt while this one is being handled.

    A brief outage is normal for any of METAR/TAF/SIGMET; only a long,
    continuous run of failures since the last known success is worth
    surfacing as a Repairs issue.
    """
    if coordinator.last_update_success_time is None:
        # Never succeeded yet - nothing has "gone stale" to report.
        return

    if dt_util.utcnow() - coordinator.last_update_success_time < threshold:
        return

    ir.async_create_issue(
        hass,
        DOMAIN,
        issue_id,
        is_fixable=False,
        severity=ir.IssueSeverity.WARNING,
        translation_key=translation_key,
        translation_placeholders=translation_placeholders,
    )
