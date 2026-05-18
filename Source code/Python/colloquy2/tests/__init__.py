from ..handlers import ui_handlers
from . import test_drives_light_values


STATES = {
    "handlers": ui_handlers(),
    "children":{
        "test male ligth patterns": {               
            "children":{
            }
        },
        "test female sound patterns": {
            "children":{}
        },
        "test drives light values": test_drives_light_values.STATES,
    }
}