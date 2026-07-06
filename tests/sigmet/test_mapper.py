"""Tests for SigmetMapper."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from custom_components.aviation_weather.sigmet.mapper import SigmetMapper


def _raw_sigmet(**overrides: object) -> dict:
    """Return a realistic raw isigmet API item for EPWW, with overrides."""
    payload = {
        "firId": "EPWW",
        "firName": "WARSZAWA FIR",
        "hazard": "TURB",
        "qualifier": "SEV",
        "base": "FL180",
        "top": "FL360",
        "validTimeFrom": "2026-07-03T10:00:00Z",
        "validTimeTo": "2026-07-03T14:00:00Z",
        "coords": [{"lat": 52.1, "lon": 20.9}],
        "rawSigmet": "WSPL31 EPWW 031000",
    }
    payload.update(overrides)
    return payload


class TestNoSigmet:
    """No SIGMET items in the raw response."""

    def test_empty_list_returns_empty_list(self) -> None:
        assert SigmetMapper().map([], fir_id="EPWW") == []

    def test_no_matching_fir_returns_empty_list(self) -> None:
        raw = [_raw_sigmet(firId="LFFF")]

        assert SigmetMapper().map(raw, fir_id="EPWW") == []


class TestOneActiveSigmet:
    """One SIGMET matching the requested FIR."""

    def test_maps_all_known_fields(self) -> None:
        raw = [_raw_sigmet()]

        result = SigmetMapper().map(raw, fir_id="EPWW")

        assert len(result) == 1
        sigmet = result[0]
        assert sigmet.fir_id == "EPWW"
        assert sigmet.fir_name == "WARSZAWA FIR"
        assert sigmet.hazard == "TURB"
        assert sigmet.qualifier == "SEV"
        assert sigmet.base == "FL180"
        assert sigmet.top == "FL360"
        assert sigmet.valid_from == datetime(2026, 7, 3, 10, 0, tzinfo=UTC)
        assert sigmet.valid_to == datetime(2026, 7, 3, 14, 0, tzinfo=UTC)
        assert sigmet.coordinates == [{"lat": 52.1, "lon": 20.9}]
        assert sigmet.raw == "WSPL31 EPWW 031000"


class TestMultipleActiveSigmets:
    """Multiple SIGMET items for the same FIR."""

    def test_returns_all_matching_items(self) -> None:
        raw = [
            _raw_sigmet(hazard="TURB"),
            _raw_sigmet(hazard="ICE", rawSigmet="WSPL31 EPWW 031001"),
        ]

        result = SigmetMapper().map(raw, fir_id="EPWW")

        assert len(result) == 2
        assert {sigmet.hazard for sigmet in result} == {"TURB", "ICE"}

    def test_multiple_hazards_are_distinct_sigmets(self) -> None:
        raw = [
            _raw_sigmet(hazard="TURB", rawSigmet="a"),
            _raw_sigmet(hazard="ICE", rawSigmet="b"),
            _raw_sigmet(hazard="TS", rawSigmet="c"),
        ]

        result = SigmetMapper().map(raw, fir_id="EPWW")

        hazards = [sigmet.hazard for sigmet in result]
        assert hazards == ["TURB", "ICE", "TS"]


class TestExpiredSigmet:
    """Mapping doesn't filter by validity — that's active_advisories's job."""

    def test_expired_sigmet_is_still_mapped(self) -> None:
        raw = [
            _raw_sigmet(
                validTimeFrom="2020-01-01T00:00:00Z",
                validTimeTo="2020-01-01T04:00:00Z",
            ),
        ]

        result = SigmetMapper().map(raw, fir_id="EPWW")

        assert len(result) == 1
        assert result[0].valid_to == datetime(2020, 1, 1, 4, 0, tzinfo=UTC)


