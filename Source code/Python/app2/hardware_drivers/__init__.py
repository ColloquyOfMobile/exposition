from .females import female1, female2, female3

def shutdown():
    female1["shutdown"]()
    female2["shutdown"]()
    female3["shutdown"]()

STATES = {
    "females": (
        female1,
        female2,
        female3,
    ),
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
        "female1": female1,
        "female2": female2,
        "female3": female3,
    }
}