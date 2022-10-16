"""Component to interface with locks that can be controlled remotely."""
from __future__ import annotations

import logging

from .gimdow import GimdowInstance
import voluptuous as vol

from pprint import pformat
import functools as ft

# Import the device class from the component that you want to support
import homeassistant.helpers.config_validation as cv 
from homeassistant.components.lock import (PLATFORM_SCHEMA, LockEntity, LockEntityDescription)
from homeassistant.const import CONF_NAME, CONF_DEVICE_ID, CONF_URL, CONF_CLIENT_ID, CONF_API_KEY
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME): cv.string,
    vol.Required(CONF_DEVICE_ID): cv.string,
    vol.Required(CONF_URL): cv.string,
    vol.Required(CONF_CLIENT_ID): cv.string,
    vol.Required(CONF_API_KEY): cv.string,
})


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the Gimdow Lock platform."""
    # Add devices
    _LOGGER.info(pformat(config))
    
    lock = {
        "name": config[CONF_NAME],
        "device_id": config[CONF_DEVICE_ID],
        "tuya_endpoint": config[CONF_URL],
        "access_id": config[CONF_CLIENT_ID],
        "access_key": config[CONF_API_KEY],
    }
    
    add_entities([GimdowLock(lock)], True)

class GimdowLock(LockEntity):

    def __init__(self, lock) -> None:
        """Initialize an GimdowLock."""
        _LOGGER.info(pformat(lock))
        self._lock = GimdowInstance(lock)
        self._name = lock["name"]
        entity_description: LockEntityDescription
        self._changed_by: str | None = None
        self._is_locked: bool | None = None
        self._state = None

    @property
    def name(self) -> str:
        """Return the display name of this lock."""
        return self._name

    @property
    def changed_by(self) -> str | None:
        """Last change triggered by."""
        return self._changed_by

    @property
    def is_locked(self) -> bool | None:
        """Return true if the lock is locked."""
        return self._is_locked

    def lock(self, **kwargs: Any) -> None:
        """lock the lock."""
        if self._lock.set_lock(False):
            self._is_locked = True

    async def async_lock(self, **kwargs: Any) -> None:
        """lock the lock."""
        await self.hass.async_add_executor_job(ft.partial(self.lock, **kwargs))

    def unlock(self, **kwargs: Any) -> None:
        """Unlock the lock."""
        if self._lock.set_lock(True):
            self._is_locked = False

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the lock."""
        await self.hass.async_add_executor_job(ft.partial(self.unlock, **kwargs))

    def update(self) -> None:
        """Fetch new state data for this lock.
        This is the only method that should fetch new data for Home Assistant.
        """
        self._lock.update()
        self._is_locked = self._lock.is_locked