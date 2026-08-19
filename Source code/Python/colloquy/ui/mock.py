# -*- coding: utf-8 -*-
# Source code/Python/colloquy/ui/mock.py

"""A small application to point the UI at, instead of the installation.

Working on the page normally means building the whole `Colloquy` object -
nine servos, an Arduino, a params file, threads - and then hunting for a
node that happens to show the thing being worked on. This is a stand-in:
a handful of nodes covering every kind of leaf the page can draw, every
kind of link it can offer, and nothing behind them.

Serve it and click around (on port 8088, so it cannot collide with the
installation's own server on 8087):

    py mock_ui.py

or drive it from a test with no socket at all:

    from colloquy.ui.mock import request
    status, html = request("/app/readings")

What it is *not* is a fake of the installation: no bodies, no hardware,
no threads. If a change to the UI needs one of those to be exercised, it
belongs in `pytest_tests` against the real classes, or in a scenario
under `colloquy/tests/`.
"""
import io
import json
from threading import Event

from colloquy.base import Base
from colloquy.ui import leaves, tree


class Readings(Base):
    """Leaves that only show. The counter proves the page is drawn from
    the tree each time rather than cached anywhere."""

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._draws = 0

    @property
    def name(self):
        return "readings"

    @property
    def snapshot_children(self):
        return {}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        self._draws += 1
        leaf = leaves.into(states, path)
        leaf("a number", 42)
        leaf("with a unit", "29.3 deg")
        leaf("times drawn", self._draws)
        return states


class Buttons(Base):
    """Commands: bare callables in the snapshot, which the page draws as
    links and calls through the "call" segment."""

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._said = []

    @property
    def name(self):
        return "buttons"

    @property
    def snapshot_children(self):
        return {}

    def say_hello(self, request=None):
        self._said.append("hello")

    def forget(self, request=None):
        self._said.clear()

    def fail_on_purpose(self, request=None):
        """What a command that raises looks like from the page.

        Worth having somewhere safe to press: against the installation,
        an exception escaping a request is taken for a crash and stops
        everything (MockServer.wsgi). Here it stops nothing.
        """
        raise RuntimeError("this command always fails")

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        states["say hello"] = self.say_hello
        states["forget"] = self.forget
        states["fail on purpose"] = self.fail_on_purpose
        states["said"] = leaves.value(path, "said", ", ".join(self._said) or "nothing")
        return states


class Notes(Base):
    """An editor leaf and the save command it posts to - the one place
    the page sends anything back other than by clicking a link."""

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._content = "Type something and press save."
        self["save"] = self.save

    @property
    def name(self):
        return "notes"

    @property
    def content(self):
        return self._content

    def save(self, content):
        self._content = content

    @property
    def snapshot_children(self):
        return {}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        states["editor"] = leaves.editor(path, "editor", self._content)
        return states


class Documents(Base):
    """The two ways to show text that is already formatted."""

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._notes = Notes(owner=self)

    @property
    def name(self):
        return "documents"

    @property
    def snapshot_children(self):
        return {self._notes.name: self._notes}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        states["rendered"] = leaves.html(
            path,
            "rendered",
            "<h3>A rendered document</h3><p>Markdown and timelines arrive "
            "here already turned into HTML.</p>",
        )
        states["a log"] = leaves.pre(
            path, "a log", "12:00:01 first line\n12:00:02 second line\n"
        )
        return states


class Pictures(Base):
    """A drawing that is already drawn, and one the browser draws."""

    @property
    def name(self):
        return "pictures"

    @property
    def snapshot_children(self):
        return {}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        states["a drawing"] = leaves.svg(
            path,
            "a drawing",
            '<svg width="200" height="60" xmlns="http://www.w3.org/2000/svg">'
            '<rect width="200" height="60" fill="#8884"/>'
            '<text x="10" y="35" font-size="16">an svg</text></svg>',
        )
        states["a graph"] = leaves.chart(
            path,
            "a graph",
            json.dumps(
                {
                    "data": [[0, 1, 2, 3, 4], [0, 1, 4, 9, 16], [0, 2, 4, 6, 8]],
                    "labels": ["squares", "doubles"],
                    "colors": ["#1f77b4", "#ff7f0e"],
                }
            ),
        )
        return states


