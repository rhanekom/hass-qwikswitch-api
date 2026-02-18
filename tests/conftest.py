from __future__ import annotations

from types import MappingProxyType
from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry, ConfigEntryState
from homeassistant.const import CONF_EMAIL
from homeassistant.setup import async_setup_component

from custom_components.qwikswitch_api.const import (
    CONF_MASTER_KEY,
    CONF_POLL_FREQUENCY,
    DOMAIN,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from homeassistant.core import HomeAssistant


@pytest.fixture
def mock_qsclient() -> Generator[MagicMock]:
    """
    Patch the QSClient constructor to return a mock instance.

    :yield: A MagicMock instance that represents the QSClient.
    """
    with patch(
        "custom_components.qwikswitch_api.__init__.QSClient"
    ) as mock_constructor:
        instance = MagicMock()
        instance.generate_api_keys.return_value = None
        instance.delete_api_keys.return_value = None
        instance.control_device.return_value = None

        mock_constructor.return_value = instance
        yield instance


@pytest.fixture
async def setup_integration(
    hass: HomeAssistant, mock_qsclient: MagicMock
) -> tuple[MagicMock, ConfigEntry]:
    """
    Sets up the hass_qwikswitchapi integration in Home Assistant
    with a mocked QSClient, returning (mock_qsclient, config_entry).

    :param hass: The HomeAssistant test instance
    :param mock_qsclient: The mocked QSClient fixture
    :return: A tuple containing the mock client and the config entry
    """  # noqa: D205, D401
    # Ensure at least the persistent_notification integration is loaded
    await async_setup_component(hass, "persistent_notification", {})

    # Create a fake config entry
    mock_entry_data = {
        CONF_EMAIL: "test@example.com",
        CONF_MASTER_KEY: "TESTMASTERKEY",
        CONF_POLL_FREQUENCY: 3,
    }

    entry: ConfigEntry = ConfigEntry(
        version=1,
        domain=DOMAIN,
        title="QwikSwitch",
        data=mock_entry_data,
        source="test",
        entry_id="test_entry_id",
        state=ConfigEntryState.NOT_LOADED,
        unique_id="test_unique_id",
        discovery_keys=MappingProxyType({}),
        minor_version=0,
        options={},
    )

    # Add the entry to Home Assistant
    hass.config_entries._entries.items.append(entry)  # noqa: SLF001

    # Set up the integration
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    # Confirm it is loaded
    assert entry.state == ConfigEntryState.LOADED

    return mock_qsclient, entry
