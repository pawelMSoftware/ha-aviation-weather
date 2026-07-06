"""Tests for integration setup/unload (__init__.py: setup_entry, unload_entry)."""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from aiohttp import ClientError
from homeassistant.helpers import issue_registry as ir
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.aviation_weather import (
    CONFIG_SCHEMA,
    async_migrate_entry,
    async_setup_entry,
    async_unload_entry,
)
from custom_components.aviation_weather.const import (
    CONF_AIRPORT,
    CONF_COUNTRY,
    CONF_ENABLED_ENTITIES,
    CONF_ENTRY_TYPE,
    CONF_FIR,
    DOMAIN,
    ENTRY_TYPE_AIRPORT,
    ENTRY_TYPE_FIR,
)
from custom_components.aviation_weather.enums import (
    AdditionalEntity,
    FirAdditionalEntity,
)


@pytest.fixture
def config_entry() -> MockConfigEntry:
    """Return a mock config entry configured for EPWA."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={CONF_COUNTRY: "PL", CONF_AIRPORT: "EPWA"},
    )


def _make_success_session() -> MagicMock:
    """Build a mock aiohttp session that returns valid METAR/TAF data."""
    metar_response = MagicMock()
    metar_response.status = 200
    metar_response.raise_for_status = MagicMock()
    metar_response.json = AsyncMock(
        return_value=[{"icaoId": "EPWA", "name": "Warsaw Chopin", "temp": 18.0}],
    )

    taf_response = MagicMock()
    taf_response.status = 200
    taf_response.raise_for_status = MagicMock()
    taf_response.json = AsyncMock(
        return_value=[{"icaoId": "EPWA", "rawTAF": "TAF EPWA ..."}],
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


class TestConfigSchema:
    """This integration is config-entry only (no YAML configuration),
    which hassfest requires CONFIG_SCHEMA to declare explicitly."""

    def test_missing_domain_key_is_valid(self) -> None:
        """No YAML config for this domain at all is fine."""
        assert CONFIG_SCHEMA({}) == {}

    def test_yaml_config_for_this_domain_logs_an_error(self, caplog) -> None:
        """YAML config under the aviation_weather key doesn't raise
        (config_entry_only_config_schema can't reject already-parsed
        YAML), but logs an error telling the user to remove it — this
        is the documented behavior of
        cv.config_entry_only_config_schema, which also raises a
        Repairs issue when running inside hass."""
        result = CONFIG_SCHEMA({DOMAIN: {}})

        assert result == {DOMAIN: {}}
        assert "does not support YAML setup" in caplog.text


class TestAsyncSetupEntry:
    """Tests for async_setup_entry."""

    async def test_setup_succeeds_and_stores_coordinators(
        self, hass, enable_custom_integrations, config_entry: MockConfigEntry
    ) -> None:
        """Setup succeeds and both coordinators are stored in hass.data."""
        config_entry.add_to_hass(hass)

        with patch(
            "custom_components.aviation_weather.async_get_clientsession",
            return_value=_make_success_session(),
        ):
            result = await hass.config_entries.async_setup(config_entry.entry_id)
            await hass.async_block_till_done()

        assert result is True
        assert config_entry.state.value == "loaded"

        stored = hass.data[DOMAIN][config_entry.entry_id]
        assert "metar_coordinator" in stored
        assert "taf_coordinator" in stored
        assert stored["metar_coordinator"].last_update_success is True
        assert stored["taf_coordinator"].last_update_success is True

    async def test_setup_forwards_to_sensor_platform(
        self, hass, enable_custom_integrations, config_entry: MockConfigEntry
    ) -> None:
        """Setup creates the summary sensor entity for the configured airport."""
        config_entry.add_to_hass(hass)

        with patch(
            "custom_components.aviation_weather.async_get_clientsession",
            return_value=_make_success_session(),
        ):
            await hass.config_entries.async_setup(config_entry.entry_id)
            await hass.async_block_till_done()

        state = hass.states.get("sensor.epwa_metar")
        assert state is not None


class TestAsyncUnloadEntry:
    """Tests for async_unload_entry."""

    async def test_unload_removes_hass_data_entry(
        self, hass, enable_custom_integrations, config_entry: MockConfigEntry
    ) -> None:
        """Unloading removes the entry's data from hass.data[DOMAIN]."""
        config_entry.add_to_hass(hass)

        with patch(
            "custom_components.aviation_weather.async_get_clientsession",
            return_value=_make_success_session(),
        ):
            await hass.config_entries.async_setup(config_entry.entry_id)
            await hass.async_block_till_done()

        assert config_entry.entry_id in hass.data[DOMAIN]

        unload_result = await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()

        assert unload_result is True
        assert config_entry.entry_id not in hass.data[DOMAIN]

    async def test_unload_removes_sensor_entity(
        self, hass, enable_custom_integrations, config_entry: MockConfigEntry
    ) -> None:
        """Unloading marks the sensor entity unavailable.

        Home Assistant keeps the entity's last state in the state machine
        as "unavailable" after a platform unload (RestoreEntity behavior)
        rather than removing it outright.
        """
        config_entry.add_to_hass(hass)

        with patch(
            "custom_components.aviation_weather.async_get_clientsession",
            return_value=_make_success_session(),
        ):
            await hass.config_entries.async_setup(config_entry.entry_id)
            await hass.async_block_till_done()

        state = hass.states.get("sensor.epwa_metar")
        assert state is not None
        assert state.state != "unavailable"

        await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("sensor.epwa_metar")
        assert state is not None
        assert state.state == "unavailable"

    async def test_failed_platform_unload_keeps_hass_data_intact(
        self, hass, enable_custom_integrations, config_entry: MockConfigEntry
    ) -> None:
        """If async_unload_platforms returns False (a platform refused
        to unload — e.g. it raised during its own async_unload_entry),
        hass.data[DOMAIN][entry_id] must NOT be popped: that data backs
        the coordinators any still-loaded platform's entities depend
        on, so removing it would leave them pointing at nothing.

        This calls async_unload_entry directly as a unit, with
        async_unload_platforms mocked at the hass.config_entries level,
        rather than going through a full hass.config_entries.async_unload
        cycle with one real platform and one faked failure. The
        end-to-end version is tempting (it looks more "real"), but it
        leaves a live weather entity with an active coordinator
        listener that genuinely never gets torn down — exactly what a
        real failed unload would do in production — which then
        conflicts with Home Assistant's own entity removal machinery
        during pytest's lingering-timer cleanup check. Testing the
        function directly avoids creating that half-torn-down state in
        the first place.
        """
        config_entry.add_to_hass(hass)

        with patch(
            "custom_components.aviation_weather.async_get_clientsession",
            return_value=_make_success_session(),
        ):
            await hass.config_entries.async_setup(config_entry.entry_id)
            await hass.async_block_till_done()

        assert config_entry.entry_id in hass.data[DOMAIN]

        with patch.object(
            hass.config_entries,
            "async_unload_platforms",
            AsyncMock(return_value=False),
        ):
            unload_result = await async_unload_entry(
                hass,
                config_entry,
            )

        assert unload_result is False
        assert config_entry.entry_id in hass.data[DOMAIN]


