"""Unit tests for colloquy.params_browser - the "params" tab that lets the
web UI browse/edit colloquy.params (see colloquy/params.py's Params) live.
No hardware/threads involved: ParamsNode just mirrors a plain dict
structure, so a tmp_path-backed real Params object (same pattern as
pytest_tests/test_params.py) is enough.
"""
from colloquy.params import Params
from colloquy.params_browser import (
    ParamsNode,
    ParamsIntLeaf,
    ParamsBoolLeaf,
    ParamsReadOnlyLeaf,
)


def make_tree(tmp_path):
    path = tmp_path / "params.json"
    params = Params(
        path,
        {
            "threashold": 300,
            "emulate light sensor": False,
            "communication port": "COM4",
            # a stray key colliding with Base's reserved "name" state -
            # confirmed to actually appear in the real local/params.json
            # (leftover from a pre-refactor code path), must not corrupt
            # the branch's own identity.
            "name": "params",
            "bar": {
                "dxl origin": 0,
                "interaction_origins": {"male1": {"female2": 2200}},
            },
        },
    )
    root = ParamsNode(owner=None, key="params", params_dict=params)
    return root, params


def test_leaf_types_are_chosen_by_value_type(tmp_path):
    root, params = make_tree(tmp_path)
    children = root.snapshot_children

    assert isinstance(children["threashold"], ParamsIntLeaf)
    assert isinstance(children["emulate light sensor"], ParamsBoolLeaf)
    assert isinstance(children["communication port"], ParamsReadOnlyLeaf)
    assert isinstance(children["bar"], ParamsNode)


def test_bool_before_int_dispatch():
    # bool is an int subclass in Python - a bool value must not be
    # mistaken for ParamsIntLeaf.
    import colloquy.params_browser as pb

    assert isinstance(True, int)
    assert pb.ParamsBoolLeaf is not pb.ParamsIntLeaf


def test_reserved_key_collision_is_skipped(tmp_path):
    root, params = make_tree(tmp_path)

    assert "name" not in root.snapshot_children
    states = root.snapshot(path=("params",), focus_path=("params",))
    assert states["name"] == "params"


def test_nested_dicts_recurse_into_params_node(tmp_path):
    root, params = make_tree(tmp_path)

    bar = root.snapshot_children["bar"]
    assert isinstance(bar, ParamsNode)
    interaction_origins = bar.snapshot_children["interaction_origins"]
    male1 = interaction_origins.snapshot_children["male1"]
    female2 = male1.snapshot_children["female2"]
    assert isinstance(female2, ParamsIntLeaf)


def test_int_leaf_value_reflects_live_current_value(tmp_path):
    root, params = make_tree(tmp_path)
    leaf = root.snapshot_children["threashold"]

    states = leaf.snapshot(path=("params", "threashold"), focus_path=("params", "threashold"))
    assert states["value"]["value"] == 300

    params["threashold"] = 301
    states = leaf.snapshot(path=("params", "threashold"), focus_path=("params", "threashold"))
    assert states["value"]["value"] == 301


def test_int_leaf_setter_writes_through_and_persists(tmp_path):
    root, params = make_tree(tmp_path)
    leaf = root.snapshot_children["threashold"]

    leaf._set(42)

    assert params["threashold"] == 42
    reloaded = Params.load(params._path)
    assert reloaded["threashold"] == 42


def test_int_leaf_setter_is_reachable_and_invokable_through_the_tree(tmp_path):
    # Regression test for a real bug: ValueSetter2's "N set" leaves used
    # to be unreachable as invokable callables through _snapshot_if_opened
    # (Base's default always dict-wraps children via snapshot_as_child,
    # so update() in colloquy/__init__.py could never bottom out at a
    # raw callable). Drill into the actual ValueSetter2 tree exactly as
    # the web UI's update() would, and confirm calling the leaf it lands
    # on actually invokes Set.__call__() and writes the value.
    root, params = make_tree(tmp_path)
    leaf = root.snapshot_children["threashold"]

    setter_root = leaf.snapshot_children[next(iter(leaf.snapshot_children))]
    # Root splits into "-" (if negative allowed) and "" branches; walk
    # into a chain of single-digit branches until a callable Set leaf.
    node = setter_root
    while True:
        states = node._snapshot_if_opened(path=())
        raw_callables = {k: v for k, v in states.items() if callable(v)}
        if raw_callables:
            name, set_leaf = next(iter(raw_callables.items()))
            break
        # descend into the first non-callable child
        child_name = next(iter(node.snapshot_children))
        node = node.snapshot_children[child_name]

    set_leaf()

    assert params["threashold"] == set_leaf._value


def test_bool_leaf_toggle_flips_value_in_place(tmp_path):
    root, params = make_tree(tmp_path)
    leaf = root.snapshot_children["emulate light sensor"]

    assert params["emulate light sensor"] is False
    leaf.toggle()
    assert params["emulate light sensor"] is True
    leaf.toggle()
    assert params["emulate light sensor"] is False


def test_bool_leaf_exposes_toggle_and_value_when_opened(tmp_path):
    root, params = make_tree(tmp_path)
    leaf = root.snapshot_children["emulate light sensor"]

    states = leaf.snapshot(
        path=("params", "emulate light sensor"),
        focus_path=("params", "emulate light sensor"),
    )
    assert states["value"]["value"] is False
    assert states["toggle"] == leaf.toggle


def test_read_only_leaf_has_no_children_and_shows_value(tmp_path):
    root, params = make_tree(tmp_path)
    leaf = root.snapshot_children["communication port"]

    assert leaf.snapshot_children == {}
    states = leaf.snapshot(
        path=("params", "communication port"),
        focus_path=("params", "communication port"),
    )
    assert states["value"]["value"] == "COM4"
