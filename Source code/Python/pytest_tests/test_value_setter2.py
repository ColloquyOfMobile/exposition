"""Unit tests for colloquy.drivers.value_setter2.ValueSetter2 - this app's
only "enter a value" mechanism (a digit-drilldown link tree), shared by
RegisterHanlder's DXL register setters and params_browser's ParamsIntLeaf.

Covers a real, confirmed pre-existing bug fixed alongside the UX
improvements requested here: the negative branch used to double-negate
its leaf values back to positive (prefix already carried a literal "-"
character, then got multiplied by sign=-1 again) - e.g. drilling into
what looked like "-3300" actually produced Set(value=3300). Fixed by
keeping prefix pure-digit always and applying sign in exactly one place.
"""
from colloquy.drivers.value_setter2 import ValueSetter2


def make_setter(min_value, max_value):
    state = {"value": 0}

    def set_func(v):
        state["value"] = v

    def get_func():
        return state["value"]

    return ValueSetter2(
        owner=None, min_value=min_value, max_value=max_value, set_func=set_func, get_func=get_func
    ), state


def find_leaf(node, value):
    """Depth-first search for the Set leaf with this exact value."""
    for child in node.snapshot_children.values():
        if not callable(child):
            found = find_leaf(child, value)
            if found is not None:
                return found
            continue
        if getattr(child, "_value", None) == value:
            return child
    return None


def test_root_name_is_generic_entry_point():
    root, _ = make_setter(-5000, 5000)
    assert root.name == "choose value"


def test_negative_and_positive_branches_have_correct_signed_range_names():
    root, _ = make_setter(-5000, 5000)
    names = set(root.snapshot_children.keys())
    assert "-0 to -4999" in names
    assert "0 to 4999" in names


def test_positive_only_range_has_no_negative_branch():
    root, _ = make_setter(0, 5000)
    names = set(root.snapshot_children.keys())
    assert not any(n.startswith("-") for n in names)


def test_negative_leaf_values_are_correctly_signed_not_double_negated():
    root, _ = make_setter(-5000, 5000)
    leaf = find_leaf(root, -3300)
    assert leaf is not None


def test_negative_leaf_invocation_writes_the_negative_value():
    root, state = make_setter(-5000, 5000)
    leaf = find_leaf(root, -3300)
    leaf()
    assert state["value"] == -3300


def test_all_ten_digits_are_reachable_on_the_negative_branch():
    # Regression: the old double-negation bug's pruning check happened to
    # (by accident) never break early; a naive fix without correcting the
    # pruning logic too would break after the first non-zero digit.
    root, _ = make_setter(-50, 50)
    neg = root.snapshot_children["-0 to -49"]
    digit_branches = [k for k in neg.snapshot_children if not k.endswith(" set")]
    assert len(digit_branches) == 5  # 0 to 49 in steps of 10 -> 5 tens-digits


def test_round_value_shortcut_exists_alongside_branch_and_sets_correctly():
    # min_value=0 so the outermost (is_root) instance's own single child
    # is the full positive range "0 to 9999" - drill one level into that
    # to reach the thousands-digit choices, where "8" both branches
    # deeper into "8000 to 8999" and offers a "8000 set" shortcut.
    root, state = make_setter(0, 10000)
    thousands = root.snapshot_children["0 to 9999"]
    children = thousands.snapshot_children
    assert "8000 set" in children
    assert "8000 to 8999" in children
    children["8000 set"]()
    assert state["value"] == 8000


def test_leaf_level_digit_has_no_redundant_shortcut():
    # At the final digit (self._digits == 1), children are already atomic
    # Set leaves - no separate "shortcut" should be added on top.
    root, _ = make_setter(0, 10)
    children = root.snapshot_children["0 to 9"].snapshot_children
    assert list(children.keys()) == [f"{i} set" for i in range(10)]


def test_current_value_is_shown_at_every_level_not_just_the_leaf():
    root, state = make_setter(0, 20000)
    state["value"] = 8000

    root_states = root._snapshot_if_opened(path=())
    assert root_states["current value"]["value"] == 8000

    pos = root.snapshot_children["0 to 19999"]
    pos_states = pos._snapshot_if_opened(path=("0 to 19999",))
    assert pos_states["current value"]["value"] == 8000


def test_setter_children_are_built_lazily(monkeypatch):
    calls = []
    real_build = ValueSetter2._build_setters

    def spy_build(self):
        calls.append(self)
        return real_build(self)

    monkeypatch.setattr(ValueSetter2, "_build_setters", spy_build)
    root, _ = make_setter(-20000, 20000)
    assert calls == []  # nothing built at construction time
    root.snapshot_children
    assert len(calls) == 1  # only the root's own level built so far
