import json
import re
from yattag import Doc, indent
from urllib.parse import unquote, parse_qs
from pathlib import Path
from colloquy.utils import (
    export_style,
)
from colloquy.base import Base
from wsgiref.simple_server import WSGIRequestHandler

WSGIRequestHandler.log_message = lambda *args, **kwargs: None

# Served as real external requests via /static/... and /vendor/... (see
# _parse_static below) - not inlined into the HTML. Still entirely local
# (same server, same machine), so this works fine offline at the
# exhibition; it just isn't embedded in every page response anymore.
_STATIC_ROOTS = {
    "static": Path(__file__).parent / "static",
    "vendor": Path(__file__).parent / "vendor",
}
_STATIC_CONTENT_TYPES = {
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    # The hardware setup document is photographs of boards: without a type
    # the browser is handed application/octet-stream and offers to save
    # them instead of showing them.
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".svg": "image/svg+xml",
}


class WSGI2(Base):
    def __init__(self, server, environ, start_response, db_path=None):
        super().__init__(owner=server)
        self._server = server
        self._colloquy = server.colloquy
        self._db_path = db_path
        self._environ = environ
        self._start_response = start_response
        self._base_path = None
        self._root = Path("app")
        self._status, self._headers, self._content = self._parse()

    def __iter__(self):
        self._start_response(self._status, self._headers)
        yield self._content

    @property
    def shutdown_event(self):
        return self.owner.shutdown_event

    @property
    def restart_event(self):
        return self.owner.restart_event

    @property
    def colloquy(self):
        return self._colloquy

    @property
    def name(self):
        return "wsgi"

    def get_states(self, *args):
        return self.colloquy.get_states(*args)

    def _parse(self):
        args = self._parse_path()

        if self._environ.get("REQUEST_METHOD") == "POST":
            return self._parse_post(*args)

        if not args:
            return self._parse_app()

        key, *leftovers = args
        if key == "emergency-stop":
            return self._parse_emergency_stop(*leftovers)

        if key == "shutdown":
            return self._parse_shutdown(*leftovers)

        if key == "unmount-main-pcb":
            return self._parse_unmount_main_pcb(*leftovers)

        if key == "restart":
            return self._parse_restart(*leftovers)

        if key == self._root.name:
            return self._parse_app(*leftovers)

        if key in _STATIC_ROOTS:
            return self._parse_static(_STATIC_ROOTS[key], *leftovers)

        content_type = "text/text; charset=utf-8"
        status = "404 Not found"
        headers = [("Content-Type", content_type)]
        return status, headers, b""

    def _parse_static(self, root, *parts):
        """Serve a file from a static asset root (static/ or vendor/) as a
        real external resource - entirely local (same server, same
        machine), so this still works offline at the exhibition, it just
        isn't inlined into every HTML response anymore."""
        content_type = "text/plain; charset=utf-8"
        not_found = ("404 Not found", [("Content-Type", content_type)], b"")

        if not parts or ".." in parts:
            return not_found

        file_path = root.joinpath(*parts)
        if not file_path.is_file():
            return not_found

        content_type = _STATIC_CONTENT_TYPES.get(
            file_path.suffix, "application/octet-stream"
        )
        headers = [
            ("Content-Type", content_type),
            ("Cache-Control", "public, max-age=3600"),
        ]
        return "200 OK", headers, file_path.read_bytes()

    def _parse_post(self, *args):
        """Minimal POST support for text-editing UIs (see the "editor" leaf
        kind in _html_recursion). The rest of this app is pure GET-link
        navigation - path segments carry every argument, which works for
        command names and short values (the "keyboard" UI) but can't carry
        arbitrary multi-line text. This mirrors the existing GET
        .../call/<command> convention (same tree walk via snapshot_children,
        same "call" marker) but takes the command's one string argument
        from the POST body's "content" field instead of further path
        segments, and expects the resolved command to already be
        registered on the node (e.g. self["save"] = self.save) exactly
        like any other command in this tree.
        """
        not_found = lambda: self._parse_not_found(
            args, NotImplementedError("POST expects app/.../call/<command>")
        )

        if len(args) < 3 or args[0] != self._root.name:
            return not_found()

        *node_keys, marker, command = args[1:]
        if marker != "call":
            return not_found()

        obj = self.colloquy
        try:
            for key in node_keys:
                obj = obj.snapshot_children[key]
            handler = obj[command]
        except KeyError:
            return not_found()

        content_length = int(self._environ.get("CONTENT_LENGTH") or 0)
        raw_body = (
            self._environ["wsgi.input"].read(content_length)
            if content_length
            else b""
        )
        content = parse_qs(raw_body.decode("utf-8")).get("content", [""])[0]

        handler(content)

        redirect_path = self._root.joinpath(*node_keys)
        return "303 See Other", [("Location", f"/{redirect_path.as_posix()}")], b""

    def _parse_path(self):
        """Parse the path."""
        request_path = self._environ["PATH_INFO"]
        request_path = unquote(request_path)
        request_path = request_path.strip("/")
        request_path = request_path.encode("iso-8859-1").decode("utf-8")
        return Path(request_path).parts

    def _parse_app(self, *args):
        try:
            to_render = self.get_states(*args)
        except NotImplementedError as error:
            return self._parse_not_found(args, error)
        self._base_path = Path(*to_render["path"])

        # pprint4(obj=to_render)
        content_type = "text/html; charset=utf-8"
        status = "200 OK"
        headers = [("Content-Type", content_type)]

        css_style = {
            "height": "100%",
            "display": "flex",
            "flex-direction": "column",
            "font-size": "1rem",
        }

        doc, tag, text = Doc().tagtext()
        doc.asis("<!DOCTYPE html>")
        with tag("html", style=export_style(css_style)):
            with tag("head"):
                doc.stag(
                    "link", rel="stylesheet", href="/vendor/uplot/uPlot.min.css"
                )
                with tag("style"):
                    doc.asis(
                        ".md-content table { border-collapse: collapse; margin: 0.5rem 0; } "
                        ".md-content th, .md-content td { border: 1px solid #8886; "
                        "padding: 0.25rem 0.6rem; text-align: left; vertical-align: top; } "
                        ".md-content code { background: #8882; padding: 0 0.3ch; border-radius: 3px; } "
                        ".md-content pre { background: #8882; padding: 0.5rem; overflow: auto; } "
                        ".md-content pre code { background: none; padding: 0; } "
                        ".md-content del { opacity: 0.6; } "
                        # The hardware setup document carries photographs
                        # of boards, some of them wider than the column.
                        ".md-content img { max-width: 100%; height: auto; "
                        "display: block; margin: 0.5rem 0; "
                        "border: 1px solid #8886; } "
                        ".md-content blockquote { border-left: 3px solid #d02; "
                        "margin: 0.5rem 0; padding: 0.1rem 0 0.1rem 1ch; } "
                        ".scenario-title { margin: 0.25rem 0; opacity: 0.85; } "
                        ".scenario { display: flex; flex-direction: column; } "
                        ".scenario-row { display: flex; gap: 1ch; padding: 0.25rem 0; "
                        "border-bottom: 1px solid #8883; align-items: baseline; } "
                        ".scenario-time { flex: 0 0 6ch; opacity: 0.6; font-family: monospace; "
                        "font-size: 0.8rem; } "
                        ".scenario-marker { flex: 0 0 5ch; font-family: monospace; font-size: 0.8rem; } "
                        ".scenario-event .scenario-marker { color: #d08; } "
                        ".scenario-activity .scenario-marker { color: #08a; } "
                        ".scenario-problem .scenario-marker, .scenario-problem .scenario-desc "
                        "{ color: #d02; font-weight: bold; } "
                        ".scenario-desc { flex: 1; }"
                    )

            with tag(
                "body",
                style="flex:1; display: flex; flex-direction: column; overflow: auto;",
            ):
                # Must come before _html_recursion()'s output below: it
                # emits inline <script> calls to colloquyRenderChart() for
                # each chart, which needs uPlot and colloquyRenderChart
                # itself to already be defined by the time those run.
                with tag("script", src="/vendor/uplot/uPlot.iife.min.js"):
                    pass
                with tag("script", src="/static/uplot_chart.js"):
                    pass

                with tag(
                    "div", name="server commands", style="display: flex; gap: 1ch;"
                ):
                    with tag("div", style=""):
                        with tag(
                            "a",
                            href="/emergency-stop",
                            style="color: white; background: red; font-weight: bold; padding: 0 1ch;",
                        ):
                            text("EMERGENCY STOP")

                    with tag("div", style=""):
                        with tag("a", href="/shutdown"):
                            text("shutdown")

                    with tag("div", style=""):
                        with tag("a", href="/restart"):
                            text("restart")

                    with tag("div", style=""):
                        path = self._root / self._base_path
                        with tag("a", href=f"/{path.as_posix()}"):
                            text("refresh")

                doc.asis(
                    self._html_navigation(
                        to_render=to_render,
                    )
                )

                with tag("div", name="thread count", style="display: flex;"):
                    text(f"thread count: {len(self.all_threads)}")

                # Commands on the left, simulated state on the right, side
                # by side: watching what the installation does while
                # driving it used to mean alternating between two pages.
                # min-height/min-width 0 keep the two columns scrolling
                # inside themselves instead of stretching the page.
                with tag(
                    "div",
                    name="split",
                    style="flex: 1; display: flex; gap: 1ch; min-height: 0;",
                ):
                    with tag(
                        "div",
                        name="commands",
                        style="flex: 1; min-width: 0; overflow: auto; display: flex;",
                    ):
                        doc.asis(
                            self._html_recursion(
                                obj=to_render,
                            )
                        )

                    if self.colloquy.is_simulated:
                        doc.asis(self._html_virtual_panel())

                with tag("script", src="/static/svg_zoom.js"):
                    pass

        html = doc.getvalue()
        html = indent(html)
        content = html.encode()

        return status, headers, content

    def _html_virtual_state(self):
        doc, tag, text = Doc().tagtext()

        for name, node in self.colloquy.virtual_drivers.snapshot_children.items():
            values = {
                key: value["value"]
                for key, value in node._snapshot_if_opened(path=()).items()
                if isinstance(value, dict) and "value" in value
            }
            if not values:
                continue

            with tag("div", style="margin-bottom: 0.6rem;"):
                with tag("div", style="font-weight: bold; opacity: 0.75;"):
                    text(name)
                for key, value in values.items():
                    with tag(
                        "div",
                        style="display: flex; gap: 1ch; padding-left: 1ch;",
                    ):
                        # min-width:0 on both halves, or a long label (the
                        # timing node has "bar full travel (10000 units)")
                        # refuses to shrink below its text and pushes the
                        # value off the edge of the panel.
                        with tag(
                            "div",
                            style=(
                                "flex: 0 0 13ch; min-width: 0; opacity: 0.6; "
                                "overflow-wrap: anywhere;"
                            ),
                        ):
                            text(key)
                        with tag(
                            "div",
                            style="flex: 1; min-width: 0; overflow-wrap: anywhere;",
                        ):
                            text(str(value))

        return doc.getvalue()

    def _html_virtual_panel(self):
        """The panel itself.

        Rendered fresh with every page, so it shows the simulation as it
        was when the page was served - the "refresh" link at the top is
        the way to update it. That link points at the current node's own
        path, not at whatever /call/... may have led here, so refreshing
        never re-runs a command.
        """
        doc, tag, text = Doc().tagtext()

        style = {
            "flex": "0 0 38ch",
            "overflow": "auto",
            "border-left": "1px gray solid",
            "padding-left": "1ch",
            "font-family": "monospace",
            "font-size": "0.8rem",
        }
        with tag("div", name="virtual drivers", style=export_style(style)):
            with tag("div", style="font-weight: bold; margin-bottom: 0.5rem;"):
                text("VIRTUAL DRIVERS")
            doc.asis(self._html_virtual_state())

        return doc.getvalue()

    def _parse_not_found(self, args, error):
        """A mistyped/stale path segment - NotImplementedError is this
        codebase's routing idiom for "no such key" (get_focus/update walk
        snapshot_children/the states dict and raise it on a miss), not a
        sign anything is actually broken. Previously this reached
        Server2.wsgi()'s catch-all, which treats ANY unhandled exception
        as a fault serious enough to emergency-stop the hardware and take
        the whole server down - a single bad/stale link shouldn't do
        that. Logged and returned as a plain 404 instead; genuine faults
        (anything other than NotImplementedError) still propagate to that
        catch-all unchanged.
        """
        self.log(f"404: no such path /{'/'.join(('app',) + args)} ({error=})")

        content_type = "text/html; charset=utf-8"
        status = "404 Not Found"
        headers = [("Content-Type", content_type)]

        doc, tag, text = Doc().tagtext()
        with tag("div"):
            with tag("strong"):
                text("404: no such path.")
        with tag("div"):
            text("/" + "/".join(("app",) + args))
        with tag("div"):
            with tag("a", href="/app"):
                text("home")

        html = doc.getvalue()
        return status, headers, html.encode()

    def _html_navigation(self, to_render):
        doc, tag, text = Doc().tagtext()
        css_style = {
            "display": "flex",
            "overflow-x": "auto",
            "text-wrap": "nowrap",
        }
        with tag("div", name="navigation", style=export_style(css_style)):
            with tag("div"):
                with tag("a", href="/"):
                    text("/home")
            href = self._root
            for name in to_render["path"]:
                href = href / name
                with tag("div"):
                    with tag("a", href=f"/{href.as_posix()}"):
                        text("/" + name)

        html = doc.getvalue()
        return indent(html)

    def _html_recursion(self, obj):
        doc, tag, text = Doc().tagtext()

        style = {
            "margin-left": "1ch",
            "padding-left": "0.5ch",
            "border-left": "1px gray dashed",
            "display": "flex",
            "flex-direction": "column",
            "flex": "1",
            "overflow": "auto",
            "min-height": "10rem",
            "justify-content": "space-between",
        }

        with tag("div", name=obj["name"], style=export_style(style)):
            for key, value in obj.items():
                # print(f"{key=}")
                if key in (
                    "name",
                    "subject",
                    "id",
                    "path",
                    "focus",
                    "func",
                    "ref",
                    "checked",
                    "keyboard",
                    "close",
                    "open",
                    "opened",
                ):
                    continue

                if key == "value":
                    # Two shapes reach here under the literal key "value":
                    # a bare scalar (obj["value"] set directly), or the
                    # wrapped {"path", "name", "value"} leaf dict used
                    # everywhere else in this function (and by classes
                    # like LightSensor, whose _snapshot_if_opened key
                    # happens to also be "value") - unwrap the latter so
                    # it doesn't print the dict's own repr.
                    display_value = (
                        value["value"]
                        if isinstance(value, dict) and "value" in value
                        else value
                    )
                    with tag("div"):
                        text(f"value: {display_value}")
                    continue

                if not isinstance(value, dict):
                    func_path = Path(*obj["path"]) / key
                    call_path = func_path.relative_to(self._base_path)
                    path = self._root / self._base_path / "call" / call_path

                    style = {"flex": "1"}
                    with tag("div", name=key, style=export_style(style)):
                        with tag("a", href=f"/{path.as_posix()}"):
                            text(f"{key}()")
                    continue

                if "editor" in value:
                    node_path = Path(*value["path"][:-1])
                    call_path = node_path.relative_to(self._base_path)
                    save_path = self._root / self._base_path / "call" / call_path / "save"

                    style = {
                        "width": "100%",
                        "min-height": "50vh",
                        "box-sizing": "border-box",
                        "font-family": "monospace",
                        "font-size": "0.85rem",
                    }
                    with tag("div", name=key):
                        with tag(
                            "form",
                            method="post",
                            action=f"/{save_path.as_posix()}",
                            style="display: flex; flex-direction: column; gap: 0.5ch;",
                        ):
                            with tag(
                                "textarea", name="content", style=export_style(style)
                            ):
                                text(value["editor"])
                            with tag("div"):
                                with tag("button", type="submit"):
                                    text("save")
                    continue

                if "html" in value:
                    style = {
                        "overflow": "auto",
                        "max-height": "75vh",
                        "border": "1px solid #8888",
                        "padding": "0.5ch 1.5ch",
                    }
                    with tag("div", name=key, klass="md-content", style=export_style(style)):
                        doc.asis(value["html"])
                    continue

                if "chart" in value:
                    container_id = "chart-" + re.sub(
                        r"[^a-zA-Z0-9_-]+", "-", "-".join(value["path"])
                    )
                    with tag("div", name=key):
                        with tag(
                            "div",
                            style="font-size: 0.75rem; opacity: 0.7;",
                        ):
                            text(
                                "scroll to zoom - shift+scroll x only - alt+scroll y only - "
                                "drag to pan - drag an axis to rescale it - double-click to reset"
                            )
                        with tag(
                            "div", style="display: flex; gap: 1ch; margin: 0.25rem 0;"
                        ):
                            for label, action in (
                                ("zoom in", "in"),
                                ("zoom out", "out"),
                                ("zoom in x", "in-x"),
                                ("zoom out x", "out-x"),
                                ("zoom in y", "in-y"),
                                ("zoom out y", "out-y"),
                                ("reset zoom", "reset"),
                            ):
                                onclick = f"colloquyZoomChart({json.dumps(container_id)}, {json.dumps(action)})"
                                with tag(
                                    "button", type="button", onclick=onclick
                                ):
                                    text(label)
                        with tag(
                            "div",
                            id=container_id,
                            style="width: 100%; max-width: 900px;",
                        ):
                            pass
                        with tag("script"):
                            doc.asis(
                                f"colloquyRenderChart({json.dumps(container_id)}, {value['chart']});"
                            )
                    continue

                if "pre" in value:
                    style = {
                        "overflow": "auto",
                        "max-height": "70vh",
                        "border": "1px solid #8888",
                        "padding": "0.5ch 1ch",
                        "font-size": "0.85rem",
                        "white-space": "pre-wrap",
                    }
                    with tag("div", name=key):
                        with tag("pre", style=export_style(style)):
                            text(value["pre"])
                    continue

                if "svg" in value:
                    style = {
                        "overflow": "hidden",
                        "border": "1px solid #8888",
                        "cursor": "grab",
                        "touch-action": "none",
                    }
                    with tag("div", name=key):
                        with tag(
                            "div",
                            style="font-size: 0.75rem; opacity: 0.7;",
                        ):
                            text(
                                "scroll to zoom - shift+scroll to zoom x-axis only - drag to pan - double-click to reset"
                            )
                        with tag(
                            "div", **{"data-svg-zoom": ""}, style=export_style(style)
                        ):
                            doc.asis(value["svg"])
                    continue

                # print(f"{value=}")
                if value.get("opened", False):
                    if value:
                        doc.asis(self._html_if_opened(obj=value))
                    continue

                # Use the dict key rather than value["name"] for display:
                # a parent can (and does, e.g. TestNeopixels/TestSensors)
                # register the same kind of child multiple times under
                # distinct keys precisely because the child's own .name is
                # a fixed literal shared across every instance of that
                # type ("light sensor", "head", ...) - showing value["name"]
                # here made every such sibling display identical link text
                # even though their hrefs (built from the key) already
                # correctly pointed at different objects.
                name = key

                # Plain informational leaves (e.g. _snapshot_if_opened
                # entries like "sender"/"matches"/"last match") aren't real
                # openable nodes - they have no "open" handler, so drawing
                # the open-arrow/call-link below would 404/crash on click.
                if "value" in value:
                    with tag("div", name="value"):
                        text(f"{name}: {value['value']}")
                    continue

                value_path = Path(*value["path"])

                style = {"display": "flex", "gap": "1ch", "flex": "1"}

                with tag("div", name="title", style=export_style(style)):
                    with tag("div", name="open"):
                        call_path = value_path.relative_to(self._base_path)
                        path = (
                            self._root / self._base_path / "call" / call_path / "open"
                        )

                        with tag("a", href=f"/{path.as_posix()}"):
                            text(">")

                    # name = obj["name"]
                    path = self._root / value_path
                    with tag("div", name="name"):
                        with tag("a", href=f"/{path.as_posix()}"):
                            text(f"{name}")

        html = doc.getvalue()
        return indent(html)

    def _html_if_opened(self, obj):
        doc, tag, text = Doc().tagtext()
        name = obj["name"]

        style = {
            "margin-bottom": "0.5rem",
            "flex": "1",
            "overflow": "auto",
            "min-height": "10rem",
        }

        with tag("div", name="opened", style=export_style(style)):
            style = {"display": "flex", "gap": "1ch", "margin-bottom": "0.5rem"}

            with tag("div", name="title", style=export_style(style)):
                with tag("div", name="close"):
                    call_path = Path(*obj["path"]).relative_to(self._base_path)
                    path = self._root / self._base_path / "call" / call_path / "close"

                    with tag("a", href=f"/{path.as_posix()}"):
                        text("<")

                with tag("div", name="name"):
                    path = self._root / Path(*obj["path"])
                    with tag("a", href=f"/{path.as_posix()}"):
                        text(f"{name}:")

            doc.asis(self._html_recursion(obj=obj))

        html = doc.getvalue()
        return indent(html)

    def _parse_emergency_stop(self):
        """Disable torque and signal every thread to stop right now - no
        homing, no coordinated move (that's the opposite of an emergency
        stop). Unlike /shutdown, the HTTP server itself is kept alive so
        this page (and /restart) stay reachable; the hardware side is
        inert until a real process restart, since BaseThread._shutdown is
        never cleared once set.
        """
        self.colloquy.emergency_stop()

        content_type = "text/html; charset=utf-8"
        status = "200 OK"
        headers = [("Content-Type", content_type)]

        doc, tag, text = Doc().tagtext()
        with tag("div"):
            with tag("strong"):
                text("EMERGENCY STOP: torque disabled, all threads signaled to stop.")
        with tag("div"):
            text(
                "Motion is inert until the process is restarted "
                "(BaseThread._shutdown does not clear on its own)."
            )
        with tag("div"):
            with tag("a", href="/restart"):
                text("restart")

        html = doc.getvalue()
        content = html.encode()

        return status, headers, content

    def _parse_unmount_main_pcb(self):
        """Shut down, and say the board can come out.

        The same sequence as /shutdown - it *is* a shutdown - with the
        note written first (`MainPCB.unmount`) and a last line that
        answers the only question somebody standing over a screwdriver
        has. It is a route rather than a tree command because it ends
        with the server stopped: the tree re-renders the node a command
        was called on and discards whatever the command returned, which
        would leave a page full of navigation links served by a server in
        the act of stopping.
        """
        main_pcb = self.colloquy.hardware.main_pcb

        with self.colloquy.hold_commands() as held:
            arrived = main_pcb.unmount()

        self.shutdown_event.set()

        content_type = "text/plain; charset=utf-8"
        status = "200 OK"
        headers = [("Content-Type", content_type)]
        lines = [
            f"thread count: {len(self.all_threads)}",
        ]
        if not held:
            lines.append(
                "Note: a command was still running and did not finish in time; "
                "shut down anyway."
            )
        if arrived:
            lines.append("Everything reached its origin; torque is off.")
        else:
            lines.append(
                "WARNING: not everything reached its origin before torque was "
                "cut. A servo powered down away from its origin loses its turn "
                "count - check the bar before trusting its calibration."
            )
        lines.append("")
        lines.append("The server is stopped and the main PCB is noted as unmounted.")
        lines.append("It is now safe to disconnect the Arduino and the U2D2.")
        lines.append("")
        lines.append(
            "When the board is back: start the app again, then hardware > "
            'main pcb > "the main PCB is back", and restart once more.'
        )
        lines.append("")
        lines.append("Goodbye!")
        content = "\n".join(lines).encode()

        return status, headers, content

    def _parse_shutdown(self):
        # Under the command lock: the server answers several requests at
        # once now, so without it this could home every body and cut
        # torque while a command from another tab was still driving one
        # of them somewhere. Bounded, and it goes ahead regardless when
        # the wait runs out - see Colloquy.hold_commands.
        with self.colloquy.hold_commands() as held:
            # Threads down, lights off, everything home, then torque off -
            # see Colloquy.power_down. Homing before the power can go is
            # what keeps the calibration: a servo in extended position
            # mode holds its turn count in volatile memory, and the bar's
            # travel is 2.4 turns of its servo.
            arrived = self.colloquy.power_down()

        self.shutdown_event.set()

        content_type = "text/plain; charset=utf-8"
        status = "200 OK"
        headers = [("Content-Type", content_type)]
        lines = [
            f"thread count: {len(self.all_threads)}",
        ]
        if not held:
            lines.append(
                "Note: a command was still running and did not finish in time; "
                "shut down anyway."
            )
        if arrived:
            lines.append("Everything reached its origin; torque is off.")
        else:
            lines.append(
                "WARNING: not everything reached its origin before torque was "
                "cut. A servo powered down away from its origin loses its turn "
                "count - check the bar before trusting its calibration."
            )
        lines.append("Goodbye!")
        content = "\n".join(lines).encode()

        return status, headers, content

    def _parse_restart(self):
        self.colloquy.shutdown()
        self.colloquy.join_all()
        self.shutdown_event.set()
        self.restart_event.set()

        content_type = "text/html; charset=utf-8"
        status = "200 OK"
        headers = [("Content-Type", content_type)]

        doc, tag, text = Doc().tagtext()
        with tag("div"):
            with tag("a", href="/"):
                text("reload")

        html = doc.getvalue()
        content = html.encode()

        return status, headers, content
