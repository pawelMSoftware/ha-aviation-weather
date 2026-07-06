"""Tests for the Aviation Weather config flow."""

from __future__ import annotations

from unittest.mock import patch

import pytest
import voluptuous as vol
from homeassistant.config_entries import SOURCE_RECONFIGURE
from homeassistant.data_entry_flow import FlowResultType

from custom_components.aviation_weather.airports.models import Airport
from custom_components.aviation_weather.config_flow import CONF_ADD_FIR
from custom_components.aviation_weather.const import (
    CONF_AIRPORT,
    CONF_CONTINENT,
    CONF_COUNTRY,
    CONF_ENABLED_ENTITIES,
    CONF_ENTRY_TYPE,
    CONF_FIR,
    CONF_METAR_INTERVAL,
    CONF_SIGMET_INTERVAL,
    CONF_TAF_INTERVAL,
    DOMAIN,
    ENTRY_TYPE_AIRPORT,
    ENTRY_TYPE_FIR,
    METAR_INTERVAL_DEFAULT,
    SIGMET_INTERVAL_DEFAULT,
    TAF_INTERVAL_DEFAULT,
)
from custom_components.aviation_weather.enums import (
    AdditionalEntity,
    FirAdditionalEntity,
)

# Warsaw, Poland - used so the "nearest airport" suggestion is
# deterministic and falls within the EU continent / PL country.
WARSAW_LATITUDE = 52.2297
WARSAW_LONGITUDE = 21.0122


@pytest.fixture(autouse=True)
def _set_warsaw_location(hass):
    """Set hass's configured location to Warsaw for every test."""
    hass.config.latitude = WARSAW_LATITUDE
    hass.config.longitude = WARSAW_LONGITUDE


@pytest.fixture(autouse=True)
def _mock_setup_entry():
    """Prevent config entries created in tests from making real network
    calls. Without this, completing the flow triggers a real METAR/TAF
    fetch attempt against aviationweather.gov via async_setup_entry."""
    with patch(
        "custom_components.aviation_weather.async_setup_entry",
        return_value=True,
    ):
        yield


async def _skip_related_objects_if_present(hass, result: dict) -> dict:
    """If the flow stopped at the related_objects step (because the
    selected airport has a mapped FIR), skip it by submitting
    add_fir=False. Tests that want to exercise the related_objects step
    itself should not call this helper."""
    if (
        result.get("type") is FlowResultType.FORM
        and result.get("step_id") == "related_objects"
    ):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_ADD_FIR: False},
        )
    return result


class TestHappyPathFollowsNearestAirport:
    """Accepting every default should configure the nearest airport."""

    async def test_full_flow_with_defaults(self, hass) -> None:
        """Continent -> country -> airport, accepting suggested defaults."""

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

        # Continent step: accept the suggested default (EU, for Warsaw).
        continent_field = next(iter(result["data_schema"].schema))
        continent_default = continent_field.default()

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"continent": continent_default},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "country"

        country_field = next(iter(result["data_schema"].schema))
        country_default = country_field.default()

        assert country_default == "PL"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"country": country_default},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "airport"

        airport_field = next(iter(result["data_schema"].schema))
        airport_default = airport_field.default()

        assert airport_default == "EPWA"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"airport": airport_default},
        )

        result = await _skip_related_objects_if_present(hass, result)

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_COUNTRY] == "PL"
        assert result["data"][CONF_AIRPORT] == "EPWA"
        assert result["data"][CONF_ENTRY_TYPE] == ENTRY_TYPE_AIRPORT


class TestChangingCountryClearsAirportSuggestion:
    """Picking a non-default country should not keep the old airport default."""

    async def test_different_country_has_no_suggested_airport(self, hass) -> None:
        """Choosing a different country than the nearest one clears the
        suggested airport default."""

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
        )

        # Pick the same continent (EU) as the nearest airport's continent,
        # since "Germany" is also in Europe.
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"continent": "eu"},
        )

        assert result["step_id"] == "country"

        # Deliberately choose a country other than the suggested one (PL).
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"country": "DE"},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "airport"

        airport_field = next(iter(result["data_schema"].schema))
        airport_default = airport_field.default()

        # No airport should be pre-selected, since we diverged from the
        # nearest-airport suggestion at the country step.
        assert airport_default is None


