"""Config flow for Gimdow integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.data_entry_flow import FlowResult
from tuya_connector import TuyaOpenAPI

from .const import (
    DOMAIN,
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_ENDPOINT,
    CONF_DEVICE_ID,
    DEFAULT_ENDPOINT
)

_LOGGER = logging.getLogger(__name__)

class GimdowConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Gimdow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        
        if user_input is not None:
             # Validate credentials
            access_id = user_input[CONF_ACCESS_ID]
            access_secret = user_input[CONF_ACCESS_SECRET]
            endpoint = user_input[CONF_ENDPOINT]
            device_id = user_input[CONF_DEVICE_ID]

            # Check if already configured
            await self.async_set_unique_id(device_id)
            self._abort_if_unique_id_configured()

            # Verify with Tuya
            openapi = TuyaOpenAPI(endpoint, access_id, access_secret)
            try:
                # Use tuya-connector-python style connection
                response = await self.hass.async_add_executor_job(openapi.connect)
                _LOGGER.debug("Tuya connection test result: %s", response)
                
            except Exception as err:
                _LOGGER.exception("Exception during Tuya connection attempt")
                errors["base"] = "cannot_connect"
            else:
                # tuya-connector-python connect() typically returns the token check result or success boolean
                # If we get a response and it doesn't indicate catastrophic failure (like False)
                if response is not False:
                    # Connection successful, create entry
                    return self.async_create_entry(
                        title=f"Gimdow Lock {device_id}",
                        data=user_input
                    )
                else:
                    _LOGGER.error("Tuya authentication failed (connect returned False)")
                    errors["base"] = "invalid_auth"

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_ACCESS_ID): str,
                    vol.Required(CONF_ACCESS_SECRET): str,
                    vol.Required(
                        CONF_ENDPOINT, default=DEFAULT_ENDPOINT
                    ): str,
                    vol.Required(CONF_DEVICE_ID): str,
                }
            ),
            errors=errors,
        )
