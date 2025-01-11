"""Adds config flow for QwikSwitch API."""

from __future__ import annotations

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_EMAIL
from homeassistant.helpers import selector
from qwikswitchapi.qsapi import QSApi
from qwikswitchapi.qsexception import QSException
from slugify import slugify

from .const import CONF_MASTER_KEY, DOMAIN, LOGGER


class QSFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
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
                self._test_credentials(
                    email=user_input[CONF_EMAIL],
                    master_key=user_input[CONF_MASTER_KEY],
                )
            except QSException as exception:
                LOGGER.warning(exception)
                _errors["base"] = "auth"
            else:
                await self.async_set_unique_id(
                    unique_id=slugify(user_input[CONF_EMAIL])
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_EMAIL],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
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
                        selector.TextSelectorConfig(
                            type=selector.TextSelectorType.PASSWORD,
                        ),
                    ),
                },
            ),
            errors=_errors,
        )

    def _test_credentials(self, email: str, master_key: str) -> None:
        """Validate credentials."""
        client = QSApi()
        return client.generate_api_keys(email, master_key)
