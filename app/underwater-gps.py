#!/usr/bin/python

import time
import socket
import json
import argparse
import requests
from datetime import datetime
from os import system
import operator
import urllib.request, urllib.error, urllib.parse
from math import floor
from functools import reduce

STATUS_REPORT_URL = "http://127.0.0.1:2770/report_service_status"
MAVLINK2REST_URL = "http://host.docker.internal/mavlink2rest"

# holds the last status so we dont flood it
last_status = ""

# Nmea messages templates
# https://www.trimble.com/oem_receiverhelp/v4.44/en/NMEA-0183messages_GGA.html
gpgga = ("$GPGGA,"                                    # Message ID
       + "{hours:02d}{minutes:02d}{seconds:02.4f},"   # UTC Time
       + "{lat:02.0f}{latmin:02.6f},"                 # Latitude (degrees + minutes)
       + "{latdir},"                                  # Latitude direction (N/S)
       + "{lon:03.0f}{lonmin:02.6},"                  # Longitude (degrees + minutes)
       + "{londir},"                                  # Longitude direction (W/E)
       + "1,"                                         # Fix? (0-5)
       + "06,"                                        # Number of Satellites
       + "1.2,"                                       # HDOP
       + "0,"                                         # MSL altitude
       + "M,"                                         # MSL altitude unit (Meters)
       + "0,"                                         # Geoid separation
       + "M,"                                         # Geoid separation unit (Meters)
       + "00,"                                        # Age of differential GPS data, N/A
       + "0000"                                       # Age of differential GPS data, N/A
       + "*")                                         # Checksum

# https://www.trimble.com/oem_receiverhelp/v4.44/en/NMEA-0183messages_RMC.html
gprmc = ("$GPRMC,"                                  # Message ID
       + "{hours:02d}{minutes:02d}{seconds:02.4f}," # UTC Time
       + "A,"                                       # Status A=active or V=void
       + "{lat:02.0f}{latmin:02.6f},"               # Latitude (degrees + minutes)
       + "{latdir},"                                # Latitude direction (N/S)
       + "{lon:03.0f}{lonmin:02.6},"                # Longitude (degrees + minutes)
       + "{londir},"                                # Longitude direction (W/E)
       + "0.0,"                                     # Speed over the ground in knots
       + "{orientation:03.2f},"                     # Track angle in degrees
       + "{date},"                                  # Date
       + ","                                        # Magnetic variation in degrees
       + ","                                        # Magnetic variation direction
       + "A"                                        # A=autonomous, D=differential,
                                                    # E=Estimated, N=not valid, S=Simulator.
       + "*")                                       # Checksum

# https://www.trimble.com/oem_receiverhelp/v4.44/en/NMEA-0183messages_VTG.html
gpvtg = ("$GPVTG,"                    # Message ID
       + "{orientation:03.2f},"       # Track made good (degrees true)
       + "T,"                         # T: track made good is relative to true north
       + ","                          # Track made good (degrees magnetic)1
       + "M,"                         # M: track made good is relative to magnetic north
       + "0.0,"                       # Speed, in knots
       + "N,"                         # N: speed is measured in knots
       + "0.0,"                       # Speed over ground in kilometers/hour (kph)
       + "K,"                         # K: speed over ground is measured in kph
       + "A"                          # A=autonomous, D=differential,
                                      # E=Estimated, N=not valid, S=Simulator.
       + "*")                         # Checksum


def report_status(*args):
    """
    reports the current status of this service
    """
    # Do not report the same status multiple times
    #global last_status
    #if args == last_status:
    #    return
    print((" ".join(args)))
    # try:
    #     requests.post(STATUS_REPORT_URL, data={"waterlinked": " ".join(args)})
    #     last_status = args
    # except:
    #     print("Unable to talk to webui! Could not report status")


def request(url):
    try:
        return urllib.request.urlopen(url, timeout=1).read()
    except Exception as error:
        print(error)
        return None


def get_mavlink(path):
    """
    Helper to get mavlink data from mavlink2rest
    Example: get_mavlink('/VFR_HUD')
    Returns the data as text
    """
    url = MAVLINK2REST_URL + '/mavlink/vehicles/1/components/1/messages/' + path
    print(f"getting {url}")
    response = request(url)
    if not response:
        report_status("Error trying to access mavlink2rest!")
        return "0.0"
    return response


def get_message_frequency(message_name):
    """
    Returns the frequency at which message "message_name" is being received, 0 if unavailable
    """
    try:
        return float(get_mavlink('{0}/status/time/frequency'.format(message_name)))
    except:
        return 0



