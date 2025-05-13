from pprint import pprint
import json
from pathlib import Path
from server.html_element import HTMLElement
from copy import deepcopy

class Parameter:

    def __init__(self, owner):
        self._owner

    def save(self):
        self._owner.save()


class Parameters(HTMLElement):
    _path = Path("local/parameters.json")
    _default = {
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
            "communication port": None,
            "baudrate": 57600,
            },
        "arduino":{
            "communication port": None,
            "baudrate": 57600,
            },
        "female1": {
            "origin": None,
            "dynamixel id": 1,
            "mirror": {
                "origin": None,
                "dynamixel id": 2,
                }
            },
        "female2": {
            "origin": None,
            "dynamixel id": 3,
            "mirror": {
                "origin": None,
                "dynamixel id": 4,
                }
            },
        "female3": {
            "origin": None,
            "dynamixel id": 5,
            "mirror": {
                "origin": None,
                "dynamixel id": 6,
                }
            },
        "male1": {
            "origin": None,
            "dynamixel id": 7,
            },
        "male2": {
            "origin": None,
            "dynamixel id": 8,
            },
        "bar": {
            "origin": None,
            "dynamixel ids": [9, 10],
                "motion range": 10000,
            },
        }

    def __init__(self, owner):
        HTMLElement.__init__(self, owner)
        if not self._path.parent.is_dir():
            self._path.parent.mkdir()

        if not self._path.is_file():
            with self._path.open("w") as file:
                json.dump(self._default, file, indent=2)

        with self._path.open() as file:
            self._data = json.load(file)


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
            if not isinstance(value, (dict)):
                continue
            names = value.get("names", [])
            for name in names:
                self._data[name].update( value.get("share", {}))
                self._data[name]["name"] = name

    def __getitem__(self, key):
        return self._data[key]
        raise NotImplementedError

    def __setitem__(self, key, value):
        raise NotImplementedError

    def save(self):
        json_data = {}
        for key in self._default:
            json_data[key] = self._data[key]

        with self._path.open("w") as file:
            json.dump(json_data, file, indent=2)

    def as_dict(self):
        return deepcopy(self._data)

    def pprint(self):
        return pprint(self.as_dict())