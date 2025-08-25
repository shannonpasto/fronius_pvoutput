# Fronius Gen24 to PVOutput

[![Python](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/github/license/shannonpasto/fronius_pvoutput)](./LICENSE)
[![Last Commit](https://img.shields.io/github/last-commit/shannonpasto/fronius_pvoutput)](https://github.com/shannonpasto/fronius_pvoutput/commits/main)

A python script to upload Fronius Gen24 Inverter (with smart meter) data to [PVOutput](https://pvoutput.org)

For best results a python [virtual environment](https://docs.python.org/3/library/venv.html) is recommended.

1. clone the repo to your server
2. copy `config-default.py` to `config.py` and configure the 3 mandatory options
   - `inverter_addr` - IP or hostname of your inverter
   - `pvo_sid` - your PVOutput system id
   - `pvo_api_key` - your PVOutput API key
   - `timezone` - (optional). Add your timezone. Use [List of tz database time zones](https://en.wikipedia.org/wiki/List_of_tz_database_time_zones) to find yours. If not set the timezone will be determined from either the inverter or local system. PVOutput requires that timestamps are your local timezone
   - `write_csv` - (optional). set this to `True` to always write the data to a csv for import into PVOutput
   - `csv_path` - (optional). path to save the csv file to. Defaults to the same locaiton as `main.py`.
3. install the requirements `pip3 install -r requirements.txt`
4. do a dry run to make sure everything works `python3 ./main.py --dry-run`. Fix any errors before proceeding
5. run the script `python3 ./main.py`

No output will be returned if everything works. Next step would be to configure cron
1. `crontab -e`
2. add `*/5 * * * * cd /usr/local/fronius-pvoutput; python3 ./main.py`

---
#### Notes
- currrently only v2 (Power Generation) and v4 (Power Consumption) are sent
- while Energy Generation is available in the inverter, I can only find the total generated and not the daily total

---
#### To-do
- better logging
- see if v1 (Energy Generation) can be used
