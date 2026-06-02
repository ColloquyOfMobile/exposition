from yattag import Doc, indent
from build_css import build_css
from pathlib import Path

def build_child(nickname, child, iframe_href, focus, app_href, base_href):
    doc, tag, text = Doc().tagtext()
    
    css = {
        "display": "flex",
        "flex-direction": "column",
        "min-height": "2rem",
        "flex": 1,
    }
    if "opened" in child:
        css["flex"] = 2
    
    with tag("div", name=nickname, style=build_css(css)):   
        if "opened" in child:
            doc.asis(
                opened_title(focus, app_href, nickname, base_href)
                )        
            doc.asis(child_as_iframe(nickname, child, focus))
            
        else:
            doc.asis(
                closed_title(child, focus, app_href, nickname, base_href)
                )

    html = doc.getvalue()
    html = indent(html)    
    return html


def opened_title(focus, app_href, nickname, base_href):
    doc, tag, text = Doc().tagtext()   
    
    focus_path = Path(*focus)
    app_focus = base_href / focus_path 
    
    css = {
        "display": "flex",
        # "flex": 1,
        "gap": "1ch",
    }
    
    with tag("div", name="title", style=build_css(css)):         
        
        with tag("div"):
            href = app_focus / "call" / "close" / nickname
            with tag("a", href=f"/{href.as_posix()}"):
                text("<")
            
        doc.asis(child_nickname(nickname, focus_path, app_href))
        
        doc.asis(hide(nickname, app_focus))

    html = doc.getvalue()
    html = indent(html)    
    return html


def closed_title(child, focus, app_href, nickname, base_href):
    doc, tag, text = Doc().tagtext()   
    
    focus_path = Path(*focus)
    app_focus = base_href / focus_path 
    
    css = {
        "display": "flex",
        # "flex": 1,
        "gap": "1ch",
    }
    
    with tag("div", name="title", style=build_css(css)):         
        
        if "children" in child:
            with tag("div"):
                href = app_focus / "call" / "open" / nickname
                with tag("a", href=f"/{href.as_posix()}"):
                    text(">")
            
            doc.asis(child_nickname(nickname, focus_path, app_href))
            
            doc.asis(hide(nickname, app_focus))
            
        elif "value" in child:
            doc.asis(as_value(nickname, child))
            
        elif "text" in child:
            doc.asis(as_text(nickname, child))
            
        else:
            raise NotImplementedError(child)

    html = doc.getvalue()
    html = indent(html)    
    return html

def as_value(nickname, child):
    doc, tag, text = Doc().tagtext()
    value = child["value"]
    with tag("div"):
        text(f"{nickname}: {value}")    
    html = doc.getvalue()
    return indent(html) 

def as_text(nickname, child):
    doc, tag, text = Doc().tagtext()
    value = child["text"]
    with tag("div"):
        with tag("strong"):
            text(f"{nickname}:") 
    # with tag("pre"):
        # text(value)    
    html = doc.getvalue()
    return indent(html) 
    

def child_nickname(nickname, focus_path, app_href):    
    doc, tag, text = Doc().tagtext()     
    
    with tag("div", name="nickname"):
        href = app_href / focus_path / nickname
        # raise NotImplementedError(href)
        with tag("a", href=f"/{href.as_posix()}", target="_parent"):
            text(f"{nickname}")
    
    html = doc.getvalue()
    return indent(html)  
    

def hide(nickname, app_focus):    
    doc, tag, text = Doc().tagtext()     
        
    with tag("div", name="hide"):
        href = app_focus / "call" / "hide" / nickname
        with tag("a", href=f"/{href.as_posix()}"):
            text("hide")
    
    html = doc.getvalue()
    return indent(html)  
    
    

def child_as_iframe(nickname, child, focus):
    doc, tag, text = Doc().tagtext()
    
    css = {
        "border": "none",
        "min-height": "2rem",
        "flex": 1,
    }
    
    src = Path("/iframe") / Path(*focus) / nickname
    # print(f"{src=}")
    
    with tag("iframe", src=src.as_posix(), style=build_css(css)):   
        pass

    html = doc.getvalue()
    html = indent(html)    
    return html   