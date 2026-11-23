"""The operator console shared by the installation and the hardware-free preview."""
from pathlib import Path

from yattag import Doc
from colloquy.logs.monitor import active_thread_count

ASSETS = Path(__file__).parent / "static" / "console"


def page(request, state, *, installation):
    path = state["path"]
    title = path[-1] if path else "Home"
    canonical = "/" + "/".join((request._root.name, *path))
    doc, tag, text = Doc().tagtext()
    doc.asis("<!DOCTYPE html>")
    with tag("html", lang="en"):
        with tag("head"):
            doc.stag("meta", charset="utf-8")
            doc.stag("meta", name="viewport", content="width=device-width, initial-scale=1")
            with tag("title"):
                text(f"{title} · Colloquy of Mobiles")
            doc.stag("link", rel="stylesheet", href="/console-assets/console.css")
        with tag("body", **{"data-canonical": canonical}):
            with tag("header", klass="masthead"):
                with tag("a", klass="brand", href="/home"):
                    with tag("span", klass="mobile-mark", **{"aria-hidden": "true"}):
                        doc.asis("<i></i><i></i><i></i>")
                    text("Colloquy of Mobiles")
                with tag("nav", klass="server-actions", **{"aria-label": "Server controls"}):
                    with tag("details", klass="server-menu"):
                        with tag("summary"):
                            text("Server")
                        with tag("div"):
                            doc.asis(request._html_restart_link())
                            with tag("a", href="/shutdown"):
                                text("shutdown")
                    if installation:
                        with tag("a", klass="stop", href="/emergency-stop"):
                            text("EMERGENCY STOP")
            if installation:
                from colloquy.server2 import updates
                doc.asis(updates.banner_html(request.colloquy.repository, back=canonical))
            with tag("main"):
                with tag("nav", klass="crumbs", **{"aria-label": "Breadcrumb"}):
                    with tag("a", href="/home"):
                        text("Home")
                    for level, name in enumerate(path, 1):
                        with tag("a", href="/" + "/".join((request._root.name, *path[:level]))):
                            text(name)
                with tag("div", klass="page-heading"):
                    with tag("h1"):
                        text(title)
                    with tag("span", klass="mode"):
                        text(("Simulated installation" if request.colloquy.is_simulated else "Installation")
                             if installation else "Mock preview")
                with tag("section", id="explorer", klass="explorer", **{"aria-label": "Object tree"}):
                    with tag("div", klass="panel-heading"):
                        with tag("h2"):
                            text("Object tree")
                        with tag("a", klass="reload", href=canonical, title="Refresh tree values"):
                            text("Refresh values")
                    with tag("div", id="command-result", role="status"):
                        pass
                    with tag("div", name="commands", klass="controls"):
                        doc.asis(request._html_recursion(obj=state))
            for url in ("/static/svg_zoom.js", "/console-assets/console.js"):
                with tag("script", src=url):
                    pass
            if installation:
                doc.asis(updates.script_html(request.colloquy.repository))
    return "200 OK", [("Content-Type", "text/html; charset=utf-8"), ("Cache-Control", "no-store")], doc.getvalue().encode()


def thread_monitor(log_source=""):
    doc, tag, text = Doc().tagtext()
    with tag("section", id="monitor", klass="monitor", **{"aria-label": "Live thread log", "data-source": log_source}):
        with tag("div", klass="panel-heading"):
            with tag("h2"):
                text("Thread log")
            with tag("span", id="log-status", role="status"):
                text("Connecting")
        with tag("div", klass="log-toolbar"):
            with tag("select", id="source", **{"aria-label": "Log source"}):
                with tag("option", value=""):
                    text("Recent threads")
            with tag("button", id="pause", type="button"):
                text("Pause")
        with tag("div", id="log-feed", tabindex="0", **{"aria-label": "Recent log output"}):
            with tag("noscript"):
                text("Enable JavaScript for live output. ")
                text("Open a log file to read its saved output.")
        with tag("footer", klass="log-footer"):
            with tag("span", id="thread-count"):
                active = active_thread_count()
                text(f"{active} active thread" if active == 1 else f"{active} active threads")
            with tag("span", id="event-count"):
                pass
    return doc.getvalue()
