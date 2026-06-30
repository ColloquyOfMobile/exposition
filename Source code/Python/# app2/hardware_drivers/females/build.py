from pathlib import Path
from app2.handlers import ui_handlers
# from app2.hardware_drivers.drive import build_drive

def update_neopixels_mock():
    pass

def build_shutdown():
    def shutdown():
        pass
    return shutdown

def build(number, drives):    
    return {
        "female_number": number,
        "handlers": ui_handlers(),
        "shutdown": build_shutdown(),
        "drives": drives,
        "children":{
            "drives": drives,
        },
    }



    




# def build_female_P_drive(female_number, start_value):
    # drive = build_drive(
        # name=f"female{female_number}'s P drive", 
        # start_value = start_value, 
        # update_neopixels=build_update_female_neopixels(
            # female_number=1
        # ),
    # )
    # return drive    
    
# # female1_p_drive = build_drive(
    # # name="female1's P drive", 
    # # start_value=25, 
    # # update_neopixels=update_neopixels_mock,
    # # )