class TestChangingContinentClearsCountrySuggestion:
    """Picking a non-default continent should not keep the old country default.

    Since the airport database currently covers Europe only, the only
    selectable continent is EU. This test verifies that submitting EU
    (which is also the default) still proceeds to the country step
    with the expected country suggestion.
    """

    async def test_selecting_eu_proceeds_to_country_step(self, hass) -> None:
        """Choosing EU (the only available continent) moves to the country
        step with the nearest-airport country pre-suggested."""

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
        )

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"continent": "eu"},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "country"


class TestDefaultConfigFallback:
    """Tests for default_config()'s fallback when nearest-airport lookup
    fails entirely (e.g. an empty registry, or any other lookup error)."""

    def test_falls_back_to_eu_with_no_country_or_airport(self, hass) -> None:
        from custom_components.aviation_weather.config_flow import default_config

        with patch(
            "custom_components.aviation_weather.config_flow.find_nearest_airport",
            side_effect=ValueError("no airports in registry"),
        ):
            defaults = default_config(hass)

        assert defaults == {
            CONF_CONTINENT: "EU",
            CONF_COUNTRY: "",
            CONF_AIRPORT: "",
        }

    def test_key_error_also_falls_back_to_eu(self, hass) -> None:
        from custom_components.aviation_weather.config_flow import default_config

        with patch(
            "custom_components.aviation_weather.config_flow.find_nearest_airport",
            side_effect=KeyError("PL"),
        ):
            defaults = default_config(hass)

        assert defaults[CONF_CONTINENT] == "EU"
        assert defaults[CONF_COUNTRY] == ""
        assert defaults[CONF_AIRPORT] == ""


class TestSelectingNonDefaultContinentClearsSuggestions:
    """When the airport database covers more than one continent, picking
    a continent other than the nearest-airport default must clear the
    suggested country/airport (they only make sense for the default
    continent's nearest airport).

    The real database currently covers only "EU"
    (ALLOWED_CONTINENTS = {"EU"} in scripts/generators/airport_filter.py),
    so this patches the resolver's registries with a second, fake
    continent/country/airport to exercise this otherwise-unreachable
    branch — this is forward-looking coverage for when multi-continent
    support lands, not a scenario possible with today's real data.
    """

    FAKE_AIRPORT = Airport(
        icao="ZZFAKE",
        country="ZZ",
        name="Fake Oceania Airport",
        latitude=-25.0,
        longitude=135.0,  # Central Australia - far from every real test location.
    )

    async def test_choosing_other_continent_clears_country_and_airport_defaults(
        self, hass
    ) -> None:
        from custom_components.aviation_weather.airports import resolver

        patched_continents = {**resolver.CONTINENTS, "ZZ": "OC"}
        patched_countries = {
            **resolver.COUNTRIES,
            "ZZ": {"ZZFAKE": self.FAKE_AIRPORT},
        }

        with (
            patch.object(resolver, "CONTINENTS", patched_continents),
            patch.object(resolver, "COUNTRIES", patched_countries),
        ):
            result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "user"},
            )

            continent_field = next(iter(result["data_schema"].schema))
            default_continent = continent_field.default()
            assert default_continent == "eu"

            # Deliberately pick the non-default continent.
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"],
                {"continent": "oc"},
            )

            assert result["type"] is FlowResultType.FORM
            assert result["step_id"] == "country"

            country_field = next(iter(result["data_schema"].schema))
            assert country_field.default() is None