class Branch(Base):
    """A node whose only content is another node - for clicking down into
    and back out of."""

    def __init__(self, owner, name, depth):
        self._name = name
        super().__init__(owner=owner)
        self._child = (
            Branch(owner=self, name=f"{name} again", depth=depth - 1)
            if depth
            else None
        )

    @property
    def name(self):
        return self._name

    @property
    def snapshot_children(self):
        return {self._child.name: self._child} if self._child else {}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        if self._child is None:
            states["bottom"] = leaves.value(path, "bottom", "nothing below this")
        return states


class MockApp(Base):
    """A root the UI can be pointed at.

    Everything the server and the renderer ask of `Colloquy` and nothing
    else: children to walk, a tree walk, and the handful of lifecycle
    calls the shutdown route makes - recorded here rather than done,
    since there is nothing to stop. No emergency stop: that one belongs
    to an application with servos to cut torque on, and the mock's
    renderer neither offers it nor answers its route.
    """

    def __init__(self):
        super().__init__(owner=None)
        self._readings = Readings(owner=self)
        self._buttons = Buttons(owner=self)
        self._documents = Documents(owner=self)
        self._pictures = Pictures(owner=self)
        self._deep = Branch(owner=self, name="deep", depth=2)
        self.called = []

    @property
    def name(self):
        return "mock"

    @property
    def is_simulated(self):
        # There is no simulated hardware behind this, so no panel for it.
        return False

    @property
    def snapshot_children(self):
        return {
            self._readings.name: self._readings,
            self._buttons.name: self._buttons,
            self._documents.name: self._documents,
            self._pictures.name: self._pictures,
            self._deep.name: self._deep,
        }

    def get_states(self, *args):
        return tree.get_states(self, *args)

    def _record(self, name):
        self.called.append(name)

    def shutdown(self):
        self._record("shutdown")

    def join_all(self):
        self._record("join_all")

    def shutdown_neopixels(self):
        self._record("shutdown_neopixels")

    def move_to_origin(self):
        self._record("move_to_origin")

    def disable_torque(self):
        self._record("disable_torque")


class OfflineServer:
    """What MockWSGI asks of a server, minus the socket."""

    def __init__(self, app=None):
        self.colloquy = app if app is not None else MockApp()
        self.owners = []
        self.name = "offline server"
        self.shutdown_event = Event()
        self.restart_event = Event()


def request(path, app=None, server=None, content=None):
    """One request against the mock, returning (status, html).

    `content` makes it a POST carrying that string as the form's content
    field - what an editor's save posts.
    """
    # Imported here rather than at module scope: the renderer pulls in
    # yattag, which a caller that only wants MockApp has no use for.
    from colloquy.ui.wsgi import MockWSGI

    if server is None:
        server = OfflineServer(app=app)

    body = b"" if content is None else f"content={content}".encode("utf-8")
    environ = {
        "PATH_INFO": path,
        "REQUEST_METHOD": "GET" if content is None else "POST",
        "QUERY_STRING": "",
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
    }

    captured = []
    wsgi = MockWSGI(
        server=server,
        environ=environ,
        start_response=lambda status, headers: captured.append((status, headers)),
    )
    html = b"".join(wsgi).decode("utf-8", errors="replace")
    return captured[0][0], html


def serve(port=None):
    """Serve the mock at http://localhost:8088/app.

    Its own server and its own renderer, not the installation's - see
    ui/wsgi.py for why the two are forked while the page is rebuilt.
    """
    from colloquy.ui.server import MockServer

    MockServer(colloquy=MockApp(), port=port)


if __name__ == "__main__":
    serve()
