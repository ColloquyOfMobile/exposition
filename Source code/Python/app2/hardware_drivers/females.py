from .drive import build_drive


def build_shutdown(drives):
    def shutdown():
        for drive in drives:
            drive["shutdown"]()
    return shutdown

def build_female(o_drive, p_drive):    
    return {
            "shutdown": build_shutdown((o_drive, p_drive)),
            "drives": (o_drive, p_drive),
            "children":{
                "drives": {
                    "children":{
                        "O": o_drive,
                        "P": p_drive,
                        },
                    },
                },
            }
    

female1 = build_female(
    o_drive=build_drive(name="female1/o drive", start_value=300), 
    p_drive=build_drive(name="female1/p drive", start_value=1200),
    )
female2 = build_female(
    o_drive=build_drive(name="female2/o drive",start_value=600), 
    p_drive=build_drive(name="female2/p drive",start_value=600),
)
female3 = build_female(
    o_drive=build_drive(name="female3/o drive",start_value=1200), 
    p_drive=build_drive(name="female3/p drive",start_value=300),
    )

