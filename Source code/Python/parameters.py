from pprint import pprint
import json
from pathlib import Path


# Set these value with trial and error once thank to the mecanical_calibration.py file.
FEMALE1_ORIGIN = 3000
FEMALE2_ORIGIN = 2300
FEMALE3_ORIGIN = 2100
MIRROR1_ORIGIN = 1968
MIRROR2_ORIGIN = 950
MIRROR3_ORIGIN = 1080
MALE1_ORIGIN = 1300
MALE2_ORIGIN = 2900
BAR_ORIGIN = 1100 # 3500

# Look in windows device manager.
DXL_COM = None # "COM8" # Set to None if not plugged

class Parameters:

    def __init__(self):
        with Path("local/parameters.json").open() as file:
            self._data = json.load(file)
        print(f'{self._data["dynamixel network"]["communication port"]=}')

        for mirror_name, female_name in zip(self._data["mirrors"]["names"], self._data["females"]["names"]):
            self._data[mirror_name] = self._data[female_name]["mirror"]

        self._data["elements"] = {
            "names": [
                *self._data["females"]["names"],
                *self._data["mirrors"]["names"],
                *self._data["males"]["names"],
                ]
            }

        self._process(self._data)

    def _process(self, data):
        for key, value in data.items():
            names = value.get("names", [])
            for name in names:
                self._data[name].update( value.get("share", {}))
                self._data[name]["name"] = name

    def as_dict(self):
        return dict(self._data)

    def pprint(self):
        return pprint(self.as_dict())