from .handlers import ui_handlers

def start(content):
    raise NotImplementedError


STATES = {
    "handlers": ui_handlers(),
    "children":{
        "test male ligth patterns": {               
            "children":{
            }
        },
        "test female sound patterns": {
            "children":{}
        },
        "test drives light values": {
            "handlers": {
                "start": start,
            }, 
            "children":{
                "start": {
                    "func": start,
                },
            }
        },
    }
}