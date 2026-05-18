from .female import female

STATES = {
    "children":{
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
        "female1": female(),
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
    }
}