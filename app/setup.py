#!/usr/bin/env python3

import os
import ssl

from setuptools import setup

# Ignore ssl if it fails
if not os.environ.get("PYTHONHTTPSVERIFY", "") and getattr(ssl, "_create_unverified_context", None):
    ssl._create_default_https_context = ssl._create_unverified_context

setup(
    name="blueos-waterlinked-ugps-g2-extension",
    version="0.1.0",
    description="BlueOS extension for Water Linked Underwater GPS G2",
    license="MIT",
    install_requires=[
        "requests == 2.28.2",
        "loguru == 0.6"
    ],
)