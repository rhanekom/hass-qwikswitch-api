"""Tests for the config and options flows."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import CONF_EMAIL
from homeassistant.data_entry_flow import FlowResultType
from pytest_homeassistant_custom_component.common import MockConfigEntry
from qwikswitchapi.exceptions import QSError

from custom_components.qwikswitch_api.const import (
    CONF_COMMAND_DELAY,
    CONF_MASTER_KEY,
    CONF_POLL_FREQUENCY,
    DOMAIN,
)

if TYPE_CHECKING:
    from collections.abc import Generator

    from homeassistant.core import HomeAssistant

USER_INPUT = {
    CONF_EMAIL: "test@example.com",
    CONF_MASTER_KEY: "TESTMASTERKEY",
    CONF_POLL_FREQUENCY: 5,
    CONF_COMMAND_DELAY: 2,
}


@pytest.fixture
def mock_flow_client() -> Generator[MagicMock]:
    """Patch QSClient as used inside the config flow's credential test."""
    with patch("custom_components.qwikswitch_api.config_flow.QSClient") as constructor:
        instance = MagicMock()
        instance.generate_api_keys.return_value = MagicMock()
        constructor.return_value = instance
        yield instance


async def test_user_flow_shows_form(hass: HomeAssistant) -> None:
    """The initial user step shows the input form."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert not result["errors"]


async def test_user_flow_success_creates_entry(
    hass: HomeAssistant,
    mock_flow_client: MagicMock,
) -> None:
    """Valid credentials create a config entry titled by the master key."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == USER_INPUT[CONF_MASTER_KEY]
    assert result["data"] == USER_INPUT
    mock_flow_client.generate_api_keys.assert_called_once()


async def test_user_flow_auth_error_shows_error(
    hass: HomeAssistant,
    mock_flow_client: MagicMock,
) -> None:
    """Invalid credentials re-show the form with an auth error."""
    mock_flow_client.generate_api_keys.side_effect = QSError("bad creds")

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "auth"}


async def test_user_flow_aborts_if_already_configured(
    hass: HomeAssistant,
    mock_flow_client: MagicMock,
) -> None:
    """A duplicate master key (same unique id) aborts the flow."""
    existing = MockConfigEntry(
        domain=DOMAIN,
        unique_id="testmasterkey",
        data=USER_INPUT,
    )
    existing.add_to_hass(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], USER_INPUT
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_options_flow_shows_form(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """The options flow presents a form seeded with current values."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "init"


async def test_options_flow_saves_values(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
) -> None:
    """Submitting the options flow stores the new option values."""
    mock_config_entry.add_to_hass(hass)

    result = await hass.config_entries.options.async_init(mock_config_entry.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_POLL_FREQUENCY: 15, CONF_COMMAND_DELAY: 4},
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {CONF_POLL_FREQUENCY: 15, CONF_COMMAND_DELAY: 4}
