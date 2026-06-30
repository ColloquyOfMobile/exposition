from threading import Event, Lock
from ..thread_handler import build_thread_handler
from ..handlers import ui_handlers
from time import sleep

"""logic35_systems.ino: line 86
//act_drive
const int   internal_drive_LL = 600;      //interested floor, in samples     600 = 30 seconds
const int   internal_drive_UL = 3600;     //desperate floor, in samples     3600 = 3 minutes
const int   internal_drive_MAX = 4800;    //in samples                      4800 = 4 minutes
const int   internal_drive_adjustment_O = 1;
const int   internal_drive_adjustment_P  = 1;
int         internal_drive_O = 0;
int         internal_drive_P = 0;
int         internal_drive_state = 0;     //Undefined, Neither[Inert], O, P, OP

Starting Values (set manually)
- Male A: 0 = 600; P = 400
- Male B: 0 = 400; P = 600
- Female C: 0 = 300; P = 1200
- Female D: 0 = 600; P = 600
- Female E: 0 = 1200; P = 300
"""

"""logic35_systems.ino: line 196
const int color_orange[4] = {80, 255, 25, 16}; //GRBW/orangish
const int color_puce[4] = {180, 160, 0, 40}; //GRBW//greenish
"""
lock = Lock()

# def build_shutdown(event):
    # def shutdown():
        # event.set()
    # return shutdown

    
# shutdown_event = Event()
# shutdown = build_shutdown(event=shutdown_event)

def setdown():
    pass
    
def setup():
    pass

    
def build_drive_counter(name, start_value,):
    
    def loop():
        with lock:
            value = drive["count"]["value"]
            if value == maximum:
                return
            if value > maximum:
                value = maximum
            else:
                value += 1
            drive["count"]["value"] = value
            drive["children"]["count"]["value"] = value

        sleep(update_interval)
    
    delay_to_maximum = 60*4 # 4 min
    maximum = 100
    update_interval = delay_to_maximum / maximum
    delay_to_unsatisfication = 30 # 30 seconds
    satisfaction_threashold = delay_to_unsatisfication / update_interval
    delay_to_frustration = 60*3 # 3 min
    frustation_threashold =  delay_to_frustration / update_interval
    
    count = {"value": start_value}
    
    drive = {
        "handlers": ui_handlers(),
        "count": count,
        "step": 1,
        "max": maximum,
        "min": 0,
        "update interval": update_interval,
        "satisfaction threashold": satisfaction_threashold,
        "frustration threashold": frustation_threashold,        
    }
    
    thread_handler = build_thread_handler(
        name=name, 
        loop=loop, 
        setdown=setdown, 
        setup=setup,
    )
    
    children = {
        "update interval": {"value": update_interval},
        "count": count,
        "start value":{
            "value": start_value,
        },
        "thread": thread_handler,
    }
    
    drive.update({
        "name": name,
        "thread": thread_handler,
        "stop": thread_handler["stop"],
        "children": children,
    })
    
    return drive

