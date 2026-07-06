"""Tests for diagnostics.py (async_get_config_entry_diagnostics)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aviation_weather.const import (
    CONF_AIRPORT,
    CONF_COUNTRY,
    CONF_ENABLED_ENTITIES,
    CONF_ENTRY_TYPE,
    CONF_FIR,
    DOMAIN,
    ENTRY_TYPE_FIR,
)
from custom_components.aviation_weather.diagnostics import (
    async_get_config_entry_diagnostics,
)
from custom_components.aviation_weather.enums import AdditionalEntity


def _make_session() -> MagicMock:
    """Build a mock aiohttp session with a minimal valid METAR/TAF pair."""
    metar_response = MagicMock()
    metar_response.status = 200
    metar_response.raise_for_status = MagicMock()
    metar_response.json = AsyncMock(
        return_value=[{"icaoId": "EPWA", "temp": 18.0}],
    )

    taf_response = MagicMock()
    taf_response.status = 200
    taf_response.raise_for_status = MagicMock()
    taf_response.json = AsyncMock(
        return_value=[{"icaoId": "EPWA", "rawTAF": "TAF EPWA ..."}],
    )

    def get(url, params=None, **kwargs):
        context_manager = MagicMock()
        if "taf" in url:
            context_manager.__aenter__ = AsyncMock(return_value=taf_response)
        else:
            context_manager.__aenter__ = AsyncMock(return_value=metar_response)
        context_manager.__aexit__ = AsyncMock(return_value=False)
        return context_manager

    session = MagicMock()
    session.get = MagicMock(side_effect=get)
    return session


async def _set_up_entry(hass) -> MockConfigEntry:
    """Set up a fully working config entry and return it."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_COUNTRY: "PL", CONF_AIRPORT: "EPWA"},
        options={CONF_ENABLED_ENTITIES: [AdditionalEntity.TAF.value]},
    )
    entry.add_to_hass(hass)

    with patch(
        "custom_components.aviation_weather.async_get_clientsession",
        return_value=_make_session(),
    ):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    return entry


class TestConfigEntrySection:
    """The config_entry section reflects the entry's own data/options."""

    async def test_includes_entry_identity_fields(
        self, hass, enable_custom_integrations
    ) -> None:
        entry = await _set_up_entry(hass)

        diagnostics = await async_get_config_entry_diagnostics(
            hass,
            entry,
        )

        assert diagnostics["config_entry"]["entry_id"] == entry.entry_id
        assert diagnostics["config_entry"]["version"] == entry.version
        assert diagnostics["config_entry"]["minor_version"] == entry.minor_version

    async def test_includes_data_and_options(
        self, hass, enable_custom_integrations
    ) -> None:
        entry = await _set_up_entry(hass)

        diagnostics = await async_get_config_entry_diagnostics(
            hass,
            entry,
        )

        assert diagnostics["config_entry"]["data"] == {
            CONF_COUNTRY: "PL",
            CONF_AIRPORT: "EPWA",
        }
        assert diagnostics["config_entry"]["options"] == {
            CONF_ENABLED_ENTITIES: [AdditionalEntity.TAF.value],
        }


