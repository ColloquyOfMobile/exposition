import params
from pathlib import Path
import json

PARAMS = params.load(path=Path("local/params.json"))


STATES = {    
    "focus": tuple(),
    "children": {
        "params": {
                "children":{
                }
            },
        "male1": {
            "children":{
                "O drive start": {"value": 600},
                "P drive start": {"value": 400},
            },
        },
        "male2": {
            "children":{
                "O drive start": {"value": 400},
                "P drive start": {"value": 600},
            },
        },
        "female1": {
            "children":{
                "drives": {
                    "children":{
                        "O": {
                            "children":{
                                "start value":{
                                    "value": 300
                                },
                            },
                        },
                        "P": {
                            "children":{
                                "start value":{
                                    "value": 1200
                                },
                            },
                        },
                    },
                },
            },
        },
        "female2": {
            "children":{
                "O drive start": {"value": 600},
                "P drive start": {"value": 600},
            },
        },
        "female3": {
            "children":{
                "O drive start": {"value": 1200},
                "P drive start": {"value": 300},
            },
        },
    },
}

def colloquy2(*args):

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
        json.dump(STATES, f, indent=2)
        
    return content

def call(*args, content):
    if not args:
        return
        
    handlers = {
        "open": open,
        "close": close,
        "hide": hide,
        "show all": show_all,
    }
    
    key, *leftovers = args
    handlers[key](*leftovers, content=content)

def open(name, content):    
    content["children"][name]["opened"] = None 

def close(name, content):
    content["children"][name].pop("opened", None) 

def hide(name, content):    
    content["children"][name]["hidden"] = None 
    count = content.get("hidden count", 0)
    count += 1
    content["hidden count"] = count

def show_all(*args, content):
    if args:
        key = args[0]
        content = content["children"][key]
    
    for child in content["children"].values():
        child.pop("hidden", None)
        
    content["hidden count"] = 0
    