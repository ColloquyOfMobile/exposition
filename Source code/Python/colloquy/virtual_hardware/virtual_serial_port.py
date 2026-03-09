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
            "f1/head": self._set_female_neopixel,
            "f1/bodyO": self._set_female_neopixel,
            "f1/bodyP": self._set_female_neopixel,
            "f1/feet": self._set_female_neopixel,
            "f1/light sensor": self._read_f1_sensor,
            
            "f2/head": self._set_female_neopixel,
            "f2/bodyO": self._set_female_neopixel,
            "f2/bodyP": self._set_female_neopixel,
            "f2/feet": self._set_female_neopixel,
            "f2/light sensor": self._read_sensor,
            
            "f3/head": self._set_female_neopixel,
            "f3/bodyO": self._set_female_neopixel,
            "f3/bodyP": self._set_female_neopixel,
            "f3/feet": self._set_female_neopixel,
            "f3/light sensor": self._read_sensor,
            
            "m1/ring": self._set_male_neopixel,
            "m1/p drive level": self._set_male_neopixel,
            "m1/o drive level": self._set_male_neopixel,
            "m1/light sensor/a": self._read_sensor,
            "m1/light sensor/b": self._read_sensor,
            "m1/light sensor/c": self._read_sensor,
            "m1/light sensor/d": self._read_sensor,
            
            "m2/ring": self._set_male_neopixel,
            "m2/p drive level": self._set_male_neopixel,
            "m2/o drive level": self._set_male_neopixel,
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
            states[f"female{i+1}"] = female = {}
            for name in ("head", "bodyO", "bodyP", "feet"):
                female[name] = dict(r=0, g=0, b=0)
            
            female["light sensor"] = 0
                    
        for i in range(2):
            states[f"male{i+1}"] = male = {}
            for name in ("ring", "p drive level", "o drive level"):
                male[name] = dict(r=0, g=0, b=0, w=0)
            
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

    @property
    def colloquy(self):
        return self.owner.colloquy

    def close(self):
        self._is_open = False

    def open(self):
        assert not self.is_open
        assert self._port is not None
        self._to_return = b"Hello!"
        self._is_open = True
    
    def _set_female_neopixel(self, data):
        states = self._states
        female, name = Path(data["path"]).parts
        female = female.replace("f", "female")
        neopixel = states[female][name]
        
        neopixel["r"] = data["r"]
        neopixel["g"] = data["g"]
        neopixel["b"] = data["b"]
        neopixel["w"] = data["w"]
    
    def _set_male_neopixel(self, data):
        states = self._states
        male, name = Path(data["path"]).parts
        male = male.replace("m", "male")
        neopixel = states[male][name]
        
        neopixel["r"] = data["r"]
        neopixel["g"] = data["g"]
        neopixel["b"] = data["b"]
        neopixel["w"] = data["w"]
            
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
            return params["photosensor_threashold"] - 100
        
        male = self._get_nearest_male(female="female1")
        print(f"{male=}")
        if male is None:
            return  params["photosensor_threashold"] - 100
        
        # print()
        if self._states[male]["ring"]["w"] != 0: 
            return params["photosensor_threashold"] + 100
        return params["photosensor_threashold"] - 100
    
    def _is_near_origin(self, name, dxl):
        params = self.colloquy.params
        threashold = params["near_origin_threashold"]
        origin = params[name]["dxl origin"]
        position = dxl.position
        return origin - threashold < position < origin + threashold
        
    
    def _get_nearest_male(self, female):
        males = []
        for i, dxl_id in enumerate((6, 7)):
            dxl = self.owner.dxls[dxl_id]
            name = f"male{i+1}"
            if self._is_near_origin(name, dxl):
                males.append(name)
                break
        if not males:
            return
                
        params = self.colloquy.params
        bar_dxl = self.owner.dxls[8]
        threashold = params["near_origin_threashold"]
        position = bar_dxl.position
        for male in males:
            conditions = []
            origin = params["bar"]["interaction_origins"][male][female]
            print(f"{position=}")
            print(f"{origin=}")
        
            if origin - threashold < position < origin + threashold:
                return male
        return

    def _load_possible_paths(self):
        """Read arduino code to extract the possible paths."""
        # path = Path("Source code/Arduino/colloquy_of_mobiles/colloquy_of_mobiles.ino")
        path = Path("Source code/Arduino/colloquy_of_mobiles/colloquy_of_mobiles.ino")
        text = path.read_text()

        # Expression régulière pour capturer les valeurs de path == "..."
        paths = re.findall(r'if\s*\(\s*path\s*==\s*"([^"]+)"\s*\)', text)

        # Stocker les chemins extraits
        self._possible_paths = sorted(paths)

