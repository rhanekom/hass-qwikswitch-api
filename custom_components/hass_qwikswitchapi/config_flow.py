"""Adds config flow for QwikSwitch API."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import homeassistant.helpers.config_validation as cv
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL
from homeassistant.helpers import selector
from qwikswitchapi.client import QSClient
from qwikswitchapi.exceptions import QSException
from slugify import slugify

from .const import (
    CONF_MASTER_KEY,
    CONF_POLL_FREQUENCY,
    DEFAULT_POLL_FREQUENCY,
    DOMAIN,
    LOGGER,
)

if TYPE_CHECKING:
    from homeassistant.config_entries import ConfigFlowResult
    from qwikswitchapi.entities import ApiKeys


class QwikSwitchConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for QwikSwitch API."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle a flow initialized by the user."""
        _errors = {}
        if user_input is not None:
            try:
                await self.hass.async_add_executor_job(
                    self._test_credentials,
                    user_input[CONF_EMAIL],
                    user_input[CONF_MASTER_KEY],
                )
            except QSException as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            else:
                await self.async_set_unique_id(
                    unique_id=slugify(user_input[CONF_MASTER_KEY])
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[
                        CONF_MASTER_KEY
                    ],  # Could be multiple entries added to the same email
                    data=user_input,
                )

        data_schema = vol.Schema(
            {
                vol.Required(
                    CONF_EMAIL,
                    default=(user_input or {}).get(CONF_EMAIL, vol.UNDEFINED),
                ): selector.TextSelector(
                    selector.TextSelectorConfig(
                        type=selector.TextSelectorType.EMAIL,
                    ),
                ),
                vol.Required(CONF_MASTER_KEY): selector.TextSelector(
                    selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT),
                ),
                vol.Required(
                    CONF_POLL_FREQUENCY, default=DEFAULT_POLL_FREQUENCY
                ): vol.All(cv.positive_int, vol.Range(min=1)),
            }
        )

        return self.async_show_form(
            step_id="user", data_schema=data_schema, errors=_errors
        )

    def _test_credentials(self, email: str, master_key: str) -> ApiKeys:
        """Validate credentials."""
        client = QSClient(email=email, master_key=master_key)
        return client.generate_api_keys()


class QwikSwitchAPIOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle the options flow to update entry settings."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize the QwikSwitch options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the QwikSwitch options."""
        if user_input is not None:
            return self.async_create_entry(data=user_input)

        current_poll_freq: int = self.config_entry.data.get(
            CONF_POLL_FREQUENCY, DEFAULT_POLL_FREQUENCY
        )
        options_schema = vol.Schema(
            {
                vol.Optional(CONF_POLL_FREQUENCY, default=current_poll_freq): vol.All(
                    cv.positive_int, vol.Range(min=1)
                )
            }
        )

        return self.async_show_form(step_id="init", data_schema=options_schema)
