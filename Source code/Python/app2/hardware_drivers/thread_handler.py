from threading import Thread, Event, Lock

def build_thread_handler(name, run, shutdown_event):
    
    states = {}
    
    states["is started"] = build_is_started(states)
    
    def start(started_by):            
        if states["is started"]():
            return
        
        states["stop event"] = Event()
        states["thread"] = thread = Thread(
            target=run, 
            name=name
            )
        thread.start()
    
    states["start"] = start
        
    return states


def build_is_started(states):
    
    def is_started():
        thread = states.get("thread")
        if thread is None:
            return False
        return thread.is_alive()
        
    return is_started