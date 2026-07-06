"""Tests for the shared AirspaceAdvisory model and active_advisories helper."""

from __future__ import annotations

from datetime import UTC, datetime

from custom_components.aviation_weather.airspace_advisory import (
    AirspaceAdvisory,
    active_advisories,
)


def _make_advisory(
    *,
    advisory_id: str,
    valid_from: datetime,
    valid_to: datetime,
) -> AirspaceAdvisory:
    return AirspaceAdvisory(
        id=advisory_id,
        fir_id="EPWW",
        fir_name="WARSZAWA FIR",
        hazard="TURB",
        qualifier="SEV",
        base="FL180",
        top="FL360",
        valid_from=valid_from,
        valid_to=valid_to,
        coordinates=[],
        raw="raw text",
        extra={},
    )


class TestActiveAdvisories:
    def test_advisory_within_window_is_active(self) -> None:
        advisory = _make_advisory(
            advisory_id="a",
            valid_from=datetime(2026, 7, 3, 10, tzinfo=UTC),
            valid_to=datetime(2026, 7, 3, 14, tzinfo=UTC),
        )

        result = active_advisories(
            [advisory],
            now=datetime(2026, 7, 3, 12, tzinfo=UTC),
        )

        assert result == [advisory]

    def test_advisory_before_window_is_not_active(self) -> None:
        advisory = _make_advisory(
            advisory_id="a",
            valid_from=datetime(2026, 7, 3, 10, tzinfo=UTC),
            valid_to=datetime(2026, 7, 3, 14, tzinfo=UTC),
        )

        result = active_advisories(
            [advisory],
            now=datetime(2026, 7, 3, 9, tzinfo=UTC),
        )

        assert result == []

    def test_advisory_after_window_is_not_active(self) -> None:
        advisory = _make_advisory(
            advisory_id="a",
            valid_from=datetime(2026, 7, 3, 10, tzinfo=UTC),
            valid_to=datetime(2026, 7, 3, 14, tzinfo=UTC),
        )

        result = active_advisories(
            [advisory],
            now=datetime(2026, 7, 3, 15, tzinfo=UTC),
        )

        assert result == []

    def test_now_exactly_at_valid_from_is_active(self) -> None:
        advisory = _make_advisory(
            advisory_id="a",
            valid_from=datetime(2026, 7, 3, 10, tzinfo=UTC),
            valid_to=datetime(2026, 7, 3, 14, tzinfo=UTC),
        )

        result = active_advisories(
            [advisory],
            now=datetime(2026, 7, 3, 10, tzinfo=UTC),
        )

        assert result == [advisory]

    def test_now_exactly_at_valid_to_is_active(self) -> None:
        advisory = _make_advisory(
            advisory_id="a",
            valid_from=datetime(2026, 7, 3, 10, tzinfo=UTC),
            valid_to=datetime(2026, 7, 3, 14, tzinfo=UTC),
        )

        result = active_advisories(
            [advisory],
            now=datetime(2026, 7, 3, 14, tzinfo=UTC),
        )

        assert result == [advisory]

    def test_empty_list_returns_empty_list(self) -> None:
        assert active_advisories([], now=datetime(2026, 7, 3, tzinfo=UTC)) == []

    def test_now_defaults_to_utcnow_when_omitted(self) -> None:
        advisory = _make_advisory(
            advisory_id="a",
            valid_from=datetime(1970, 1, 1, tzinfo=UTC),
            valid_to=datetime(2099, 1, 1, tzinfo=UTC),
        )

        assert active_advisories([advisory]) == [advisory]
