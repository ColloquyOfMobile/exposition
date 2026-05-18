

def open(name, content):    
    content["children"][name]["opened"] = None 

def close(name, content):
    content["children"][name].pop("opened", None) 

def hide(name, content):    
    content["children"][name]["hidden"] = None 
    count = content.get("hidden count", 0)
    count += 1
    content["hidden count"] = count

def show_all(*args, content):
    if args:
        key = args[0]
        content = content["children"][key]
    
    for child in content["children"].values():
        child.pop("hidden", None)
        
    content["hidden count"] = 0


def ui_handlers():
    
    return {
        "open": open,
        "close": close,
        "hide": hide,
        "show all": show_all,
    }