"""Lock platform for Gimdow integration."""
from __future__ import annotations

from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.helpers.device_registry import DeviceInfo

from .const import DOMAIN
from .coordinator import GimdowCoordinator

async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the Gimdow Lock platform."""
    coordinator: GimdowCoordinator = hass.data[DOMAIN][entry.entry_id]
    
    async_add_entities([GimdowLock(coordinator, entry.entry_id)])


class GimdowLock(CoordinatorEntity[GimdowCoordinator], LockEntity):
    """Gimdow Lock Entity."""

    def __init__(self, coordinator: GimdowCoordinator, entry_id: str) -> None:
        """Initialize the lock."""
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.device_id}_lock"
        self._attr_has_entity_name = True
        self._attr_name = None 
        self._entry_id = entry_id
        
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, coordinator.device_id)},
            name="Gimdow Smart Lock",
            manufacturer="Tuya/Gimdow",
            model="Gimdow Lock",
        )

    @property
    def is_locked(self) -> bool | None:
        """Return true if lock is locked."""
        data = self.coordinator.data
        if not data:
            return None
        
        # State determined by coordinator from logs/status
        return data.get("is_locked")

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the lock."""
        await self.coordinator.async_lock()

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the lock."""
        await self.coordinator.async_unlock()