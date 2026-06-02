from yattag import Doc, indent
from build_css import build_css
from pathlib import Path
from .build_title import build_title

def build_children(ui, focus, iframe_href, app_href, base_href):
    doc, tag, text = Doc().tagtext()  
    
    css = {
        "display": "flex",
        "flex-direction": "column",
        "border": "none",
        "min-height": 0,
        "flex": 1,
    } 
    
    with tag("div", name="children", style=build_css(css)):
    
        children = ui["children"]
        for nickname in sorted(children):
            # print(f"{nickname=}")
            
            child = children[nickname]
            
            if "hidden" in child:
                continue
        
            if "children" in child:                        
                doc.asis(
                    build_child(
                        ui=child, 
                        iframe_href=iframe_href,
                        focus=focus,
                        app_href=app_href,
                        base_href=base_href,
                        nickname=nickname, 
                        )
                    )
                continue
                    
            if "value" in child:
                doc.asis(as_value(nickname=nickname, value=child["value"]))
                continue
                
            if "text" in child:
                doc.asis(as_text(nickname=nickname, value=child["text"]))
                continue
            
            if "func" in child:
                doc.asis(
                    as_func(
                        focus=focus,
                        base_href=base_href,
                        nickname=nickname,),
                    )
                continue
            
            raise NotImplementedError(child)
    
    html = doc.getvalue()
    return indent(html) 

def as_text(nickname, value):
    doc, tag, text = Doc().tagtext()
    # value = child["text"]
    with tag("div"):
        with tag("div"):
            text(f"{nickname}:") 
        with tag("div", style="margin-left: 0.5ch;white-space: pre-wrap;"):
            text(value)    
    html = doc.getvalue()
    return indent(html) 

def as_value(nickname, value):
    doc, tag, text = Doc().tagtext()
    # value = ui["value"]
    with tag("div"):
        text(f"{nickname}: {value}")    
    html = doc.getvalue()
    return indent(html) 

def as_func(nickname, focus, base_href):
    doc, tag, text = Doc().tagtext()
    
    with tag("div"):
        href = base_href / Path(*focus) / "call" / nickname
        with tag("a", href=f"/{href.as_posix()}"):
            text(f"{nickname}()")
            
    html = doc.getvalue()
    return indent(html) 
    
def build_child(nickname, ui, focus, iframe_href, app_href, base_href):
    doc, tag, text = Doc().tagtext()
    css_style = {
        "display": "flex",
        "flex-direction": "column",
        "overflow": "auto",
    }
    
    if "opened" in ui:        
        css_style["flex"] = 1
        
    with tag("div", name=nickname, style=build_css(css_style)):
        doc.asis(
            build_title(
                nickname=nickname,
                ui=ui, 
                focus=focus, 
                app_href=app_href, 
                base_href=base_href)
        )
        
        if "opened" in ui:
            doc.asis(
                build_iframe(
                    iframe_href=iframe_href,
                    nickname=nickname,
                    focus=focus,
                    
                )
            )
            
    html = doc.getvalue()
    html = indent(html)    
    return html   

def build_iframe(nickname, iframe_href, focus):
    doc, tag, text = Doc().tagtext()
    
    css = {
        "border": "none",
        "min-height": "2rem",
        "flex": 1,
    }
    
    src = iframe_href / Path(*focus) 
    if nickname is not None:
        src /= nickname
    # print(f"{src=}")
    
    with tag("iframe", src=f"/{src.as_posix()}", style=build_css(css)):   
        pass

    html = doc.getvalue()
    html = indent(html)    
    return html 