class TestContinentSelectorTranslation:
    """Tests for the continent step using a translatable SelectSelector
    instead of vol.In() with hardcoded English labels."""

    async def test_continent_step_uses_select_selector(self, hass) -> None:
        """The continent step's schema uses SelectSelector."""
        from homeassistant.helpers import selector

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
        )

        assert result["step_id"] == "user"

        continent_validator = next(iter(result["data_schema"].schema.values()))
        assert isinstance(continent_validator, selector.SelectSelector)

    async def test_continent_selector_has_translation_key(self, hass) -> None:
        """The continent SelectSelector is configured with
        translation_key="continent", so labels resolve from this
        integration's translation files rather than a hardcoded
        English name."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
        )

        continent_validator = next(iter(result["data_schema"].schema.values()))

        assert continent_validator.config["translation_key"] == "continent"

    async def test_continent_selector_options_are_plain_codes(self, hass) -> None:
        """The selector's options are plain continent codes (e.g. "eu"),
        not pre-translated English names — translation happens on the
        frontend via translation_key."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
        )

        continent_validator = next(iter(result["data_schema"].schema.values()))
        options = continent_validator.config["options"]

        assert "eu" in options
        assert "Europe" not in options


class TestCountrySelectorSearchability:
    """Tests for the switch from vol.In() to the native CountrySelector."""

    async def test_country_step_uses_country_selector(self, hass) -> None:
        """The country step's schema uses CountrySelector, not vol.In."""
        from homeassistant.helpers import selector

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"continent": "eu"},
        )

        assert result["step_id"] == "country"

        country_validator = next(iter(result["data_schema"].schema.values()))
        assert isinstance(country_validator, selector.CountrySelector)

    async def test_country_selector_is_scoped_to_eu(self, hass) -> None:
        """CountrySelector's `countries` option only includes European
        countries — the database covers Europe only."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"continent": "eu"},
        )

        country_validator = next(iter(result["data_schema"].schema.values()))
        countries = country_validator.config["countries"]

        assert "PL" in countries  # Poland is in Europe
        assert "DE" in countries  # Germany is in Europe
        assert "BR" not in countries  # Brazil is not in Europe

    async def test_kosovo_is_not_selectable_via_country_selector(self, hass) -> None:
        """Kosovo (XK) has no ISO 3166-1 code, so it's excluded by
        CountrySelector's underlying country list. This is a known,
        accepted limitation: Kosovo's airports remain in the database
        but aren't reachable through this step.
        """
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"continent": "eu"},
        )

        country_validator = next(iter(result["data_schema"].schema.values()))

        with pytest.raises(vol.Invalid):
            country_validator("XK")

    async def test_user_in_kosovo_does_not_crash_the_continent_step(self, hass) -> None:
        """A user physically located in Kosovo gets a valid continent
        suggestion and form, even though their nearest airport's country
        (XK) can't be offered as a default on the next step."""
        hass.config.latitude = 42.6629  # Pristina, Kosovo
        hass.config.longitude = 21.1655

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "user"

        # Should not raise; the suggested continent is still EU.
        continent_field = next(iter(result["data_schema"].schema))
        assert continent_field.default() == "eu"

    async def test_user_in_kosovo_gets_no_suggested_country_default(self, hass) -> None:
        """When the nearest airport's country (XK) isn't supported by
        CountrySelector, no default is set (instead of crashing trying
        to default to an invalid option)."""
        hass.config.latitude = 42.6629  # Pristina, Kosovo
        hass.config.longitude = 21.1655

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"continent": "eu"},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "country"

        country_field = next(iter(result["data_schema"].schema))
        assert country_field.default() is None


