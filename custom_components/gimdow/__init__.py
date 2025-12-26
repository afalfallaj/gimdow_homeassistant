"""The Gimdow Smart Lock integration."""
from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady

from tuya_iot import TuyaOpenAPI

from .const import (
    DOMAIN,
    CONF_ACCESS_ID,
    CONF_ACCESS_SECRET,
    CONF_ENDPOINT,
    CONF_DEVICE_ID
)
from .coordinator import GimdowCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.LOCK]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Gimdow from a config entry."""
    
    access_id = entry.data[CONF_ACCESS_ID]
    access_secret = entry.data[CONF_ACCESS_SECRET]
    endpoint = entry.data[CONF_ENDPOINT]
    device_id = entry.data[CONF_DEVICE_ID]

    # Initialize Tuya OpenAPI
    openapi = TuyaOpenAPI(endpoint, access_id, access_secret)
    
    # Attempt to connect to verify/refresh token
    # We do this in the executor
    try:
        response = await hass.async_add_executor_job(openapi.connect)
    except Exception as err:
        raise ConfigEntryNotReady(f"Failed to connect to Tuya: {err}") from err
    
    if not response.get("success", False):
        raise ConfigEntryNotReady(f"Tuya authentication failed: {response.get('msg')}")

    # Initialize Coordinator
    coordinator = GimdowCoordinator(hass, openapi, device_id)
    
    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
