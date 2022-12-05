from bluerobotics/blueos-base:v0.0.7

COPY app /app
RUN python /app/setup.py install

EXPOSE 80/tcp

LABEL version="1.0.1"
# TODO: Add a Volume for persistence across boots
LABEL permissions '\
{\
  "ExposedPorts": {\
    "80/tcp": {}\
  },\
  "Env": [\
    "UGPS_IP=192.168.2.94",\
    "TOPSIDE_IP=192.168.2.94"\
    ],\
  "HostConfig": {\
    "Binds":["/root/.config:/root/.config"],\
    "ExtraHosts": ["host.docker.internal:host-gateway"],\
    "PortBindings": {\
      "80/tcp": [\
        {\
          "HostPort": ""\
        }\
      ]\
    }\
  }\
}'
LABEL authors '[\
    {\
        "name": "Willian Galvani",\
        "email": "willian@bluerobotics.com"\
    }\
]'
LABEL docs ''
LABEL company '{\
        "about": "",\
        "name": "Blue Robotics",\
        "email": "support@bluerobotics.com"\
    }'
LABEL readme 'https://raw.githubusercontent.com/Williangalvani/blueos-ugps-extension/{tag}/readme.md'
LABEL website 'https://github.com/Williangalvani/blueos-ugps-extension/'
LABEL support 'https://github.com/Williangalvani/blueos-ugps-extension/'
LABEL requirements="core >= 1"

ENTRYPOINT cd /app && python underwater-gps.py --ip $UGPS_IP --topside $TOPSIDE_IP