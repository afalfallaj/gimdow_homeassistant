"""DataUpdateCoordinator for Gimdow Smart Lock."""
from __future__ import annotations

import logging
import time
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.exceptions import ConfigEntryAuthFailed
from tuya_connector import TuyaOpenAPI

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

SCAN_INTERVAL = timedelta(seconds=10)

class GimdowCoordinator(DataUpdateCoordinator):
    """Class to manage fetching Gimdow data."""

    def __init__(
        self,
        hass: HomeAssistant,
        openapi: TuyaOpenAPI,
        device_id: str,
    ) -> None:
        """Initialize."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=SCAN_INTERVAL,
        )
        self.openapi = openapi
        self.device_id = device_id
        self._last_log_timestamp = 0

    async def _async_update_data(self) -> dict[str, Any]:
        """Update data via Tuya API."""
        try:
            return await self.hass.async_add_executor_job(self._update_data)
        except Exception as err:
            _LOGGER.exception("Error updating data from Tuya")
            raise UpdateFailed(f"Error communicating with API: {err}") from err

    def _update_data(self) -> dict[str, Any]:
        """Synchronous update data method."""
        # Ensure connected before polling
        self.openapi.connect()
        
        # Send synch_method command as required by device to update logs
        _LOGGER.debug("Sending synch_method command...")
        self.openapi.post(
            f"/v1.0/iot-03/devices/{self.device_id}/commands",
            {
                "commands": [
                    {
                        "code": "synch_method",
                        "value": True
                    }
                ]
            }
        )

        # Priority: Check Logs first as status codes are unreliable for this device
        _LOGGER.debug("Polling logs for state...")
        
        current_time_ms = int(time.time() * 1000)
        # Look back 30 days by default to find the last event
        start_time = current_time_ms - (30 * 24 * 60 * 60 * 1000) 
        
        payload = {
            "codes": "lock_record,unlock_key,manual_lock,unlock_ble,unlock_phone_remote", 
            "start_time": start_time,
            "end_time": current_time_ms,
            "size": 20 # Fetch more to ensure we find a valid event
        }
        
        response = self.openapi.get(f"/v1.0/devices/{self.device_id}/logs", payload)
        
        if response.get("success", False):
            result = response.get("result", {})
            logs = result.get("logs", [])
            _LOGGER.debug("Log response: %s", logs)
            
            for log in logs:
                code = log.get("code")
                # Logic provided by user
                if code == 'lock_record':
                    return {"is_locked": True}
                elif code == 'unlock_key':
                    return {"is_locked": False}
                elif code == 'manual_lock':
                    return {"is_locked": True}
                elif code == 'unlock_ble':
                    return {"is_locked": False}
                elif code == 'unlock_phone_remote':
                    return {"is_locked": False}
        else:
             _LOGGER.warning("Failed to fetch logs: %s", response)

        # Fallback to status if no logs or log fetch failed
        _LOGGER.debug("No relevant logs found, trying direct status...")
        response = self.openapi.get(f"/v1.0/devices/{self.device_id}/status")
        
        if response.get("success", False):
            result = response.get("result", [])
            status = {item["code"]: item["value"] for item in result}
            # Try to determine state from status as a last resort
            if "lock_motor_state" in status:
                 return {"is_locked": bool(status["lock_motor_state"])}
            return status

        # If everything fails, return empty to indicate unknown or keep previous
        _LOGGER.warning("Could not determine state from logs or status")
        return {}

    async def async_unlock(self) -> None:
        """Unlock the door."""
        try:
            await self.hass.async_add_executor_job(self._operate_door, True)
        except Exception as err:
            _LOGGER.error("Unlock failed: %s", err)
            raise
        await self.async_request_refresh()

    async def async_lock(self) -> None:
        """Lock the door."""
        try:
            await self.hass.async_add_executor_job(self._operate_door, False)
        except Exception as err:
            _LOGGER.error("Lock failed: %s", err)
            raise
        await self.async_request_refresh()

    def _operate_door(self, open_door: bool) -> None:
        """Operate the door (Lock/Unlock) sequence."""
        # 0. Ensure connected (matching original code behavior)
        self.openapi.connect()

        # 1. Get Password Ticket
        # POST /v1.0/smart-lock/devices/{device_id}/password-ticket
        ticket_resp = self.openapi.post(f"/v1.0/smart-lock/devices/{self.device_id}/password-ticket")
        
        if not ticket_resp.get("success", False):
             _LOGGER.error("Failed to get ticket. Response: %s", ticket_resp)
             raise UpdateFailed(f"Failed to get password ticket: {ticket_resp.get('msg')}")
        
        result = ticket_resp.get("result")
        if not result or "ticket_id" not in result:
             _LOGGER.error("Ticket response missing result or ticket_id: %s", ticket_resp)
             raise UpdateFailed("Failed to get password ticket: missing ticket_id in response")
             
        ticket_id = result["ticket_id"]

        # 2. Operate
        # POST /v1.0/smart-lock/devices/{device_id}/password-free/door-operate
        payload = {
            "ticket_id": ticket_id,
            "open": open_door
        }
        op_resp = self.openapi.post(f"/v1.0/smart-lock/devices/{self.device_id}/password-free/door-operate", payload)
        
        if not op_resp.get("success", False):
             _LOGGER.error("Operation failed. Response: %s", op_resp)
             raise UpdateFailed(f"Failed to operate door: {op_resp.get('msg')}")
        
        _LOGGER.info("Door operation %s successful", "unlock" if open_door else "lock")
