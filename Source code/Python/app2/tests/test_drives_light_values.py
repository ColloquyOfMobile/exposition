from ..hardware_drivers.drives import drives

def shutdown():
    for drive in drives:
        drive["shutdown"]()

def build_start(children):
    
    def start(content):
        for drive in drives:
            drive["start"](started_by=content)
            children[drive["name"]] = drive
        children.pop("start")
        children["stop"] = {
            "func": None,
            }
    
    return start


children = {
        "start": {
            "func": None,
        },
    }

STATES = {
    "handlers": {
        "start": build_start(children),
    }, 
    "children":children,
}