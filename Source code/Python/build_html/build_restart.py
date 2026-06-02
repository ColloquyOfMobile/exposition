from yattag import Doc, indent
from build_css import build_css

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