class TestDuplicateAirportRejected:
    """Adding the same airport twice should show an error, not a duplicate entry."""

    async def test_duplicate_airport_shows_error(self, hass) -> None:
        """Configuring the same airport a second time shows an error."""

        # First entry: configure EPWA successfully.
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"continent": "eu"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"country": "PL"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"airport": "EPWA"},
        )
        result = await _skip_related_objects_if_present(hass, result)
        assert result["type"] is FlowResultType.CREATE_ENTRY

        # Second attempt: try to configure EPWA again.
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"continent": "eu"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"country": "PL"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"airport": "EPWA"},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "airport"
        assert result["errors"] == {"base": "airport_exists"}

    async def test_duplicate_check_iterates_past_non_matching_entries(
        self, hass
    ) -> None:
        """With multiple airports already configured, the duplicate
        check must keep scanning past entries that don't match before
        finding the one that does — a single-entry test can't exercise
        that loop continuation."""

        async def _configure_airport(continent: str, country: str, airport: str):
            flow_result = await hass.config_entries.flow.async_init(
                DOMAIN,
                context={"source": "user"},
            )
            flow_result = await hass.config_entries.flow.async_configure(
                flow_result["flow_id"],
                {"continent": continent},
            )
            flow_result = await hass.config_entries.flow.async_configure(
                flow_result["flow_id"],
                {"country": country},
            )
            flow_result = await hass.config_entries.flow.async_configure(
                flow_result["flow_id"],
                {"airport": airport},
            )
            return await _skip_related_objects_if_present(hass, flow_result)

        # First entry: EPWA (Poland). This one will NOT match the
        # duplicate check below, forcing the loop past it.
        first = await _configure_airport("eu", "PL", "EPWA")
        assert first["type"] is FlowResultType.CREATE_ENTRY

        # Second entry: EPGD (also Poland, different airport).
        second = await _configure_airport("eu", "PL", "EPGD")
        assert second["type"] is FlowResultType.CREATE_ENTRY

        # Attempt to add EPGD again: the duplicate check must scan past
        # the EPWA entry (no match) before reaching the EPGD entry
        # (match) and rejecting it.
        duplicate = await _configure_airport("eu", "PL", "EPGD")

        assert duplicate["type"] is FlowResultType.FORM
        assert duplicate["step_id"] == "airport"
        assert duplicate["errors"] == {"base": "airport_exists"}


async def _configure_airport_flow(hass, *, continent: str, country: str, airport: str):
    """Drive the flow up to (and including) the airport step, returning
    the result without touching the related_objects step."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"continent": continent},
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"country": country},
    )
    return await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"airport": airport},
    )


class TestRelatedObjectsStep:
    """Tests for async_step_related_objects — accepting the default FIR
    suggestion, and skipping the step entirely when the FIR is already
    configured."""

    async def test_accepting_default_creates_a_fir_entry_too(self, hass) -> None:
        """Accepting the default (add_fir=True) for an airport whose FIR
        isn't configured yet creates a second, FIR config entry."""
        result = await _configure_airport_flow(
            hass, continent="eu", country="PL", airport="EPWA"
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "related_objects"

        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_ADD_FIR: True},
        )
        await hass.async_block_till_done()

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_AIRPORT] == "EPWA"

        fir_entries = [
            entry
            for entry in hass.config_entries.async_entries(DOMAIN)
            if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_FIR
        ]
        assert len(fir_entries) == 1
        assert fir_entries[0].data[CONF_FIR] == "EPWW"

    async def test_step_is_skipped_when_fir_already_configured(self, hass) -> None:
        """No related_objects form is shown when a FIR entry for the
        selected airport's FIR already exists — the flow goes straight
        to creating the airport entry."""
        from pytest_homeassistant_custom_component.common import MockConfigEntry

        fir_entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_ENTRY_TYPE: ENTRY_TYPE_FIR, CONF_FIR: "EPWW"},
        )
        fir_entry.add_to_hass(hass)

        result = await _configure_airport_flow(
            hass, continent="eu", country="PL", airport="EPWA"
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_AIRPORT] == "EPWA"


