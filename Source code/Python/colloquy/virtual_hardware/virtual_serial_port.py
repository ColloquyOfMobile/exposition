from time import sleep
import json
from pathlib import Path
import re
from queue import Queue
from colloquy.base import Base

class VirtualSerialPort(Base):

    def __init__(self, owner, port=None):
        super().__init__(owner=owner)
        assert port is None, f"Port should be none to avoid opening! ({port=})"
        self._near_origin_threashold = 400
                
                    
        self._path_handlers = {
            "f1/head": self._set_neopixel,
            "f1/bodyO": self._set_neopixel,
            "f1/bodyP": self._set_neopixel,
            "f1/feet": self._set_neopixel,
            "f1/light sensor": self._read_f1_sensor,
            
            "f2/head": self._set_neopixel,
            "f2/bodyO": self._set_neopixel,
            "f2/bodyP": self._set_neopixel,
            "f2/feet": self._set_neopixel,
            "f2/light sensor": self._read_sensor,
            
            "f3/head": self._set_neopixel,
            "f3/bodyO": self._set_neopixel,
            "f3/bodyP": self._set_neopixel,
            "f3/feet": self._set_neopixel,
            "f3/light sensor": self._read_sensor,
            
            "m1/ring": self._set_neopixel,
            "m1/p drive level": self._set_neopixel,
            "m1/o drive level": self._set_neopixel,
            "m1/light sensor/a": self._read_sensor,
            "m1/light sensor/b": self._read_sensor,
            "m1/light sensor/c": self._read_sensor,
            "m1/light sensor/d": self._read_sensor,
            
            "m2/ring": self._set_neopixel,
            "m2/p drive level": self._set_neopixel,
            "m2/o drive level": self._set_neopixel,
            "m2/light sensor/a": self._read_sensor,
            "m2/light sensor/b": self._read_sensor,
            "m2/light sensor/c": self._read_sensor,
            "m2/light sensor/d": self._read_sensor,
        }
        
        self._port = port
        self._is_open = False
        # if port is not None:
            # self._is_open = True
        self._possible_paths = set()
        self._load_possible_paths()
        self._to_return = None
        self._states = states = {}
        for i in range(3):
            states[f"f{i+1}"] = female = {}
            for name in ("head", "bodyO", "bodyP", "feet"):
                female[name] = dict(r=0, g=0, b=0)
            
            female["light sensor"] = 0
                    
        for i in range(2):
            states[f"m{i+1}"] = male = {}
            for name in ("ring", "p drive level", "o drive level"):
                male[name] = dict(r=0, g=0, b=0)
            
            male[f"light sensor"] = sensors = {}
            for name in "abcd":
                sensors[name] = 0

    def readline(self):
        if self._to_return is not None:
            to_return = self._to_return
            self._to_return = None
            return to_return

        return b'{"status": "success"}'

    def write(self, data):
        if not self._is_open:
            raise AssertionError(f"Port should be open before using it.")
        data = data.decode()
        data = json.loads(data)
        path = data["path"]
        assert path in self._possible_paths, f"{path=}, {self._possible_paths=}"
        self._to_return = self._path_handlers[path](data)
        if path.endswith("sensor"):
            self._to_return = "10".encode()

    @property
    def is_open(self):
        return self._is_open

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, value):
        self._port = value

    @property
    def name(self):
        return self._port

    def close(self):
        self._is_open = False

    def open(self):
        assert not self.is_open
        assert self._port is not None
        self._to_return = b"Hello!"
        self._is_open = True
    
    def _set_neopixel(self, data):
        states = self._states
        for part in Path(data["path"]).parts[:-1]:
            states = states[part]
            
        states[Path(data["path"]).parts[-1]]["r"] = data["r"]
        states[Path(data["path"]).parts[-1]]["g"] = data["g"]
        states[Path(data["path"]).parts[-1]]["b"] = data["b"]
        states[Path(data["path"]).parts[-1]]["w"] = data["w"]
            
        # if part.startswith("f"):
            # return self._check_neopixel(data)
        # raise NotImplementedError(self, data)
    
    def _check_neopixel(self, data):
        assert "r" in data, f"{data=}"
        assert "g" in data, f"{data=}"
        assert "b" in data, f"{data=}"
        assert "w" in data, f"{data=}"
        # assert "brightness" in data, f"{data=}"
    
    def _read_sensor(self, data):
        return 10
    
    def _read_f1_sensor(self, data):
        params = self.colloquy.params
        female_dxl = self.owner.dxls[1]
        bar_dxl = self.owner.dxls[8]
        if not self._is_near_origin(name="female1", dxl=female_dxl):
            return params["photosensor_threshold"] - 100
            
        if bar_dxl.position:
            bar_dxl.position
            return bar_dxl.position
        
        raise NotImplementedError(self.owner)
        return 10
    
    def _is_near_origin(self, name, dxl):
        params = self.colloquy.params
        threashold = params["near_origin_threashold"]
        origin = params[name]["origin"]
        position = dxl.position
        return origin - threashold < position < origin + threashold
        
    
    def _is_a_male_near(self, name):
        for i, dxl_id for enumerate((6, 7)):
            bar_dxl = self.owner.dxls[dxls]
        if self._is_near_origin
            
            
        params = self.colloquy.params
        bar_dxl = self.owner.dxls[8]
        threashold = params["bar"]["near_origin_threashold"]
        position = dxl.position
        conditions = []
        for origin in params["bar"]["interation_origins"][name]
            conditions.append(origin - threashold < position < origin + threashold)
        return any(conditions)
        
    
    def _is_bar_near(self, name):
        params = self.colloquy.params
        bar_dxl = self.owner.dxls[8]
        threashold = params["bar"]["near_origin_threashold"]
        position = dxl.position
        conditions = []
        for origin in params["bar"]["interation_origins"][name]
            conditions.append(origin - threashold < position < origin + threashold)
        return any(conditions)
        
        
        # name, _ = Path(data["path"]).parts
        # if name.startswith("f"):
            # return self._read_female_sensor(data)
        # raise NotImplementedError(data)
    
    # def _read_female_sensor(self, data):
        # name, _ = Path(data["path"]).parts
        # if name == "f1":
            # female_position = self.
            # male_1_position = self.
            # male_2_position = self.
            # return self._read_female_sensor(data)
        # raise NotImplementedError(data)

    def _load_possible_paths(self):
        """Read arduino code to extract the possible paths."""
        # path = Path("Source code/Arduino/colloquy_of_mobiles/colloquy_of_mobiles.ino")
        path = Path("Source code/Arduino/colloquy_of_mobiles/colloquy_of_mobiles.ino")
        text = path.read_text()

        # Expression régulière pour capturer les valeurs de path == "..."
        paths = re.findall(r'if\s*\(\s*path\s*==\s*"([^"]+)"\s*\)', text)

        # Stocker les chemins extraits
        self._possible_paths = sorted(paths)

