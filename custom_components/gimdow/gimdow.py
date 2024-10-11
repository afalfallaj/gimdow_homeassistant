"""Support for Gimdow Lock devices."""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from tuya_sharing import CustomerDevice, Manager

from homeassistant.components.lock import LockEntity
from homeassistant.core import callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect

from .const import (
    DOMAIN,
    LOGGER,
    GIMDOW_DISCOVERY_NEW,
    GIMDOW_HA_SIGNAL_UPDATE_ENTITY,
)

LOCK_LOG_PRIORITY = {
    'lock_record': 5,
    'unlock_key': 4,
    'manual_lock': 3,
    'unlock_ble': 2,
    'unlock_phone_remote': 1,
}


class GimdowLock(LockEntity):
    """Representation of a Gimdow Lock."""

    _attr_has_entity_name = True

    def __init__(self, device: CustomerDevice, device_manager: Manager) -> None:
        """Initialize the Gimdow Lock."""
        self._device = device
        self._device_manager = device_manager
        self._attr_unique_id = f"gimdow.{device.id}"
        self._attr_name = device.name
        self._attr_is_locked = False
        self._lock_state_last_timestamp = None

    @property
    def available(self) -> bool:
        """Return if the lock is available."""
        return self._device.online

    @property
    def device_info(self) -> dict[str, Any]:
        """Return a device description for device registry."""
        return {
            "identifiers": {(DOMAIN, self._device.id)},
            "manufacturer": "Gimdow",
            "name": self._device.name,
            "model": self._device.product_name,
            "model_id": self._device.product_id,
        }

    @property
    def is_locked(self) -> bool:
        """Return true if the lock is locked."""
        return self._attr_is_locked

    def lock(self, **kwargs: Any) -> None:
        """Lock the device."""
        LOGGER.debug("Locking the Gimdow lock: %s", self._device.id)
        self._send_command(True)

    def unlock(self, **kwargs: Any) -> None:
        """Unlock the device."""
        LOGGER.debug("Unlocking the Gimdow lock: %s", self._device.id)
        self._send_command(False)

    def _send_command(self, state: bool) -> None:
        """Send the lock/unlock command to the device."""
        try:
            # Step 1: Request a password ticket
            ticket_response = self._device_manager.customer_api.post(
                f"/v1.0/smart-lock/devices/{self._device.id}/password-ticket"
            )

            tid = ticket_response["result"].get("ticket_id")
            if tid:
                # Step 2: Use the ticket to perform the lock/unlock operation
                operate_response = self._device_manager.customer_api.post(
                    f"/v1.0/smart-lock/devices/{self._device.id}/password-free/door-operate",
                    {"ticket_id": tid, "open": not state},
                )
                if operate_response.get("success"):
                    self._attr_is_locked = state
                    self.schedule_update_ha_state()
        except Exception as error:
            LOGGER.error("Failed to send lock command: %s", error)

    async def async_added_to_hass(self) -> None:
        """Call when entity is added to hass."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                f"{GIMDOW_HA_SIGNAL_UPDATE_ENTITY}_{self._device.id}",
                self.async_write_ha_state,
            )
        )

    @callback
    def update_device(self) -> None:
        """Update the lock status using device logs."""
        self._fetch_device_logs()

    def _fetch_device_logs(self) -> None:
        """Fetch the lock's device logs to determine the latest state."""
        try:
            now = datetime.utcnow()
            end_time = int(now.timestamp() * 1000)
            start_time = int((now - timedelta(days=7)).timestamp() * 1000)

            response = self._device_manager.customer_api.get(
                f"/v1.0/devices/{self._device.id}/logs?end_time={end_time}&start_time={start_time}&type=7"
            )

            if response.get("success"):
                log_entries = response["result"]["logs"]
                self._update_lock_state_from_logs(log_entries)
            else:
                LOGGER.error("Failed to fetch logs for device: %s", self._device.id)
        except Exception as error:
            LOGGER.error("Error fetching device logs: %s", error)

    def _update_lock_state_from_logs(self, logs: list[dict[str, Any]]) -> None:
        """Update lock state based on logs fetched from the API."""
        if not logs:
            LOGGER.warning("No logs found for device: %s", self._device.id)
            return

        latest_entry = None

        for log in logs:
            event_type = log.get("type", "")
            if event_type in LOCK_LOG_PRIORITY:
                if not latest_entry or LOCK_LOG_PRIORITY[event_type] > LOCK_LOG_PRIORITY[latest_entry["type"]]:
                    latest_entry = log

        if latest_entry:
            # Determine the lock state based on the latest log entry
            self._attr_is_locked = latest_entry["type"] in {"lock_record", "manual_lock"}
            self._lock_state_last_timestamp = latest_entry.get("time", "")
            LOGGER.info("Updated lock state for %s based on logs: %s", self._device.id, latest_entry)
            self.schedule_update_ha_state()