class TestFirStepDirectInvocation:
    """Tests for async_step_fir invoked directly with context
    source="fir" (as async_step_related_objects and the airport options
    flow both do internally), rather than through the normal user flow."""

    async def test_missing_data_aborts(self, hass) -> None:
        """If the "fir" source flow is ever started without data, it
        aborts instead of crashing on a None user_input."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "fir"},
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"

    async def test_already_configured_fir_aborts(self, hass) -> None:
        """Starting the "fir" source flow for a FIR that's already
        configured aborts rather than creating a duplicate entry."""
        from pytest_homeassistant_custom_component.common import MockConfigEntry

        fir_entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_ENTRY_TYPE: ENTRY_TYPE_FIR, CONF_FIR: "EPWW"},
        )
        fir_entry.add_to_hass(hass)

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "fir"},
            data={CONF_ENTRY_TYPE: ENTRY_TYPE_FIR, CONF_FIR: "EPWW"},
        )

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "already_configured"


class TestReconfigureFlow:
    """Tests for async_step_reconfigure — changing an existing airport
    entry's country/airport without deleting and re-adding it."""

    async def _set_up_airport_entry(self, hass, *, country: str, airport: str):
        from pytest_homeassistant_custom_component.common import MockConfigEntry

        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                CONF_ENTRY_TYPE: ENTRY_TYPE_AIRPORT,
                CONF_COUNTRY: country,
                CONF_AIRPORT: airport,
            },
        )
        entry.add_to_hass(hass)
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        return entry

    async def test_reconfigure_skips_continent_and_prefills_country(self, hass) -> None:
        """Reconfigure jumps straight to the country step (the
        continent is already implied by the entry's stored country),
        pre-filled with that country."""
        entry = await self._set_up_airport_entry(hass, country="PL", airport="EPWA")

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "country"

        country_field = next(iter(result["data_schema"].schema))
        assert country_field.default() == "PL"

    async def test_reconfigure_prefills_current_airport(self, hass) -> None:
        entry = await self._set_up_airport_entry(hass, country="PL", airport="EPWA")

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"country": "PL"},
        )

        assert result["step_id"] == "airport"

        airport_field = next(iter(result["data_schema"].schema))
        assert airport_field.default() == "EPWA"

    async def test_reconfigure_updates_existing_entry_in_place(self, hass) -> None:
        """Changing the airport updates the same entry (same entry_id,
        same total entry count) rather than creating a new one."""
        entry = await self._set_up_airport_entry(hass, country="PL", airport="EPWA")

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"country": "PL"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"airport": "EPGD"},
        )
        result = await _skip_related_objects_if_present(hass, result)
        await hass.async_block_till_done()

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "reconfigure_successful"

        airport_entries = [
            e
            for e in hass.config_entries.async_entries(DOMAIN)
            if e.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_AIRPORT
        ]
        assert len(airport_entries) == 1
        assert airport_entries[0].entry_id == entry.entry_id
        assert airport_entries[0].data[CONF_AIRPORT] == "EPGD"

    async def test_resubmitting_the_same_airport_is_not_a_duplicate(self, hass) -> None:
        """Reconfiguring without actually changing the airport must not
        be rejected as a duplicate of itself."""
        entry = await self._set_up_airport_entry(hass, country="PL", airport="EPWA")

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"country": "PL"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"airport": "EPWA"},
        )
        result = await _skip_related_objects_if_present(hass, result)

        assert result["type"] is FlowResultType.ABORT
        assert result["reason"] == "reconfigure_successful"

    async def test_reconfiguring_to_an_airport_used_by_another_entry_is_rejected(
        self, hass
    ) -> None:
        await self._set_up_airport_entry(hass, country="PL", airport="EPGD")
        entry = await self._set_up_airport_entry(hass, country="PL", airport="EPWA")

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_RECONFIGURE, "entry_id": entry.entry_id},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"country": "PL"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"airport": "EPGD"},
        )

        assert result["type"] is FlowResultType.FORM
        assert result["step_id"] == "airport"
        assert result["errors"] == {"base": "airport_exists"}


