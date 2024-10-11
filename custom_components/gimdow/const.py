"""Constants for the Gimdow Lock integration."""

import logging

from homeassistant.const import Platform

# Define the domain of the integration
DOMAIN = "gimdow"
LOGGER = logging.getLogger(__package__)

# Configuration keys
CONF_ENDPOINT = "endpoint"
CONF_TERMINAL_ID = "terminal_id"
CONF_TOKEN_INFO = "token_info"
CONF_USER_CODE = "user_code"

# Authentication details
GIMDOW_CLIENT_ID = "HA_3y9q4ak7g4ephrvke"  # Example client ID for Gimdow
GIMDOW_SCHEMA = "haauthorize"

# Signal and discovery constants
GIMDOW_DISCOVERY_NEW = "gimdow_discovery_new"
GIMDOW_HA_SIGNAL_UPDATE_ENTITY = "gimdow_entry_update"

# Response fields for login flow
GIMDOW_RESPONSE_CODE = "code"
GIMDOW_RESPONSE_MSG = "msg"
GIMDOW_RESPONSE_QR_CODE = "qrcode"
GIMDOW_RESPONSE_RESULT = "result"
GIMDOW_RESPONSE_SUCCESS = "success"

# Supported platforms for the Gimdow Lock integration
PLATFORMS = [Platform.LOCK]
