"""Tests for integration setup, unload, reload and migration."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_EMAIL
from pytest_homeassistant_custom_component.common import MockConfigEntry
from qwikswitchapi.exceptions import QSError

from custom_components.qwikswitch_api import async_migrate_entry
from custom_components.qwikswitch_api.const import (
    CONF_COMMAND_DELAY,
    CONF_MASTER_KEY,
    CONF_POLL_FREQUENCY,
    CONF_VERSION,
    DATA_COMMAND_QUEUE,
    DATA_QS_CLIENT,
    DATA_QS_COORDINATOR,
    DEFAULT_COMMAND_DELAY,
    DOMAIN,
)

if TYPE_CHECKING:
    from unittest.mock import MagicMock

    from homeassistant.core import HomeAssistant


async def test_setup_entry_success(
    hass: HomeAssistant,
    setup_integration: tuple[MagicMock, MockConfigEntry],
) -> None:
    """A successful setup generates keys, stores data and loads the entry."""
    mock_client, entry = setup_integration

    assert entry.state is ConfigEntryState.LOADED
    mock_client.generate_api_keys.assert_called_once()

    domain_data = hass.data[DOMAIN]
    assert domain_data[DATA_QS_CLIENT] is mock_client
    assert DATA_COMMAND_QUEUE in domain_data
    assert DATA_QS_COORDINATOR in domain_data


async def test_setup_entry_auth_failure(
    hass: HomeAssistant,
    mock_qsclient: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> None:
    """When key generation fails, setup returns False and the entry errors."""
    mock_qsclient.generate_api_keys.side_effect = QSError("bad creds")
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert result is False
    assert mock_config_entry.state is ConfigEntryState.SETUP_ERROR


async def test_unload_entry_deletes_keys_and_cleans_up(
    hass: HomeAssistant,
    setup_integration: tuple[MagicMock, MockConfigEntry],
) -> None:
    """Unloading deletes API keys and removes all domain data."""
    mock_client, entry = setup_integration

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    mock_client.delete_api_keys.assert_called_once()
    # Last entry removed -> the whole domain bucket is dropped.
    assert DOMAIN not in hass.data


async def test_unload_entry_survives_key_delete_error(
    hass: HomeAssistant,
    setup_integration: tuple[MagicMock, MockConfigEntry],
) -> None:
    """A failure deleting keys is logged but still unloads the entry."""
    mock_client, entry = setup_integration
    mock_client.delete_api_keys.side_effect = QSError("delete failed")

    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED
    mock_client.delete_api_keys.assert_called_once()


async def test_reload_entry(
    hass: HomeAssistant,
    setup_integration: tuple[MagicMock, MockConfigEntry],
) -> None:
    """A reload tears the entry down and sets it back up cleanly."""
    mock_client, entry = setup_integration

    assert await hass.config_entries.async_reload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    # delete (unload) + regenerate (setup) both happened.
    mock_client.delete_api_keys.assert_called_once()
    assert mock_client.generate_api_keys.call_count == 2
    assert hass.data[DOMAIN][DATA_QS_CLIENT] is mock_client


async def test_options_update_triggers_reload(
    hass: HomeAssistant,
    setup_integration: tuple[MagicMock, MockConfigEntry],
) -> None:
    """Changing options reloads the entry and applies the new poll frequency."""
    mock_client, entry = setup_integration

    hass.config_entries.async_update_entry(
        entry,
        options={CONF_POLL_FREQUENCY: 30, CONF_COMMAND_DELAY: 1},
    )
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.LOADED
    # A reload re-ran setup (keys regenerated) and rebuilt the coordinator with
    # the new interval.
    assert mock_client.generate_api_keys.call_count == 2
    coordinator = hass.data[DOMAIN][DATA_QS_COORDINATOR]
    assert coordinator.update_interval == timedelta(seconds=30)


async def test_migrate_v1_adds_command_delay(hass: HomeAssistant) -> None:
    """A v1 entry without command_delay is migrated to v2 with the default."""
    entry = MockConfigEntry(
        version=1,
        domain=DOMAIN,
        title="QwikSwitch",
        data={
            CONF_EMAIL: "test@example.com",
            CONF_MASTER_KEY: "TESTMASTERKEY",
            CONF_POLL_FREQUENCY: 3,
        },
        source="user",
        unique_id="testmasterkey",
    )
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry)

    assert entry.version == CONF_VERSION
    assert entry.data[CONF_COMMAND_DELAY] == DEFAULT_COMMAND_DELAY


async def test_migrate_current_version_is_noop(hass: HomeAssistant) -> None:
    """An already-current entry is left untouched by migration."""
    entry = MockConfigEntry(
        version=CONF_VERSION,
        domain=DOMAIN,
        title="QwikSwitch",
        data={
            CONF_EMAIL: "test@example.com",
            CONF_MASTER_KEY: "TESTMASTERKEY",
            CONF_POLL_FREQUENCY: 3,
            CONF_COMMAND_DELAY: 7,
        },
        source="user",
        unique_id="testmasterkey",
    )
    entry.add_to_hass(hass)

    assert await async_migrate_entry(hass, entry)

    # Untouched: the custom command_delay is preserved, version unchanged.
    assert entry.version == CONF_VERSION
    assert entry.data[CONF_COMMAND_DELAY] == 7
