"""Unit tests for the path a typed value takes: WSGI2._parse_post.

A value box on a page posts what was typed to a command the node
registered - `self["commit"] = self.commit` - and _parse_post walks
snapshot_children to find it, exactly as a GET .../call/<command> does.

Built with __new__ against a hand-made tree, like test_leaves: none of
WSGI2.__init__'s request parsing is needed to test where a POST lands.

The case worth having tests for is the bad one. Server2.wsgi() treats any
unhandled exception in a request as an emergency stop - it disables
torque and stops the HTTP loop - so a typo in a value box, on a page a
visitor could be looking at, must not be allowed to escape.
"""
import io
from pathlib import Path
from types import SimpleNamespace

from colloquy.server2.wsgi2 import WSGI2


class FakeNode:
    """A node with one command, like any node offering a value box."""

    def __init__(self, parse=int):
        self.committed = []
        self.parse = parse
        self.children = {}

    @property
    def snapshot_children(self):
        return self.children

    def __getitem__(self, key):
        if key != "commit":
            raise KeyError(key)
        return self.commit

    def commit(self, value):
        self.committed.append(self.parse(value))


def post(node, path, content):
    """POST `content` at `path`, through the real request parsing."""
    logged = []
    body = f"content={content}".encode("utf-8")

    wsgi = WSGI2.__new__(WSGI2)
    wsgi._root = Path("app")
    wsgi._base_path = Path("params")
    # Base.log, which the not-found page writes to. Normally a Logger,
    # which would want the filesystem this suite stays off.
    wsgi._log = logged.append
    wsgi._colloquy = SimpleNamespace(
        snapshot_children={"params": node},
        log=lambda message: logged.append(message),
    )
    wsgi._environ = {
        "CONTENT_LENGTH": str(len(body)),
        "wsgi.input": io.BytesIO(body),
    }

    status, headers, _content = wsgi._parse_post(*path)
    return status, dict(headers), logged


def test_a_typed_value_reaches_the_nodes_command():
    node = FakeNode()

    status, headers, _logged = post(node, ("app", "params", "call", "commit"), 300)

    assert node.committed == [300]
    assert status.startswith("303")
    # Back to the page it was typed on.
    assert headers["Location"] == "/app/params"


def test_a_value_the_command_refuses_changes_nothing():
    node = FakeNode()

    status, _headers, logged = post(
        node, ("app", "params", "call", "commit"), "three hundred"
    )

    assert node.committed == []
    # No exception escaped - which is the whole point, since one would be
    # taken for a crash and stop the installation.
    assert status.startswith("303")
    assert len(logged) == 1
    assert "three hundred" in logged[0]


def test_the_refusal_says_what_was_typed_and_where():
    node = FakeNode()

    _status, _headers, logged = post(node, ("app", "params", "call", "commit"), "x")

    assert "params/commit" in logged[0]
    assert "invalid literal" in logged[0]


def test_a_command_a_node_does_not_offer_is_not_found():
    node = FakeNode()

    status, _headers, _logged = post(node, ("app", "params", "call", "erase"), 1)

    assert status.startswith("404")
    assert node.committed == []


def test_a_post_that_is_not_a_call_is_not_found():
    node = FakeNode()

    status, _headers, _logged = post(node, ("app", "params", "commit"), 1)

    assert status.startswith("404")


def test_a_float_command_takes_a_decimal():
    node = FakeNode(parse=float)

    post(node, ("app", "params", "call", "commit"), "64.453")

    assert node.committed == [64.453]
