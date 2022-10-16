from tuya_connector import (
	TuyaOpenAPI
)

class GimdowInstance:
    def __init__(self, lock: dict) -> None:
        self._device_id = lock["device_id"]
        self._openapi = TuyaOpenAPI(lock["tuya_endpoint"], lock["access_id"], lock["access_key"])
        self.is_locked:bool | None = None
        # self._connected = None
    
    def set_lock(self,state: bool):
        self._openapi.connect()

        # Call any API from Tuya
        ticketResponse = self._openapi.post(
            f"/v1.0/smart-lock/devices/{self._device_id}/password-ticket")
        if (ticketResponse.get("result")):
            tid = ticketResponse.get("result").get("ticket_id")
            if tid:
                operateResponse = self._openapi.post(
                    f"/v1.0/smart-lock/devices/{self._device_id}/password-free/door-operate",
                    {"ticket_id": tid, "open": state})
                if operateResponse.get("success") == True if True else False:
                    self.is_locked = state
                    return self.is_locked
    def update(self):
        self._openapi.connect()
        status_result= self._openapi.get(
            f"/v1.0/iot-03/devices/{self._device_id}/status")

        status_list = status_result.get("result")

        if status_list:
            lock_motor_state = [status for status in status_list if status.get("code") == 'lock_motor_state']
            if len(lock_motor_state):
                self.is_locked = not lock_motor_state[0].get("value")