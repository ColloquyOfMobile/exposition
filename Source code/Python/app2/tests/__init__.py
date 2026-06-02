from ..handlers import ui_handlers
from . import test_drives_light_values as _test_drives_light_values
from . import test_drives_timing






def build(drives):
    
    test_drives_light_values = _test_drives_light_values.build(drives=drives)
    
    def stop_and_wait():
        test_drives_light_values["stop and wait"]()
        test_drives_timing.STATES["stop and wait"]()
    
    return {
        "stop and wait": stop_and_wait,
        "handlers": ui_handlers(),
        "test drives light values": test_drives_light_values,
        "children":{
            "test male ligth patterns": {               
                "children":{
                }
            },
            "test female sound patterns": {
                "children":{}
            },
            "test drives light values": test_drives_light_values,
            "test drives timing": test_drives_timing.STATES,
        }
    }