# TODO: Find a way to run this check for every message received without overhead
# check https://github.com/patrickelectric/mavlink2rest/issues/9
def ensure_message_frequency(message_name, frequency):
    """
    Makes sure that a mavlink message is being received at least at "frequency" Hertz
    Returns true if successful, false otherwise
    """
    print(f"ensuring we get {message_name} at {frequency} Hz")
    message_name = message_name.upper()
    msg_ids = {
        "VFR_HUD": 74,
        "SCALED_PRESSURE2": 137
    }
    msg_id = msg_ids[message_name]
    url = MAVLINK2REST_URL + '/helper/mavlink?name=COMMAND_LONG'
    try:
        current_frequency = get_message_frequency(message_name)
        print(f"frequency for {message_name} is {current_frequency}")

        # load message template from mavlink2rest helper
        data = json.loads(requests.get(url).text)
    except Exception as e:
        print(f"failed to get helper template from {url}")
        print(e)
        return False

    data["message"]["command"] = {"type": 'MAV_CMD_SET_MESSAGE_INTERVAL'}
    data["message"]["param1"] = msg_id
    data["message"]["param2"] = int(1000/frequency)

    try:
        result = requests.post(MAVLINK2REST_URL + '/mavlink', json=data)
        return result.status_code == 200
    except Exception as error:
        report_status("error setting message frequency: " + str(error))
        return False


def set_param(param_name, param_type, param_value):
    """
    Sets parameter "param_name" of type param_type to value "value" in the autpilot
    Returns True if succesful, False otherwise
    """
    try:
        data = json.loads(requests.get(MAVLINK2REST_URL + '/helper/mavlink?name=PARAM_SET').text)

        for i, char in enumerate(param_name):
            data["message"]["param_id"][i] = char

        data["message"]["param_type"] = {"type": param_type}
        data["message"]["param_value"] = param_value

        result = requests.post(MAVLINK2REST_URL + '/mavlink', json=data)
        return result.status_code == 200
    except Exception as error:
        print(("error setting parameter: " + str(error)))
        return False


def get_depth():
    return -float(get_mavlink('VFR_HUD/message/alt'))


def get_orientation():
    return float(get_mavlink('VFR_HUD/message/heading'))


def get_temperature():
    return float(get_mavlink('SCALED_PRESSURE2/message/temperature'))/100.0


def calculateNmeaChecksum(string):
    """
    Calculates the checksum of an Nmea string
    """
    data, checksum = string.split("*")
    calculated_checksum = reduce(operator.xor, bytearray(data[1:], 'utf-8'), 0)
    return calculated_checksum


def format(message, now=0, lat=0, lon=0, orientation=0):
    """
    Formats data into nmea message
    """
    now = datetime.now()
    latdir = "N" if lat > 0 else "S"
    londir = "E" if lon > 0 else "W"
    lat = abs(lat)
    lon = abs(lon)

    msg = message.format(date=now.strftime("%d%m%y"),
                         hours=now.hour,
                         minutes=now.minute,
                         seconds=(now.second + now.microsecond/1000000.0),
                         lat=floor(lat),
                         latmin=(lat % 1) * 60,
                         latdir=latdir,
                         lon=floor(lon),
                         lonmin=(lon % 1) * 60,
                         londir=londir,
                         orientation=orientation)
    return msg + ("%02x\r\n" % calculateNmeaChecksum(msg)).upper()


def setup_streamrates():
    """
    Setup message streams to get Orientation(VFR_HUD), Depth(VFR_HUD), and temperature(SCALED_PRESSURE2)
    """
    # VFR_HUD at at least 5Hz
    while not ensure_message_frequency("VFR_HUD", 5):
        time.sleep(2)

    # SCALED_PRESSURE2 at at least 1Hz
    while not ensure_message_frequency("SCALED_PRESSURE2", 1):
        time.sleep(2)


def wait_for_waterlinked():
    """
    Waits until the Underwater GPS system is available
    Returns when it is found
    """
    global gpsUrl
    while True:
        report_status("scanning for Water Linked underwater GPS...")
        try:
            requests.get(gpsUrl + '/api/v1/about/', timeout=1)
            break
        except Exception as error:
            print(error)
        time.sleep(5)


