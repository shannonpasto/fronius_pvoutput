#!/usr/bin/python3

import requests
import sys
from urllib.parse import urlencode
from datetime import datetime
import config as cfg

pvo_url = "https://pvoutput.org/service/r2/addstatus.jsp"


def get_data(url):
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
    try:
        for key in path:
            data = data[key]
    except (KeyError, TypeError) as e:
        print(f"Error retrieving {'.'.join(path)}: {e}")
        sys.exit(1)  # stop script

    if data is None:
        print(f"Value at {'.'.join(path)} is None")
        sys.exit(1)

    if isinstance(data, (int, float)):
        if isinstance(data, float) and data.is_integer():
            return int(data)
        return data


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

interter_realtime_data = get_data(
    f"http://{cfg.inverter_addr}/solar_api/v1/"
    "GetInverterRealtimeData.cgi?Scope=Device&DataCollection=CommonInverterData"
)

power_flow_realtime_data = get_data(
    f"http://{cfg.inverter_addr}/solar_api/v1/GetPowerFlowRealtimeData.fcgi"
)

# v2
power_generation = get_num(
    power_flow_realtime_data,
    ["Body", "Data", "Site", "P_PV"]
)

# v4
power_consumption = -get_num(
    power_flow_realtime_data,
    ["Body", "Data", "Site", "P_Load"]
)

# v6
voltage = get_num(
    interter_realtime_data,
    ["Body", "Data", "UAC", "Value"]
)

params = {
    "d": datetime.today().strftime('%Y%m%d'),
    "t": datetime.today().strftime('%H:%M'),
    "v2": f"{power_generation:.2f}",
    "v4": f"{power_consumption:.2f}",
    "v6": round(voltage, 2)
}

try:
    response = requests.post(
        pvo_url,
        headers={
            'X-Pvoutput-Apikey': f'{cfg.pvo_api_key}',
            'X-Pvoutput-SystemId': f'{cfg.pvo_sid}',
        },
        params=params,
        timeout=10
    )
    response.raise_for_status()
except requests.exceptions.HTTPError as http_err:
    print(f"HTTP error occurred: {http_err}")
except requests.exceptions.RequestException as req_err:
    print(f"Request error occurred: {req_err}.\n\n{pvo_url}?"
        "{urlencode(params)}"
    )