class TestUpdateListener:
    """Tests for the options-update listener that reloads the entry."""

    async def test_changing_options_reloads_entry(
        self, hass, enable_custom_integrations, config_entry: MockConfigEntry
    ) -> None:
        """Updating the config entry's options triggers a reload."""
        config_entry.add_to_hass(hass)

        with patch(
            "custom_components.aviation_weather.async_get_clientsession",
            return_value=_make_success_session(),
        ):
            await hass.config_entries.async_setup(config_entry.entry_id)
            await hass.async_block_till_done()

            assert config_entry.state.value == "loaded"

            hass.config_entries.async_update_entry(
                config_entry,
                options={CONF_ENABLED_ENTITIES: [AdditionalEntity.TAF.value]},
            )
            await hass.async_block_till_done()

        # A reload means the entry went through unload+setup again and is
        # still loaded afterwards, now with the TAF sensor created.
        assert config_entry.state.value == "loaded"
        assert hass.states.get("sensor.epwa_taf") is not None


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


@pytest.fixture
def fir_config_entry() -> MockConfigEntry:
    """Return a mock FIR config entry for EPWW."""
    return MockConfigEntry(
        domain=DOMAIN,
        data={CONF_ENTRY_TYPE: ENTRY_TYPE_FIR, CONF_FIR: "EPWW"},
    )


