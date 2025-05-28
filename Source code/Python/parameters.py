from pprint import pprint
import json
from pathlib import Path
from server.html_element import HTMLElement
from copy import deepcopy
import serial
import serial.tools.list_ports

# class Parameter:

    # def __init__(self, owner):
        # self._owner

    # def save(self):
        # self._owner.save()


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
                "motion range": 700,
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
        self.name = "parameters"
        self._is_open = False
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

    def __getitem__(self, key):
        return self._data[key]
        raise NotImplementedError

    def __setitem__(self, key, value):
        raise NotImplementedError

    def __call__(self):
        data = self.post_data

        action = data.get("action")
        if action:
            action = action[0]
        action = self.actions.get(action, self.write_html)
        return action(**data)

        # self.write_html(environ)
        # return [self.html_doc.getvalue().encode()]

    @property
    def is_open(self):
        return self._is_open

    @property
    def colloquy(self):
        return self.owner

    @property
    def is_calibrated(self):
        return not bool(self._unset_elements)

    @property
    def _unset_elements(self):
        elements = set()
        if self["dynamixel network"]["communication port"] is None:
            elements.add("DXL com port")
        if self["arduino"]["communication port"] is None:
            elements.add("Arduino com port")

        for name in self["females"]["names"]:
            fem_param = self[name]
            if fem_param["origin"] is None:
                elements.add(f"{name}/origin")
            if fem_param["mirror"]["origin"] is None:
                elements.add(f"{name}/mirror/origin")

        for name in self["males"]["names"]:
            if self[name]["origin"] is None:
                elements.add(f"{name}/origin")

        if self["bar"]["origin"] is None:
                elements.add(f"bar/origin")
        return elements


    def save(self):
        json_data = {}
        for key in self._default:
            json_data[key] = self._data[key]

        with self._path.open("w") as file:
            json.dump(json_data, file, indent=2)

    def open(self, **kwargs):
        if self._is_open:
            return
        self.owner.opened = self
        # self._actions = {}
        self._is_open = True

    def close(self, **kwargs):
        if not self._is_open:
            return
        self._is_open = False
        self.owner.opened = None

    def as_dict(self):
        return deepcopy(self._data)

    def pprint(self):
        return pprint(self.as_dict())

    def write_html(self):
        doc, tag, text = self.html_doc.tagtext()
        if not self.is_open:
            self._write_html_open()
            return

        with tag("div", style="display: flex; flex-direction: column;"):
            with tag("div", style="display: flex; "):
                with tag("h2", style="flex: 1;" ):
                    text(self.name)
            if self.is_calibrated:
                with tag("div", style="display: flex;"):
                    with tag("div",):
                        text(f" All set :). You can close the parameters and open Colloquy!")
                    if self.is_calibrated:
                        self._write_html_action(value="params/close", label="close", func=self.close)

            for element in self._unset_elements:
                with tag("div",):
                    text(f"Set the '{element}' to open Colloquy!")

        self.colloquy.arduino.add_html()
        self.colloquy.dxl_manager.add_html()

    def _write_html_open(self):
        doc, tag, text = self.html_doc.tagtext()
        # with tag("div", style="display: flex; flex-direction: column;"):
            # with tag("div", style="display: flex;"):
                # with tag("div", ):
                    # text(self.name)
        self._write_html_action(value="params/open", label=self.name, func=self.open)

            # with tag("div", style="display: flex;"):
                # with tag("div", ):
                    # text(self.name)
                # self._write_html_action(value="params/open", label="open", func=self.open)

    def _process(self, data):
        for key, value in data.items():
            if not isinstance(value, (dict)):
                continue
            names = value.get("names", [])
            for name in names:
                self._data[name].update( value.get("share", {}))
                self._data[name]["name"] = name