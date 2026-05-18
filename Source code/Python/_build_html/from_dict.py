from yattag import Doc, indent
from build_css import build_css
from pathlib import Path
from .build_child import build_child


def from_dict(ui, app_href, iframe_href):
    doc, tag, text = Doc().tagtext()
    
    css = {
        "display": "flex",
        "flex-direction": "column",
        "flex": 1,
        "overflow": "auto",
    }
    
    with tag("div", name="app", klass="test", style=build_css(css)):
        focus = ui["focus"]
        doc.asis(part1(ui, focus, app_href))
        doc.asis(
                children2(
                    ui=ui, 
                    iframe_href=iframe_href, 
                    focus=focus,
                    app_href=app_href,
                    )
            )    
        
    html = doc.getvalue()
    html = indent(html)    
    return html

def focus_ui(focus, app_href):
    doc, tag, text = Doc().tagtext()
    
    css = {
        "display": "flex",
        "flex": 1,
    }
    
    with tag("div", name="focus", style=build_css(css)):
        with tag("div"):
            with tag("a", href=f"/"):
                text("/home")
        href = app_href
        for name in focus:
            href = href / name
            with tag("div"):
                with tag("a", href=f"/{href.as_posix()}"):
                    text("/" + name)
                    
    html = doc.getvalue()
    html = indent(html)    
    return html

def part1(ui, focus, app_href):
    doc, tag, text = Doc().tagtext()
    
    css = {
        "display": "flex",
    }
    
    with tag("div", name="part1", style=build_css(css)):
        doc.asis(
            focus_ui(focus, app_href)
        )
        hidden_count = ui.get("hidden count", 0)
        if hidden_count:
            doc.asis(
                show_all(count=hidden_count, focus=focus, app_href=app_href)
            )
                    
    html = doc.getvalue()
    html = indent(html)    
    return html

def show_all(count, focus, app_href,):
    doc, tag, text = Doc().tagtext()     
        
    with tag("div", name="show_all"):
        href = app_href / Path(*focus) / "call" / "show all"
        with tag("a", href=f"/{href.as_posix()}"):
            text(f"show all ({count} hidden)")
    
    html = doc.getvalue()
    return indent(html)  
   

def children2(ui, iframe_href, focus, app_href):
    doc, tag, text = Doc().tagtext()  
    
    css = {
        "display": "flex",
        "flex-direction": "column",
        "flex": 1,
        "gap": "0.5rem",
        "min-height": "0px",
    }
                
    with tag("div", name="children", style=build_css(css)):
        children = ui["children"]
        for nickname in sorted(children):
            child = children[nickname]
            if "hidden" in child:
                continue
            doc.asis(
                build_child(
                    nickname=nickname, 
                    child=child, 
                    iframe_href=iframe_href,
                    focus=focus,
                    app_href=app_href,
                    base_href=app_href,
                    )
            )
                    
    html = doc.getvalue()
    html = indent(html)    
    return html

    