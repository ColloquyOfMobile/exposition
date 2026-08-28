# -*- coding: utf-8 -*-
# Source code/Python/colloquy/ui/wsgi.py

"""The mock UI's renderer - the page as it is being rebuilt.

A fork of `server2/wsgi2.py`, taken the day the styling came out of it.
The two are deliberately independent for now: the installation's page
(`server2/`) keeps the look it has always had and goes on working through
the exhibition prep, while this one starts from bare markup and can be
taken apart freely without anything on the floor changing.

So expect the two to diverge, and expect a fix in one to need making
twice until they are put back together. What is here is that same
renderer minus its styling: structure, plus the hooks to hang CSS on -
`name="..."` on every div (server commands, navigation, split, commands,
title, open, name) and the classes the markdown and scenario renderers
emit (md-content, scenario-row, scenario-time, ...). The one stylesheet
linked is uPlot's, which its charts need to draw at all.

It serves its own copies of static/ and vendor/, next to this file, so
the scripts and styles this page loads can change without touching the
installation's.
"""

from email.utils import formatdate
import json
import re
from yattag import Doc, indent
from urllib.parse import unquote, parse_qs
from pathlib import Path
from colloquy.base import Base
from colloquy.ui.tree import CommandFailed
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


def _if_none_match(environ):
    """The ETags a conditional request says it already holds.

    A list rather than one value, and stripped of the `W/` weak marker,
    because both are ordinary in the header and neither is worth a stale
    photograph.
    """
    header = environ.get("HTTP_IF_NONE_MATCH")
    if not header:
        return ()
    tags = []
    for tag in header.split(","):
        tag = tag.strip()
        if tag.startswith("W/"):
            tag = tag[2:]
        tags.append(tag)
    return tuple(tags)


