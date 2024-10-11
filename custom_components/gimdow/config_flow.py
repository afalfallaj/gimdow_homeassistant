"""Config flow for Gimdow Lock."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.helpers import selector

from tuya_sharing import LoginControl

from .const import (
    CONF_ENDPOINT,
    CONF_TERMINAL_ID,
    CONF_TOKEN_INFO,
    CONF_USER_CODE,
    DOMAIN,
    GIMDOW_CLIENT_ID,
    GIMDOW_RESPONSE_CODE,
    GIMDOW_RESPONSE_MSG,
    GIMDOW_RESPONSE_QR_CODE,
    GIMDOW_RESPONSE_RESULT,
    GIMDOW_RESPONSE_SUCCESS,
    GIMDOW_SCHEMA,
)


class GimdowConfigFlow(ConfigFlow, domain=DOMAIN):
    """Gimdow lock config flow."""

    __user_code: str | None = None
    __qr_code: str | None = None
    __reauth_entry: ConfigEntry | None = None

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.__login_control = LoginControl()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step where the user inputs their user code."""
        errors = {}
        placeholders = {}

        if user_input is not None:
            # Try to get the QR code based on the entered user code
            success, response = await self.__async_get_qr_code(user_input[CONF_USER_CODE])
            if success:
                return await self.async_step_scan()

            # Display errors if the login failed
            errors["base"] = "login_error"
            placeholders = {
                GIMDOW_RESPONSE_MSG: response.get(GIMDOW_RESPONSE_MSG, "Unknown error"),
                GIMDOW_RESPONSE_CODE: response.get(GIMDOW_RESPONSE_CODE, "0"),
            }
        else:
            user_input = {}

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USER_CODE, default=user_input.get(CONF_USER_CODE, "")
                    ): str,
                }
            ),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_scan(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the scanning of the QR code."""
        if user_input is None:
            return self.async_show_form(
                step_id="scan",
                data_schema=vol.Schema(
                    {
                        vol.Optional("QR"): selector.QrCodeSelector(
                            config=selector.QrCodeSelectorConfig(
                                data=f"tuyaSmart--qrLogin?token={self.__qr_code}",
                                scale=5,
                                error_correction_level=selector.QrErrorCorrectionLevel.QUARTILE,
                            )
                        )
                    }
                ),
            )

        # Call the login_result method to check if the QR code scan was successful
        ret, info = await self.hass.async_add_executor_job(
            self.__login_control.login_result,
            self.__qr_code,
            GIMDOW_CLIENT_ID,
            self.__user_code,
        )
        if not ret:
            # If login failed, show a new form to allow retrying
            await self.__async_get_qr_code(self.__user_code)
            return self.async_show_form(
                step_id="scan",
                errors={"base": "login_error"},
                data_schema=vol.Schema(
                    {
                        vol.Optional("QR"): selector.QrCodeSelector(
                            config=selector.QrCodeSelectorConfig(
                                data=f"tuyaSmart--qrLogin?token={self.__qr_code}",
                                scale=5,
                                error_correction_level=selector.QrErrorCorrectionLevel.QUARTILE,
                            )
                        )
                    }
                ),
                description_placeholders={
                    GIMDOW_RESPONSE_MSG: info.get(GIMDOW_RESPONSE_MSG, "Unknown error"),
                    GIMDOW_RESPONSE_CODE: info.get(GIMDOW_RESPONSE_CODE, 0),
                },
            )

        # Create a new config entry with the acquired data
        entry_data = {
            CONF_USER_CODE: self.__user_code,
            CONF_TOKEN_INFO: {
                "t": info["t"],
                "uid": info["uid"],
                "expire_time": info["expire_time"],
                "access_token": info["access_token"],
                "refresh_token": info["refresh_token"],
            },
            CONF_TERMINAL_ID: info[CONF_TERMINAL_ID],
            CONF_ENDPOINT: info[CONF_ENDPOINT],
        }

        if self.__reauth_entry:
            # If re-authenticating, update the existing entry
            return self.async_update_reload_and_abort(
                self.__reauth_entry,
                data=entry_data,
            )

        return self.async_create_entry(
            title=info.get("username"),
            data=entry_data,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication with Gimdow."""
        self.__reauth_entry = self.hass.config_entries.async_get_entry(
            self.context["entry_id"]
        )

        if self.__reauth_entry and CONF_USER_CODE in self.__reauth_entry.data:
            success, _ = await self.__async_get_qr_code(
                self.__reauth_entry.data[CONF_USER_CODE]
            )
            if success:
                return await self.async_step_scan()

        return await self.async_step_reauth_user_code()

    async def async_step_reauth_user_code(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle re-authentication for the user code step."""
        errors = {}
        placeholders = {}

        if user_input is not None:
            success, response = await self.__async_get_qr_code(
                user_input[CONF_USER_CODE]
            )
            if success:
                return await self.async_step_scan()

            errors["base"] = "login_error"
            placeholders = {
                GIMDOW_RESPONSE_MSG: response.get(GIMDOW_RESPONSE_MSG, "Unknown error"),
                GIMDOW_RESPONSE_CODE: response.get(GIMDOW_RESPONSE_CODE, "0"),
            }
        else:
            user_input = {}

        return self.async_show_form(
            step_id="reauth_user_code",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_USER_CODE, default=user_input.get(CONF_USER_CODE, "")
                    ): str,
                }
            ),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def __async_get_qr_code(self, user_code: str) -> tuple[bool, dict[str, Any]]:
        """Get the QR code for the Gimdow lock."""
        response = await self.hass.async_add_executor_job(
            self.__login_control.qr_code,
            GIMDOW_CLIENT_ID,
            GIMDOW_SCHEMA,
            user_code,
        )
        if success := response.get(GIMDOW_RESPONSE_SUCCESS, False):
            self.__user_code = user_code
            self.__qr_code = response[GIMDOW_RESPONSE_RESULT][GIMDOW_RESPONSE_QR_CODE]
        return success, response
