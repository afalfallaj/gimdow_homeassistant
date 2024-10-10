"""Component to interface with locks that can be controlled remotely."""
from __future__ import annotations

import logging
from typing import Any
from .gimdow import GimdowInstance
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.components.lock import LockEntity, PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME, CONF_DEVICE_ID
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

_LOGGER = logging.getLogger(__name__)

# Validation of the user's configuration (if using static config, which we're not currently using)
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Optional(CONF_NAME): cv.string,
    vol.Required(CONF_DEVICE_ID): cv.string,
})


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None
) -> None:
    """Set up the Gimdow Lock platform."""
    lock_config = discovery_info if discovery_info else config
    gimdow_lock = GimdowLock(lock_config)
    add_entities([gimdow_lock], True)


class GimdowLock(LockEntity):
    """Representation of a Gimdow Lock."""

    def __init__(self, lock: dict) -> None:
        """Initialize the lock."""
        _LOGGER.info("Initializing Gimdow Lock: %s", lock)
        self._lock = GimdowInstance(lock)
        self._name = lock.get("device_name", "Gimdow Lock")
        self._is_locked = None

    @property
    def name(self) -> str:
        """Return the name of the lock."""
        return self._name

    @property
    def is_locked(self) -> bool | None:
        """Return true if the lock is locked."""
        return self._is_locked

    def lock(self, **kwargs: Any) -> None:
        """Lock the lock."""
        _LOGGER.info("Locking the lock.")
        if self._lock.set_lock(False):
            self._is_locked = True
        else:
            _LOGGER.error("Failed to lock the device.")

    def unlock(self, **kwargs: Any) -> None:
        """Unlock the lock."""
        _LOGGER.info("Unlocking the lock.")
        if self._lock.set_lock(True):
            self._is_locked = False
        else:
            _LOGGER.error("Failed to unlock the device.")

    def update(self) -> None:
        """Fetch new state data for this lock."""
        _LOGGER.info("Updating lock state.")
        self._lock.update()
        self._is_locked = self._lock.is_locked