class TestCoordinatorsSection:
    """The coordinators section reports the live state of both
    coordinators — useful for diagnosing why an airport shows
    unavailable without the user needing to enable debug logging."""

    async def test_successful_coordinators_report_success(
        self, hass, enable_custom_integrations
    ) -> None:
        entry = await _set_up_entry(hass)

        diagnostics = await async_get_config_entry_diagnostics(
            hass,
            entry,
        )

        assert diagnostics["coordinators"]["metar"]["last_update_success"] is True
        assert diagnostics["coordinators"]["metar"]["last_exception"] is None
        assert diagnostics["coordinators"]["taf"]["last_update_success"] is True
        assert diagnostics["coordinators"]["taf"]["last_exception"] is None

    async def test_update_interval_is_a_string(
        self, hass, enable_custom_integrations
    ) -> None:
        """update_interval (a timedelta) must be serialized to a string
        — diagnostics output is JSON, which can't represent timedelta
        objects directly."""
        entry = await _set_up_entry(hass)

        diagnostics = await async_get_config_entry_diagnostics(
            hass,
            entry,
        )

        assert isinstance(
            diagnostics["coordinators"]["metar"]["update_interval"],
            str,
        )
        assert isinstance(
            diagnostics["coordinators"]["taf"]["update_interval"],
            str,
        )

    async def test_failed_coordinator_reports_the_exception(
        self, hass, enable_custom_integrations
    ) -> None:
        """When a coordinator's last refresh failed, its exception is
        included as a repr string — this is the actual diagnostic
        value: a developer reading a bug report can see exactly what
        went wrong without needing the user's debug logs."""
        entry = await _set_up_entry(hass)

        taf_coordinator = hass.data[DOMAIN][entry.entry_id]["taf_coordinator"]
        taf_coordinator.last_update_success = False
        taf_coordinator.last_exception = ValueError("No TAF data returned")

        diagnostics = await async_get_config_entry_diagnostics(
            hass,
            entry,
        )

        assert diagnostics["coordinators"]["taf"]["last_update_success"] is False
        assert (
            "No TAF data returned"
            in diagnostics["coordinators"]["taf"]["last_exception"]
        )


class TestHomeAssistantSection:
    """The home_assistant section captures ambient HA configuration
    that's useful context when diagnosing location- or
    language-dependent behavior (e.g. unit conversion, translations)."""

    async def test_includes_hass_config_fields(
        self, hass, enable_custom_integrations
    ) -> None:
        hass.config.latitude = 52.1
        hass.config.longitude = 21.0
        entry = await _set_up_entry(hass)

        diagnostics = await async_get_config_entry_diagnostics(
            hass,
            entry,
        )

        assert diagnostics["home_assistant"]["latitude"] == 52.1
        assert diagnostics["home_assistant"]["longitude"] == 21.0
        assert "time_zone" in diagnostics["home_assistant"]
        assert "language" in diagnostics["home_assistant"]


def _make_isigmet_session() -> MagicMock:
    """Build a mock aiohttp session returning an empty isigmet response."""
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


async def _set_up_fir_entry(hass) -> MockConfigEntry:
    """Set up a fully working FIR config entry and return it."""
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


class TestFirEntryDiagnostics:
    """FIR entries report a sigmet coordinator section instead of
    metar/taf."""

    async def test_includes_sigmet_coordinator_section(
        self, hass, enable_custom_integrations
    ) -> None:
        entry = await _set_up_fir_entry(hass)

        diagnostics = await async_get_config_entry_diagnostics(
            hass,
            entry,
        )

        assert diagnostics["coordinators"]["sigmet"]["last_update_success"] is True
        assert diagnostics["coordinators"]["sigmet"]["last_exception"] is None
        assert isinstance(
            diagnostics["coordinators"]["sigmet"]["update_interval"],
            str,
        )
        assert diagnostics["coordinators"]["sigmet"]["active_sigmet_count"] == 0

    async def test_config_entry_section_reflects_fir_entry(
        self, hass, enable_custom_integrations
    ) -> None:
        entry = await _set_up_fir_entry(hass)

        diagnostics = await async_get_config_entry_diagnostics(
            hass,
            entry,
        )

        assert diagnostics["config_entry"]["entry_type"] == ENTRY_TYPE_FIR
        assert diagnostics["config_entry"]["data"][CONF_FIR] == "EPWW"


class TestUnknownEntryType:
    """An entry_type this version doesn't recognize yields an empty
    coordinators section instead of crashing."""

    async def test_empty_coordinators_section(self, hass) -> None:
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_ENTRY_TYPE: "unknown_future_type"},
        )
        entry.add_to_hass(hass)
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
            "entry_type": "unknown_future_type",
        }

        diagnostics = await async_get_config_entry_diagnostics(
            hass,
            entry,
        )

        assert diagnostics["coordinators"] == {}
