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

        # 1. Attempt to get status directly
        response = self.openapi.get(f"/v1.0/devices/{self.device_id}/status")
        _LOGGER.debug("Status polling response: %s", response)
        
        if response.get("success", False):
            result = response.get("result", [])
            # Convert list of dicts to a dict for easier access
            # e.g. [{'code': 'lock_motor_state', 'value': True}] -> {'lock_motor_state': True}
            status = {item["code"]: item["value"] for item in result}
            
            # If we have valid status likely to be correct, return it
            # Note: Gimdow might use different codes. 
            # We will return the raw status dict to be processed by the entity.
            return status

        # 2. Fallback to logs if status failed
        _LOGGER.debug("Direct status unavailable, trying logs")
        
        current_time_ms = int(time.time() * 1000)
        start_time = current_time_ms - (7 * 24 * 60 * 60 * 1000) # Default to 7 days ago if first run
        
        if self._last_log_timestamp > 0:
             # Look back a bit further than last success to ensure no overlap overlap issues? 
             # Or just use the last timestamp. 
             start_time = self._last_log_timestamp

        payload = {
            "codes": "lock_record", # Filter for lock records
            "start_time": start_time,
            "end_time": current_time_ms,
            "size": 1 
        }
        
        # Searching mainly for the last event to determine state
        response = self.openapi.get(f"/v1.0/devices/{self.device_id}/logs", payload)
        
        if response.get("success", False):
            result = response.get("result", {})
            logs = result.get("logs", [])
            if logs:
                last_log = logs[0]
                self._last_log_timestamp = last_log.get("event_time", current_time_ms)
                # Attempt to parse lock state from the value
                # This depends heavily on what 'value' looks like in the log
                # For now, we return the log item as a pseudo-status
                # The entity will need to know how to handle this.
                return {"_log_fallback": last_log}

        raise UpdateFailed("Could not fetch status or logs from Tuya")

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