class TestAsyncSetupFirEntry:
    """Tests for async_setup_entry with a FIR entry."""

    async def test_setup_succeeds_and_stores_sigmet_coordinator(
        self, hass, enable_custom_integrations, fir_config_entry: MockConfigEntry
    ) -> None:
        fir_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.aviation_weather.async_get_clientsession",
            return_value=_make_isigmet_session(),
        ):
            result = await hass.config_entries.async_setup(fir_config_entry.entry_id)
            await hass.async_block_till_done()

        assert result is True
        assert fir_config_entry.state.value == "loaded"

        stored = hass.data[DOMAIN][fir_config_entry.entry_id]
        assert "sigmet_coordinator" in stored
        assert stored["sigmet_coordinator"].last_update_success is True

    async def test_setup_creates_binary_sensor_and_sensor_platforms(
        self, hass, enable_custom_integrations, fir_config_entry: MockConfigEntry
    ) -> None:
        """The main SIGMET binary sensor is always created."""
        fir_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.aviation_weather.async_get_clientsession",
            return_value=_make_isigmet_session(),
        ):
            await hass.config_entries.async_setup(fir_config_entry.entry_id)
            await hass.async_block_till_done()

        state = hass.states.get("binary_sensor.epww_sigmet")
        assert state is not None
        assert state.state == "off"

    async def test_detail_sensors_created_when_option_enabled(
        self, hass, enable_custom_integrations, fir_config_entry: MockConfigEntry
    ) -> None:
        fir_config_entry.add_to_hass(
            hass,
        )
        hass.config_entries.async_update_entry(
            fir_config_entry,
            options={
                CONF_ENABLED_ENTITIES: [FirAdditionalEntity.SIGMET_SENSORS.value],
            },
        )

        with patch(
            "custom_components.aviation_weather.async_get_clientsession",
            return_value=_make_isigmet_session(),
        ):
            await hass.config_entries.async_setup(fir_config_entry.entry_id)
            await hass.async_block_till_done()

        assert hass.states.get("sensor.epww_sigmet_count") is not None
        assert hass.states.get("sensor.epww_sigmet_valid_until") is not None
        assert hass.states.get("sensor.epww_sigmet_hazards") is not None


class TestAsyncUnloadFirEntry:
    """Tests for async_unload_entry with a FIR entry."""

    async def test_unload_removes_hass_data_entry(
        self, hass, enable_custom_integrations, fir_config_entry: MockConfigEntry
    ) -> None:
        fir_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.aviation_weather.async_get_clientsession",
            return_value=_make_isigmet_session(),
        ):
            await hass.config_entries.async_setup(fir_config_entry.entry_id)
            await hass.async_block_till_done()

        assert fir_config_entry.entry_id in hass.data[DOMAIN]

        unload_result = await hass.config_entries.async_unload(
            fir_config_entry.entry_id
        )
        await hass.async_block_till_done()

        assert unload_result is True
        assert fir_config_entry.entry_id not in hass.data[DOMAIN]

    async def test_unload_removes_binary_sensor_entity(
        self, hass, enable_custom_integrations, fir_config_entry: MockConfigEntry
    ) -> None:
        fir_config_entry.add_to_hass(hass)

        with patch(
            "custom_components.aviation_weather.async_get_clientsession",
            return_value=_make_isigmet_session(),
        ):
            await hass.config_entries.async_setup(fir_config_entry.entry_id)
            await hass.async_block_till_done()

        assert hass.states.get("binary_sensor.epww_sigmet") is not None

        await hass.config_entries.async_unload(fir_config_entry.entry_id)
        await hass.async_block_till_done()

        state = hass.states.get("binary_sensor.epww_sigmet")
        assert state is not None
        assert state.state == "unavailable"


class TestAsyncSetupEntryUnknownEntryType:
    """Tests for the defensive fallback when entry_type is neither
    ENTRY_TYPE_AIRPORT nor ENTRY_TYPE_FIR (e.g. a future entry type
    this version of the integration doesn't know about yet)."""

    async def test_returns_false(self, hass, enable_custom_integrations) -> None:
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_ENTRY_TYPE: "unknown_future_type"},
        )
        entry.add_to_hass(hass)

        result = await async_setup_entry(hass, entry)

        assert result is False


