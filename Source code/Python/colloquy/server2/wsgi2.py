from email.utils import formatdate
from yattag import Doc
from urllib.parse import quote, unquote
from pathlib import Path
from colloquy.ui import console
from colloquy.logs import monitor
from colloquy.ui.console_tree import ConsoleTree
from colloquy.base import Base
from colloquy.drivers.arduino.errors import ArduinoError
from colloquy.hardware.pcb_files import catalog, gerbers, kicad_projects, orders
from colloquy.server2 import standby, updates
from colloquy.server2.remedies import remedy_html
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
# Where the zip of the KiCad projects is built and kept between
# downloads. Under local/, like every other piece of working state: it is
# a hundred megabytes that can be made again from the checkout.
DOWNLOADS_FOLDER = Path("local/downloads")
# The screenshots somebody attached to a PCB order step that went wrong
# (`hardware/pcb_files/orders.py`). The records themselves are in params.
PCB_ORDERS_FOLDER = Path("local/pcb orders")

# The most that goes to the socket in one write. A connection has
# `CONNECTION_TIMEOUT` (server2/__init__.py) for each write to leave, so
# the size of a write is a floor under the link it will work over: the
# Gerber package in a single one wants 75 KB/s, and in these, six.
PIECE = 1 << 16

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


class WSGI2(ConsoleTree, Base):
    def __init__(self, server, environ, start_response, db_path=None):
        super().__init__(owner=server)
        self._server = server
        self._colloquy = server.colloquy
        self._db_path = db_path
        self._environ = environ
        self._start_response = start_response
        self._base_path = None
        self._status, self._headers, self._content = self._parse()

    def __iter__(self):
        self._start_response(self._status, self._headers)
        if isinstance(self._content, bytes):
            # In pieces though it is all in hand - see PIECE. Anything
            # that fits in one goes out exactly as it always did.
            if len(self._content) <= PIECE:
                yield self._content
                return
            for start in range(0, len(self._content), PIECE):
                yield self._content[start : start + PIECE]
            return
        # A download too big to hold whole (the KiCad projects) arrives
        # as an iterable of pieces rather than as bytes.
        yield from self._content

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

    def _parse(self):
        args = self._parse_path()
        self._root = Path("app" if args[:1] == ("app",) else "home")

        # With the main PCB out of the rack the tree is not served at
        # all - see `_board_is_out`. Everything that does not go through
        # the tree is answered as usual, which is what leaves the
        # downloads, the restart and the way back all reachable.
        board_is_out = self._board_is_out()

        if args and args[0] == "pcb-order":
            # Ahead of the gate below, which turns every POST away while
            # the board is out: ordering its replacement is what that
            # page is for, and the order's presses are forms.
            return orders.response(
                tuple(args[1:]),
                self._environ,
                orders.book_of(self.colloquy),
                PCB_ORDERS_FOLDER,
            )

        if self._environ.get("REQUEST_METHOD") == "POST":
            if board_is_out:
                return self._redirect("/")
            return self._parse_post(*args)

        if not args:
            if board_is_out:
                return self._parse_standby()
            return self._parse_app()

        key, *leftovers = args
        if key == "thread-log" and not leftovers:
            if board_is_out:
                return self._redirect("/")
            return monitor.response(self._environ)
        if key == "pcb":
            return catalog.response(leftovers)
        if key == "live":
            # Off the lock: it only ever *tries* it (ui/live.py).
            return self._parse_live(*leftovers)
        if key == "emergency-stop":
            return self._parse_emergency_stop(*leftovers)

        if key == "shutdown":
            return self._parse_shutdown(*leftovers)

        if key == "unmount-main-pcb":
            return self._parse_unmount_main_pcb(*leftovers)

        if key == "mount-main-pcb":
            return self._parse_mount_main_pcb(*leftovers)

        if key == "update-status":
            return self._parse_update_status(*leftovers)

        if key == "download":
            return self._parse_download(*leftovers)

        if key == "virtual-panel":
            return self._parse_virtual_panel(*leftovers)

        if key == "restart":
            return self._parse_restart(*leftovers)

        if key == self._root.name:
            if board_is_out:
                # One address for the one page there is. A bookmark or a
                # tab left open on a node lands here rather than on a 404
                # about a tree that is deliberately not being served.
                return self._redirect("/")
            if leftovers[:1] == ["virtual drivers"] and self.colloquy.is_simulated:
                return self._redirect(quote("/" + "/".join(("app", "simulation", *leftovers[1:]))))
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
        except ArduinoError as error:
            # The same page, for the same kind of fault met while
            # *rendering* rather than while running a command - a reading
            # that has to ask the board something.
            return self._parse_command_failed(args, CommandFailed((), error))
        self._base_path = Path(*to_render["path"])

        return console.page(self, to_render, installation=True)

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

    def _parse_command_failed(self, args, failure):
        """A command raised. Say what failed, and where to go next.

        The same trade as _parse_not_found above, made for the same
        reason and with the same limit - but drawn around what raised
        rather than around its type, which is what stopped this being a
        new catch every time a different exception found its way out.

        **Why it is safe to answer rather than to stop.** Server2.wsgi
        emergency-stops on an unhandled exception because the exception
        kills the HTTP loop, and a running thread would then go on moving
        with no page left to stop it. Answering keeps the loop, so the
        page is still there - EMERGENCY STOP included - and the thing the
        catch-all exists to protect against cannot happen. Twice now the
        cure has been worse than the fault: a board carrying last month's
        sketch, and a COM number remembered from a machine the board is no
        longer plugged into, each took the whole server down along with
        the pages that fix them.

        The limit is unchanged. Everything raised *outside* a command -
        the walk, the render, the parse - still propagates and still
        emergency-stops, because there the process really is somewhere
        nobody can describe.
        """
        error = failure.error
        where = "/" + "/".join((self._root.name,) + args)
        self.log(f"Command failed on {where}: {type(error).__name__}: {error}")

        # The node the command hangs off, so "back" does not re-run the
        # thing that just failed. Everything from "call" on is the command
        # and its arguments - see ui/tree.py.
        node = args[: args.index("call")] if "call" in args else args
        command = "/".join(str(part) for part in failure.command)

        status = "200 OK"
        headers = [("Content-Type", "text/html; charset=utf-8")]

        doc, tag, text = Doc().tagtext()
        with tag("div"):
            with tag("strong"):
                text(f"{command} failed." if command else "That did not work.")
        with tag("div"):
            text(f"{type(error).__name__}: {error}")
        with tag("div"):
            text(
                "The installation is still running and this page is still "
                "here - nothing was stopped."
            )

        remedy = remedy_html(error)
        if remedy is not None:
            doc.asis(remedy)

        with tag("div"):
            with tag("a", href="/" + "/".join((self._root.name,) + node)):
                text("back")
        with tag("div"):
            with tag("a", href="/app"):
                text("home")

        return status, headers, doc.getvalue().encode()

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

    def _homing_lines(self, arrived):
        """What the goodbye page says about the servos. Three cases.

        There were two, and the missing one was being reported as the
        wrong one of the pair: a run that never opened the servo bus
        homes nothing, which `power_down` correctly does not call a
        failure - so the page said "Everything reached its origin; torque
        is off" about an installation where nothing had been moved and no
        torque had been cut.

        That is the one page somebody reads before pulling a cable out,
        so it is the last page in the program that should be reassuring
        about something it did not do.
        """
        if not self.colloquy.servos_were_opened:
            return [
                "The servo bus was never opened this run, so nothing was "
                "homed and there was no torque to cut. Every servo is "
                "exactly as the last run left it."
            ]
        if arrived:
            return ["Everything reached its origin; torque is off."]
        return [
            "WARNING: not everything reached its origin before torque was "
            "cut. A servo powered down away from its origin loses its turn "
            "count - check the bar before trusting its calibration."
        ]

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

        if not main_pcb.is_mounted:
            # A stale link, or this page loaded again. The board is
            # already noted as out, and running the sequence a second
            # time would do exactly one thing: stop the server, on a
            # machine whose front page is now the downloads and whose
            # updates only arrive while it is up.
            return self._redirect("/")

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
        lines.extend(self._homing_lines(arrived))
        lines.append("")
        lines.append("The server is stopped and the main PCB is noted as unmounted.")
        lines.append("It is now safe to disconnect the Arduino and the U2D2.")
        lines.append("")
        lines.append(
            "Start the app again for the Gerbers and the KiCad projects of "
            "the boards that replace it. When a board is back in the rack: "
            'press "the new PCB is mounted" on that front page.'
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
        lines.extend(self._homing_lines(arrived))
        lines.append("Goodbye!")
        content = "\n".join(lines).encode()

        return status, headers, content

    def _parse_restart(self, *back):
        """Re-exec the process, and offer the way back to where it was
        pressed.

        `back` is the app path `_html_restart_link` put after `/restart/`,
        so `reload` lands on the node that was being looked at. Without
        one - the emergency-stop page's link, or a typed URL - it is the
        front page, as it always was. The tree's open and shut is in
        memory and does not survive the exec, and does not need to: the
        walk to a node follows `snapshot_children`, which is what
        `refresh` relies on too.
        """
        self.colloquy.shutdown()
        self.colloquy.join_all()
        self.shutdown_event.set()
        self.restart_event.set()

        content_type = "text/html; charset=utf-8"
        status = "200 OK"
        headers = [("Content-Type", content_type)]

        # Quoted back, since `_parse_path` unquoted it on the way in:
        # "main pcb" is a page somebody restarts from.
        reload_path = quote("/" + "/".join(back), safe="/")

        doc, tag, text = Doc().tagtext()
        with tag("div"):
            with tag("a", href=reload_path):
                text("reload")

        html = doc.getvalue()
        content = html.encode()

        return status, headers, content

    # --- while the main PCB is out ---------------------------------------

    def _redirect(self, location):
        return "303 See Other", [("Location", location)], b""

    def _board_is_out(self):
        """Is the main PCB noted as out of the rack?

        Then the tree is not served, and that is the whole of what keeps
        the drivers from being activated: there is no Arduino and no
        servo bus to drive, and with no page that reaches a node there is
        no link that can start one. `main.py` skips opening the hardware
        on the same note, and the exposition schedule refuses to start
        against it, so nothing starts by itself either.

        Asked of the note and not of the hostname. The note is what
        `main.py` read at startup, so the page and the process agree by
        construction - and a development machine can be put in this state
        to look at it.
        """
        return not self.colloquy.hardware.main_pcb.is_mounted

    def _parse_standby(self):
        """The front page with the board out: the two downloads and the
        way back. See `standby.py`."""
        headers = [("Content-Type", "text/html; charset=utf-8")]
        return "200 OK", headers, standby.page(self.colloquy)

    def _parse_mount_main_pcb(self, *_ignored):
        """Note the board as back, and restart onto the usual page.

        A route, for `/unmount-main-pcb`'s reason turned round: it ends
        with the server restarting, and the last thing it says has to be
        that. It is also not a command anybody could reach - the tree is
        not served while the board is out.

        The restart is what "activates the drivers". Both ports are
        opened once, by `main.py` at startup, and a process that came up
        with the board out never opened them; re-running is the one
        sequence that is known to leave everything in the state a normal
        start leaves it in.

        **Nothing starts moving.** The piece is started from the page or
        by the schedule, as on any other start - a board that has never
        been powered in this rack is the last thing to hand to a clock.
        """
        main_pcb = self.colloquy.hardware.main_pcb
        if main_pcb.is_mounted:
            # A stale link, or this page loaded again after the restart
            # it caused. Nothing to do, and certainly not a second
            # restart.
            return self._redirect("/")

        main_pcb.remount()

        self.colloquy.shutdown()
        self.colloquy.join_all()
        self.shutdown_event.set()
        self.restart_event.set()

        headers = [("Content-Type", "text/html; charset=utf-8")]
        content = standby.restarting_page(
            self.colloquy.repository,
            "The new PCB is noted as mounted",
            (
                "The server is restarting to open the Arduino and the U2D2. "
                "The usual page comes back in a few seconds.",
                "If either link does not open, that page says which and why "
                "under 'startup problems'. Nothing starts moving by itself.",
            ),
        )
        return "200 OK", headers, content

    def _parse_update_status(self, *_ignored):
        """What the update banner should say now, for the script that
        keeps it true on an open page. Reads a handful of fields off the
        repository and nothing else - never the tree, so it answers while
        a command holds the lock, and while the board is out."""
        headers = [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Cache-Control", "no-store"),
        ]
        return "200 OK", headers, updates.status_json(self.colloquy.repository)

    def _parse_download(self, *parts):
        """The Gerbers, or the KiCad projects, as a zip.

        Routes rather than tree commands because the answer is a file. It
        also means neither touches the command lock, so a hundred
        megabytes being sent holds up nothing.

        **Nothing raised in here may leave.** Outside a command an
        exception reaches `Server2.wsgi`'s catch-all, which emergency-
        stops the installation and shuts the server down - over a zip.
        The reasoning that answers a failed command with a page applies
        whole: saying what went wrong keeps the loop, and with it the
        page somebody would press EMERGENCY STOP on.
        """
        try:
            if parts == ("gerbers",):
                return self._download_gerbers()
            if len(parts) == 2 and parts[0] == "gerbers":
                return self._download_board(parts[1])
            if parts == ("kicad",):
                return self._download_kicad()
        except gerbers.PackageError as error:
            return self._download_unavailable("404 Not Found", str(error))
        except Exception as error:  # noqa: BLE001 - see the docstring
            self.log(f"Download {'/'.join(parts)} failed: {error!r}")
            return self._download_unavailable(
                "500 Internal Server Error", f"{type(error).__name__}: {error}"
            )
        return self._download_unavailable(
            "404 Not Found", f"there is no download called {'/'.join(parts)!r}"
        )

    def _commit(self):
        """The short hash this process is running, for a file name."""
        running = self.colloquy.repository.running or ""
        return running.split(" ")[0]

    def _attachment(self, name, length):
        return [
            ("Content-Type", "application/zip"),
            ("Content-Disposition", f'attachment; filename="{name}"'),
            ("Content-Length", str(length)),
            ("Cache-Control", "no-store"),
        ]

    def _download_gerbers(self):
        # Old bookmarks and pages must reach the same checked exports as the catalog.
        gerbers.load()
        status, headers, body = self._redirect("/pcb/all/fabrication")
        return status, headers + [("Cache-Control", "no-store")], body

    def _download_board(self, board_id):
        board = gerbers.find(gerbers.load(), board_id)
        status, headers, body = self._redirect(f"/pcb/{board.id}/fabrication")
        return status, headers + [("Cache-Control", "no-store")], body

    def _download_kicad(self):
        listed = kicad_projects.files(self.colloquy.repository.git.tracked)
        path = kicad_projects.archive(DOWNLOADS_FOLDER, listed)
        commit = self._commit()
        name = f"colloquy-kicad-{commit}.zip" if commit else path.name
        headers = self._attachment(name, path.stat().st_size)
        return "200 OK", headers, kicad_projects.chunks(path)

    def _download_unavailable(self, status, sentence):
        doc, tag, text = Doc().tagtext()
        with tag("div"):
            with tag("strong"):
                text("That download is not available.")
        with tag("div"):
            text(sentence)
        with tag("div"):
            with tag("a", href="/"):
                text("home")

        headers = [("Content-Type", "text/html; charset=utf-8")]
        return status, headers, doc.getvalue().encode()
