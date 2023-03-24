# BlueOS Extension for Water Linked Underwater GPS

This service
* forwards mavlink data from Mavlink2Rest (https://github.com/patrickelectric/mavlink2rest) like depth to the UGPS Topside
* forwards locator position from UGPS Topside to mavlink
* forwards topside position from UGPS Topside to UDP NMEA to be received by QGroundControl (implemented, but currently not tested)

Hardware documentation can be found at https://waterlinked.github.io/underwater-gps/integration/bluerov-integration/

## State

This extension is currently in early development.

## How to install

There are 2 options

### Use the extensions manager in BlueOS 1.1
* Click Extensions > Extensions Manager
* Install this extension

### Create docker image manually and start it

To set this up, ssh into the Raspberry Pi (or access via `red-pill` in [BlueOS Terminal](https://docs.bluerobotics.com/ardusub-zola/software/onboard/BlueOS-1.0/advanced-usage/#terminal))

install git, clone this repository and run
```
docker build -t ghcr.io/waterlinked/blueos-ugps-extension:latest .
# see all images
docker images

# either: run image detached and with defaults
docker run -d --net=host ghcr.io/waterlinked/blueos-ugps-extension:latest
# or: run image detached with different demo server
docker run -d --net=host ghcr.io/waterlinked/blueos-ugps-extension:latest python app/main.py --ugps_host https://demo.waterlinked.com --mavlink_host http://192.168.2.2:6040 --qgc_ip 192.168.2.1
# or: in interactive shell to get debug output
docker run -it ghcr.io/waterlinked/blueos-ugps-extension:latest /bin/bash
#   with standard command
cd app && python main.py --ugps_host http://192.168.2.94 --mavlink_host http://192.168.2.2:6040 --qgc_ip 192.168.2.1
#   or with demo server
cd app && python main.py --ugps_host https://demo.waterlinked.com --mavlink_host http://192.168.2.2:6040 --qgc_ip 192.168.2.1
# end interactive session
exit

# then stop/start/look at log with
docker stop [container-id]
docker start [container-id]
docker log [container-id] # if run detached
```