def processMasterPosition(response, *args, **kwargs):
    """
    Callback to handle the Master position request. This sends the topside position and orientation
    to QGroundControl via UDP port 14401
    """
    #print('got master response:', response.text)
    result = json.loads(response)
    if 'lat' not in result or 'lon' not in result or 'orientation' not in result:
        report_status('master(topside) response is not valid:')
        return
    # new approach: nmea messages to port 14401
    try:
        for message in [gpgga, gprmc, gpvtg]:
            msg = format(
                message,
                datetime.now(),
                float(result['lat']),
                float(result['lon']),
                orientation=result['orientation']
                )
            qgc_nmea_socket.sendto(msg.encode('utf-8'), ('192.168.2.1', 14401))
    except Exception as error:
        report_status("Error reading master position: " + error)


def processLocatorPosition(response, *args, **kwargs):
    """
    Callback to handle the Locator position request.
    Forwards the locator(ROV) position to mavproxy's GPSInput module
    TODO: Change this too to use mavlink2rest
    """
    result = json.loads(response)
    if 'lat' not in result or 'lon' not in result:
        report_status('global response is not valid!')
        print((json.dumps(result, indent=4, sort_keys=True)))
        return

    data = json.loads(requests.get(MAVLINK2REST_URL + '/helper/mavlink?name=GPS_INPUT').text)

    data["message"]['lat'] = floor(result['lat'] * 1e7)
    data["message"]['lon'] = floor(result['lon'] * 1e7)
    data["message"]['fix_type'] = 3
    data["message"]['hdop'] = 1.0
    data["message"]['vdop'] = 1.0
    data["message"]['satellites_visible'] = 10
    data["message"]['ignore_flags'] = 8 | 16 | 32

    try:
        result = requests.post(MAVLINK2REST_URL + '/mavlink', json=data)
        return result.status_code == 200
    except Exception as error:
        print("error sending GPS_INPUT")
        print(error)
        return False


# Socket to send GPS data to mavproxy
socket_mavproxy = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
socket_mavproxy.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
socket_mavproxy.setblocking(0)

if __name__ == "__main__":
    print("starting")
    parser = argparse.ArgumentParser(description="Driver for the Water Linked Underwater GPS system.")
    parser.add_argument('--ip', action="store", type=str, default="demo.waterlinked.com", help="remote ip to query on.")
    parser.add_argument('--port', action="store", type=str, default="80", help="remote port to query on.")
    args = parser.parse_args()

    # Use UDP port 14401 to send NMEA data to QGC for topside location
    qgc_nmea_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    qgc_nmea_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    qgc_nmea_socket.setblocking(0)

    gpsUrl = "http://" + args.ip + ":" + args.port

    setup_streamrates()

    wait_for_waterlinked()

    report_status("Running")

    # Sets GPS type to MAVLINK
    set_param("GPS_TYPE", "MAV_PARAM_TYPE_UINT8", 14)

    # update at 5Hz
    update_period = 0.25
    last_master_update = 0
    last_locator_update = 0
    last_position_update = 0

    depth_endpoint = gpsUrl + "/api/v1/external/depth"
    ext_depth = {}
    orientation_endpoint = gpsUrl + "/api/v1/external/orientation"
    ext_orientation = {}
    locator_endpoint = gpsUrl + "/api/v1/position/global"
    master_endpoint = gpsUrl + "/api/v1/position/master"

    # TODO: upgrade this to async once we have Python >= 3.6
    while True:
        time.sleep(0.02)
        print(".")
        if time.time() > last_locator_update + update_period:
            last_locator_update = time.time()

            response = request(locator_endpoint)
            if response:
                processLocatorPosition(response)
            else:
                report_status("Unable to fetch Locator position from Waterlinked API")

        if time.time() > last_master_update + update_period:
            last_master_update = time.time()

            response = request(master_endpoint)
            if response:
                processMasterPosition(response)
            else:
                report_status("Unable to fetch Master position from Waterlinked API")

        if time.time() < last_position_update + update_period:
            continue
        try:
            last_position_update = time.time()
            # send depth and temprature information
            ext_depth['depth'] = get_depth()
            ext_depth['temp'] = get_temperature()
            # Equivalent
            # curl -X PUT -H "Content-Type: application/json" -d '{"depth":1,"temp":2}' "http://37.139.8.112:8000/api/v1/external/depth"
            requests.put(depth_endpoint, json=ext_depth, timeout=1)

            # Send heading to external/orientation api
            ext_orientation['orientation'] = max(min(360, get_orientation()), 0)
            requests.put(orientation_endpoint, json=ext_orientation, timeout=1)
            report_status("Running")

        except Exception as error:
            report_status("Error: ", str(error))