class TestMalformedRecordIsSkippedNotFatal:
    """valid_from/valid_to are required to evaluate "is this active" —
    but a single malformed record must not take down the whole batch:
    it's logged and skipped, and every other, valid record is still
    returned."""

    def test_missing_valid_from_is_skipped_with_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        raw_item = _raw_sigmet()
        del raw_item["validTimeFrom"]

        with caplog.at_level("WARNING"):
            result = SigmetMapper().map([raw_item], fir_id="EPWW")

        assert result == []
        assert "Skipping malformed SIGMET record" in caplog.text
        assert "EPWW" in caplog.text

    def test_missing_valid_to_is_skipped_with_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        raw_item = _raw_sigmet()
        del raw_item["validTimeTo"]

        with caplog.at_level("WARNING"):
            result = SigmetMapper().map([raw_item], fir_id="EPWW")

        assert result == []
        assert "Skipping malformed SIGMET record" in caplog.text

    def test_one_malformed_record_does_not_discard_the_others(self) -> None:
        """The core requirement: 99 good records must survive 1 bad one."""
        broken = _raw_sigmet(rawSigmet="BROKEN")
        del broken["validTimeFrom"]
        good = [_raw_sigmet(rawSigmet=f"GOOD-{i}") for i in range(5)]

        result = SigmetMapper().map([broken, *good], fir_id="EPWW")

        assert len(result) == 5
        assert {sigmet.raw for sigmet in result} == {f"GOOD-{i}" for i in range(5)}

    def test_structurally_invalid_item_is_skipped(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        """An item that isn't even a well-formed dict (e.g. a bare
        string) must be skipped, not crash the mapper."""
        with caplog.at_level("WARNING"):
            result = SigmetMapper().map(["not-a-dict"], fir_id="EPWW")

        assert result == []
        assert "Skipping malformed SIGMET record" in caplog.text


class TestMissingOptionalFields:
    """base, top, and qualifier are optional and may be absent."""

    def test_missing_base_top_qualifier_map_to_none(self) -> None:
        raw = [_raw_sigmet(base=None, top=None, qualifier=None)]

        result = SigmetMapper().map(raw, fir_id="EPWW")

        sigmet = result[0]
        assert sigmet.base is None
        assert sigmet.top is None
        assert sigmet.qualifier is None

    def test_absent_optional_keys_map_to_none(self) -> None:
        raw_item = _raw_sigmet()
        del raw_item["base"]
        del raw_item["top"]
        del raw_item["qualifier"]

        result = SigmetMapper().map([raw_item], fir_id="EPWW")

        sigmet = result[0]
        assert sigmet.base is None
        assert sigmet.top is None
        assert sigmet.qualifier is None

    def test_absent_coords_defaults_to_empty_list(self) -> None:
        raw_item = _raw_sigmet()
        del raw_item["coords"]

        result = SigmetMapper().map([raw_item], fir_id="EPWW")

        assert result[0].coordinates == []

    def test_absent_raw_sigmet_defaults_to_empty_string(self) -> None:
        raw_item = _raw_sigmet()
        del raw_item["rawSigmet"]

        result = SigmetMapper().map([raw_item], fir_id="EPWW")

        assert result[0].raw == ""


class TestDeterministicId:
    """ID generation when the API doesn't return a stable ID."""

    def test_id_is_used_when_present(self) -> None:
        raw = [_raw_sigmet(id="isigmet-123")]

        result = SigmetMapper().map(raw, fir_id="EPWW")

        assert result[0].id == "isigmet-123"

    def test_generated_id_is_deterministic_for_identical_input(self) -> None:
        raw = [_raw_sigmet()]

        first = SigmetMapper().map(raw, fir_id="EPWW")
        second = SigmetMapper().map(raw, fir_id="EPWW")

        assert first[0].id == second[0].id
        assert first[0].id != ""

    def test_generated_id_differs_for_different_sigmets(self) -> None:
        raw = [
            _raw_sigmet(hazard="TURB", rawSigmet="a"),
            _raw_sigmet(hazard="ICE", rawSigmet="b"),
        ]

        result = SigmetMapper().map(raw, fir_id="EPWW")

        assert result[0].id != result[1].id


class TestExtraFieldsPreserved:
    """Fields not part of the known schema are preserved in `extra`."""

    def test_unknown_fields_are_preserved(self) -> None:
        raw = [_raw_sigmet(seriesId="A", icaoId="EPWW", dir="NE", spd=25)]

        result = SigmetMapper().map(raw, fir_id="EPWW")

        assert result[0].extra == {
            "seriesId": "A",
            "icaoId": "EPWW",
            "dir": "NE",
            "spd": 25,
        }

    def test_no_unknown_fields_yields_empty_extra(self) -> None:
        raw = [_raw_sigmet()]

        result = SigmetMapper().map(raw, fir_id="EPWW")

        assert result[0].extra == {}
