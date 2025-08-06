#!/usr/bin/python3

import requests
from urllib.parse import urlencode
from datetime import datetime
import config as cfg

pvo_url = "https://pvoutput.org/service/r2/addstatus.jsp"


def getData(url):
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


inverterRealtimeData = getData(f"http://{cfg.inverter_addr}/solar_api/v1/GetInverterRealtimeData.cgi?Scope=Device&DataCollection=CommonInverterData")
powerFlowRealTimeData = getData(f"http://{cfg.inverter_addr}/solar_api/v1/GetPowerFlowRealtimeData.fcgi")

cumulative_energy_generation = inverterRealtimeData["Body"]["Data"]["TOTAL_ENERGY"]["Value"]  # v1 c1=1
power_generation = powerFlowRealTimeData["Body"]["Data"]["Site"]["P_PV"]  # v2
power_consumption = -powerFlowRealTimeData["Body"]["Data"]["Site"]["P_Load"]  # v4
voltage = inverterRealtimeData["Body"]["Data"]["UAC"]["Value"]  # v6

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
    print(f"Request error occurred: {req_err}.\n\n{pvo_url}?{urlencode(params)}")
