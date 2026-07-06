"""Tests for system_health.py.

Covers two things: that `async_register` is callable the way Home
Assistant's core integration loader actually calls it (synchronously,
without await — see the module's own docstring for why this matters),
and that `system_health_info` returns sensible counts based on what's
configured and running.
"""

from __future__ import annotations

import warnings
from unittest.mock import AsyncMock, MagicMock, patch

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aviation_weather.const import (
    CONF_AIRPORT,
    CONF_COUNTRY,
    CONF_ENTRY_TYPE,
    CONF_FIR,
    DOMAIN,
    ENTRY_TYPE_FIR,
)
from custom_components.aviation_weather.system_health import (
    async_register,
    system_health_info,
)


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


class TestAsyncRegister:
    """async_register must be a plain synchronous @callback function,
    not `async def` — Home Assistant's core loader
    (system_health._register_system_health_platform) calls it without
    awaiting the result. An `async def` version would silently never
    run, since nothing ever awaits the coroutine it returns."""

    def test_does_not_return_a_coroutine(self, hass) -> None:
        """Calling async_register synchronously (exactly as HA core
        does) must not produce a coroutine object — it must actually
        run and return None."""
        register = MagicMock()

        result = async_register(
            hass,
            register,
        )

        assert result is None

    def test_does_not_raise_unawaited_coroutine_warning(self, hass) -> None:
        """A regression guard for the specific bug this function once
        had: calling it synchronously must not produce Python's
        "coroutine was never awaited" RuntimeWarning."""
        register = MagicMock()

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            async_register(
                hass,
                register,
            )

        unawaited_warnings = [
            warning
            for warning in caught
            if issubclass(warning.category, RuntimeWarning)
            and "was never awaited" in str(warning.message)
        ]

        assert not unawaited_warnings

    def test_registers_system_health_info_as_the_callback(self, hass) -> None:
        register = MagicMock()

        async_register(
            hass,
            register,
        )

        register.async_register_info.assert_called_once_with(
            system_health_info,
        )


class TestSystemHealthInfo:
    """Tests for the actual health-check payload."""

    async def test_no_configured_airports_returns_zero_counts(self, hass) -> None:
        info = await system_health_info(
            hass,
        )

        assert info == {
            "configured_airports": 0,
            "metar_coordinators": 0,
            "taf_coordinators": 0,
            "configured_firs": 0,
            "sigmet_coordinators": 0,
        }

    async def test_one_fully_set_up_airport(
        self, hass, enable_custom_integrations
    ) -> None:
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

        info = await system_health_info(
            hass,
        )

        assert info == {
            "configured_airports": 1,
            "metar_coordinators": 1,
            "taf_coordinators": 1,
            "configured_firs": 0,
            "sigmet_coordinators": 0,
        }

    async def test_two_configured_airports(
        self, hass, enable_custom_integrations
    ) -> None:
        first_entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_COUNTRY: "PL", CONF_AIRPORT: "EPWA"},
            entry_id="first_entry_id",
            unique_id="EPWA",
        )
        first_entry.add_to_hass(hass)

        with patch(
            "custom_components.aviation_weather.async_get_clientsession",
            return_value=_make_session(),
        ):
            await hass.config_entries.async_setup(first_entry.entry_id)
            await hass.async_block_till_done()

            second_entry = MockConfigEntry(
                domain=DOMAIN,
                data={CONF_COUNTRY: "PL", CONF_AIRPORT: "EPGD"},
                entry_id="second_entry_id",
                unique_id="EPGD",
            )
            second_entry.add_to_hass(hass)

            await hass.config_entries.async_setup(second_entry.entry_id)
            await hass.async_block_till_done()

        info = await system_health_info(
            hass,
        )

        assert info["configured_airports"] == 2
        assert info["metar_coordinators"] == 2
        assert info["taf_coordinators"] == 2

    async def test_config_entry_without_runtime_data_is_skipped(self, hass) -> None:
        """A config entry that exists but was never successfully set up
        (e.g. mid-setup, or setup failed) has no entry in hass.data —
        system_health_info must not crash on this, and must not count
        it as having coordinators."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_COUNTRY: "PL", CONF_AIRPORT: "EPWA"},
        )
        entry.add_to_hass(hass)
        # Deliberately not calling async_setup: hass.data[DOMAIN] never
        # gets populated for this entry.

        info = await system_health_info(
            hass,
        )

        assert info["configured_airports"] == 1
        assert info["metar_coordinators"] == 0
        assert info["taf_coordinators"] == 0


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


class TestSystemHealthInfoForFirEntries:
    """The FIR counters mirror the airport ones, but count FIR entries
    and the SIGMET coordinator instead of METAR/TAF."""

    async def test_one_fully_set_up_fir(self, hass, enable_custom_integrations) -> None:
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

        info = await system_health_info(
            hass,
        )

        assert info == {
            "configured_airports": 0,
            "metar_coordinators": 0,
            "taf_coordinators": 0,
            "configured_firs": 1,
            "sigmet_coordinators": 1,
        }

    async def test_fir_entry_without_runtime_data_is_skipped(self, hass) -> None:
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_ENTRY_TYPE: ENTRY_TYPE_FIR, CONF_FIR: "EPWW"},
        )
        entry.add_to_hass(hass)

        info = await system_health_info(
            hass,
        )

        assert info["configured_firs"] == 1
        assert info["sigmet_coordinators"] == 0


class TestSystemHealthInfoForUnknownEntryType:
    """An entry_type this version doesn't recognize is counted in
    neither configured_airports/firs nor any coordinator, instead of
    crashing."""

    async def test_unknown_entry_type_without_runtime_data(self, hass) -> None:
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_ENTRY_TYPE: "unknown_future_type"},
        )
        entry.add_to_hass(hass)

        info = await system_health_info(
            hass,
        )

        assert info == {
            "configured_airports": 0,
            "metar_coordinators": 0,
            "taf_coordinators": 0,
            "configured_firs": 0,
            "sigmet_coordinators": 0,
        }

    async def test_unknown_entry_type_with_runtime_data_present(self, hass) -> None:
        """Even if runtime data somehow exists for an unrecognized
        entry_type, no coordinator is counted for it."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_ENTRY_TYPE: "unknown_future_type"},
        )
        entry.add_to_hass(hass)
        hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
            "entry_type": "unknown_future_type",
        }

        info = await system_health_info(
            hass,
        )

        assert info["metar_coordinators"] == 0
        assert info["taf_coordinators"] == 0
        assert info["sigmet_coordinators"] == 0
