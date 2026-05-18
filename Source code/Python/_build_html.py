from yattag import Doc, indent
from pathlib import Path


def build_css(style):
    lines = []
    for a, b in style.items():
        lines.append(f"{a}: {b};")
    return " ".join(lines)

def build_restart():
    doc, tag, text = Doc().tagtext()
    doc.asis("<!DOCTYPE html>")
    with tag("html"):
        with tag("body"):                        
            with tag("div"):
                text("Restarting server.")
            with tag("div"):
                with tag("a", href="/"):
                    text("Reload UI.")

    html = doc.getvalue()
    html = indent(html)
    content = html.encode()
    
    return content
    

def build_html(app):
    app_href = Path("app")      
        
    css_style = {
        "height": "100%",
        "display": "flex",
        "flex-direction": "column",
        "font-size": "1rem",
    }
        
    doc, tag, text = Doc().tagtext()
    doc.asis("<!DOCTYPE html>")
    with tag("html", style=build_css(css_style)):
        with tag("body", style="flex:1; display: flex; flex-direction: column; overflow: auto;"):
            with tag("div", style="display: flex; gap: 1ch;"):
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
            
            
            if isinstance(app, str):
                with tag("pre"):
                    text(str(app))
            elif isinstance(app, dict):
                build_app_from_dict(app=app)
            else:
                raise NotImplementedError(app)
                        
            # with tag("div", style="display: flex;"):
                # with tag("div", style="f"):
                    # with tag("a", href=f"/"):
                        # text("/home")
                # href = app_href
                # for name in to_render["path"]:
                    # href = href / name
                    # with tag("div", style="f"):
                        # with tag("a", href=f"/{href.as_posix()}"):
                            # text("/" + name)
                            
            # with tag("div", name="thread count", style="display: flex;"):
                    # text(f"thread count: {len(self.all_threads)}")
            
            # doc.asis(self._html_recursion(obj=to_render, ))
            

    html = doc.getvalue()
    html = indent(html)
    content = html.encode()
    
    return content