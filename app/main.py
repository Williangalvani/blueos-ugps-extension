#!/usr/bin/python

import time
import argparse

from loguru import logger
from mavlink2resthelper import Mavlink2RestHelper
from ugps_connection import UgpsConnection
from qgc_connection import QgcConnection


class UgpsExtension:
    """
    Main class for the BlueOS Extension for Water Linked Underwater GPS
    """
    def __init__(self, args) -> None:
        self.mavlink = Mavlink2RestHelper(host=args.mavlink_host, vehicle=1, component=220, get_vehicle=1, get_component=1)
        self.ugps = UgpsConnection(host=args.ugps_host)
        self.qgc = QgcConnection(ip=args.qgc_ip, port=14401)

    def run(self) -> None:
        self.setup_streamrates()
        # Sets GPS type to MAVLINK
        self.mavlink.set_param("GPS_TYPE", "MAV_PARAM_TYPE_UINT8", 14)

        self.ugps.wait_for_connection()

        logger.info("Running")

        update_period = 0.25
        last_master_update = 0
        last_locator_update = 0
        last_position_update = 0

        while True:
            time.sleep(0.02)
            if time.time() > last_position_update + update_period:
                last_position_update = time.time()
                logger.info("Forwarding depth, temperature and orientation from mavlink to ugps")
                # send depth and temprature information to upgs
                self.ugps.send_locator_depth_temperature(self.mavlink.get_depth(), self.mavlink.get_temperature())

                # Send heading to ugps
                self.ugps.send_locator_orientation(self.mavlink.get_orientation())

            if time.time() > last_locator_update + update_period:
                last_locator_update = time.time()

                logger.info("Forwarding locator position from ugps to mavlink")
                locator_position = self.ugps.get_locator_position()
                if locator_position:
                    self.mavlink.send_gps_input(locator_position)

            if args.qgc_ip != "" and time.time() > last_master_update + update_period:
                last_master_update = time.time()

                logger.info("Forwarding topside position from upgs to qgc")
                topside_position = self.ugps.get_ugps_topside_position()
                if topside_position:
                    self.qgc.send_topside_position(topside_position)

    def setup_streamrates(self):
        """
        Setup message streams to get Orientation(VFR_HUD), Depth(VFR_HUD), and temperature(SCALED_PRESSURE2)
        """
        # VFR_HUD at at least 5Hz
        while not self.mavlink.ensure_message_frequency("VFR_HUD", 5):
            time.sleep(2)

        # SCALED_PRESSURE2 at at least 1Hz
        while not self.mavlink.ensure_message_frequency("SCALED_PRESSURE2", 1):
            time.sleep(2)


if __name__ == "__main__":
    logger.info("Starting BlueOS extension for Water Linked Underwater GPS G2.")
    parser = argparse.ArgumentParser(description="BlueOS extension for Water Linked Underwater GPS G2.\
                                     The defaults of the command line arguments allow for easy testing of \
                                     the extension in a development environment, see the dockerfile for \
                                     values to be used inside BlueOS.")
    parser.add_argument('--ugps_host', action="store", type=str, default="https://demo.waterlinked.com",
                        help="Host address or IP for UGPS Topside, e.g. http://192.168.2.94 or \
                            https://demo.waterlinked.com (Port not needed as default http)")
    parser.add_argument('--mavlink_host', action="store", type=str, default="http://blueos.local:6040",
                        help="Host address or IP for mavlink2rest API, e.g. http://blueos.local:6040 \
                            or http://192.168.2.2:6040 (Port needed as non-default.)")
    parser.add_argument('--qgc_ip', action="store", type=str, default="192.168.2.2",
                        help="IP address to send UGPS Topside position via UDP to. Set to '' \
                            to not send any NMEA-strings over UDP.")
    args = parser.parse_args()

    service = UgpsExtension(args)
    service.run()