class TestOptionsFlow:
    """Tests for the options flow (additional entities)."""

    async def test_options_flow_defaults(self, hass) -> None:
        """The options flow shows the default (empty) set of additional entities."""

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"continent": "eu"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"country": "PL"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"airport": "EPWA"},
        )
        result = await _skip_related_objects_if_present(hass, result)

        entry = result["result"]

        options_result = await hass.config_entries.options.async_init(
            entry.entry_id,
        )

        assert options_result["type"] is FlowResultType.FORM
        assert options_result["step_id"] == "init"

        result = await hass.config_entries.options.async_configure(
            options_result["flow_id"],
            {CONF_ENABLED_ENTITIES: [AdditionalEntity.TAF.value]},
        )

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_ENABLED_ENTITIES] == [AdditionalEntity.TAF.value]

    async def test_options_flow_shows_interval_sliders_with_defaults(
        self, hass, enable_custom_integrations
    ) -> None:
        """The options form includes METAR and TAF interval sliders,
        pre-filled with the default values when the user hasn't set
        them yet."""
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"continent": "eu"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"country": "PL"}
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {"airport": "EPWA"}
        )
        result = await _skip_related_objects_if_present(hass, result)

        entry = result["result"]
        options_result = await hass.config_entries.options.async_init(
            entry.entry_id,
        )

        schema = options_result["data_schema"].schema
        schema_keys = {str(k): k for k in schema if hasattr(k, "default")}

        assert CONF_METAR_INTERVAL in schema_keys
        assert CONF_TAF_INTERVAL in schema_keys
        assert schema_keys[CONF_METAR_INTERVAL].default() == METAR_INTERVAL_DEFAULT
        assert schema_keys[CONF_TAF_INTERVAL].default() == TAF_INTERVAL_DEFAULT

    async def test_custom_intervals_are_saved_and_reloaded(
        self, hass, enable_custom_integrations
    ) -> None:
        """Custom interval values entered by the user are saved to
        entry.options and shown as the default next time the form opens."""
        from unittest.mock import AsyncMock, MagicMock, patch

        def _make_session():
            metar_response = MagicMock()
            metar_response.status = 200
            metar_response.raise_for_status = MagicMock()
            metar_response.json = AsyncMock(
                return_value=[{"icaoId": "EPWA", "temp": 18.0}]
            )
            taf_response = MagicMock()
            taf_response.status = 200
            taf_response.raise_for_status = MagicMock()
            taf_response.json = AsyncMock(
                return_value=[{"icaoId": "EPWA", "rawTAF": "TAF EPWA ..."}]
            )

            def get(url, params=None, **kwargs):
                cm = MagicMock()
                if "taf" in url:
                    cm.__aenter__ = AsyncMock(return_value=taf_response)
                else:
                    cm.__aenter__ = AsyncMock(return_value=metar_response)
                cm.__aexit__ = AsyncMock(return_value=False)
                return cm

            session = MagicMock()
            session.get = MagicMock(side_effect=get)
            return session

        from pytest_homeassistant_custom_component.common import MockConfigEntry

        from custom_components.aviation_weather.const import CONF_COUNTRY

        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_COUNTRY: "PL", CONF_AIRPORT: "EPWA"},
        )
        entry.add_to_hass(hass)

        with patch(
            "custom_components.aviation_weather.async_get_clientsession",
            return_value=_make_session(),
        ):
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

        options_result = await hass.config_entries.options.async_init(
            entry.entry_id,
        )
        with patch(
            "custom_components.aviation_weather.async_get_clientsession",
            return_value=_make_session(),
        ):
            saved = await hass.config_entries.options.async_configure(
                options_result["flow_id"],
                {
                    CONF_ENABLED_ENTITIES: [],
                    CONF_METAR_INTERVAL: 5,
                    CONF_TAF_INTERVAL: 60,
                },
            )
            await hass.async_block_till_done()

        assert saved["type"] is FlowResultType.CREATE_ENTRY
        assert saved["data"][CONF_METAR_INTERVAL] == 5
        assert saved["data"][CONF_TAF_INTERVAL] == 60

        # Open the form again — saved values should be pre-filled.
        options_result2 = await hass.config_entries.options.async_init(
            entry.entry_id,
        )
        schema2_keys = {
            str(k): k
            for k in options_result2["data_schema"].schema
            if hasattr(k, "default")
        }
        assert schema2_keys[CONF_METAR_INTERVAL].default() == 5
        assert schema2_keys[CONF_TAF_INTERVAL].default() == 60

    async def test_enabled_entities_selector_uses_translation_key(self, hass) -> None:
        """The enabled_entities SelectSelector is configured with
        translation_key="enabled_entities", so option labels (e.g.
        "METAR details" / "Szczegóły METAR") resolve from this
        integration's translation files rather than a hardcoded
        English string baked into the enum.
        """
        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"continent": "eu"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"country": "PL"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"airport": "EPWA"},
        )
        result = await _skip_related_objects_if_present(hass, result)

        entry = result["result"]

        options_result = await hass.config_entries.options.async_init(
            entry.entry_id,
        )

        selector_validator = options_result["data_schema"].schema[CONF_ENABLED_ENTITIES]

        assert selector_validator.config["translation_key"] == "enabled_entities"

        # Options are plain string values, not pre-translated labels —
        # translation happens on the frontend via translation_key.
        assert selector_validator.config["options"] == [
            AdditionalEntity.METAR_SENSORS.value,
            AdditionalEntity.TAF.value,
        ]

    async def test_taf_option_offered_for_airport_with_taf(self, hass) -> None:
        """TAF forecast is offered as an option for an airport that has TAF
        data (EPWA - Warsaw Chopin)."""

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"continent": "eu"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"country": "PL"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"airport": "EPWA"},
        )
        result = await _skip_related_objects_if_present(hass, result)

        entry = result["result"]

        options_result = await hass.config_entries.options.async_init(
            entry.entry_id,
        )

        offered_values = set(
            options_result["data_schema"]
            .schema[CONF_ENABLED_ENTITIES]
            .config["options"],
        )

        assert AdditionalEntity.TAF.value in offered_values
        assert AdditionalEntity.METAR_SENSORS.value in offered_values

    async def test_taf_option_not_offered_for_airport_without_taf(self, hass) -> None:
        """TAF forecast is NOT offered as an option for an airport that has
        no TAF data (EDFE - Frankfurt-Egelsbach, METAR-only)."""

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"continent": "eu"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"country": "DE"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"airport": "EDFE"},
        )
        result = await _skip_related_objects_if_present(hass, result)

        entry = result["result"]

        options_result = await hass.config_entries.options.async_init(
            entry.entry_id,
        )

        offered_values = set(
            options_result["data_schema"]
            .schema[CONF_ENABLED_ENTITIES]
            .config["options"],
        )

        assert AdditionalEntity.TAF.value not in offered_values
        # METAR details should still be offered - only TAF is unavailable.
        assert AdditionalEntity.METAR_SENSORS.value in offered_values

    async def test_selecting_taf_rejected_for_airport_without_taf(self, hass) -> None:
        """Even if somehow submitted, TAF cannot be selected for an airport
        without TAF data, since vol.In() only accepts offered options."""

        result = await hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": "user"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"continent": "eu"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"country": "DE"},
        )
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {"airport": "EDFE"},
        )
        result = await _skip_related_objects_if_present(hass, result)

        entry = result["result"]

        options_result = await hass.config_entries.options.async_init(
            entry.entry_id,
        )

        with pytest.raises(vol.Invalid):
            options_result["data_schema"](
                {CONF_ENABLED_ENTITIES: [AdditionalEntity.TAF.value]},
            )


