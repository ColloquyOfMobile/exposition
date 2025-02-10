from pprint import pprint


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
        self._data = {
            "females":{
                "names": ["female1", "female2", "female3"],
                "share":{
                    "motion range": 2000,
                    },
                },
            "males":{
                "names": ["male1", "male2"],
                "share":{
                    "motion range": 1500,
                    },
                },
            "mirrors":{
                "names": ["mirror1", "mirror2", "mirror3"],
                "share":{
                    "motion range": 500,
                    },
                },
            "dynamixel network":{
                "communication port": "COM8",
                "baudrate": 57600,
                },
            "arduino":{
                "communication port": "COM9",
                "baudrate": 57600,
                },
            "female1": {
                "origin": FEMALE1_ORIGIN,
                "dynamixel id": 1,
                "mirror": {
                    "origin": MIRROR1_ORIGIN,
                    "dynamixel id": 2,
                    }
                },
            "female2": {
                "origin": FEMALE2_ORIGIN,
                "dynamixel id": 3,
                "mirror": {
                    "origin": MIRROR2_ORIGIN,
                    "dynamixel id": 4,
                    }
                },
            "female3": {
                "origin": FEMALE3_ORIGIN,
                "dynamixel id": 5,
                "mirror": {
                    "origin": MIRROR3_ORIGIN,
                    "dynamixel id": 6,
                    }
                },
            "male1": {
                "origin": MALE1_ORIGIN,
                "dynamixel id": 7,
                },
            "male2": {
                "origin": MALE2_ORIGIN,
                "dynamixel id": 8,
                },
            "bar": {
                "origin": BAR_ORIGIN,
                "dynamixel ids": [9, 10],
                    "motion range": 10000,
                },
            }

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