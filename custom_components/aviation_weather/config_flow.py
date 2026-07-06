from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import SOURCE_RECONFIGURE, ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers import selector

from .airports import (
    AIRPORTS,
    CONTINENTS,
    airport_options,
    continent_options,
    countries_for_continent,
    find_nearest_airport,
)
from .airports.models import Airport
from .const import (
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
    METAR_INTERVAL_MAX,
    METAR_INTERVAL_MIN,
    SIGMET_INTERVAL_DEFAULT,
    SIGMET_INTERVAL_MAX,
    SIGMET_INTERVAL_MIN,
    TAF_INTERVAL_DEFAULT,
    TAF_INTERVAL_MAX,
    TAF_INTERVAL_MIN,
)
from .enums import AdditionalEntity, FirAdditionalEntity
from .firs import get_fir
from .helpers import get_entry_value

CONF_ADD_FIR = "add_fir"


def default_config(
    hass: HomeAssistant,
) -> dict[str, object]:
    """Return default configuration based on the nearest airport.

    Since the airport database currently covers Europe only, the
    continent default is always "EU". If the nearest-airport lookup
    finds nothing (e.g. the HA instance is located outside Europe),
    the defaults fall back to a central-European reference point so
    the form still opens without crashing.
    """
    try:
        nearest_airport = find_nearest_airport(
            hass.config.latitude,
            hass.config.longitude,
        )
        continent = CONTINENTS.get(nearest_airport.country, "EU")
        country = nearest_airport.country
        airport = nearest_airport.icao
    except (ValueError, KeyError):
        # No airports in the database match — use safe EU defaults.
        continent = "EU"
        country = ""
        airport = ""

    return {
        CONF_CONTINENT: continent,
        CONF_COUNTRY: country,
        CONF_AIRPORT: airport,
    }


def default_options() -> dict[str, object]:
    """Return default options."""

    return {
        CONF_ENABLED_ENTITIES: AdditionalEntity.default_values(),
        CONF_METAR_INTERVAL: METAR_INTERVAL_DEFAULT,
        CONF_TAF_INTERVAL: TAF_INTERVAL_DEFAULT,
    }


def default_fir_options() -> dict[str, object]:
    """Return default options for a FIR entry."""

    return {
        CONF_ENABLED_ENTITIES: FirAdditionalEntity.default_values(),
        CONF_SIGMET_INTERVAL: SIGMET_INTERVAL_DEFAULT,
    }


def build_fir_options_schema(
    defaults: dict[str, object],
) -> vol.Schema:
    """Build the options schema for a FIR entry."""

    return vol.Schema(
        {
            vol.Required(
                CONF_ENABLED_ENTITIES,
                default=defaults[CONF_ENABLED_ENTITIES],
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                    translation_key="fir_enabled_entities",
                    options=[entity.value for entity in FirAdditionalEntity.options()],
                ),
            ),
            vol.Required(
                CONF_SIGMET_INTERVAL,
                default=defaults[CONF_SIGMET_INTERVAL],
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=SIGMET_INTERVAL_MIN,
                    max=SIGMET_INTERVAL_MAX,
                    step=5,
                    unit_of_measurement="min",
                    mode=selector.NumberSelectorMode.SLIDER,
                ),
            ),
        },
    )


def build_continent_schema(
    defaults: dict[str, object],
) -> vol.Schema:
    """Build continent selection schema.

    Uses SelectSelector with translation_key="continent" so the option
    labels (e.g. "Europe" / "Europa") are resolved from this
    integration's translation files, in the user's configured language,
    instead of a hardcoded English name.

    continent_options()/CONTINENTS use uppercase codes (e.g. "EU",
    matching pycountry_convert's convention used throughout the airport
    generator pipeline), but hassfest requires translation keys to be
    lowercase — and the frontend's translation_key lookup is an exact,
    case-sensitive match against the option value. So the options and
    default passed to the selector are lowercased here; async_step_user
    uppercases the submitted value back before storing it, keeping
    "EU" as the one canonical form everywhere else in the flow.
    """

    return vol.Schema(
        {
            vol.Required(
                CONF_CONTINENT,
                default=defaults[CONF_CONTINENT].lower(),
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=[code.lower() for code in continent_options()],
                    translation_key="continent",
                    sort=True,
                ),
            ),
        },
    )


def _is_supported_by_country_selector(
    country_code: str,
    available_codes: list[str],
) -> bool:
    """Return whether CountrySelector recognizes this ISO country code.

    A handful of codes used by the airport database (e.g. "XK" for
    Kosovo, which has no ISO 3166-1 code) are not recognized by
    CountrySelector, since it follows the same ISO 3166-1 list as the
    rest of Home Assistant. Those countries simply won't appear as
    selectable options in this step — a known, accepted limitation
    rather than a bug.

    Must be checked against a CountrySelector configured with the same
    `countries` list used for the actual form: an unconfigured
    CountrySelector() performs no validation at all and would accept
    any string, masking unsupported codes like "XK".
    """

    try:
        selector.CountrySelector(
            selector.CountrySelectorConfig(
                countries=available_codes,
            ),
        )(
            country_code,
        )
    except vol.Invalid:
        return False

    return True


