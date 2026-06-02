from app2.hardware_drivers.drive_counter import build_drive_counter
from app2.handlers import ui_handlers
from app2.thread_handler import build_thread_handler






def build_p_drive(number, start_value, arduino):
    name =  f"female{number}'s P drive"
    states = {
        "handlers": ui_handlers(),
        "name": name,
    }
    
    counter = build_drive_counter(
        name=f"female{number}'s P drive counter",
        start_value= start_value,
        )
        
    states["counter"] = counter
    
    def setdown():       
        counter["thread"]["stop"]()


    def setup(): 
        counter["thread"]["start"](started_by=states)

    def loop():
        # for drive in (o_drive, p_drive):
        if not counter["thread"]["is started"]():
            thread_handler["stop"]()
            
        update_neopixels(
            value = counter["value"], 
        )
        
    thread_handler = build_thread_handler(
                                name=name, 
                                loop=loop, 
                                setdown=setdown, 
                                setup=setup,
                            )
    
    states["thread"] = thread_handler
    
    states["children"] = {}
    return states