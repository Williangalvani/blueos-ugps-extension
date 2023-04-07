### UGPS Extension

⚠️ This extension **has not been validated**, and currently **has no UI page** (so creates no listing in the sidebar).

#### Usage

Configuration is done by editing the extension in the "Installed" tab of the Extensions Manager.

Editing requires [Pirate Mode](https://docs.bluerobotics.com/ardusub-zola/software/onboard/BlueOS-latest/advanced-usage/#pirate-mode)
to be enabled, after which the "Edit" button can be used. Copy the Original Settings contents
into the Custom settings box, and (if necessary) change the IPs to relevant alternatives:
```
    "UGPS_IP=192.168.2.94",
    "TOPSIDE_IP=192.168.2.1"
```

Use the "View Logs" button to check the status.

#### Communication Details

Assuming the UGPS is detected and working (which should be visible in the extension logs):
- the extension sends depth and orientation information to the UGPS (to enable it to function)
- the extension sends NMEA GPS messages of the master position to port `14401` on the topside
- the extension sends`GPS_INPUT` MAVLink messages of the locator position to the autopilot
    - the autopilot should send corresponding `GPS_RAW_INT` messages to the topside
- the autopilot sends regular `GLOBAL_POSITION_INT` messages to the topside with its filtered position estimates