class MockWSGI(Base):
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
        if key == "shutdown":
            return self._parse_shutdown(*leftovers)

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

        # A validator, not a promise. This said `max-age=3600` and nothing
        # else, which tells the browser not to *ask* for an hour - so a
        # file replaced on disk went on being drawn from the old copy
        # until the hour was up, with the server serving the new bytes to
        # anything that bothered to request them. That is how Thomas's pin
        # labels stayed missing from the page on the day they were put
        # back.
        #
        # `no-cache` does not mean "do not store": it means store it and
        # check first. The check is one conditional request answered with
        # a 304 and no body, over a socket to this same machine, which is
        # what the max-age was saving in the first place.
        stat = file_path.stat()
        # Nanoseconds, not seconds: a file regenerated twice inside one
        # second at the same size is exactly the case this is here to
        # notice, and `py extract_hardware_photos.py` writes four of them
        # in a row.
        etag = f'"{stat.st_mtime_ns:x}-{stat.st_size:x}"'
        headers = [
            ("Cache-Control", "no-cache"),
            ("ETag", etag),
            ("Last-Modified", formatdate(stat.st_mtime, usegmt=True)),
        ]
        if etag in _if_none_match(self._environ):
            return "304 Not Modified", headers, b""

        headers.insert(0, ("Content-Type", content_type))
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
            self._environ["wsgi.input"].read(content_length) if content_length else b""
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
        except CommandFailed as error:
            return self._parse_command_failed(args, error)
        self._base_path = Path(*to_render["path"])

        # pprint4(obj=to_render)
        content_type = "text/html; charset=utf-8"
        status = "200 OK"
        headers = [("Content-Type", content_type)]

        doc, tag, text = Doc().tagtext()
        doc.asis("<!DOCTYPE html>")
        with tag("html"):
            with tag("head"):
                doc.stag("link", rel="stylesheet", href="/vendor/uplot/uPlot.min.css")
            with tag("body"):
                # Must come before _html_recursion()'s output below: it
                # emits inline <script> calls to colloquyRenderChart() for
                # each chart, which needs uPlot and colloquyRenderChart
                # itself to already be defined by the time those run.
                with tag("script", src="/vendor/uplot/uPlot.iife.min.js"):
                    pass
                with tag("script", src="/static/uplot_chart.js"):
                    pass

                with tag("div", name="server commands"):
                    # No emergency stop: it cuts torque on nine servos and
                    # signals every thread to give up, and there is
                    # nothing here to do that to. shutdown and restart
                    # stay - stopping and restarting this server is
                    # exactly what is wanted while working on the page.
                    with tag("div"):
                        with tag("a", href="/shutdown"):
                            text("shutdown")

                    with tag("div"):
                        with tag("a", href="/restart"):
                            text("restart")

                    with tag("div"):
                        path = self._root / self._base_path
                        with tag("a", href=f"/{path.as_posix()}"):
                            text("refresh")

                doc.asis(self._html_navigation(to_render=to_render))

                with tag("div", name="thread count"):
                    text(f"thread count: {len(self.all_threads)}")

                # Commands and simulated state, both on the page:
                # watching what the installation does while driving it
                # used to mean alternating between two of them. They sat
                # side by side until the styling came out; the markup
                # still names them, so it can again.
                with tag("div", name="split"):
                    with tag("div", name="commands"):
                        doc.asis(self._html_recursion(obj=to_render))

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

            with tag("div"):
                with tag("div"):
                    text(name)
                for key, value in values.items():
                    with tag("div"):
                        with tag("div"):
                            text(key)
                        with tag("div"):
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

        with tag("div", name="virtual drivers"):
            with tag("div"):
                text("VIRTUAL DRIVERS")
            doc.asis(self._html_virtual_state())

        return doc.getvalue()

    def _parse_not_found(self, args, error):
        """A mistyped/stale path segment - NotImplementedError is this
        codebase's routing idiom for "no such key" (get_focus/update walk
        snapshot_children/the states dict and raise it on a miss), not a
        sign anything is actually broken. It would otherwise reach
        MockServer.wsgi()'s catch-all, which treats ANY unhandled
        exception as a fault serious enough to take the whole server
        down - a single bad/stale link shouldn't do that. Logged and
        returned as a plain 404 instead; genuine faults (anything other
        than NotImplementedError) still propagate to that catch-all
        unchanged.
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

    def _parse_command_failed(self, args, failure):
        """A command raised. Say what failed, and leave the server up.

        The installation's twin of this (`server2/wsgi2.py`) carries the
        reasoning and a remedy for the two failures it can name a next
        click for. There are none here: nothing is plugged into the mock,
        so a sentence about which COM ports exist would be fiction. What
        the mock has instead is the `fail on purpose` button, which is now
        a page to look at rather than a dead server - see
        `colloquy/ui/mock.py`.
        """
        error = failure.error
        self.log(
            f"Command failed on /{'/'.join(('app',) + args)}: "
            f"{type(error).__name__}: {error}"
        )

        node = args[: args.index("call")] if "call" in args else args
        command = "/".join(str(part) for part in failure.command)

        status = "200 OK"
        headers = [("Content-Type", "text/html; charset=utf-8")]

        doc, tag, text = Doc().tagtext()
        with tag("div", name="command failed"):
            with tag("div", name="title"):
                text(f"{command} failed." if command else "That did not work.")
            with tag("div", name="error"):
                text(f"{type(error).__name__}: {error}")
            with tag("div", name="reassurance"):
                text("The server is still running and this page is still here.")
            with tag("div"):
                with tag("a", href="/" + "/".join((self._root.name,) + node)):
                    text("back")
            with tag("div"):
                with tag("a", href="/app"):
                    text("home")

        return status, headers, doc.getvalue().encode()

    def _html_navigation(self, to_render):
        doc, tag, text = Doc().tagtext()
        with tag("div", name="navigation"):
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

        with tag("div", name=obj["name"]):
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

                    with tag("div", name=key):
                        with tag("a", href=f"/{path.as_posix()}"):
                            text(f"{key}()")
                    continue

                if "editor" in value:
                    node_path = Path(*value["path"][:-1])
                    call_path = node_path.relative_to(self._base_path)
                    save_path = (
                        self._root / self._base_path / "call" / call_path / "save"
                    )

                    with tag("div", name=key):
                        with tag(
                            "form", method="post", action=f"/{save_path.as_posix()}"
                        ):
                            with tag("textarea", name="content"):
                                text(value["editor"])
                            with tag("div"):
                                with tag("button", type="submit"):
                                    text("save")
                    continue

                if "html" in value:
                    with tag("div", name=key, klass="md-content"):
                        doc.asis(value["html"])
                    continue

                if "chart" in value:
                    container_id = "chart-" + re.sub(
                        r"[^a-zA-Z0-9_-]+", "-", "-".join(value["path"])
                    )
                    with tag("div", name=key):
                        with tag("div"):
                            text(
                                "scroll to zoom - shift+scroll x only - alt+scroll y only - "
                                "drag to pan - drag an axis to rescale it - double-click to reset"
                            )
                        with tag("div"):
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
                                with tag("button", type="button", onclick=onclick):
                                    text(label)
                        with tag("div", id=container_id):
                            pass
                        with tag("script"):
                            doc.asis(
                                f"colloquyRenderChart({json.dumps(container_id)}, {value['chart']});"
                            )
                    continue

                if "pre" in value:
                    with tag("div", name=key):
                        with tag("pre"):
                            text(value["pre"])
                    continue

                if "svg" in value:
                    with tag("div", name=key):
                        with tag("div"):
                            text(
                                "scroll to zoom - shift+scroll to zoom x-axis only - drag to pan - double-click to reset"
                            )
                        with tag("div", **{"data-svg-zoom": ""}):
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

                with tag("div", name="title"):
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

        with tag("div", name="opened"):
            with tag("div", name="title"):
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

    def _parse_shutdown(self):
        self.colloquy.shutdown()
        self.colloquy.join_all()
        self.colloquy.shutdown_neopixels()
        self.colloquy.move_to_origin()
        self.colloquy.disable_torque()

        self.shutdown_event.set()

        content_type = "text/plain; charset=utf-8"
        status = "200 OK"
        headers = [("Content-Type", content_type)]
        lines = [
            f"thread count: {len(self.all_threads)}",
            "Goodbye!",
        ]
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
