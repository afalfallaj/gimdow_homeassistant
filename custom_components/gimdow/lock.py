"""Support for Gimdow Lock platform."""
from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HomeAssistantTuyaData
from .gimdow import GimdowLock
from .const import DOMAIN, LOGGER


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Gimdow Lock based on a config entry."""
    hass_data: HomeAssistantTuyaData = hass.data[DOMAIN][entry.entry_id]

    entities: list[GimdowLock] = []
    for device in hass_data.manager.device_map.values():
        if device.category in {"jtmspro", "lock"}:  # Categories for locks
            LOGGER.debug("Setting up Gimdow Lock: %s", device.id)
            entities.append(GimdowLock(device, hass_data.manager))

    if entities:
        async_add_entities(entities)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload Gimdow Lock entry."""
    return True
