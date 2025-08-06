# Fronius Gen24 to PVOutput

A python script to upload Fronius Gen24 Inverter (with smart meter) data to [PVOutput](https://pvoutput.org)

For best results a python [virtual environment](https://docs.python.org/3/library/venv.html) is recommended.

1. clone the repo to your server
2. copy `config-default.py` to `config.py` and configure the 3 options
   - `inverter_addr` - IP or hostname of your inverter
   - `pvo_sid` - your PVOutput system id
   - `pvo_api_key` - your PVOutput API key
3. install the requirements `pip3 install -r requirements.txt`
4. run the script `python3 ./main.py`

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
