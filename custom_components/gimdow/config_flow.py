"""Config flow for Gimdow Lock integration."""
from homeassistant import config_entries
import voluptuous as vol
from tuya_sharing import LoginControl
import logging
from io import BytesIO
import base64

# Import the constants from const.py
from .const import DOMAIN, LOGGER, CONF_USER_CODE, CONF_CLIENT_ID, CONF_SCHEMA

APP_QR_CODE_HEADER = "tuyaSmart--qrLogin?token="

_LOGGER = logging.getLogger(__name__)

class GimdowConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Gimdow Lock."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._qr_code: str | None = None
        self.login_control = LoginControl()  # Initialize LoginControl
        self._available_devices = []  # Store available devices to present to the user
        self.user_code = None  # Placeholder for user_code
        self.token_info = {}  # Placeholder for token information

    async def async_step_user(self, user_input=None):
        """Handle the initial step for QR code login."""
        errors = {}
        if user_input is not None:
            # Store the user_code provided by the user
            self.user_code = user_input.get(CONF_USER_CODE)

            # Generate a QR code for the user to scan using constants for client_id and schema
            response = await self.hass.async_add_executor_job(
                self.login_control.qr_code,
                CONF_CLIENT_ID,  # Use constant from const.py
                CONF_SCHEMA,     # Use constant from const.py
                self.user_code
            )
            _LOGGER.debug("QR code response: %s", response)

            if response.get("success", False):
                self._qr_code = response["result"]["qrcode"]
                _LOGGER.info("Generated QR Code: %s", self._qr_code)
                
                # Generate the QR code image
                qr_image = self._generate_qr_code(APP_QR_CODE_HEADER + self._qr_code)
                _LOGGER.debug("Generated QR Code Image: %s", qr_image)

                # Display the form with the QR code
                return self.async_show_form(
                    step_id="scan",
                    description_placeholders={
                        "qr_code": qr_image
                    },
                )
            else:
                errors["base"] = "qr_code_error"
                _LOGGER.error("Failed to generate QR code: %s", response.get("msg"))

        # Show a form asking for user_code if not provided yet
        data_schema = vol.Schema(
            {
                vol.Required(CONF_USER_CODE, default=self.user_code or ""): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors
        )

    async def async_step_scan(self, user_input=None):
        """Handle the step for scanning and validating the QR code."""
        # Call the login_result method to check the result of the QR code scanning
        ret, info = await self.hass.async_add_executor_job(
            self.login_control.login_result, self._qr_code, CONF_CLIENT_ID, self.user_code
        )
        _LOGGER.debug("Login result = %s, info = %s", ret, info)

        if ret:
            # Successfully authenticated, store the token information
            self.token_info = {
                "access_token": info.get("access_token"),
                "refresh_token": info.get("refresh_token"),
                "t": info.get("t"),
                "expire_time": info.get("expire_time"),
                "uid": info.get("uid")
            }
            endpoint = info.get("endpoint")

            # Fetch the list of devices
            self._available_devices = await self._fetch_devices()
            if not self._available_devices:
                return self.async_abort(reason="no_devices_found")

            # Proceed to the device selection step
            return await self.async_step_select_device(endpoint)

        # If the login fails, display an error message and regenerate the QR code
        errors = {"base": "login_error"}
        _LOGGER.error("Failed to log in with QR code: %s", info.get("msg"))

        return self.async_show_form(
            step_id="scan",
            errors=errors,
            description_placeholders={
                "qr_code": self._generate_qr_code(APP_QR_CODE_HEADER + self._qr_code),
            },
        )

    async def async_step_select_device(self, endpoint, user_input=None):
        """Step to select a device from the available devices."""
        if user_input is not None:
            # Store selected device information and complete the setup
            selected_device_id = user_input["device_id"]
            selected_device = next((device for device in self._available_devices if device["device_id"] == selected_device_id), None)

            if selected_device:
                return self.async_create_entry(
                    title=selected_device["name"],
                    data={
                        "device_id": selected_device["device_id"],
                        "device_name": selected_device["name"],
                        "access_token": self.token_info["access_token"],  # Use token_info directly
                        "refresh_token": self.token_info["refresh_token"],  # Use token_info directly
                        "client_id": CONF_CLIENT_ID,  # Use constant client ID
                        "user_code": self.user_code,  # Save user code dynamically
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

    def _generate_qr_code(self, data: str) -> str:
        """Generate a base64 PNG string representing QR Code image of the given data."""
        import pyqrcode  # Ensure `pyqrcode` is installed

        qr_code = pyqrcode.create(data)
        with BytesIO() as buffer:
            qr_code.svg(file=buffer, scale=4)  # Create an SVG format of the QR code
            svg_content = buffer.getvalue().decode("utf-8")

            # Convert SVG content to a base64 string to be displayed
            svg_base64 = base64.b64encode(svg_content.encode("utf-8")).decode("utf-8")
            return f"data:image/svg+xml;base64,{svg_base64}"
