#!/usr/bin/env python3

import argparse
import csv
import os
import sys
from urllib.parse import urlencode
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import requests
import tzlocal
import config as cfg

PVO_BASE_URL = "https://pvoutput.org"

# set up cli args
parser = argparse.ArgumentParser()
parser.add_argument("-d", "--dry-run", action="store_true",
                    help="Run in dry-run mode")
args = parser.parse_args()
if args.dry_run:
    print("[DRY RUN] Starting dry run")


def get_data(url):
    """Fetch JSON from the URL with a 10s timeout; raises for HTTP errors."""
    if args.dry_run:
        print(f"[DRY RUN] GETting: {url}")
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
    KeyError and TypeError errors and exits.
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


def write_csv(date_str, data):
    """Append one row to <date>.csv, creating file with header if missing.
    Input is: date as a string, data as a list
    Output is: write to csv"""
    csv_header = [
        "Time", "Energy Generation", "Power Generation", "Energy Consumption",
        "Power Consumption", "Temperature", "Voltage"
    ]

    if cfg.csv_path:
        csv_file = os.path.join(cfg.csv_path, f"{date_str}.csv")
        os.makedirs(os.path.dirname(csv_file), exist_ok=True)
    else:
        csv_file = os.path.join(os.path.dirname(__file__), f"{date_str}.csv"
        )

    file_exists = os.path.isfile(csv_file)
    with open(csv_file, mode="a", newline="") as csvfile:
        writer = csv.writer(csvfile)
        if not file_exists:
            writer.writerow(csv_header)
        writer.writerow(data)


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
power_generation = int(round(get_num(
    power_flow_realtime_data,
    ["Body", "Data", "Site", "P_PV"]
)))

# v4 - Power Consumption
power_consumption = -int(round(get_num(
    power_flow_realtime_data,
    ["Body", "Data", "Site", "P_Load"]
)))

# v6 - Voltage
voltage = round(get_num(
    inverter_realtime_data,
    ["Body", "Data", "UAC", "Value"]), 1
)

# inverter timestamp
inverter_timestamp = inverter_realtime_data["Head"]["Timestamp"]

# check timestamp is in local time. convert if needed
dt = datetime.fromisoformat(inverter_timestamp)

tz_name = getattr(cfg, "timezone", None) or tzlocal.get_localzone_name()
site_tz = ZoneInfo(tz_name)

timetstamp_converted = False
if dt.utcoffset() == timezone.utc.utcoffset(dt):
    dt = dt.astimezone(site_tz)
    timetstamp_converted = True
if args.dry_run:
    print("[DRY RUN] Timestamp:"
          "converted UTC->local" if timetstamp_converted else "already local",
          "final =", dt.isoformat()
    )
d = dt.strftime("%Y%m%d")
t = dt.strftime("%H:%M")

# set the URL parameters
# c1=2 as v1 is total energy, ie cumulative value
params = {
    "d": d,
    "t": t,
    "v2": power_generation,
    "v4": power_consumption,
    "v6": voltage
}

if cfg.write_csv:
    write_csv(d, [
        t, '', power_generation, '',
        power_consumption, '', voltage
    ])

headers = {
    'X-Pvoutput-Apikey': cfg.pvo_api_key,
    'X-Pvoutput-SystemId': cfg.pvo_sid,
}

# make the PVOutput POST
if args.dry_run:
    def _scrub_headers(h):
        """Mask API key when printing/logging."""
        k = h.get("X-Pvoutput-Apikey")
        if k:
          return {**h, "X-Pvoutput-Apikey": f"...{k[-4:]}"}
        return h
    print("[DRY RUN] Would POST:")
    print("  URL: ", f"{PVO_BASE_URL}/service/r2/addstatus.jsp")
    print("  payload:", params)
    print("  payload (query):", urlencode(params))
    print("  headers:", _scrub_headers(headers))
else:
    try:
        response = requests.post(
            f"{PVO_BASE_URL}/service/r2/addstatus.jsp",
            headers=headers,
            data=params,
            timeout=10
        )
        response.raise_for_status()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
        if not cfg.write_csv:
            write_csv(d, [
                t, '', power_generation, '',
                power_consumption, '', voltage
            ])
    except requests.exceptions.RequestException as req_err:
        print(
            f"Request error occurred: {req_err}.\n\n"
            f"{PVO_BASE_URL}/service/r2/addstatus.jsp?{urlencode(params)}"
        )
        write_csv(d, [
                t, '', power_generation, '',
                power_consumption, '', voltage
            ])
