"""colloquy.base.Base's generic tree-walk (snapshot/snapshot_as_child/
_snapshot_if_opened) is what actually serves the web UI (see
colloquy/server2/wsgi2.py's get_states -> get_focus/update). It's pure
logic given a fake owner and a snapshot_children override - no hardware
object graph needed.
"""
from colloquy.base import Base, SnapchotError


class Leaf(Base):
    """Minimal concrete Base with no children - like a DXL register."""

    def __init__(self, owner, name):
        super().__init__(owner=owner)
        self._name = name

    @property
    def name(self):
        return self._name

    @property
    def snapshot_children(self):
        return {}


class Branch(Base):
    """A Base node with children, mirroring how e.g. Bar wires up
    dxl_origin/search/etc. via snapshot_children."""

    def __init__(self, owner, name, children=None):
        super().__init__(owner=owner)
        self._name = name
        self._children = children or {}

    @property
    def name(self):
        return self._name

    @property
    def snapshot_children(self):
        return self._children


def test_dict_protocol():
    root = Leaf(owner=None, name="root")
    root["foo"] = 123
    assert "foo" in root
    assert root["foo"] == 123
    assert list(root) == ["foo"]


def test_getitem_missing_key_raises_keyerror():
    root = Leaf(owner=None, name="root")
    try:
        root["missing"]
    except KeyError:
        pass
    else:
        assert False, "expected KeyError"


def test_path_is_slash_joined_from_owner_chain():
    # The owner-less root contributes an empty path segment (mirrors
    # Colloquy itself: owner=None, so "/app/hardware/..." never has a
    # leading "colloquy/" segment) - only descendants' names show up.
    root = Leaf(owner=None, name="root")
    child = Leaf(owner=root, name="child")
    grandchild = Leaf(owner=child, name="grandchild")

    assert root.path.as_posix() == "."
    assert child.path.as_posix() == "child"
    assert grandchild.path.as_posix() == "child/grandchild"


def test_owners_returns_full_ancestor_chain():
    root = Leaf(owner=None, name="root")
    child = Leaf(owner=root, name="child")
    grandchild = Leaf(owner=child, name="grandchild")

    assert grandchild.owners == [child, root]


def test_open_close_toggle_is_opened():
    node = Leaf(owner=None, name="n")
    assert node._is_opened is False
    node.open()
    assert node._is_opened is True
    node.close()
    assert node._is_opened is False


def test_snapshot_children_not_implemented_by_default():
    root = Base(owner=None)
    try:
        root.snapshot_children
    except NotImplementedError:
        pass
    else:
        assert False, "expected NotImplementedError"


def test_snapshot_off_focus_path_still_recurses_through_non_callable_children():
    # Base.snapshot's non-focus branch (`for k, v in self.snapshot_children:
    # if not callable(v): states[k] = v.snapshot(...)`) recurses
    # unconditionally through every non-callable child regardless of
    # whether focus_path matches - it doesn't stop at a mismatched
    # focus_path, it just keeps walking snapshot_children all the way
    # down. What focus_path actually gates is _snapshot_if_opened's EXTRA
    # per-node content (see the next test) - not whether children show up
    # at all.
    grandchild = Leaf(owner=None, name="grandchild")
    child = Branch(owner=None, name="child", children={"grandchild": grandchild})
    root = Branch(owner=None, name="root", children={"child": child})

    states = root.snapshot(path=("root",), focus_path=("elsewhere",))

    assert states["name"] == "root"
    assert states["child"]["name"] == "child"
    assert states["child"]["grandchild"]["name"] == "grandchild"


def test_snapshot_if_opened_extra_content_only_fires_exactly_at_focus_path():
    # This is the actual difference focus_path makes: a node's own
    # _snapshot_if_opened override (e.g. BaseThread injecting "start"/
    # "stop", or a register injecting a live "value" reading) only runs
    # when that node's path matches focus_path - not for nodes off that
    # path, even though the walk still recurses through and renders them
    # (previous test). Reaching the match doesn't require calling
    # .snapshot() directly on the target: root's own recursive walk lands
    # on it too, once its accumulated path equals focus_path.
    class Instrumented(Branch):
        def _snapshot_if_opened(self, path):
            states = super()._snapshot_if_opened(path)
            states["extra"] = "only when focused"
            return states

    sibling = Instrumented(owner=None, name="sibling", children={})
    focused_child = Instrumented(owner=None, name="focused_child", children={})
    root = Branch(
        owner=None,
        name="root",
        children={"sibling": sibling, "focused_child": focused_child},
    )

    states = root.snapshot(path=("root",), focus_path=("root", "focused_child"))

    assert "extra" not in states["sibling"]
    assert states["focused_child"]["extra"] == "only when focused"


def test_snapshot_at_focus_path_expands_that_nodes_children():
    grandchild = Leaf(owner=None, name="grandchild")
    child = Branch(owner=None, name="child", children={"grandchild": grandchild})

    # Simulates get_focus() landing on `child` and calling
    # child.snapshot(path, focus_path=path) directly (focus_path == path).
    states = child.snapshot(path=("root", "child"), focus_path=("root", "child"))

    assert states["name"] == "child"
    assert states["grandchild"]["name"] == "grandchild"


def test_snapshot_children_that_are_callable_are_stored_raw_not_recursed():
    # Base.snapshot's non-focus branch treats a callable child as a leaf
    # command (stored as-is) rather than recursing into .snapshot() on it -
    # this is the same behavior that made bare bound methods/instances with
    # __call__ crash when mixed into snapshot_children (see the "value" /
    # __call__ dead-code fixes elsewhere in this refactor).
    root = Branch(owner=None, name="root", children={"cmd": lambda: None})

    states = root.snapshot(path=("root",), focus_path=("elsewhere",))

    assert callable(states["cmd"])


def test_snapshot_wraps_unexpected_errors_in_snapchot_error():
    class Broken(Branch):
        @property
        def snapshot_children(self):
            raise ValueError("boom")

    root = Broken(owner=None, name="root")
    try:
        root.snapshot(path=("root",), focus_path=("elsewhere",))
    except SnapchotError:
        pass
    else:
        assert False, "expected SnapchotError"


def test_snapshot_as_child_expands_only_when_opened():
    grandchild = Leaf(owner=None, name="grandchild")
    child = Branch(owner=None, name="child", children={"grandchild": grandchild})

    closed = child.snapshot_as_child(path=("root", "child"))
    assert "grandchild" not in closed

    child.open()
    opened = child.snapshot_as_child(path=("root", "child"))
    assert opened["grandchild"]["name"] == "grandchild"
