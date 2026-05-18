from threading import Event
from .thread_handler import build_thread_handler

def build_shutdown(event):
    def shutdown():
        event.set()
    return shutdown

def build_start(children, thread_starter):
    
    def start(started_by):
        thread_starter(started_by)
    
    return start
    
def run():
    raise NotImplementedError
    
def build_drive(name, start_value):
    
    shutdown_event = Event()
    
    thread_handler = build_thread_handler(
        name=name, 
        run=run, 
        shutdown_event=shutdown_event
    )
    
    children = {
        "start value":{
            "value": start_value
        }
    }
    
    drive = {
        "name": name,
        "thread handler": thread_handler,
        "start": build_start(
            children=children, 
            thread_starter=thread_handler["start"]
            ),
        "shutdown": build_shutdown(event=shutdown_event),
        "children": children,
    }
    
    return drive

