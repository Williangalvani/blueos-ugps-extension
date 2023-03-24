import math
from typing import Any, Optional

import requests
from loguru import logger


class Mavlink2RestBase:
    """
    Responsible for interfacing with Mavlink2Rest
    This class is supposed to be usecase independant.

    Exception handling: All exceptions are caught and reported over logging. Severity "error", as they should not happen.
    """

    def __init__(self, host: str = "http://127.0.0.1/mavlink2rest", vehicle: int = 1, component: int = 220, get_vehicle: int = 1, get_component: int = 1):
        # store mavlink-url, vehicle and component to access telemetry data from
        self.host = host
        # default own role in mavlink protocol (for sending data)
        self.vehicle = vehicle
        self.component = component  # default for post
        # default for acquiring data (e.g. from flight controller)
        self.get_vehicle = get_vehicle
        self.get_component = get_component

    def get(self, path: str):
        """
        Helper to request with GET from mavlink2rest
        Returns the response object or None on failure
        """
        full_url = self.host + path
        logger.debug(f"Request url: {full_url}")
        response = None
        try:
            response = requests.get(full_url)
            if response.status_code == 200:
                logger.debug(f"Got response: {response.text}")
                if response.text == "None":
                    return None
                return response.json()
            else:
                logger.error(f"Got HTTP Error: {response.status_code} {response.reason} {response.text}")
                return None
        except Exception as e:
            logger.error(f"Got exception: {e}")
            return None

    def get_message(self, path: str, vehicle: Optional[int] = None, component: Optional[int] = None) -> Optional[str]:
        """
        Get mavlink data from mavlink2rest
        Uses initialised get_vehicle and get_component as defaults, unless overridden.
        Example: get_message('/VFR_HUD')
        Returns the data or None on failure
        """
        vehicle = vehicle or self.get_vehicle
        component = component or self.get_component
        message_path = f"/mavlink/vehicles/{vehicle}/components/{component}/messages" + path
        return self.get(message_path)

    def get_float(self, path: str, vehicle: Optional[int] = None, component: Optional[int] = None) -> float:
        """
        Get mavlink data from mavlink2rest.
        Uses initialised get_vehicle and get_component as defaults, unless overridden.
        Example: get_float('/VFR_HUD')
        Returns the data as a float (nan on failure)
        """
        response = self.get_message(path, vehicle, component)
        try:
            result = float(response)
        except Exception:
            result = float("nan")
        return result

    def post(self, path: str, json: object) -> bool:
        """
        Helper to request with POST from mavlink2rest
        Returns if request was successful
        """
        full_url = self.host + path
        logger.debug(f"Request url: {full_url} json: {json}")
        response = None
        try:
            response = requests.post(full_url, json=json)
            if response.status_code == 200:
                logger.debug(f"Got response: {response.reason}")
                return True
            else:
                logger.error(f"Got HTTP Error: {response.status_code} {response.reason} {response.text}")
                return False
        except Exception as e:
            logger.error(f"Got exception: {e}")
            return False

    def ensure_message_frequency(self, message_name: str, frequency: int) -> bool:
        """
        Makes sure that a mavlink message is being received at least at "frequency" Hertz
        Returns true if successful, false otherwise
        """
        msg_ids = {
            "VFR_HUD": 74,
            "SCALED_PRESSURE2": 137
        }
        message_name = message_name.upper()

        logger.info(f"Trying to set message frequency of {message_name} to {frequency} Hz")

        previous_frequency = self.get_float(f"/{message_name}/message_information/frequency")
        if math.isnan(previous_frequency):
            previous_frequency = 0.0

        # load message template from mavlink2rest helper
        command = self.get("/helper/mavlink?name=COMMAND_LONG")
        if command is None:
            return False

        try:
            msg_id = msg_ids[message_name]
            # msg_id = getattr(mavutil.mavlink, 'MAVLINK_MSG_ID_' + message_name)
        except Exception:
            logger.error(f"{message_name} not in internal LUT")
            return False

        command["message"]["command"] = {"type": "MAV_CMD_SET_MESSAGE_INTERVAL"}
        command["message"]["param1"] = msg_id
        command["message"]["param2"] = int(1000 / frequency)

        success = self.post("/mavlink", json=command)
        if success:
            logger.info(f"Successfully set message frequency of {message_name} to {frequency} Hz, was {previous_frequency} Hz")
        return success

    def set_param(self, param_name, param_type, param_value):
        """
        Sets parameter "param_name" of type param_type to value "value" in the autpilot
        Returns True if succesful, False otherwise
        """
        payload = self.get("/helper/mavlink?name=PARAM_SET")
        if payload is None:
            return False
        try:
            for i, char in enumerate(param_name):
                payload["message"]["param_id"][i] = char

            payload["message"]["param_type"] = {"type": param_type}
            payload["message"]["param_value"] = param_value

            success = self.post("/mavlink", json=payload)
            if success:
                logger.info(f"Successfully set parameter {param_name} to {param_value}")
            return success
        except Exception as error:
            logger.warning(f"Error setting parameter '{param_name}': {error}")
            return False


class Mavlink2RestHelper(Mavlink2RestBase):
    def get_depth(self):
        return -self.get_float('/VFR_HUD/message/alt')

    def get_orientation(self):
        return self.get_float('/VFR_HUD/message/heading')

    def get_temperature(self):
        return self.get_float('/SCALED_PRESSURE2/message/temperature')/100.0

    def send_gps_input(self, in_json: object, gps_id: int = 0):
        """
        Forwards the locator(ROV) position to mavproxy's GPSInput module
        """
        out_json = self.get("/helper/mavlink?name=GPS_INPUT")

        try:
            out_json["header"]["system_id"] = self.vehicle
            out_json["header"]["component_id"] = self.component
            out_json["message"]["gps_id"] = gps_id
            out_json["message"]['lat'] = math.floor(in_json['lat'] * 1e7)
            out_json["message"]['lon'] = math.floor(in_json['lon'] * 1e7)
            # fix_quality of demo.waterlinked.com is 1
            out_json["message"]['fix_type'] = 0 if in_json['fix_quality'] == 0 else 3
            out_json["message"]['hdop'] = 65535.0 if in_json['hdop'] == -1 else in_json['hdop']
            out_json["message"]['vdop'] = 65535.0
            out_json["message"]['satellites_visible'] = max(in_json['numsats'], 0)
            # GPS orientation is forwarded from the received heading /VFR_HUD/message/heading
            if in_json['orientation'] == -1:
                out_json["message"]['yaw'] = 0  # invalid
            elif in_json['orientation'] == 0:
                out_json["message"]['yaw'] = 36000  # remap 0 -> 360
            else:
                out_json["message"]['yaw'] = math.floor(in_json['orientation'] * 100)  # default
            out_json["message"]['ignore_flags']['bits'] = 1 | 4 | 8 | 16 | 32 | 64 | 128
        except Exception as e:
            logger.error(f"Parsing locator position not successfull. {e}")
            return

        self.post("/mavlink", out_json)
