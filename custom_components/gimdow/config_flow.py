from homeassistant import config_entries
from tuya_sharing import LoginControl
from .const import DOMAIN, LOGGER

class GimdowConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Gimdow Lock."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._qr_code: str | None = None
        self.login_control = LoginControl()  # Initialize LoginControl
        self._available_devices = []  # Store available devices to present to the user

    async def async_step_user(self, user_input=None):
        """Handle the initial step for QR code login."""
        if user_input is not None:
            # Generate a QR code for the user to scan
            response = await self.hass.async_add_executor_job(self.login_control.qr_code)
            LOGGER.debug("QR code response = %s", response)
            if response.get("success", False):
                self._qr_code = response["result"]["qrcode"]
                img = _generate_qr_code(APP_QR_CODE_HEADER + self._qr_code)
                return self.async_show_form(
                    step_id="scan",
                    description_placeholders={"qr_code": img},
                )

        return self.async_show_form(step_id="user")

    async def async_step_scan(self, user_input=None):
        """Handle the step for scanning and validating the QR code."""
        # Check the login result by polling the Tuya API for the scanned QR code
        ret, info = await self.hass.async_add_executor_job(
            self.login_control.login_result, self._qr_code
        )
        LOGGER.debug("Login result = %s, info = %s", ret, info)

        if ret:
            # Successfully authenticated, fetch required data for creating CustomerApi
            client_id = self.login_control.client_id  # Get client ID from LoginControl
            user_code = self.login_control.user_code  # Get user code from LoginControl
            endpoint = info.get("endpoint")  # Get the endpoint from the login response

            # Proceed to fetch devices or other operations as needed
            self._available_devices = await self._fetch_devices()
            if not self._available_devices:
                return self.async_abort(reason="no_devices_found")

            # Save the client ID, user code, and other data to the config entry
            return await self.async_step_select_device(client_id, user_code, endpoint)

        return self.async_show_form(
            step_id="scan",
            errors={"base": "login_error"},
            description_placeholders={"qr_code": _generate_qr_code(APP_QR_CODE_HEADER + self._qr_code)},
        )

    async def async_step_select_device(self, client_id, user_code, endpoint, user_input=None):
        """Step to select a device from the available devices."""
        if user_input is not None:
            # Store selected device information and complete the setup
            selected_device_id = user_input["device_id"]
            selected_device = next((device for device in self._available_devices if device["device_id"] == selected_device_id), None)

            if selected_device:
                # Create entry with all the necessary information
                return self.async_create_entry(
                    title=selected_device["name"],
                    data={
                        "device_id": selected_device["device_id"],
                        "device_name": selected_device["name"],
                        "access_token": self.login_control.token_info.access_token,
                        "refresh_token": self.login_control.token_info.refresh_token,
                        "client_id": client_id,  # Save client ID dynamically
                        "user_code": user_code,  # Save user code dynamically
                        "endpoint": endpoint,  # Save endpoint dynamically
                    }
                )

        # Create a selection schema for devices
        devices_schema = vol.Schema(
            {
                vol.Required("device_id"): vol.In(
                    {device["device_id"]: device["name"] for device in self._available_devices}
                )
            }
        )

        return self.async_show_form(
            step_id="select_device",
            data_schema=devices_schema,
            description_placeholders={"devices": self._available_devices},
        )

    async def _fetch_devices(self):
        """Fetch the list of devices from the Tuya API using LoginControl."""
        response = await self.hass.async_add_executor_job(self.login_control.get_devices)
        if response.get("success", False):
            return response.get("result", [])
        return []
