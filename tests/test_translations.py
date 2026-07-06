"""Tests for the translation files (strings.json + translations/*.json).

These guard against the translation files drifting out of sync with the
actual data — e.g. a new continent being added to the airport database
without a corresponding translated label, which would surface as a raw
continent code ("EU") in the UI instead of a translated name.

strings.json is the source of truth for English strings (the modern HA
convention); translations/*.json holds every other language. Both are
checked here since both are shown directly to users.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from custom_components.aviation_weather.airports import continent_options
from custom_components.aviation_weather.enums import (
    AdditionalEntity,
    FirAdditionalEntity,
)

INTEGRATION_DIR = (
    Path(__file__).parent.parent / "custom_components" / "aviation_weather"
)
TRANSLATIONS_DIR = INTEGRATION_DIR / "translations"
STRINGS_FILE = INTEGRATION_DIR / "strings.json"

TRANSLATION_FILES = sorted(
    [STRINGS_FILE, *TRANSLATIONS_DIR.glob("*.json")],
)


@pytest.fixture(params=TRANSLATION_FILES, ids=lambda path: path.stem)
def translation_file(request) -> dict:
    """Load and parse each translation file in turn."""
    with request.param.open(
        encoding="utf-8",
    ) as file:
        return json.load(file)


class TestTranslationFilesAreValid:
    """Basic sanity checks that apply to every translation file."""

    def test_at_least_one_translation_file_exists(self) -> None:
        """Sanity check that the glob pattern actually found files."""
        assert len(TRANSLATION_FILES) > 0

    def test_is_valid_json(self, translation_file: dict) -> None:
        """Each translation file parses as valid JSON (enforced by the
        `translation_file` fixture itself; this test exists so a parse
        failure is reported per-file instead of erroring at collection
        time for all of them)."""
        assert isinstance(translation_file, dict)


class TestContinentTranslations:
    """Every continent the airport database uses must have a translated
    label in every translation file, or the frontend will fall back to
    showing the raw, untranslated continent code.

    The frontend looks up a SelectSelector's translated label by the
    exact, case-sensitive option value (no lowercasing on either side),
    so the JSON keys here must match continent_options() exactly (e.g.
    "EU", not "eu") — a case mismatch is exactly what caused the
    continent step to show a raw code instead of a translated name.
    """

    def test_every_continent_code_has_a_translated_label(
        self, translation_file: dict
    ) -> None:
        """Every code from continent_options() has an entry under
        selector.continent.options in this translation file."""
        labels = translation_file["selector"]["continent"]["options"]

        for code in continent_options():
            assert code in labels, (
                f"Continent code {code!r} is missing a translated label"
            )

    def test_no_translated_label_is_empty(self, translation_file: dict) -> None:
        """No continent label is an empty string (which would render as
        a blank option in the dropdown)."""
        labels = translation_file["selector"]["continent"]["options"]

        for code, label in labels.items():
            assert label.strip(), f"Continent {code!r} has an empty label"


class TestSystemHealthTranslations:
    """Every key returned by system_health_info() must have a
    translated label in every translation file, or the System
    Information panel falls back to showing the raw dict key (e.g.
    "configured_airports") instead of a readable label.

    The expected keys are hardcoded here rather than introspected from
    system_health_info() itself, since that function's return keys are
    a fixed, deliberately small set defined directly in its source —
    same tradeoff as a sensor's hardcoded attribute keys.
    """

    EXPECTED_KEYS = frozenset(
        {
            "configured_airports",
            "metar_coordinators",
            "taf_coordinators",
            "configured_firs",
            "sigmet_coordinators",
        },
    )

    def test_every_system_health_key_has_a_translated_label(
        self, translation_file: dict
    ) -> None:
        labels = translation_file["system_health"]["info"]

        for key in self.EXPECTED_KEYS:
            assert key in labels, (
                f"system_health key {key!r} is missing a translated label"
            )

    def test_no_translated_label_is_empty(self, translation_file: dict) -> None:
        labels = translation_file["system_health"]["info"]

        for key, label in labels.items():
            assert label.strip(), f"system_health key {key!r} has an empty label"


class TestEnabledEntitiesTranslations:
    """Every AdditionalEntity value must have a translated label in
    every translation file, or the options flow's "Additional
    entities" selector falls back to showing the raw enum value (e.g.
    "metar_sensors") instead of a readable label like "METAR
    details"."""

    def test_every_entity_value_has_a_translated_label(
        self, translation_file: dict
    ) -> None:
        labels = translation_file["selector"]["enabled_entities"]["options"]

        for entity in AdditionalEntity:
            assert entity.value in labels, (
                f"AdditionalEntity {entity.value!r} is missing a translated label"
            )

    def test_no_translated_label_is_empty(self, translation_file: dict) -> None:
        labels = translation_file["selector"]["enabled_entities"]["options"]

        for value, label in labels.items():
            assert label.strip(), f"enabled_entities value {value!r} has an empty label"


class TestFirEnabledEntitiesTranslations:
    """Every FirAdditionalEntity value must have a translated label, or
    the FIR options flow's "Additional entities" selector falls back to
    showing the raw enum value (e.g. "sigmet_sensors") instead of a
    readable label like "SIGMET details"."""

    def test_every_entity_value_has_a_translated_label(
        self, translation_file: dict
    ) -> None:
        labels = translation_file["selector"]["fir_enabled_entities"]["options"]

        for entity in FirAdditionalEntity:
            assert entity.value in labels, (
                f"FirAdditionalEntity {entity.value!r} is missing a translated label"
            )

    def test_no_translated_label_is_empty(self, translation_file: dict) -> None:
        labels = translation_file["selector"]["fir_enabled_entities"]["options"]

        for value, label in labels.items():
            assert label.strip(), (
                f"fir_enabled_entities value {value!r} has an empty label"
            )
