from .females import female1, female2, female3
from app2.handlers import ui_handlers



def build(arduino):
    _female1 = female1.build(arduino=arduino)
    _female2 = female2.build(arduino=arduino)
    _female3 = female3.build(arduino=arduino)
    
    def shutdown():
        _female1["shutdown"]()
        _female2["shutdown"]()
        _female3["shutdown"]()
    
    return {
        "shutdown": shutdown,
        "handlers": ui_handlers(),
        "females": (
            _female1,
            _female2,
            _female3,
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
            "female1": _female1,
            "female2": _female2,
            "female3": _female3,
        }
    }