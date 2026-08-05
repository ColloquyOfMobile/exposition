from colloquy.base import Base
from colloquy.hardware.value_setter2 import ValueSetter2

# Params values are always dict/int/bool/str in the current schema (see
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
    itself on Colloquy. Children are built once at construction: nested
    dicts recurse into another ParamsNode, scalars become the matching
    leaf type below."""

    def __init__(self, owner, key, params_dict):
        self._key = key
        self._params_dict = params_dict
        super().__init__(owner=owner)

        self._children = {}
        for k, v in params_dict.items():
            if k in _RESERVED_KEYS:
                continue
            if isinstance(v, dict):
                self._children[k] = ParamsNode(owner=self, key=k, params_dict=v)
            elif isinstance(v, bool):
                self._children[k] = ParamsBoolLeaf(
                    owner=self, key=k, params_dict=params_dict
                )
            elif isinstance(v, int):
                self._children[k] = ParamsIntLeaf(
                    owner=self, key=k, params_dict=params_dict
                )
            else:
                self._children[k] = ParamsReadOnlyLeaf(
                    owner=self, key=k, params_dict=params_dict
                )

    @property
    def name(self):
        return self._key

    @property
    def snapshot_children(self):
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
