from threading import Event
from time import time
from datetime import timedelta
from ..hardware_drivers.drive_counter import build_drive_counter
from ..thread_handler import build_thread_handler
from ..handlers import ui_handlers

name="test drives timing"

    
test_drive = build_drive_counter(
    name="test drive", 
    start_value=0, 
    )

def setdown():
    test_drive["thread"]["stop"]()

def setup():
    test_drive["thread"]["start"](started_by=STATES)
    STATES["started at"] = time()

def loop():    
    thread = test_drive["thread"]
    is_started = thread["is started"]
    count = test_drive["count"]
    seconds_elapsed = round(time() - STATES["started at"])
    if seconds_elapsed > 60:
        minutes = seconds_elapsed // 60
        seconds = seconds_elapsed % 60
        seconds_elapsed_as_string = f"{minutes}min {seconds}s"
    else:
        seconds_elapsed_as_string = f"{seconds_elapsed}s"
    
    STATES["children"]["second elapsed"]["value"] = seconds_elapsed_as_string
    if count["value"] >= 100:
        thread_handler["stop"]()
        return
    
    if not is_started():
        raise Exception(f"Shouldn't stop by itself")
            

children = {
}

STATES = {
    "handlers": ui_handlers(),
    "children":children,
}

thread_handler = build_thread_handler(
    name=name, 
    loop=loop, 
    setdown=setdown, 
    setup=setup,
)

STATES["thread"] = thread_handler
STATES["stop and wait"] = thread_handler["stop and wait"]
children["thread"] = thread_handler
STATES["children"]["second elapsed"] = {"value": 0}
STATES["children"]["test drive"] = test_drive