from yattag import Doc, indent
from pathlib import Path
from build_css import build_css
from .build_children import build_children
    

def build_iframe2(ui, app_href, iframe_href):
        
    css_style = {
        "display": "flex",
        "flex-direction": "column",
        "font-size": "1rem",
    }
        
    doc, tag, text = Doc().tagtext()
    doc.asis("<!DOCTYPE html>")
    with tag("html", style=build_css(css_style)):
        doc.asis(head())
        doc.asis(body(ui, app_href, iframe_href))

    html = doc.getvalue()
    html = indent(html)
    content = html.encode()
    
    return content

def body(ui, app_href, iframe_href):
    doc, tag, text = Doc().tagtext() 
        
    css_style = {
        "flex": 1,
        "display": "flex",
        "flex-direction": "column",
    }
    
    with tag("body", style=build_css(css_style)):          
            
        focus = ui["focus"]
        focus_path = Path(*focus)
        
        doc.asis(
            build_children(
                ui=ui, 
                iframe_href=iframe_href,
                focus=focus,
                app_href=app_href,
                base_href=iframe_href,
                # nickname=focus[-1], 
            )
        )   
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

    
# def children(ui, app_href, iframe_href, focus):
    # doc, tag, text = Doc().tagtext()  
    
    # css = {
        # "display": "flex",
        # "flex-direction": "column",
        # "border": "none",
        # "min-height": 0,
    # }  
    
    # children = ui["children"]
    # for nickname in sorted(children):
        # child = children[nickname] 
        
        # if "hidden" in child:
            # continue
    
        # if "children" in child:                        
            # doc.asis(
                # build_children(
                    # ui=child, 
                    # iframe_href=iframe_href,
                    # focus=focus,
                    # app_href=app_href,
                    # base_href=iframe_href,
                    # nickname=nickname, 
                    # )
                # )  
                
        # elif "value" in child:
            # doc.asis(as_value(nickname=nickname, ui=child))
        # else:
            # raise NotImplementedError(child)
    
    # html = doc.getvalue()
    # # return indent(html)    

# def as_value(nickname, ui):
    # doc, tag, text = Doc().tagtext()
    # value = ui["value"]
    # with tag("div"):
        # text(f"{nickname}: {value}")    
    # html = doc.getvalue()
    # return indent(html) 
    
    
