"""
Custom integration to integrate QwikSwitch with Home Assistant via their API.

For more details about this integration, please refer to
https://github.com/rhanekom/hass-qwikswitch-api
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from homeassistant.const import CONF_EMAIL, Platform
from homeassistant.core import HomeAssistant
from qwikswitchapi.client import QSClient
from qwikswitchapi.exceptions import QSException

from .const import (
    CONF_MASTER_KEY,
    CONF_POLL_FREQUENCY,
    DATA_QS_CLIENT,
    DATA_QS_COORDINATOR,
    DEFAULT_POLL_FREQUENCY,
    DOMAIN,
)
from .coordinator import QwikSwitchDataUpdateCoordinator

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigEntry
    from homeassistant.core import HomeAssistant

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.LIGHT,
    Platform.SWITCH,
]


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """
    Set up QwikSwitch API from a config entry.

    :param hass: HomeAssistant instance
    :param entry: Config entry to set up
    :return: True if setup was successful, False otherwise.
    """
    hass.data.setdefault(DOMAIN, {})

    email: str = entry.data[CONF_EMAIL]
    master_key: str = entry.data[CONF_MASTER_KEY]
    poll_frequency: int = entry.options.get(
        CONF_POLL_FREQUENCY, entry.data.get(CONF_POLL_FREQUENCY, DEFAULT_POLL_FREQUENCY)
    )

    try:
        qs_client = QSClient(email, master_key)  # No base_uri specified

        # Generate keys once at startup
        await hass.async_add_executor_job(qs_client.generate_api_keys)
    except QSException:
        _LOGGER.exception("Failed to set up QwikSwitch API integration")
        return False

    # Create the coordinator for periodic updates
    coordinator = QwikSwitchDataUpdateCoordinator(hass, qs_client, poll_frequency)
    # Perform first refresh to ensure data is available
    await coordinator.async_config_entry_first_refresh()

    # Store references
    hass.data[DOMAIN][DATA_QS_CLIENT] = qs_client
    hass.data[DOMAIN][DATA_QS_COORDINATOR] = coordinator

    # Forward setup to child platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Unload a QwikSwitch config entry.

    :param hass: HomeAssistant instance
    :param entry: Config entry to unload
    :return: True if unload was successful, False otherwise.
    """
    unload_ok: bool = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        qs_client = hass.data[DOMAIN].pop(DATA_QS_CLIENT, None)
        if qs_client:
            # Optionally delete keys if you do not want them to persist
            try:
                await hass.async_add_executor_job(qs_client.delete_api_keys)
            except QSException as err:
                _LOGGER.warning("Could not delete QwikSwitch API keys: %s", err)

        hass.data[DOMAIN].pop(DATA_QS_COORDINATOR, None)

        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    return unload_ok


async def async_reload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """
    Reload a QwikSwitch config entry.

    :param hass: HomeAssistant instance
    :param entry: Config entry to unload
    """
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
