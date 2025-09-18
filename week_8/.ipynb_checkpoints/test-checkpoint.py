import os
import sys
import logging
from datetime import datetime
import asyncio

import traceback

from arduino_iot_cloud import ArduinoCloudClient

# === CONFIG (your Manual/Python device creds) ===
DEVICE_ID  = "6c8475fb-9c60-4eca-a447-0f9afe37b9ac"
SECRET_KEY = "vNmW7vrM@rQNlx21V43qI9Klf"


def on_x_changed(client, value): print("x", value)
# def on_y_changed(client, value): print("y", value)
# def on_z_changed(client, value): print("z", value)

def main():
    client = ArduinoCloudClient (device_id = DEVICE_ID, username=DEVICE_ID, password=SECRET_KEY)

    client.register("x" , value = None , on_write = on_x_changed)
    # client.register("y", value=None, on_write = on_y_changed)
    # client.register("z", value=None, on_write = on_z_changed)

    # start cloud client
    client.start()


if __name__ == "__main__":
    try:
        main()  # main function which runs in an internal infinite loop
    except:
        exc_type, exc_value, exc_traceback = sys.exc_info()
        traceback.print_tb(exc_type, file=print)