def build_country_schema(
    continent: str,
    suggested_country: str | None,
) -> vol.Schema:
    """Build country selection schema.

    Uses the native CountrySelector for a searchable dropdown with
    automatic country-name translation, scoped to the countries in the
    given continent.
    """

    codes = sorted(
        countries_for_continent(
            continent,
        ),
    )

    default = (
        suggested_country
        if suggested_country is not None
        and _is_supported_by_country_selector(
            suggested_country,
            codes,
        )
        else None
    )

    return vol.Schema(
        {
            vol.Required(
                CONF_COUNTRY,
                default=default,
            ): selector.CountrySelector(
                selector.CountrySelectorConfig(
                    countries=codes,
                ),
            ),
        },
    )


def build_airport_schema(
    country: str,
    suggested_airport: str | None,
) -> vol.Schema:
    """Build airport selection schema.

    Uses SelectSelector in DROPDOWN mode so the frontend renders a
    searchable dropdown — the same look-and-feel as the country step.
    The nearest airport is set as the default value; SelectSelector
    highlights it automatically without any label prefix.
    """
    options = [
        selector.SelectOptionDict(value=icao, label=label)
        for icao, label in airport_options(country).items()
    ]

    return vol.Schema(
        {
            vol.Required(
                CONF_AIRPORT,
                default=suggested_airport,
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    options=options,
                    mode=selector.SelectSelectorMode.DROPDOWN,
                ),
            ),
        },
    )


def build_options_schema(
    defaults: dict[str, object],
    airport: Airport,
) -> vol.Schema:
    """Build options schema.

    Only additional entities that make sense for the configured airport
    are offered (e.g. TAF forecast is omitted for airports that don't
    publish TAF data).
    """

    return vol.Schema(
        {
            vol.Required(
                CONF_ENABLED_ENTITIES,
                default=defaults[CONF_ENABLED_ENTITIES],
            ): selector.SelectSelector(
                selector.SelectSelectorConfig(
                    multiple=True,
                    mode=selector.SelectSelectorMode.LIST,
                    translation_key="enabled_entities",
                    options=[
                        entity.value
                        for entity in AdditionalEntity.options(
                            airport,
                        )
                    ],
                ),
            ),
            vol.Required(
                CONF_METAR_INTERVAL,
                default=defaults[CONF_METAR_INTERVAL],
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=METAR_INTERVAL_MIN,
                    max=METAR_INTERVAL_MAX,
                    step=1,
                    unit_of_measurement="min",
                    mode=selector.NumberSelectorMode.SLIDER,
                ),
            ),
            vol.Required(
                CONF_TAF_INTERVAL,
                default=defaults[CONF_TAF_INTERVAL],
            ): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=TAF_INTERVAL_MIN,
                    max=TAF_INTERVAL_MAX,
                    step=5,
                    unit_of_measurement="min",
                    mode=selector.NumberSelectorMode.SLIDER,
                ),
            ),
        },
    )


