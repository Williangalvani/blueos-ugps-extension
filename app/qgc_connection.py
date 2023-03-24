from typing import Any, Optional

import socket
from datetime import datetime, timezone
from math import floor
from functools import reduce
import operator
from loguru import logger


class QgcConnection:
    """
    Responsible for interfacing with QGroundControl over UDP

    Exception handling: All exceptions are caught and reported over logging.
    NMEA Format: https://gpsd.gitlab.io/gpsd/NMEA.html
    """

    def __init__(self, ip: str = "192.168.2.1", port: int = 14401):
        # store host
        self.ip = ip
        self.port = port

        # Use UDP port 14401 to send NMEA data to QGC for topside location
        self.nmea_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.nmea_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.nmea_socket.setblocking(0)

        # Nmea messages templates
        self.gpgga = ("$GPGGA,"                           # Message ID
            + "{hours:02d}{minutes:02d}{seconds:02.2f},"  # UTC Time
            + "{lat:02.0f}{latmin:02.3f},"                # Latitude (degrees + minutes)
            + "{latdir},"                                 # Latitude direction (N/S)
            + "{lon:03.0f}{lonmin:02.3f},"                # Longitude (degrees + minutes)
            + "{londir},"                                 # Longitude direction (W/E)
            + "{fix},"                                    # Fix? (0-5)
            + "{satellites:02d},"                         # Number of Satellites
            + "{hdop:01.2f},"                             # HDOP
            + "0,"                                        # MSL altitude
            + "M,"                                        # MSL altitude unit (Meters)
            + "0,"                                        # Geoid separation
            + "M,"                                        # Geoid separation unit (Meters)
            + "00,"                                       # Age of differential GPS data, N/A
            + "0000"                                      # Age of differential GPS data, N/A
            + "*")                                        # Checksum

        self.gprmc = ("$GPRMC,"                           # Message ID
            + "{hours:02d}{minutes:02d}{seconds:02.2f},"  # UTC Time
            + "A,"                                        # Status A=active or V=void
            + "{lat:02.0f}{latmin:02.3f},"                # Latitude (degrees + minutes)
            + "{latdir},"                                 # Latitude direction (N/S)
            + "{lon:03.0f}{lonmin:02.3f},"                # Longitude (degrees + minutes)
            + "{londir},"                                 # Longitude direction (W/E)
            + "{knots:01.1f},"                            # Speed over the ground in knots
            + "{orientation:03.2f},"                      # Track angle in degrees
            + "{date},"                                   # Date
            + ","                                         # Magnetic variation in degrees
            + ","                                         # Magnetic variation direction
            + "A"                                         # A=autonomous, D=differential, E=Estimated, N=not valid, S=Simulator
            + "*")                                        # Checksum

        self.gpvtg = ("$GPVTG,"                           # Message ID
            + "{cog:03.1f},"                              # Track made good (degrees true)
            + "T,"                                        # T: track made good is relative to true north
            + ","                                         # Track made good (degrees magnetic)
            + "M,"                                        # M: track made good is relative to magnetic north
            + "{knots:02.1f},"                            # Speed, in knots
            + "N,"                                        # N: speed is measured in knots
            + "{kph:02.1f},"                              # Speed over ground in kilometers/hour (kph)
            + "K,"                                        # K: speed over ground is measured in kph
            + "A"                                         # A=autonomous, D=differential, E=Estimated, N=not valid, S=Simulator.
            + "*")                                        # Checksum

    def send_topside_position(self, in_json: object):
        """
        This sends the topside position and orientation
        to QGroundControl via UDP port 14401
        """
        try:
            for message in [self.gpgga, self.gprmc, self.gpvtg]:
                msg = self.format_nmea(
                    message,
                    datetime.now(timezone.utc),
                    in_json
                    )
                logger.debug(f"Sending UDP {msg}")
                self.nmea_socket.sendto(msg.encode('utf-8'), (self.ip, self.port))
        except Exception as e:
            logger.error(f"Got exception: {e}")

    def format_nmea(self, message, now, in_json):
        """
        Formats data into nmea message
        """
        lat = float(in_json['lat'])
        lon = float(in_json['lon'])
        latdir = "N" if lat > 0 else "S"
        londir = "E" if lon > 0 else "W"
        lat = abs(lat)
        lon = abs(lon)

        msg = message.format(date=now.strftime("%d%m%y"),
                            hours=now.hour,
                            minutes=now.minute,
                            seconds=(now.second + now.microsecond/1000000.0),
                            # fix type of demo.waterlinked.com is 1
                            fix=0 if in_json['fix_quality'] == 0 else 3,
                            satellites=max(in_json['numsats'], 0),
                            hdop= (9.9 if in_json['hdop'] == -1 else in_json['hdop']),
                            lat=floor(lat),
                            latmin=(lat % 1) * 60,
                            latdir=latdir,
                            lon=floor(lon),
                            lonmin=(lon % 1) * 60,
                            londir=londir,
                            orientation=in_json['orientation'],
                            knots=in_json['sog']/1.852,
                            kph=in_json['sog'],
                            cog=in_json['cog'],)
        return f"{msg}{self.calculate_nmea_checksum(msg):02x}\r\n"

    def calculate_nmea_checksum(self, string):
        """
        Calculates the checksum of an Nmea string
        """
        data, _ = string.split("*")
        bytes = bytearray(data[1:], "utf-8")
        calculated_checksum = reduce(operator.xor, bytes, 0)
        return calculated_checksum
