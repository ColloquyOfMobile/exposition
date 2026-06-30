from .build import build as _build
from .build_drives import build_drives

number = 2
      


def build(arduino):
    
    drives = build_drives(
        number = number,
        o_drive_start_value = 12.5, 
        p_drive_start_value = 12.5, 
        arduino=arduino,
    )  
    
    return _build(
        number=number,
        drives=drives,
    )