class TestAirportOptionsFlowFirCheckbox:
    """Tests for the "add FIR device" checkbox shown at the top of an
    airport's own options form."""

    async def test_checkbox_offered_and_checking_it_creates_a_fir_entry(
        self, hass
    ) -> None:
        """When the airport's FIR isn't configured yet, the options form
        offers the add_fir checkbox; checking it creates a FIR entry,
        same as accepting the default at the related_objects step."""
        result = await _configure_airport_flow(
            hass, continent="eu", country="PL", airport="EPWA"
        )
        assert result["step_id"] == "related_objects"

        # Decline at setup time, so the FIR stays unconfigured.
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_ADD_FIR: False},
        )
        assert result["type"] is FlowResultType.CREATE_ENTRY

        entry = result["result"]

        options_result = await hass.config_entries.options.async_init(
            entry.entry_id,
        )

        assert CONF_ADD_FIR in options_result["data_schema"].schema

        result = await hass.config_entries.options.async_configure(
            options_result["flow_id"],
            {
                CONF_ADD_FIR: True,
                CONF_ENABLED_ENTITIES: [],
                CONF_METAR_INTERVAL: METAR_INTERVAL_DEFAULT,
                CONF_TAF_INTERVAL: TAF_INTERVAL_DEFAULT,
            },
        )
        await hass.async_block_till_done()

        assert result["type"] is FlowResultType.CREATE_ENTRY

        fir_entries = [
            e
            for e in hass.config_entries.async_entries(DOMAIN)
            if e.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_FIR
        ]
        assert len(fir_entries) == 1
        assert fir_entries[0].data[CONF_FIR] == "EPWW"

    async def test_no_checkbox_when_fir_already_configured(self, hass) -> None:
        """Once the FIR is configured, the options form no longer offers
        the checkbox, and no fir_label placeholder is set."""
        result = await _configure_airport_flow(
            hass, continent="eu", country="PL", airport="EPWA"
        )
        assert result["step_id"] == "related_objects"

        # Accept at setup time, so the FIR is already configured.
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"],
            {CONF_ADD_FIR: True},
        )
        await hass.async_block_till_done()
        assert result["type"] is FlowResultType.CREATE_ENTRY

        entry = result["result"]

        options_result = await hass.config_entries.options.async_init(
            entry.entry_id,
        )

        assert CONF_ADD_FIR not in options_result["data_schema"].schema
        assert options_result["description_placeholders"] == {}


