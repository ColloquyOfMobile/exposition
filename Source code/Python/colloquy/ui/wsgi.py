# -*- coding: utf-8 -*-
# Source code/Python/colloquy/ui/wsgi.py

"""Hardware-free preview of the installation console with its own lifecycle routes."""

from email.utils import formatdate
from yattag import Doc
from urllib.parse import quote, unquote
from pathlib import Path
from colloquy.ui import console
from colloquy.logs import monitor
from colloquy.ui.console_tree import ConsoleTree
from colloquy.base import Base
from colloquy.hardware.pcb_files import catalog
from colloquy.ui.tree import CommandFailed
from wsgiref.simple_server import WSGIRequestHandler

WSGIRequestHandler.log_message = lambda *args, **kwargs: None

# Served as real external requests via /static/... (see _parse_static
# below) - not inlined into the HTML. Still entirely local (same server,
# same machine), so this works fine offline at the exhibition; it just
# isn't embedded in every page response anymore. There was a /vendor/
# root beside it until uPlot was retired on 2026-09-09 and left nothing
# vendored; the table is a dict so putting one back is one line.
_STATIC_ROOTS = {
    "static": Path(__file__).parent / "static",
    "console-assets": console.ASSETS,
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


class MockWSGI(ConsoleTree, Base):
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
        if key == "thread-log" and not leftovers:
            return monitor.response(self._environ)
        if key == "pcb":
            return catalog.response(leftovers)
        if key == "shutdown":
            return self._parse_shutdown(*leftovers)

        if key == "virtual-panel":
            return self._parse_virtual_panel(*leftovers)

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
        """Serve a file from a static asset root (static/) as a
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

        return console.page(self, to_render, installation=False)

    def _html_restart_link(self):
        """Restart, carrying the current node path for the reload link."""
        doc, tag, text = Doc().tagtext()

        back = (self._root / self._base_path).as_posix()
        with tag("a", href=f"/restart/{back}"):
            text("restart")

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

    def _parse_restart(self, *back):
        """Re-exec the process, and offer the way back to where it was
        pressed: `back` is the app path `_html_restart_link` put after
        `/restart/`, and without one `reload` is the front page.
        """
        self.colloquy.shutdown()
        self.colloquy.join_all()
        self.shutdown_event.set()
        self.restart_event.set()

        content_type = "text/html; charset=utf-8"
        status = "200 OK"
        headers = [("Content-Type", content_type)]

        # Quoted back, since `_parse_path` unquoted it on the way in.
        reload_path = quote("/" + "/".join(back), safe="/")

        doc, tag, text = Doc().tagtext()
        with tag("div"):
            with tag("a", href=reload_path):
                text("reload")

        html = doc.getvalue()
        content = html.encode()

        return status, headers, content