class TestAsyncMigrateEntry:
    """Tests for async_migrate_entry (config entry schema migrations)."""

    async def test_airport_entry_title_is_normalized(
        self, hass, enable_custom_integrations
    ) -> None:
        """A pre-1.1 airport entry's title is normalized to "ICAO — Name"."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            version=1,
            minor_version=0,
            title="EPWA",
            data={
                CONF_ENTRY_TYPE: ENTRY_TYPE_AIRPORT,
                CONF_COUNTRY: "PL",
                CONF_AIRPORT: "EPWA",
            },
        )
        entry.add_to_hass(hass)

        result = await async_migrate_entry(hass, entry)

        assert result is True
        assert entry.title == "EPWA — Warsaw Chopin Airport"
        assert entry.minor_version == 1

    async def test_airport_not_in_registry_is_left_unchanged(
        self, hass, enable_custom_integrations
    ) -> None:
        """An airport ICAO that no longer exists in the registry (e.g.
        removed in a database refresh) is skipped rather than crashing
        or producing a garbage title."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            version=1,
            minor_version=0,
            title="Old Title",
            data={
                CONF_ENTRY_TYPE: ENTRY_TYPE_AIRPORT,
                CONF_COUNTRY: "PL",
                CONF_AIRPORT: "NOSUCHAIRPORT",
            },
        )
        entry.add_to_hass(hass)

        result = await async_migrate_entry(hass, entry)

        assert result is True
        assert entry.title == "Old Title"
        assert entry.minor_version == 0

    async def test_fir_entry_title_is_normalized(
        self, hass, enable_custom_integrations
    ) -> None:
        """A pre-1.1 FIR entry's title is normalized to "ICAO — Name"."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            version=1,
            minor_version=0,
            title="EPWW",
            data={CONF_ENTRY_TYPE: ENTRY_TYPE_FIR, CONF_FIR: "EPWW"},
        )
        entry.add_to_hass(hass)

        result = await async_migrate_entry(hass, entry)

        assert result is True
        assert entry.title == "EPWW — Warszawa FIR"
        assert entry.minor_version == 1

    async def test_fir_entry_unknown_to_registry_falls_back_to_icao_only(
        self, hass, enable_custom_integrations
    ) -> None:
        """A FIR code not in firs/registry.py falls back to just the
        ICAO code as the title (get_fir's fallback name == the ICAO
        itself, so no "ICAO — ICAO" duplication)."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            version=1,
            minor_version=0,
            title="ZZZZ",
            data={CONF_ENTRY_TYPE: ENTRY_TYPE_FIR, CONF_FIR: "ZZZZ"},
        )
        entry.add_to_hass(hass)

        result = await async_migrate_entry(hass, entry)

        assert result is True
        assert entry.title == "ZZZZ"
        assert entry.minor_version == 1

    async def test_already_migrated_entry_is_left_unchanged(
        self, hass, enable_custom_integrations
    ) -> None:
        """An entry already at 1.1 is not touched again."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            version=1,
            minor_version=1,
            title="EPWA — Warsaw Chopin Airport",
            data={
                CONF_ENTRY_TYPE: ENTRY_TYPE_AIRPORT,
                CONF_COUNTRY: "PL",
                CONF_AIRPORT: "EPWA",
            },
        )
        entry.add_to_hass(hass)

        result = await async_migrate_entry(hass, entry)

        assert result is True
        assert entry.title == "EPWA — Warsaw Chopin Airport"
        assert entry.minor_version == 1

    async def test_unknown_entry_type_is_left_unchanged(
        self, hass, enable_custom_integrations
    ) -> None:
        """An entry_type this version doesn't recognize is neither the
        airport nor the FIR branch — it's simply left alone rather than
        crashing."""
        entry = MockConfigEntry(
            domain=DOMAIN,
            version=1,
            minor_version=0,
            title="Untouched",
            data={CONF_ENTRY_TYPE: "unknown_future_type"},
        )
        entry.add_to_hass(hass)

        result = await async_migrate_entry(hass, entry)

        assert result is True
        assert entry.title == "Untouched"
        assert entry.minor_version == 0


class TestStaleMetarRepairIssueLifecycle:
    """Integration-level test that the stale-METAR Repairs issue is
    cleaned up when the config entry unloads — not just on recovery.
    (Unit-level creation/clearing is covered in
    tests/metar/test_coordinator.py and tests/test_helpers.py; this
    exercises the entry.async_on_unload cleanup registered in
    MetarCoordinator.__init__, which needs a real setup/unload cycle to
    trigger.)"""

    async def test_unloading_the_entry_clears_the_issue(
        self, hass, enable_custom_integrations, config_entry: MockConfigEntry
    ) -> None:
        config_entry.add_to_hass(hass)

        with patch(
            "custom_components.aviation_weather.async_get_clientsession",
            return_value=_make_success_session(),
        ):
            await hass.config_entries.async_setup(config_entry.entry_id)
            await hass.async_block_till_done()

        metar_coordinator = hass.data[DOMAIN][config_entry.entry_id][
            "metar_coordinator"
        ]
        metar_coordinator.last_update_success_time -= timedelta(hours=7)
        metar_coordinator._client.get_metar = AsyncMock(
            side_effect=ClientError("connection reset"),
        )

        await metar_coordinator.async_refresh()

        issue_id = f"stale_metar_{config_entry.entry_id}"
        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is not None

        await hass.config_entries.async_unload(config_entry.entry_id)
        await hass.async_block_till_done()

        assert ir.async_get(hass).async_get_issue(DOMAIN, issue_id) is None
