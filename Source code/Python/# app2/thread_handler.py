from threading import Thread, Event, Lock
import traceback
from .handlers import ui_handlers
from time import time, sleep


def build_thread_handler(name, loop, setdown, setup):
    assert "/" not in name, f"'/' is need for paths ({name=})"
    
    stop_event = Event()
    
    children = {            
        "start": {
            "func": None,
        },
    }   
    
    handlers = ui_handlers()
    
    states = {
        "handlers": handlers,
        "children": children,
    }
    
    states["is started"] = is_started = build_is_started(states)
        
    states["stop"] = handlers["stop"] = stop = build_stop(
        children=children, 
        is_started=is_started, 
        name=name, 
        stop_event=stop_event,
        )
    
    states["stop and wait"] = build_stop_and_wait(stop=stop, states=states)
    
    handlers["start"] = states["start"] = build_start(
        # started_by=started_by, 
        children=children,
        is_started=is_started,
        stop=stop,
        name=name,
        loop=loop,
        setdown=setdown,
        states=states,
        setup=setup,
        stop_event=stop_event
        )
    return states

def build_start(children, is_started, name, loop, setdown, states, setup, stop, stop_event):
    
    def start(content=None, started_by=None):    
        if is_started():
            return
        
        stop_event.clear()
        children.pop("error", None)
        
        children.pop("start")
        children["stop"] = {
            "func": None,
            }
        
        states["thread"] = thread = Thread(
            target=build_run(
                name=name, 
                loop=loop, 
                setdown=setdown, 
                setup=setup,
                children=children,
                stop=stop,
                stop_event=stop_event
            ), 
            name=name
            )
        thread.start()
    return start




def build_is_started(states):
    
    def is_started():
        thread = states.get("thread")
        if thread is None:
            return False
        return thread.is_alive()
        
    return is_started

def build_run(name, loop, setdown, children, setup, stop, stop_event):
    
    def run():
        try:
            setup()
            run_unsafe(loop=loop, stop_event=stop_event)
        except Exception as error:  
            print(f"error in {name=}")
            error_dict = {
                "text": "".join(traceback.format_exception(error))
            } 
            children["error"] = error_dict
            
        finally:
            setdown()   
            stop()
            
    return  run

def run_unsafe(loop, stop_event):
    stop_event_is_set = stop_event.is_set
    while not stop_event_is_set():               
        loop()
        sleep(0.01)

def build_stop(children, is_started, name, stop_event):
    
    def stop(content=None,):            
        if stop_event.is_set():
            return
            
        stop_event.set()
        
        children.pop("stop", None)
        children["start"] = {
            "func": None,
            }
            
    return stop
    
def build_stop_and_wait(stop, states):
    
    def stop_and_wait():  
        thread = states.get("thread")
        if thread is not None:
            stop()
            thread.join()
            
    return stop