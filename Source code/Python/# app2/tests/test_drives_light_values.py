from threading import Event
# from ..hardware_drivers.drives import drives
from ..thread_handler import build_thread_handler
from ..handlers import ui_handlers

name="test drives light values"


def build(drives):
    
    def setdown():        
        for drive_pair in drives:
            drive_pair["thread"]["stop"]()

    def setup():
        for drive_pair in drives:
            drive_pair["thread"]["start"](started_by=states)

    def loop():
        for drive_pair in drives:
            if not drive_pair["thread"]["is started"]():
                thread_handler["stop"]()

    children = {
    }

    states = {
        "handlers": ui_handlers(),
        "children":children,
    }

    thread_handler = build_thread_handler(
        name=name, 
        loop=loop, 
        setdown=setdown, 
        setup=setup,
    )

    states["thread"] = thread_handler
    states["stop and wait"] = thread_handler["stop and wait"]
    children["thread"] = thread_handler
        
    for drive_pair in drives:
        # for drive in drive_pair["pair"]:
        children[drive_pair["name"]] = drive_pair
    
    return states