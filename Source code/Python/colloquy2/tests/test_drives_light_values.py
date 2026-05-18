


def start(content):
    raise NotImplementedError


STATES = {
    "handlers": {
        "start": start,
    }, 
    "children":{
        "start": {
            "func": None,
        },
    }
}