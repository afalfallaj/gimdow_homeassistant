from tuya_connector import (
	TuyaOpenAPI
)
import time  

class GimdowInstance:
    def __init__(self, lock: dict) -> None:
        self._device_id = lock["device_id"]
        self._openapi = TuyaOpenAPI(lock["tuya_endpoint"], lock["access_id"], lock["access_key"])
        self.is_locked:bool | None = None
        self._latest_update:int = self.get_timestamp()
    
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
        start_time= self._latest_update
        end_time = self.get_timestamp()

        self._openapi.connect()
        query_result= self._openapi.get(
            f"/v1.0/devices/{self._device_id}/logs?end_time={end_time}&start_time={start_time}&type=7")

        query_list = query_result.get("result")

        if query_list.get("logs"):
            for logs in query_list.get("logs"):
                if logs.get("code") == 'lock_motor_state':
                    self.is_locked = not logs.get("value")
                    break
                elif logs.get("code") == 'lock_record':
                    self.is_locked = True
                    break
                elif logs.get("code") == 'unlock_key':
                    self.is_locked = False
                    break
                elif logs.get("code") == 'manual_lock':
                    self.is_locked = True
                    break
                elif logs.get("code") == 'unlock_ble':
                    self.is_locked = False
                    break
                elif logs.get("code") == 'unlock_phone_remote':
                    self.is_locked = False
                    break
        else:
            #if no logs found then get results from 30 days ago
            self._latest_update = start_time - 2592000000
    def get_timestamp(self):
        return int(time.time() *1000)