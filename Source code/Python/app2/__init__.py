import params
from pathlib import Path
import json
from inspect import getsourcefile
from types import FunctionType
from . import exposition
from . import tests
from . import hardware_drivers
from .handlers import ui_handlers
from colloquy.hardware.arduino import Arduino

PARAMS = params.load(path=Path("local/params.json"))

arduino = Arduino(owner=None)

def shutdown():
    hardware_drivers["shutdown"]()
    tests["stop and wait"]()
    

def app2(*args):

    content = STATES
    
    leftovers = args
    
    focus = list()
    while leftovers:
        key, *leftovers = leftovers
        if key == "call":
            leftovers = call(*leftovers, content=content)
            continue
        
        focus.append(key)
        content = content["children"][key]
        content["focus"] = tuple(focus)
        
    with Path("local/states.json").open("w", encoding="utf-8") as f:
        json.dump(as_json2(STATES), f, indent=2)
        
    return content

def call(*args, content):
    if not args:
        return
        
    handlers = content["handlers"]
    
    key, *leftovers = args
    handlers[key](*leftovers, content=content)



def as_json2(data, _seen=None):
    if _seen is None:
        _seen = set()

    # Types simples
    if data is None or isinstance(data, (str, int, float, bool)):
        return data

    obj_id = id(data)

    # Détection de cycle
    if obj_id in _seen:
        return "<cyclic_ref>"

    # On marque l'objet comme visité
    _seen.add(obj_id)

    try:
        if isinstance(data, (list, tuple)):
            return [as_json2(e, _seen) for e in data]

        if isinstance(data, dict):
            return {
                k: as_json2(v, _seen)
                for k, v in data.items()
            }

        if isinstance(data, FunctionType):
            filename = Path(getsourcefile(data))
            filename = filename.relative_to(Path().resolve())
            return f"{filename.as_posix()}/{data.__name__}"
        
        return repr(data)

    finally:
        _seen.remove(obj_id)

hardware_drivers = hardware_drivers.build(arduino=arduino)
drives = tuple(
    female["drives"] for female in hardware_drivers["females"]
)
tests = tests.build(drives=drives)
    
STATES = {  
    "func": app2,
    "focus": tuple(),
    "shutdown": shutdown,
    "hardware drivers": hardware_drivers,
    "tests": tests,
    "handlers": ui_handlers(),
    "children": {
        "hardware drivers": hardware_drivers,
        "tests": tests,
        "exposition": exposition.STATES,        
    },
}