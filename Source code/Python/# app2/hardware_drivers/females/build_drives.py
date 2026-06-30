from app2.handlers import ui_handlers
from app2.thread_handler import build_thread_handler
from .build_o_drive import build_o_drive
from .build_p_drive import build_p_drive


def build_drives(number, o_drive_start_value, p_drive_start_value, arduino):
    name=f"female{number}'s drives"
    
    states = {
        "name": name,
        "handlers": ui_handlers(),
    }
    
    states["o drive"] = o_drive = build_o_drive(
        number=number,
        start_value=o_drive_start_value,
        arduino=arduino,
    )
    
    states["p drive"] = p_drive = build_p_drive(
        start_value=p_drive_start_value,
        number=number,
        arduino=arduino,
    )
    
    states["pair"] = (o_drive, p_drive)
        
    def setdown():       
        o_drive["thread"]["stop"]()
        p_drive["thread"]["stop"]()


    def setup(): 
        o_drive["thread"]["start"](started_by=states)
        p_drive["thread"]["start"](started_by=states)

    def loop():
        for drive in (o_drive, p_drive):
            if not drive["thread"]["is started"]():
                thread_handler["stop"]()
            
            update_female_neopixels(
                o_value = o_drive["counter"]["value"], 
                p_value = p_value["counter"],
            )
            
    
    thread_handler = build_thread_handler(
                                    name=name, 
                                    loop=loop, 
                                    setdown=setdown, 
                                    setup=setup,
                                )
    
    states["thread"] = thread_handler
    
    states["children"] = {
        "o drive": o_drive,
        "p drive": p_drive,
    }
    return states


# def build_update_female_neopixels(female_number):
    
    # set_head_brightness = build_set_head_brightness(
        # female_number=female_number
    # )
    # def update_female_neopixels(o_value, p_value):

        # set_head_brightness(value= max(o_value, p_value))        
        # set_body_o_brightness(value=o_value)
        # set_body_p_brightness(value=p_value)
        
        # if p_value < o_value:
            # set_feet_color(value="orange")
        # else:
            # set_feet_color(value="puce")
            
    # return update_female_neopixels
    
# def build_set_head_brightness(female_number):
    # arduino_path = Path(f"f{female_number}/head")
    # red=0
    # green=0
    # blue=0        
    # white=255
    
    # def set_head_brightness(): 
        
        # data = dict(
            # r = adjust_brightness(red),
            # g = adjust_brightness(green),
            # b = adjust_brightness(blue),
            # w = adjust_brightness(white)
            # )   

        # with self.arduino:
            # self.arduino.send(arduino_path, **data)

# def set_body_o_brightness(): pass

# def set_body_p_brightness(): pass

# def set_feet_color(): pass



# def adjust_brightness(self, value):
    # return int((value * self.brightness.value) / 100)
