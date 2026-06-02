from pathlib import Path
from app2.hardware_drivers.drive_counter import build_drive_counter
from app2.handlers import ui_handlers
from app2.thread_handler import build_thread_handler


def build_o_drive(number, start_value, arduino):
    name =  f"female{number}'s O drive"
    
    states = {
        "handlers": ui_handlers(),
        "name": name,
    }
    
    counter = build_drive_counter(
        name=f"female{number}'s O drive counter",
        start_value= start_value,
        )
        
    states["counter"] = counter
    
    update_neopixels = build_update_neopixel(female_number=number, arduino=arduino)
    
    def setdown():       
        counter["thread"]["stop"]()

    def setup(): 
        counter["thread"]["start"](started_by=states)

    def loop():
        # for drive in (o_drive, p_drive):
        if not counter["thread"]["is started"]():
            thread_handler["stop"]()
            
        update_neopixels(
            value = counter["count"]["value"], 
        )
        
    thread_handler = build_thread_handler(
                                name=name, 
                                loop=loop, 
                                setdown=setdown, 
                                setup=setup,
                            )
    
    states["thread"] = thread_handler
    
    states["children"] = {
        "thread": thread_handler,
    }
    return states

def build_update_neopixel(female_number, arduino):
    arduino_path = Path(f"f{female_number}/bodyO")
    
    # Orange color
    red=255
    green=80
    blue=25        
    white=16 
    
    def update_neopixels(value):    
            
        data = dict(
            r = adjust_brightness(brightness=value, value=red),
            g = adjust_brightness(brightness=value, value=green),
            b = adjust_brightness(brightness=value, value=blue),
            w = adjust_brightness(brightness=value, value=white)
            )   

        with arduino:
            arduino.send(arduino_path, **data)
            
    return update_neopixels





def adjust_brightness(brightness, value):
    return int((value * brightness) / 100)
    