def _make_isigmet_session():
    """Build a mock aiohttp session returning an empty isigmet response."""
    from unittest.mock import AsyncMock, MagicMock

    response = MagicMock()
    response.status = 200
    response.raise_for_status = MagicMock()
    response.json = AsyncMock(return_value=[])

    context_manager = MagicMock()
    context_manager.__aenter__ = AsyncMock(return_value=response)
    context_manager.__aexit__ = AsyncMock(return_value=False)

    session = MagicMock()
    session.get = MagicMock(return_value=context_manager)
    return session


class TestFirOptionsFlow:
    """Tests for the FIR entry options flow (SIGMET settings)."""

    async def _set_up_fir_entry(self, hass):
        from pytest_homeassistant_custom_component.common import MockConfigEntry

        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_ENTRY_TYPE: ENTRY_TYPE_FIR, CONF_FIR: "EPWW"},
        )
        entry.add_to_hass(hass)

        with patch(
            "custom_components.aviation_weather.async_get_clientsession",
            return_value=_make_isigmet_session(),
        ):
            await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()

        return entry

    async def test_fir_options_flow_shows_fir_init_step(
        self, hass, enable_custom_integrations
    ) -> None:
        entry = await self._set_up_fir_entry(hass)

        options_result = await hass.config_entries.options.async_init(
            entry.entry_id,
        )

        assert options_result["type"] is FlowResultType.FORM
        assert options_result["step_id"] == "fir_init"

    async def test_fir_options_flow_defaults(
        self, hass, enable_custom_integrations
    ) -> None:
        entry = await self._set_up_fir_entry(hass)

        options_result = await hass.config_entries.options.async_init(
            entry.entry_id,
        )

        schema_keys = {
            str(k): k
            for k in options_result["data_schema"].schema
            if hasattr(k, "default")
        }

        assert schema_keys[CONF_ENABLED_ENTITIES].default() == []
        assert schema_keys[CONF_SIGMET_INTERVAL].default() == SIGMET_INTERVAL_DEFAULT

    async def test_fir_enabled_entities_selector_offers_sigmet_sensors(
        self, hass, enable_custom_integrations
    ) -> None:
        entry = await self._set_up_fir_entry(hass)

        options_result = await hass.config_entries.options.async_init(
            entry.entry_id,
        )

        selector_validator = options_result["data_schema"].schema[CONF_ENABLED_ENTITIES]

        assert selector_validator.config["translation_key"] == "fir_enabled_entities"
        assert selector_validator.config["options"] == [
            FirAdditionalEntity.SIGMET_SENSORS.value,
        ]

    async def test_enabling_sigmet_sensors_is_saved(
        self, hass, enable_custom_integrations
    ) -> None:
        entry = await self._set_up_fir_entry(hass)

        options_result = await hass.config_entries.options.async_init(
            entry.entry_id,
        )

        with patch(
            "custom_components.aviation_weather.async_get_clientsession",
            return_value=_make_isigmet_session(),
        ):
            result = await hass.config_entries.options.async_configure(
                options_result["flow_id"],
                {
                    CONF_ENABLED_ENTITIES: [FirAdditionalEntity.SIGMET_SENSORS.value],
                    CONF_SIGMET_INTERVAL: 10,
                },
            )
            await hass.async_block_till_done()

        assert result["type"] is FlowResultType.CREATE_ENTRY
        assert result["data"][CONF_ENABLED_ENTITIES] == [
            FirAdditionalEntity.SIGMET_SENSORS.value,
        ]
        assert result["data"][CONF_SIGMET_INTERVAL] == 10