class AviationWeatherConfigFlow(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Handle Aviation Weather config flow."""

    VERSION = 1
    MINOR_VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._continent: str | None = None
        self._country: str | None = None
        self._suggested_country: str | None = None
        self._suggested_airport: str | None = None
        self._selected_airport: str | None = None

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> AviationWeatherOptionsFlow:
        """Return options flow."""
        return AviationWeatherOptionsFlow(
            config_entry,
        )

    def _airport_already_configured(
        self,
        airport: str,
    ) -> bool:
        """Check if airport already exists.

        During reconfigure, the entry being reconfigured is excluded —
        otherwise resubmitting the same airport it already holds would
        be rejected as a duplicate of itself.
        """
        exclude_entry_id = (
            self._reconfigure_entry_id if self.source == SOURCE_RECONFIGURE else None
        )

        for entry in self._async_current_entries():
            if entry.entry_id == exclude_entry_id:
                continue

            if (
                entry.data.get(
                    CONF_AIRPORT,
                )
                == airport
            ):
                return True

        return False

    async def async_step_reconfigure(
        self,
        user_input: dict | None = None,
    ):
        """Handle reconfiguration of an existing airport entry.

        Lets the user pick a different country/airport without deleting
        and re-adding the entry. Jumps straight to the country step
        (skipping continent selection, since the entry's continent is
        already implied by its stored country) pre-filled with the
        entry's current country/airport, then reuses the same
        country -> airport -> related_objects chain as initial setup.
        `_create_airport_entry` detects the reconfigure source and
        updates the existing entry instead of creating a new one.
        """
        entry = self._get_reconfigure_entry()
        country = entry.data.get(CONF_COUNTRY)

        self._continent = CONTINENTS.get(country, "EU")
        self._country = country
        self._suggested_country = country
        self._suggested_airport = entry.data.get(CONF_AIRPORT)

        return await self.async_step_country()

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ):
        """Handle continent selection."""

        defaults = default_config(
            self.hass,
        )

        if user_input is not None:
            self._continent = user_input[CONF_CONTINENT].upper()

            if self._continent == defaults[CONF_CONTINENT]:
                self._suggested_country = defaults[CONF_COUNTRY]
                self._suggested_airport = defaults[CONF_AIRPORT]
            else:
                self._suggested_country = None
                self._suggested_airport = None

            return await self.async_step_country()

        return self.async_show_form(
            step_id="user",
            data_schema=build_continent_schema(
                defaults,
            ),
        )

    async def async_step_country(
        self,
        user_input: dict | None = None,
    ):
        """Handle country selection."""

        assert self._continent is not None

        if user_input is not None:
            self._country = user_input[CONF_COUNTRY]

            if self._country != self._suggested_country:
                self._suggested_airport = None

            return await self.async_step_airport()

        return self.async_show_form(
            step_id="country",
            data_schema=build_country_schema(
                self._continent,
                self._suggested_country,
            ),
        )

    async def async_step_airport(
        self,
        user_input: dict | None = None,
    ):
        """Handle airport selection."""

        assert self._country is not None

        if user_input is not None:
            airport = user_input[CONF_AIRPORT]

            if self._airport_already_configured(
                airport,
            ):
                return self.async_show_form(
                    step_id="airport",
                    data_schema=build_airport_schema(
                        self._country,
                        self._suggested_airport,
                    ),
                    errors={
                        "base": "airport_exists",
                    },
                )

            self._selected_airport = airport
            return await self.async_step_related_objects()

        return self.async_show_form(
            step_id="airport",
            data_schema=build_airport_schema(
                self._country,
                self._suggested_airport,
            ),
        )

    async def async_step_related_objects(
        self,
        user_input: dict | None = None,
    ):
        """Optionally add the FIR device related to the selected airport.

        If the airport has a fir_icao set and that FIR isn't already a
        configured entry, we offer to add it. The user can uncheck the
        box to skip FIR creation entirely.

        If there's no related FIR (fir_icao is empty) or the FIR is
        already configured, we skip this step entirely and go straight
        to creating the airport entry.
        """
        assert self._selected_airport is not None
        assert self._country is not None

        airport = AIRPORTS[self._selected_airport]
        fir_icao = airport.fir_icao

        # Skip this step if no FIR is mapped or it's already configured.
        if not fir_icao or self._fir_already_configured(fir_icao):
            return self._create_airport_entry()

        if user_input is not None:
            # Optionally kick off a separate FIR flow before creating
            # the airport entry. The FIR flow runs independently and
            # produces its own config entry; the airport entry is the
            # result of this step.
            if user_input.get(CONF_ADD_FIR, True):
                fir = get_fir(fir_icao)
                await self.hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": "fir"},
                    data={
                        CONF_ENTRY_TYPE: ENTRY_TYPE_FIR,
                        CONF_FIR: fir_icao,
                    },
                )

            return self._create_airport_entry()

        fir = get_fir(fir_icao)
        fir_label = f"{fir_icao} — {fir.name}" if fir.name != fir_icao else fir_icao

        return self.async_show_form(
            step_id="related_objects",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_ADD_FIR,
                        default=True,
                    ): selector.BooleanSelector(),
                },
            ),
            description_placeholders={
                "fir_label": fir_label,
            },
        )

    def _create_airport_entry(self):
        """Create the airport config entry, or update it during reconfigure."""
        assert self._selected_airport is not None
        assert self._country is not None

        title = airport_options(
            self._country,
        )[self._selected_airport]
        data = {
            CONF_ENTRY_TYPE: ENTRY_TYPE_AIRPORT,
            CONF_COUNTRY: self._country,
            CONF_AIRPORT: self._selected_airport,
        }

        if self.source == SOURCE_RECONFIGURE:
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(),
                title=title,
                data=data,
            )

        return self.async_create_entry(
            title=title,
            data=data,
        )

    def _fir_already_configured(
        self,
        fir_icao: str,
    ) -> bool:
        """Check if a FIR entry already exists for this FIR code."""
        for entry in self._async_current_entries():
            if (
                entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_FIR
                and entry.data.get(CONF_FIR) == fir_icao
            ):
                return True

        return False

    async def async_step_fir(
        self,
        user_input: dict | None = None,
    ):
        """Handle programmatic creation of a FIR entry.

        Called internally (context source="fir") when the user accepts
        the FIR suggestion in async_step_related_objects. The FIR ICAO
        code is passed as user_input by the HA flow engine (it comes
        from the `data` argument of config_entries.flow.async_init).
        """
        if user_input is None:
            return self.async_abort(reason="already_configured")

        fir_icao = user_input.get(CONF_FIR, "")

        if not fir_icao or self._fir_already_configured(fir_icao):
            return self.async_abort(reason="already_configured")

        fir = get_fir(fir_icao)
        title = f"{fir_icao} — {fir.name}" if fir.name != fir_icao else fir_icao

        return self.async_create_entry(
            title=title,
            data={
                CONF_ENTRY_TYPE: ENTRY_TYPE_FIR,
                CONF_FIR: fir_icao,
            },
        )


class AviationWeatherOptionsFlow(
    config_entries.OptionsFlow,
):
    """Handle Aviation Weather options flow."""

    def __init__(
        self,
        config_entry: ConfigEntry,
    ) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict | None = None,
    ):
        """Manage options.

        Dispatches to the FIR options step for FIR entries. For airport
        entries, if the airport has a fir_icao set but the FIR device
        does not yet exist, an optional checkbox is shown at the top of
        the form so the user can add it without having to remove and
        re-add the airport.
        """
        entry_type = self._config_entry.data.get(
            CONF_ENTRY_TYPE,
            ENTRY_TYPE_AIRPORT,
        )

        if entry_type == ENTRY_TYPE_FIR:
            return await self.async_step_fir_init(user_input)

        airport_icao = get_entry_value(
            self._config_entry,
            CONF_AIRPORT,
        )
        airport = AIRPORTS[airport_icao]
        fir_icao = airport.fir_icao
        fir_missing = bool(fir_icao) and self._fir_not_configured(fir_icao)

        defaults = {
            CONF_ENABLED_ENTITIES: get_entry_value(
                self._config_entry,
                CONF_ENABLED_ENTITIES,
                default_options()[CONF_ENABLED_ENTITIES],
            ),
            CONF_METAR_INTERVAL: get_entry_value(
                self._config_entry,
                CONF_METAR_INTERVAL,
                default_options()[CONF_METAR_INTERVAL],
            ),
            CONF_TAF_INTERVAL: get_entry_value(
                self._config_entry,
                CONF_TAF_INTERVAL,
                default_options()[CONF_TAF_INTERVAL],
            ),
        }

        if user_input is not None:
            if fir_missing and user_input.pop(CONF_ADD_FIR, False):
                await self.hass.config_entries.flow.async_init(
                    DOMAIN,
                    context={"source": "fir"},
                    data={
                        CONF_ENTRY_TYPE: ENTRY_TYPE_FIR,
                        CONF_FIR: fir_icao,
                    },
                )

            return self.async_create_entry(
                title="",
                data=user_input,
            )

        schema = build_options_schema(defaults, airport)

        if fir_missing:
            fir = get_fir(fir_icao)
            fir_label = f"{fir_icao} — {fir.name}" if fir.name != fir_icao else fir_icao
            schema = vol.Schema(
                {
                    vol.Optional(
                        CONF_ADD_FIR,
                        default=False,
                    ): selector.BooleanSelector(),
                    **schema.schema,
                }
            )
        else:
            fir_label = ""

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
            description_placeholders=({"fir_label": fir_label} if fir_missing else {}),
        )

    def _fir_not_configured(self, fir_icao: str) -> bool:
        """Return True if no FIR entry exists yet for this FIR code."""
        return not any(
            entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_FIR
            and entry.data.get(CONF_FIR) == fir_icao
            for entry in self.hass.config_entries.async_entries(DOMAIN)
        )

    async def async_step_fir_init(
        self,
        user_input: dict | None = None,
    ):
        """Manage options for a FIR entry.

        Lets the user enable the optional SIGMET detail sensors and
        adjust the SIGMET refresh interval — the same
        enabled-entities/interval shape as the airport options step,
        scoped to FirAdditionalEntity instead of AdditionalEntity.
        """
        fir_icao = self._config_entry.data.get(CONF_FIR, "")

        defaults = {
            CONF_ENABLED_ENTITIES: get_entry_value(
                self._config_entry,
                CONF_ENABLED_ENTITIES,
                default_fir_options()[CONF_ENABLED_ENTITIES],
            ),
            CONF_SIGMET_INTERVAL: get_entry_value(
                self._config_entry,
                CONF_SIGMET_INTERVAL,
                default_fir_options()[CONF_SIGMET_INTERVAL],
            ),
        }

        if user_input is not None:
            return self.async_create_entry(
                title="",
                data=user_input,
            )

        return self.async_show_form(
            step_id="fir_init",
            data_schema=build_fir_options_schema(defaults),
            description_placeholders={"fir_icao": fir_icao},
        )
