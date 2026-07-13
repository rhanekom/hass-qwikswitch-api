"""Shared fixtures for the qwikswitch_api test suite."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import CONF_EMAIL
from homeassistant.setup import async_setup_component
from pytest_homeassistant_custom_component.common import MockConfigEntry
from qwikswitchapi.entities import DeviceStatus, DeviceStatuses

from custom_components.qwikswitch_api.const import (
    CONF_COMMAND_DELAY,
    CONF_MASTER_KEY,
    CONF_POLL_FREQUENCY,
    CONF_VERSION,
    DOMAIN,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from homeassistant.core import HomeAssistant

# Device type strings from the qwikswitch-api DEVICES map. These determine the
# DeviceStatus.device_class used by the light/switch platforms.
DIMMER_TYPE = "RELAY QS-D-S5"
RELAY_TYPE = "RELAY QS-R-S5"

# Slugified form of the master key below; the config flow derives the unique id
# from slugify(master_key), so tests that check for aborts rely on this match.
TEST_EMAIL = "test@example.com"
TEST_MASTER_KEY = "TESTMASTERKEY"
TEST_UNIQUE_ID = "testmasterkey"


def make_device_status(  # noqa: PLR0913
    device_id: str,
    value: int,
    device_type: str = RELAY_TYPE,
    *,
    firmware: str = "1.0",
    epoch: int = 1_700_000_000,
    rssi: int = 80,
) -> DeviceStatus:
    """Build a DeviceStatus like the ones the QwikSwitch API returns."""
    return DeviceStatus(device_id, device_type, firmware, epoch, rssi, value)


@pytest.fixture(autouse=True)
def _auto_enable_custom_integrations(
    enable_custom_integrations: object,
) -> None:
    """Make the custom component loadable in every test (HA plugin requirement)."""
    return


@pytest.fixture
def device_statuses() -> list[DeviceStatus]:
    """
    Devices the mocked API reports.

    Override this fixture in a test module to control which entities are created.
    """
    return [
        make_device_status("dimmer-1", 40, DIMMER_TYPE),
        make_device_status("relay-1", 100, RELAY_TYPE),
    ]


@pytest.fixture
def mock_qsclient(device_statuses: list[DeviceStatus]) -> Generator[MagicMock]:
    """
    Patch the QSClient constructor to return a mock instance.

    :yield: A MagicMock instance that represents the QSClient.
    """
    with patch("custom_components.qwikswitch_api.QSClient") as mock_constructor:
        instance = MagicMock()
        instance.generate_api_keys.return_value = None
        instance.delete_api_keys.return_value = None
        instance.control_device.return_value = None
        instance.get_all_device_status.return_value = DeviceStatuses(
            list(device_statuses)
        )

        mock_constructor.return_value = instance
        yield instance


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Build a current-schema (v2) config entry for the integration."""
    return MockConfigEntry(
        version=CONF_VERSION,
        domain=DOMAIN,
        title="QwikSwitch",
        data={
            CONF_EMAIL: TEST_EMAIL,
            CONF_MASTER_KEY: TEST_MASTER_KEY,
            CONF_POLL_FREQUENCY: 3,
            # Zero delay keeps the command queue from sleeping between commands,
            # so async_block_till_done() resolves quickly in tests.
            CONF_COMMAND_DELAY: 0,
        },
        source="user",
        unique_id=TEST_UNIQUE_ID,
        options={},
    )


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant,
    mock_qsclient: MagicMock,
    mock_config_entry: MockConfigEntry,
) -> tuple[MagicMock, MockConfigEntry]:
    """
    Set up the qwikswitch_api integration with a mocked QSClient.

    :return: A tuple of (mock client, loaded config entry).
    """
    await async_setup_component(hass, "persistent_notification", {})

    mock_config_entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is ConfigEntryState.LOADED

    return mock_qsclient, mock_config_entry
