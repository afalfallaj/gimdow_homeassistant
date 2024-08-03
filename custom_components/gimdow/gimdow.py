import time

from tuya_connector import TuyaOpenAPI


class GimdowInstance:
    def __init__(self, lock: dict) -> None:
        self._device_id = lock["device_id"]
        self._openapi = TuyaOpenAPI(
            lock["tuya_endpoint"], lock["access_id"], lock["access_key"]
        )
        self.is_locked: bool | None = None
        self._latest_update: int = self.get_timestamp()
        self._battery_state: str | None = None

    def set_lock(self, state: bool):
        self._openapi.connect()

        # Call any API from Tuya
        ticketResponse = self._openapi.post(
            f"/v1.0/smart-lock/devices/{self._device_id}/password-ticket"
        )
        if ticketResponse.get("result"):
            tid = ticketResponse.get("result").get("ticket_id")
            if tid:
                operateResponse = self._openapi.post(
                    f"/v1.0/smart-lock/devices/{self._device_id}/password-free/door-operate",
                    {"ticket_id": tid, "open": state},
                )
                if operateResponse.get("success") == True if True else False:
                    self.is_locked = state
                    return self.is_locked

    def update(self):
        start_time = self._latest_update
        end_time = self.get_timestamp()

        self._openapi.connect()
        query_sync = self._openapi.post(
            f"/v1.0/iot-03/devices/{self._device_id}/commands",
            {"commands": [{"code": "synch_method", "value": True}]},
        )
        query_result = self._openapi.get(
            f"/v1.0/devices/{self._device_id}/logs?codes=lock_record,unlock_key,manual_lock,unlock_ble,unlock_phone_remote&end_time={end_time}&query_type=1&size=5&start_time={start_time}&type=7"
        )

        query_list = query_result.get("result")

        if query_list.get("logs"):
            for logs in query_list.get("logs"):
                if logs.get("code") == "lock_record":
                    self.is_locked = True
                    break
                elif logs.get("code") == "unlock_key":
                    self.is_locked = False
                    break
                elif logs.get("code") == "manual_lock":
                    self.is_locked = True
                    break
                elif logs.get("code") == "unlock_ble":
                    self.is_locked = False
                    break
                elif logs.get("code") == "unlock_phone_remote":
                    self.is_locked = False
                    break
        else:
            # if no logs found then get results from 30 days ago
            self._latest_update = start_time - 2592000000

        battery_result = self._openapi.get(
            f"/v1.0/devices/{self._device_id}/shadow/properties?codes=battery_state"
        )
        if battery_result.get("result"):
            self._battery_state = (
                battery_result.get("result", {}).get("properties", [{}])[0].get("value")
            )
        else:
            self._battery_state = "unknown"

    def get_timestamp(self):
        return int(time.time() * 1000)

    def battery_state(self):
        return self._battery_state
