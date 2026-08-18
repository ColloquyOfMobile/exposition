from colloquy.base import Base
from colloquy.hardware.value_setter2 import ValueSetter2

# Params values are dict/int/float/bool/str in the current schema (see
# colloquy/params.py's DEFAULTS and local/params.json) - dispatch on type
# to pick a leaf class. bool must be checked before int since bool is an
# int subclass in Python.

# Wide enough to cover every current int param (bar interaction origins
# up to ~10400) plus real-world values that don't fit a narrower guess -
# e.g. arduino.baudrate is 57600, which didn't even fit in an earlier,
# narrower version of this range. Safe to be generous: ValueSetter2
# builds its digit tree lazily (one level at a time, on actual
# navigation), so the range size no longer affects Colloquy() startup
# time the way it did before that fix.
_INT_SETTER_MIN = -1_000_000
_INT_SETTER_MAX = 1_000_000

# Base._snapshot_base_states always sets these on every node (path/name/
# close/open/opened) and _snapshot_if_opened's default walk merges child
# states in by dict key afterward - a params.json key that happens to
# collide with one of these would silently overwrite the branch's own
# identity/controls instead of showing up as a value. params.json is
# free-form calibration data (not schema-validated), so skip any
# colliding key defensively rather than assume it can't happen - it
# already has happened (a stray leftover "name" key from an old,
# pre-refactor implementation, see "# threads/hardware.py").
_RESERVED_KEYS = {"path", "name", "close", "open", "opened"}


class ParamsNode(Base):
    """A branch mirroring one dict level of Params - one instance per
    nesting level, including the root registered as the "params" tab
    itself on Colloquy. Nested dicts recurse into another ParamsNode,
    scalars become the matching leaf type below."""

    def __init__(self, owner, key, params_dict):
        self._key = key
        self._params_dict = params_dict
        super().__init__(owner=owner)

        self._children = {}
        self._sync_children()

    def _leaf_class_for(self, value):
        if isinstance(value, dict):
            return ParamsNode
        # bool first: it is an int subclass.
        if isinstance(value, bool):
            return ParamsBoolLeaf
        if isinstance(value, (int, float)):
            return ParamsIntLeaf if isinstance(value, int) else ParamsFloatLeaf
        return ParamsReadOnlyLeaf

    def _make_child(self, key):
        value = self._params_dict[key]
        leaf_class = self._leaf_class_for(value)
        if leaf_class is ParamsNode:
            return ParamsNode(owner=self, key=key, params_dict=value)
        return leaf_class(owner=self, key=key, params_dict=self._params_dict)

    def _sync_children(self):
        """Bring this level's children in line with the dict.

        Children used to be built once, at construction, which is a moment
        that happens exactly as Colloquy() starts. A key added to params
        after that - or one whose type changed, which is what the move to
        degrees did to the bar's meeting points - never reached the page,
        and the page said nothing about it either. Existing children are
        kept as they are, so anything the reader has opened stays open.
        """
        wanted = {k for k in self._params_dict if k not in _RESERVED_KEYS}

        for key in wanted:
            child = self._children.get(key)
            if child is None or not isinstance(
                child, self._leaf_class_for(self._params_dict[key])
            ):
                self._children[key] = self._make_child(key)

        for key in set(self._children) - wanted:
            del self._children[key]

    @property
    def name(self):
        return self._key

    @property
    def snapshot_children(self):
        self._sync_children()
        return self._children


class ParamsIntLeaf(Base):
    """An editable integer param. Exposes a ValueSetter2 (this app's only
    "enter a value" mechanism - a digit-drilldown link tree, see
    RegisterHanlder for the precedent) whose set_func writes straight
    back into the live Params dict, which persists to local/params.json
    via Params.__setitem__."""

    def __init__(self, owner, key, params_dict):
        self._key = key
        self._params_dict = params_dict
        super().__init__(owner=owner)
        self._setter = ValueSetter2(
            owner=self,
            min_value=_INT_SETTER_MIN,
            max_value=_INT_SETTER_MAX,
            set_func=self._set,
            get_func=self._get,
        )

    def _set(self, value):
        self._params_dict[self._key] = value

    def _get(self):
        return self._params_dict[self._key]

    @property
    def name(self):
        return self._key

    @property
    def snapshot_children(self):
        return {self._setter.name: self._setter}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        states["value"] = {
            "path": path + ("value",),
            "name": "value",
            "value": self._params_dict[self._key],
        }
        return states


class ParamsFloatLeaf(Base):
    """An editable float param.

    Every float in this file is an angle in degrees - the bar's meeting
    points, the simulated facing-forward windows - and they became floats
    when params.json went from servo units to degrees. Before this leaf
    existed they fell through to the read-only leaf, so the values most
    likely to be adjusted at the rig were the ones the page would not let
    you touch.

    ValueSetter2 is a digit tree over whole numbers, so it sets the whole
    degree; the jog commands cover the fraction. A tenth of a degree is
    3.4 servo units on the bar and 1.1 on a direct body - finer than
    anything anybody sets by hand here, and calibrating against the room
    is done by moving the body and reading its angle anyway.
    """

    # Coarse then fine, both ways, like the angle node's own jogs.
    JOGS = (-1, -0.1, 0.1, 1)

    def __init__(self, owner, key, params_dict):
        self._key = key
        self._params_dict = params_dict
        super().__init__(owner=owner)
        self._setter = ValueSetter2(
            owner=self,
            min_value=_INT_SETTER_MIN,
            max_value=_INT_SETTER_MAX,
            set_func=self._set,
            get_func=self._get_whole,
        )

    def _set(self, value):
        self._params_dict[self._key] = float(value)

    def _get(self):
        return self._params_dict[self._key]

    def _get_whole(self):
        return round(self._get())

    def _jog(self, step):
        def command(request=None):
            # Rounded: 64.453 + 0.1 is 64.55299999999999 in binary floats,
            # and this value is written straight to a file a human reads.
            self._params_dict[self._key] = round(self._get() + step, 3)

        return command

    @property
    def name(self):
        return self._key

    @property
    def snapshot_children(self):
        return {self._setter.name: self._setter}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        for step in self.JOGS:
            states[f"{step:+g}"] = self._jog(step)
        states["value"] = {
            "path": path + ("value",),
            "name": "value",
            "value": self._get(),
        }
        return states


class ParamsBoolLeaf(Base):
    """A toggleable boolean param."""

    def __init__(self, owner, key, params_dict):
        self._key = key
        self._params_dict = params_dict
        super().__init__(owner=owner)

    def toggle(self):
        self._params_dict[self._key] = not self._params_dict[self._key]

    @property
    def name(self):
        return self._key

    @property
    def snapshot_children(self):
        return {}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        states["toggle"] = self.toggle
        states["value"] = {
            "path": path + ("value",),
            "name": "value",
            "value": self._params_dict[self._key],
        }
        return states


class ParamsReadOnlyLeaf(Base):
    """A param this UI has no editing affordance for (e.g. the arduino
    communication port string) - display only."""

    def __init__(self, owner, key, params_dict):
        self._key = key
        self._params_dict = params_dict
        super().__init__(owner=owner)

    @property
    def name(self):
        return self._key

    @property
    def snapshot_children(self):
        return {}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        states["value"] = {
            "path": path + ("value",),
            "name": "value",
            "value": self._params_dict[self._key],
        }
        return states
