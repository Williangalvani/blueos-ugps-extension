FROM python:3.9-slim-bullseye

COPY app /app
RUN python /app/setup.py install

EXPOSE 80/tcp

LABEL version="1.0.1"

LABEL permissions '\
{\
  "ExposedPorts": {\
    "80/tcp": {}\
  },\
  "HostConfig": {\
    "Binds":["/root/.config:/root/.config"],\
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
        "name": "Blue Robotics/Water Linked",\
        "email": "support@bluerobotics.com"\
    }'
LABEL readme 'https://github.com/waterlinked/blueos-ugps-extension/blob/master/readme.md'
LABEL website 'https://github.com/waterlinked/blueos-ugps-extension/'
LABEL support 'https://github.com/waterlinked/blueos-ugps-extension/'
LABEL requirements="core >= 1"

CMD cd /app && python main.py --ugps_host http://192.168.2.94 --mavlink_host http://192.168.2.2:6040 --qgc_ip 192.168.2.1
