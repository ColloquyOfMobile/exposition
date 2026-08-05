from yattag import Doc, indent
from build_css import build_css
from pathlib import Path


def show_all(focus, app_href, nickname=None):
    doc, tag, text = Doc().tagtext()

    with tag("div", name="show_all"):
        href = app_href / Path(*focus) / "call" / "show all"
        if nickname is not None:
            href /= nickname
        with tag("a", href=f"/{href.as_posix()}"):
            text(f"show all")

    html = doc.getvalue()
    return indent(html)
