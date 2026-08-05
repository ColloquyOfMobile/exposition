from yattag import Doc, indent
from build_css import build_css
from pathlib import Path
from .show_all import show_all


def build_title(ui, focus, app_href, base_href, nickname):
    doc, tag, text = Doc().tagtext()
    if "opened" in ui:
        doc.asis(
            build_opened_title(
                ui=ui,
                focus=focus,
                app_href=app_href,
                nickname=nickname,
                base_href=base_href,
            )
        )
    else:
        doc.asis(
            build_closed_title(
                ui=ui,
                focus=focus,
                app_href=app_href,
                nickname=nickname,
                base_href=base_href,
            )
        )

    html = doc.getvalue()
    html = indent(html)
    return html


def build_opened_title(ui, focus, app_href, nickname, base_href):
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

        doc.asis(
            show_all(
                focus=focus,
                app_href=app_href,
                nickname=nickname,
            )
        )

    html = doc.getvalue()
    html = indent(html)
    return html


def build_closed_title(ui, focus, app_href, nickname, base_href):
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
            href = app_focus / "call" / "open" / nickname
            with tag("a", href=f"/{href.as_posix()}"):
                text(">")

        doc.asis(child_nickname(nickname, focus_path, app_href))

        doc.asis(hide(nickname, app_focus))

        # doc.asis(
        # show_all(
        # focus=focus,
        # app_href=app_href,
        # nickname=nickname,
        # )
        # )

    html = doc.getvalue()
    html = indent(html)
    return html


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
