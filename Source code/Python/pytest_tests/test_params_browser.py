"""Unit tests for colloquy.params_browser - the "params" tab that lets the
web UI browse/edit colloquy.params (see colloquy/params.py's Params) live.
No hardware/threads involved: ParamsNode just mirrors a plain dict
structure, so a tmp_path-backed real Params object (same pattern as
pytest_tests/test_params.py) is enough.
"""
import json

import pytest

from colloquy.params import Params
from colloquy.params_browser import (
    ParamsNode,
    ParamsFloatLeaf,
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


def shown_value(leaf, path):
    """What the page shows for a leaf - through the editable payload, since
    an editable leaf carries its reading inside the box it draws."""
    states = leaf.snapshot(path=path, focus_path=path)
    return states["value"]["editable"]["value"]


def test_int_leaf_value_reflects_live_current_value(tmp_path):
    root, params = make_tree(tmp_path)
    leaf = root.snapshot_children["threashold"]
    path = ("params", "threashold")

    assert shown_value(leaf, path) == 300

    params["threashold"] = 301

    assert shown_value(leaf, path) == 301


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


# --- floats --------------------------------------------------------------
# Every float in params.json is an angle in degrees. They only became
# floats when the file moved from servo units to degrees, and until this
# leaf existed they fell through to the read-only one - so the six bar
# meeting points, the values most likely to be adjusted at the rig, were
# exactly the ones the page would not let you touch.


def make_angle_tree(tmp_path):
    path = tmp_path / "params.json"
    params = Params(
        path,
        {
            "near origin threshold": {"female": 11.719, "male": 35.156},
            "bar": {
                "dxl origin": 0,
                "interaction_origins": {"male1": {"female2": 64.453}},
            },
        },
    )
    return ParamsNode(owner=None, key="params", params_dict=params), params


def meeting_point_leaf(root):
    return (
        root.snapshot_children["bar"]
        .snapshot_children["interaction_origins"]
        .snapshot_children["male1"]
        .snapshot_children["female2"]
    )


def test_a_float_param_is_editable_not_read_only(tmp_path):
    root, _params = make_angle_tree(tmp_path)

    assert isinstance(meeting_point_leaf(root), ParamsFloatLeaf)
    assert isinstance(
        root.snapshot_children["near origin threshold"].snapshot_children["male"],
        ParamsFloatLeaf,
    )


def test_float_leaf_shows_the_whole_value_not_the_rounded_one(tmp_path):
    # The box holds 64.453 even though its digit tree works in whole
    # degrees - the tree is for jumping, the box is for saying exactly.
    root, _params = make_angle_tree(tmp_path)
    leaf = meeting_point_leaf(root)
    path = ("params", "bar", "interaction_origins", "male1", "female2")

    assert shown_value(leaf, path) == 64.453


def test_typing_a_value_into_a_float_param_writes_it(tmp_path):
    root, params = make_angle_tree(tmp_path)
    leaf = meeting_point_leaf(root)

    leaf.commit("125.977")

    assert params["bar"]["interaction_origins"]["male1"]["female2"] == 125.977


def test_typing_something_that_is_not_a_number_is_refused(tmp_path):
    # It has to raise: the request layer turns that into a message, where
    # a silent pass would look like a change that did not happen.
    root, params = make_angle_tree(tmp_path)
    leaf = meeting_point_leaf(root)

    with pytest.raises(ValueError):
        leaf.commit("64,453")

    assert params["bar"]["interaction_origins"]["male1"]["female2"] == 64.453


def test_typing_a_fraction_into_an_int_param_is_refused(tmp_path):
    # The value in the file is a whole number and the tree picked this
    # leaf because of that; writing 1.5 would change its type underneath.
    root, params = make_tree(tmp_path)
    leaf = root.snapshot_children["threashold"]

    with pytest.raises(ValueError):
        leaf.commit("300.5")

    assert params["threashold"] == 300


def test_jogging_a_float_writes_through_and_persists(tmp_path):
    root, params = make_angle_tree(tmp_path)
    leaf = meeting_point_leaf(root)
    path = ("params", "bar", "interaction_origins", "male1", "female2")

    states = leaf.snapshot(path=path, focus_path=path)
    states["+0.1"]()

    assert params["bar"]["interaction_origins"]["male1"]["female2"] == 64.553
    # Read back off disk rather than through Params.load(), which would
    # migrate this fixture (it carries no version key) and convert the
    # degrees it just wrote as though they were servo units.
    on_disk = json.loads((tmp_path / "params.json").read_text(encoding="utf-8"))
    assert on_disk["bar"]["interaction_origins"]["male1"]["female2"] == 64.553


def test_jogging_rounds_rather_than_writing_binary_float_noise(tmp_path):
    # 64.453 + 0.1 is 64.55299999999999, and this value is written
    # straight to a file a human reads.
    root, params = make_angle_tree(tmp_path)
    leaf = meeting_point_leaf(root)
    path = ("params", "bar", "interaction_origins", "male1", "female2")
    states = leaf.snapshot(path=path, focus_path=path)

    states["+0.1"]()
    states["-1"]()

    assert params["bar"]["interaction_origins"]["male1"]["female2"] == 63.553


def test_the_digit_setter_jumps_to_a_whole_degree(tmp_path):
    root, params = make_angle_tree(tmp_path)
    leaf = meeting_point_leaf(root)

    leaf._set(200)

    assert params["bar"]["interaction_origins"]["male1"]["female2"] == 200.0
    assert isinstance(params["bar"]["interaction_origins"]["male1"]["female2"], float)


def test_the_digit_setter_starts_from_the_whole_part_of_the_current_value(tmp_path):
    root, _params = make_angle_tree(tmp_path)
    leaf = meeting_point_leaf(root)

    assert leaf._get_whole() == 64


# --- keeping up with the dict --------------------------------------------


def test_a_key_added_after_construction_shows_up(tmp_path):
    # Children used to be built once, at the moment Colloquy() starts, so
    # anything added to params later was invisible on the page and the
    # page said nothing about it either.
    root, params = make_angle_tree(tmp_path)

    params["mirror1"] = {"dxl origin": 0}

    assert isinstance(root.snapshot_children["mirror1"], ParamsNode)


def test_a_key_removed_from_params_disappears(tmp_path):
    root, params = make_angle_tree(tmp_path)
    assert "bar" in root.snapshot_children

    del params["bar"]

    assert "bar" not in root.snapshot_children


def test_a_value_that_changes_type_gets_the_right_leaf(tmp_path):
    # Which is what the move to degrees did to the meeting points: ints
    # became floats under a tree that had already decided they were ints.
    root, params = make_angle_tree(tmp_path)
    assert isinstance(root.snapshot_children["bar"].snapshot_children["dxl origin"], ParamsIntLeaf)

    params["bar"]["dxl origin"] = 12.5

    assert isinstance(
        root.snapshot_children["bar"].snapshot_children["dxl origin"], ParamsFloatLeaf
    )


def test_children_that_are_still_right_are_left_alone(tmp_path):
    # Rebuilding them all would drop whatever the reader has opened.
    root, params = make_angle_tree(tmp_path)
    bar = root.snapshot_children["bar"]
    bar.open()

    params["mirror1"] = {"dxl origin": 0}

    assert root.snapshot_children["bar"] is bar
    assert bar._is_opened is True
