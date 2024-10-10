"""Handle the connection and control logic for Gimdow Lock using Tuya APIs."""
from tuya_sharing.customerapi import CustomerApi, CustomerTokenInfo  # Corrected import statement
import logging
import time

_LOGGER = logging.getLogger(__name__)

class GimdowInstance:
    """Gimdow Lock instance to handle Tuya API interaction."""

    def __init__(self, lock: dict) -> None:
        """Initialize with Tuya API credentials and device ID."""
        self._device_id = lock["device_id"]

        # Use the values provided from LoginControl (from config entry)
        client_id = lock["client_id"]
        user_code = lock["user_code"]
        endpoint = lock["endpoint"]

        # Create a CustomerTokenInfo instance with the token information
        token_info = CustomerTokenInfo({
            "access_token": lock["access_token"],
            "refresh_token": lock["refresh_token"],
            "t": int(time.time() * 1000),  # Current timestamp in milliseconds
            "expire_time": 7200,  # Placeholder value, adjust as needed
            "uid": lock.get("uid", "")
        })

        # Create a CustomerApi instance using dynamic values
        self.customer_api = CustomerApi(
            token_info=token_info,
            client_id=client_id,  # Dynamically obtained from LoginControl
            user_code=user_code,  # Dynamically obtained from LoginControl
            end_point=endpoint,  # Dynamically obtained from login response
            listener=None  # No token listener is required for this use case
        )
        self.is_locked: bool | None = None
        self._latest_update = int(time.time() * 1000)  # Store the latest update timestamp in milliseconds

    def set_lock(self, state: bool) -> bool:
        """Set the lock state to locked or unlocked using a ticket."""
        _LOGGER.info("Setting lock state to: %s", "Unlock" if state else "Lock")

        # Step 1: Get a password ticket for the lock operation
        ticket_response = self.customer_api.post(
            f"/v1.0/smart-lock/devices/{self._device_id}/password-ticket"
        )
        _LOGGER.debug("Ticket response: %s", ticket_response)

        # Check if ticket retrieval was successful
        if ticket_response and ticket_response.get("success"):
            # Step 2: Extract the ticket ID
            tid = ticket_response.get("result", {}).get("ticket_id")
            _LOGGER.info("Obtained ticket ID: %s", tid)
            if tid:
                # Step 3: Use the ticket to operate the lock
                operate_response = self.customer_api.post(
                    f"/v1.0/smart-lock/devices/{self._device_id}/password-free/door-operate",
                    body={"ticket_id": tid, "open": state}
                )
                _LOGGER.debug("Operate response: %s", operate_response)

                # Check if the operation was successful
                if operate_response and operate_response.get("success"):
                    # Step 4: Update the internal lock state
                    self.is_locked = not state  # `state` should be False for locking and True for unlocking
                    _LOGGER.info("Lock state set successfully: %s", "Locked" if not state else "Unlocked")
                    return True

        # If any step fails, log an error and return False
        _LOGGER.error("Failed to set the lock state. State: %s", "Unlock" if state else "Lock")
        return False

    def update(self) -> None:
        """Update the lock state by querying the device logs."""
        _LOGGER.info("Updating lock state with device synchronization.")

        # Step 1: Call the `synch_method` before querying logs to ensure data is up-to-date
        sync_response = self.customer_api.post(
            f"/v1.0/iot-03/devices/{self._device_id}/commands",
            body={
                "commands": [
                    {
                        "code": "synch_method",
                        "value": True  # Synchronize the device with the cloud
                    }
                ]
            }
        )
        _LOGGER.debug("Device synchronization response: %s", sync_response)

        # Check if synchronization was successful
        if not sync_response or not sync_response.get("success"):
            _LOGGER.error("Failed to synchronize the device before updating status.")
            return

        # Step 2: Set up the time window for fetching logs
        start_time = self._latest_update
        end_time = int(time.time() * 1000)  # Current time in milliseconds

        # Fetch the device logs from the Tuya API
        path = f"/v1.0/devices/{self._device_id}/logs?end_time={end_time}&start_time={start_time}&type=7"
        response = self.customer_api.get(path)
        _LOGGER.debug("Device logs response: %s", response)

        if response and response.get("success"):
            log_list = response.get("result", {}).get("logs", [])

            # Priority levels for different types of events
            priority = {
                'lock_record': 5,
                'unlock_key': 4,
                'manual_lock': 3,
                'unlock_ble': 2,
                'unlock_phone_remote': 1
            }

            # Track the highest priority event
            highest_priority = 0
            final_state = None

            # Iterate through the logs to find the most important state update
            for log in log_list:
                log_code = log.get("code")
                _LOGGER.debug(f"Processing log code: {log_code}, value: {log.get('value')}")

                if log_code in priority:
                    current_priority = priority[log_code]
                    _LOGGER.debug(f"Current priority: {current_priority}, Highest priority so far: {highest_priority}")

                    if current_priority >= highest_priority:
                        highest_priority = current_priority
                        if log_code in ['lock_record', 'manual_lock']:
                            final_state = True  # Lock is engaged
                        elif log_code in ['unlock_key', 'unlock_ble', 'unlock_phone_remote']:
                            final_state = False  # Lock is disengaged

            # Update the internal lock state based on the highest-priority event found
            if final_state is not None:
                self.is_locked = final_state
                self._latest_update = end_time  # Update the timestamp to the latest
                _LOGGER.info(f"Updated lock state to: {'Locked' if final_state else 'Unlocked'} based on highest priority event: {highest_priority}")
        else:
            _LOGGER.error("Failed to update lock state. Could not fetch device logs.")
