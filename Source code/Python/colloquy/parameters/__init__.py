from pprint import pprint
import json
from pathlib import Path
from copy import deepcopy
import serial
import serial.tools.list_ports
# from colloquy.wsgi.root.body.workspace.item import Item, HTML as _HTML
# from colloquy.colloquy_item import ColloquyItem
# from colloquy.wsgi.root.body.workspace.share_commands import Commands
from colloquy.base import Base
from .defaults import DEFAULTS

class Parameters(Base):


    def __init__(self, owner):
        super().__init__(owner=owner)
        self._file = Path("local/parameters.json")
        # self._html = HTML(owner=self)
        # self._commands = Commands(owner=self)
        if not self.file.parent.is_dir():
            self.file.parent.mkdir()

        if not self.file.is_file():
            with self.file.open("w") as file:
                json.dump(DEFAULTS, file, indent=2)

        with self.file.open() as file:
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
        # raise NotImplementedError

        # TODO move the process into the as_dict and the __getitem__
        self._process(self._data)

    # def __getitem__(self, key):
        # return self._data[key]

    # def __setitem__(self, key, value):
        # if not isinstance(value, ColloquyItem):
            # raise NotImplementedError(f"{key=}, {value=}")
        # Item.__setitem__(self, key, value)

    # def __call__(self):
        # if not self.is_opened:
            # self.open()

    def get(self, key):
        return self._data[key]

    def set(self, key, value):
        self._data[key] = value
        self.save()

    @property
    def name(self):
        return "parameters"

    @property
    def file(self):
        return self._file

    @property
    def is_calibrated(self):
        return not bool(self._unset_elements)

    @property
    def _unset_elements(self):
        elements = set()
        if self.get("dynamixel network")["communication port"] is None:
            elements.add("DXL com port")
        if self.get("arduino")["communication port"] is None:
            elements.add("Arduino com port")

        for name in self.get("females")["names"]:
            fem_param = self.get(name)
            if fem_param["origin"] is None:
                elements.add(f"{name}/origin")
            if fem_param["mirror"]["origin"] is None:
                elements.add(f"{name}/mirror/origin")

        for name in self.get("males")["names"]:
            if self.get(name)["origin"] is None:
                elements.add(f"{name}/origin")

        if self.get("bar")["origin"] is None:
                elements.add(f"bar/origin")
        return elements


    def save(self):
        json_data = {}
        for key in DEFAULTS:
            value = self._data[key]
            # print(value)
            json_data[key] = value

        with self._path.open("w") as file:
            json.dump(json_data, file, indent=2)

    def close(self, **kwargs):
        return self.commands.close()
        # self.owner.opened = None

    def as_dict(self):
        return deepcopy(self._data)

    def pprint(self):
        return pprint(self.as_dict())

    def _process(self, data):
        for key, value in data.items():
            if not isinstance(value, (dict)):
                continue
            names = value.get("names", [])
            for name in names:
                self._data[name].update( value.get("share", {}))
                self._data[name]["name"] = name




# class HTML(_HTML):

    # def _call_body(self):
        # doc, tag, text = self.doc.tagtext()
        # if self.owner.is_calibrated:
            # with tag("div", style="display: flex;"):
                # with tag("div",):
                    # text(f" All set :). You can close the parameters and open Hardware!")
            # return

        # for element in self._unset_elements:
            # with tag("div",):
                # text(f"Set the '{element}' to open Hardware!")

        # self.hardware.arduino.add_html()
        # self.hardware.dxl_manager.add_html()



