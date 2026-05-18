from yattag import Doc, indent
from pathlib import Path
from build_css import build_css
from .build_children import build_children
from .build_title import build_title
from .build_iframe import build_iframe2
from .show_all import show_all

NOTES = """Starting Values (set manually)
- Male A: 0 = 600; P = 400
- Male B: 0 = 400; P = 600
- Female C: 0 = 300; P = 1200
- Female D: 0 = 600; P = 600
- Female E: 0 = 1200; P = 300"""
    

def build_html(ui, app_href, iframe_href, base_href):    
        
    css_style = {
        "height": "100%",
        "display": "flex",
        "flex-direction": "column",
        "font-size": "1rem",
        "overflow": "auto",
    }
        
    doc, tag, text = Doc().tagtext()
    doc.asis("<!DOCTYPE html>")
    with tag("html", style=build_css(css_style)):
        doc.asis(head())
        doc.asis(
            body(
                ui=ui, 
                app_href=app_href, 
                iframe_href=iframe_href,
                base_href=base_href,
            )
        )
            

    html = doc.getvalue()
    html = indent(html)
    content = html.encode()
    
    return content

def body(ui, app_href, iframe_href, base_href):
    
    focus = ui["focus"]
    css_style = {
        "flex": "1",
        "display": "flex",
        "flex-direction": "column",
        "overflow": "auto",
    }
    doc, tag, text = Doc().tagtext()
    
    with tag("body", style=build_css(css_style)):
        with tag("div", name="server commands", style="display: flex; gap: 1ch;"):
            with tag("div", style=""):
                with tag("a", href="/shutdown"):
                    text("shutdown")
                    
            with tag("div", style=""):
                with tag("a", href="/restart"):
                    text("restart")
                    
            with tag("div", style=""):
                path = app_href
                with tag("a", href=f"/{path.as_posix()}"):
                    text("refresh")
        
        doc.asis(notes())
        doc.asis(
            app(
                ui=ui, 
                focus=focus, 
                app_href=app_href, 
                base_href=base_href, 
                iframe_href=iframe_href,
            )
        )

    html = doc.getvalue()
    html = indent(html)    
    return html
    

def notes():
    doc, tag, text = Doc().tagtext()
        
    with tag("div", name="text"):
        with tag("div"):
            with tag("strong"):
                text("notes:")
        with tag("pre"):
            text(NOTES)
                  
    html = doc.getvalue()
    html = indent(html)    
    return html

def head():
    doc, tag, text = Doc().tagtext()
        
    with tag("head"):
        doc.asis(styles())
        
    html = doc.getvalue()
    html = indent(html)    
    return html
    
def styles():   
    doc, tag, text = Doc().tagtext()
    with tag("style"):
        text(f"")
                  
    html = doc.getvalue()
    html = indent(html)    
    return html
    
def app(ui, focus, app_href, base_href, iframe_href):   
    doc, tag, text = Doc().tagtext()
    
    css = {
        "display": "flex",
        "flex-direction": "column",
        "flex": 1,
        "overflow": "auto",
    }
    
    with tag("div", name="app", style=build_css(css)):
        doc.asis(
            build_focus_title(
                    ui=ui, 
                    focus=focus, 
                    app_href=app_href, 
                    base_href = base_href,
                    # nickname=nickname,
            )
        )
        doc.asis(
            build_children(
                ui=ui, 
                app_href=app_href, 
                iframe_href=iframe_href,
                base_href=base_href,
                focus=focus,
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
            with tag("a", href=f"/{app_href.as_posix()}"):
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

def build_focus_title(ui, focus, app_href, base_href):
    doc, tag, text = Doc().tagtext()
    
    css = {
        "display": "flex",
    }
    
    with tag("div", name="title", style=build_css(css)):
        doc.asis(
            focus_ui(focus, app_href)
        )
        doc.asis(
            show_all(
                focus=focus, 
                app_href=app_href,
            )
        )
                    
    html = doc.getvalue()
    html = indent(html)    
    return html