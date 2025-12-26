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
        # Data format is determined by coordinator.
        # It can be a dict of status codes or a log entry.
        
        data = self.coordinator.data
        if not data:
            return None
            
        # Check for log fallback
        if "_log_fallback" in data:
            log_item = data["_log_fallback"]
            code = log_item.get("code", "")
            
            if code in ["lock_record", "manual_lock"]:
                return True
            if code in ["unlock_key", "unlock_ble", "unlock_phone_remote"]:
                return False
            
            val = str(log_item.get("value", "")).lower()
            if "unlock" in val or "open" in val:
                 return False
            if "lock" in val or "close" in val:
                 return True
            return None
            
        # Standard status check
        for key, value in data.items():
            if key in ["lock_motor_state", "lock_state", "door_state"]:
                if isinstance(value, bool):
                     return value
        
        return None

    async def async_lock(self, **kwargs: Any) -> None:
        """Lock the lock."""
        await self.coordinator.async_lock()

    async def async_unlock(self, **kwargs: Any) -> None:
        """Unlock the lock."""
        await self.coordinator.async_unlock()