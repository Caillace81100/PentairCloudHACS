"""Pentair config flow."""
from __future__ import annotations

import logging
import asyncio
from typing import Any

from pypentair import Pentair, PentairAuthenticationError
import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_PASSWORD, CONF_USERNAME
from homeassistant.data_entry_flow import FlowResult
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError # Importez HomeAssistantError d'ici
from .pentaircloud import PentairCloudHub

from .const import DOMAIN


_LOGGER = logging.getLogger(__name__)
STEP_USER_DATA_SCHEMA = vol.Schema(
    {vol.Required(CONF_USERNAME): str, vol.Required(CONF_PASSWORD): str}
)

async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    # TODO validate the data can be used to set up a connection.

    # If your PyPI package is not built with async, pass your methods
    # to the executor:
    # await hass.async_add_executor_job(
    #     your_validate_func, data["username"], data["password"]
    # )

    hub = PentairCloudHub(_LOGGER)
    if not await hass.async_add_executor_job(
        #hub.authenticate, data["username"], data["password"]
        hub.authenticate, data[CONF_USERNAME], data[CONF_PASSWORD]
    ):
        raise InvalidAuth

    # If you cannot connect:
    # throw CannotConnect
    # If the authentication is wrong:
    # InvalidAuth

    # Return info that you want to store in the config entry.
    return {"title": "PentairCloudHACS"}



class PentairConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Pentair."""

    VERSION = 1

    async def _async_create_entry(self, user_input: dict[str, Any]) -> FlowResult:
        """Create the config entry."""
        existing_entry = await self.async_set_unique_id(DOMAIN)

        config_data = {k: v for k, v in user_input.items() if k != CONF_PASSWORD}

        if existing_entry:
            self.hass.config_entries.async_update_entry(
                existing_entry, data=config_data
            )
            await self.hass.config_entries.async_reload(existing_entry.entry_id)
            return self.async_abort(reason="reauth_successful")

        return self.async_create_entry(
            title=config_data[CONF_USERNAME], data=config_data
        )

    async def async_pentair_login(
        self, step_id, user_input: dict[str, Any] | None, schema: vol.Schema
    ) -> FlowResult:
        """Attempt a login with Pentair."""
        errors = {}

        pentair = Pentair(username=user_input[CONF_USERNAME])
        try:
            await self.hass.async_add_executor_job(
                pentair.authenticate, user_input[CONF_PASSWORD]
            )
        except PentairAuthenticationError:
            errors["base"] = "invalid_auth"
        except Exception as ex:  # pylint: disable=broad-except
            _LOGGER.exception(ex)
            errors["base"] = "unknown"

        if not errors:
            return await self._async_create_entry(user_input | pentair.get_tokens())

        return self.async_show_form(step_id=step_id, data_schema=schema, errors=errors)

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            for entry in self._async_current_entries():
                if entry.data[CONF_USERNAME] == user_input[CONF_USERNAME]:
                    return self.async_abort(reason="already_configured")

            return await self.async_pentair_login(
                step_id="user", user_input=user_input, schema=STEP_USER_DATA_SCHEMA
            )

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Perform reauth upon an API authentication error."""
        return await self.async_step_reauth_confirm(user_input)

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Dialog that informs the user that reauth is required."""
        if user_input is None:
            user_input = {}

        reauth_schema = vol.Schema(
            {
                vol.Required(
                    CONF_USERNAME,
                    default=user_input.get(
                        CONF_USERNAME, self.init_data.get(CONF_USERNAME)
                    ),
                ): str,
                vol.Required(CONF_PASSWORD): str,
            }
        )

        if user_input.get(CONF_PASSWORD) is None:
            return self.async_show_form(
                step_id="reauth_confirm", data_schema=reauth_schema
            )

        return await self.async_pentair_login(
            step_id="reauth_confirm", user_input=user_input, schema=reauth_schema
        )
    
#class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
#    """Handle a config flow for PentairCloud."""

#    VERSION = 1

#    async def async_step_user(self, user_input: dict[str, Any] | None = None ) -> FlowResult:
#        """Handle the initial step."""
#        if user_input is None:
#            return self.async_show_form(
#                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
#            )

#        errors = {}

#        try:
#            info = await validate_input(self.hass, user_input)
#        except CannotConnect:
#            errors["base"] = "cannot_connect"
#        except InvalidAuth:
#            errors["base"] = "invalid_auth"
#        except Exception:  # pylint: disable=broad-except
#            _LOGGER.exception("Unexpected exception")
#            errors["base"] = "unknown"
#        else:
#            return self.async_create_entry(title=info["title"], data=user_input)

#        return self.async_show_form(
#            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
#       )

class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""
