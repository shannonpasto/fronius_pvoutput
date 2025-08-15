#!/usr/bin/env python3

import sys
from urllib.parse import urlencode
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import requests
import tzlocal

import config as cfg

PVO_BASE_URL = "https://pvoutput.org"


def get_data(url):
    """Fetch JSON from the URL with a 10s timeout; raises for HTTP errors.
    Returns JSON response
    """
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"Request error occurred: {req_err}")
    except ValueError as json_err:
        print(f"JSON decode error: {json_err}")


def get_num(data, path):
    """Ensure the data from the JSON is a number; raises for
    KeyError and TypeError errors and exists.
    Input is: JSON, path to key
    """
    try:
        for key in path:
            data = data[key]
    except (KeyError, TypeError) as e:
        print(f"Error retrieving {'.'.join(path)}: {e}")
        sys.exit(1)

    if data is None:
        print(f"Value at {'.'.join(path)} is None")
        sys.exit(1)

    if isinstance(data, (int, float)):
        if isinstance(data, float) and data.is_integer():
            return int(data)
        return data


# start the script here
# check for the required config options
req_attr = [
    ("inverter_addr", cfg.inverter_addr),
    ("pvo_sid", cfg.pvo_sid),
    ("pvo_api_key", cfg.pvo_api_key)
]

missing_attr = []
for name, value in req_attr:
    if not value:
        missing_attr.append(name)

if len(missing_attr) > 0:
    print(
        "\nThe following options are not set in the config file\n"
        "Please set them and try again\n",
        *missing_attr,
        sep='\n'
    )
    print()
    sys.exit(1)

# get the json data from the inverter
inverter_realtime_data = get_data(
    f"http://{cfg.inverter_addr}/solar_api/v1/"
    "GetInverterRealtimeData.cgi?Scope=Device&DataCollection=CommonInverterData"
)
if inverter_realtime_data is None:
    sys.exit(1)

# get the json data from the smart meter
power_flow_realtime_data = get_data(
    f"http://{cfg.inverter_addr}/solar_api/v1/GetPowerFlowRealtimeData.fcgi"
)
if power_flow_realtime_data is None:
    sys.exit(1)

# get the required values from the inverter and smart meter
# https://pvoutput.org/help/api_specification.html#add-status-service

# v2 - Power Generation
power_generation = get_num(
    power_flow_realtime_data,
    ["Body", "Data", "Site", "P_PV"]
)

# v4 - Power Consumption
power_consumption = -get_num(
    power_flow_realtime_data,
    ["Body", "Data", "Site", "P_Load"]
)

# v6 - Voltage
voltage = get_num(
    inverter_realtime_data,
    ["Body", "Data", "UAC", "Value"]
)

# inverter timestamp
inverter_timestamp = inverter_realtime_data["Head"]["Timestamp"]

# check timestamp is in local time. convert if needed
dt = datetime.fromisoformat(inverter_timestamp)

tz_name = getattr(cfg, "timezone", None) or tzlocal.get_localzone_name()
site_tz = ZoneInfo(tz_name)

if dt.utcoffset() == timezone.utc.utcoffset(dt):
    dt = dt.astimezone(site_tz)

# set the URL parameters
# c1=2 as v1 is total energy, ie cumulative value
params = {
    "d": dt.strftime("%Y%m%d"),
    "t": dt.strftime("%H:%M"),
    "v2": int(round(power_generation)),
    "v4": int(round(power_consumption)),
    "v6": round(voltage, 1)
}

# make the PVOutput POST
try:
    response = requests.post(
        f"{PVO_BASE_URL}/service/r2/addstatus.jsp",
        headers={
            'X-Pvoutput-Apikey': f'{cfg.pvo_api_key}',
            'X-Pvoutput-SystemId': f'{cfg.pvo_sid}',
        },
        data=params,
        timeout=10
    )
    response.raise_for_status()
except requests.exceptions.HTTPError as http_err:
    print(f"HTTP error occurred: {http_err}")
except requests.exceptions.RequestException as req_err:
    print(
        f"Request error occurred: {req_err}.\n\n"
        f"{PVO_BASE_URL}/service/r2/addstatus.jsp?{urlencode(params)}"
    )
