from yattag import Doc, indent
from build_css import build_css
from pathlib import Path
from .build_child import build_child
from .build_children import build_children


def build_div(ui, app_href, iframe_href, base_href, focus):
    doc, tag, text = Doc().tagtext()
    
    is_root = (base_href == app_href)
    is_opened = ("opened" in ui)
    
    css = {
        "display": "flex",
        "flex-direction": "column",
        "flex": 1,
        "overflow": "auto",
    }
    
    if not is_root:
        if is_opened:
            css["flex"] = 2
    
    with tag("div", name="app", style=build_css(css)):
        # focus = ui["focus"]
        if is_root:
            doc.asis(
                    build_children(
                        # nickname=nickname, 
                        ui=ui, 
                        focus=focus,
                        iframe_href=iframe_href,
                        base_href=base_href,
                        app_href=app_href,
                    )
                )
        else:
            if is_opened:
                doc.asis(
                    build_children(
                        # nickname=nickname, 
                        ui=ui, 
                        focus=focus,
                        iframe_href=iframe_href,
                        base_href=base_href,
                        app_href=app_href,
                    )
                )
            
    html = doc.getvalue()
    html = indent(html)    
    return html  
   

# def children2(ui, iframe_href, focus, app_href):
    # doc, tag, text = Doc().tagtext()  
    
    # css = {
        # "display": "flex",
        # "flex-direction": "column",
        # "flex": 1,
        # "gap": "0.5rem",
        # "min-height": "0px",
    # }
                
    # with tag("div", name="children", style=build_css(css)):
        # children = ui["children"]
        # for nickname in sorted(children):
            # child = children[nickname]
            # if "hidden" in child:
                # continue
            # doc.asis(
                # build_child(
                    # nickname=nickname, 
                    # child=child, 
                    # iframe_href=iframe_href,
                    # focus=focus,
                    # app_href=app_href,
                    # base_href=app_href,
                    # )
            # )
                    
    # html = doc.getvalue()
    # html = indent(html)    
    # return html

    