import json
from pathlib import Path

# Bumped whenever the shape or the units of this file change, so an older
# file can be recognised and converted rather than misread. See migrate().
PARAMS_VERSION = 3

DEFAULTS = {
    "params version": PARAMS_VERSION,
    "photosensor_threashold": 300,
    # How far off its own origin a body can be and still count as facing
    # forward, in degrees of the body. Only the simulated sensor geometry
    # uses it (virtual_hardware/virtual_serial_port.py). It began as one
    # number of servo units for everyone, and it is written per kind so
    # that one of them can be narrowed on its own; now that every body
    # runs at 1:3 the three come out at the same angle again.
    "near origin threshold": {"female": 11.719, "male": 11.719, "bar": 11.719},
    "emulate light sensor": False,
    "arduino": {
        "baudrate": 57600,
        "communication port": None,
    },
    # "dxl origin" is in servo units: it is the raw reading a body gives
    # when it is pointing where it should. Everything else here is in
    # degrees of the thing that moves.
    #
    # "motion range" is how far a body travels end to end. A female, a
    # male and a mirror sway half of it either side of their origin; the
    # bar runs from its origin to the far end, which is why its number is
    # so much bigger. They are per body rather than per kind so that one
    # that fouls something in the room can be reined in on its own.
    "female1": {
        "dxl origin": 0,
        "motion range": 58.594,
    },
    "female2": {
        "dxl origin": 0,
        "motion range": 58.594,
    },
    "female3": {
        "dxl origin": 0,
        "motion range": 58.594,
    },
    "bar": {
        "dxl origin": 0,
        "motion range": 292.969,
        # The narrower sweep it makes when it stays near one pair
        # (TurnBackAndForthAroundF1), rather than crossing the whole rail.
        "motion range around female1": 87.891,
        # How far the bar turns from its origin to bring each male in
        # front of each female, in degrees of the bar.
        "interaction_origins": {
            "male1": {"female1": 0, "female2": 64.453, "female3": 125.977},
            "male2": {"female1": 181.641, "female2": 246.094, "female3": 304.688},
        },
    },
    "male1": {"dxl origin": 0, "motion range": 58.594},
    "male2": {"dxl origin": 0, "motion range": 58.594},
    # One per female, on the servos between them. Nothing drives them yet,
    # and nobody has measured how far one can turn before it fouls - hence
    # a range of zero, which means "stays where it is" rather than "turns
    # freely". Measure it at the rig and type it in here.
    "mirror1": {"dxl origin": 0, "motion range": 0.0},
    "mirror2": {"dxl origin": 0, "motion range": 0.0},
    "mirror3": {"dxl origin": 0, "motion range": 0.0},
}


# Frozen on purpose: what a v1 file's servo units meant when it was
# written. The live conversion lives in hardware/angle/conversion.py and
# may be corrected some day - this one may not, or old files stop
# converting to the same angles they used to describe.
_V1_TICKS_PER_TURN = 4096
_V1_REDUCTIONS = {"female": 3, "male": 1, "bar": 3}


def _v1_ticks_to_degrees(ticks, kind):
    return round(ticks * 360 / (_V1_TICKS_PER_TURN * _V1_REDUCTIONS[kind]), 3)


def _to_v2(data):
    """v1 said servo units; v2 says degrees of the body.

    Two things move: where the bar goes to bring a male in front of a
    female, and how far off its origin a body still counts as facing
    forward. A body's own "dxl origin" stays as it is - it is a raw servo
    reading, and rounding it into degrees and back would move it.
    """
    interaction_origins = data.get("bar", {}).get("interaction_origins", {})
    for male, per_female in interaction_origins.items():
        for female, ticks in per_female.items():
            per_female[female] = _v1_ticks_to_degrees(ticks, "bar")

    threshold = data.pop("near_origin_threashold", None)
    if threshold is not None:
        data["near origin threshold"] = {
            kind: _v1_ticks_to_degrees(threshold, kind)
            for kind in ("female", "male", "bar")
        }

    data["params version"] = 2
    return data


# What a v2 file's male degrees meant when they were written: a male was
# believed to turn with his servo, so his angles were three times the
# angle he actually turned through. Every other kind was right.
_V2_MALE_ERROR = 3


def _to_v3(data):
    """v2 believed a male turned one for one with his servo; he is geared
    1:3 like a female and the bar.

    Nothing about the file's units changes - it still says degrees of the
    body - but every number that was a male angle described three times
    the motion it was meant to, and would now be *obeyed* as three times
    the motion: 175.781 degrees of sway used to reach the servo as 2000
    units and does not any more. Divided back, so a migrated installation
    moves exactly as it did before the reduction was corrected.

    A male's "dxl origin" is untouched, being raw servo units, and so are
    the bar's interaction origins, which are degrees of the bar.
    """
    for male in ("male1", "male2"):
        body = data.get(male)
        if body and "motion range" in body:
            body["motion range"] = round(body["motion range"] / _V2_MALE_ERROR, 3)

    threshold = data.get("near origin threshold")
    if threshold and "male" in threshold:
        threshold["male"] = round(threshold["male"] / _V2_MALE_ERROR, 3)

    data["params version"] = 3
    return data


def _fill_missing(data, defaults):
    """Add any key the defaults have and this file doesn't.

    A params file written before a key existed used to be missing it
    forever - Params.load() reads the file *or* the defaults, never both -
    and the first read of that key raised KeyError somewhere far away
    (the one that bites today is "drive start values", at Drive
    construction).
    """
    for key, value in defaults.items():
        if key not in data:
            data[key] = value
        elif isinstance(value, dict) and isinstance(data[key], dict):
            _fill_missing(data[key], value)
    return data


def migrate(data):
    """Bring a file read off disk up to the current shape."""
    if data.get("params version", 1) < 2:
        data = _to_v2(data)
    if data["params version"] < 3:
        data = _to_v3(data)
    return _fill_missing(data, DEFAULTS)


class Params(dict):
    def __init__(self, path: Path, initial=None, _root=None):
        super().__init__()
        self._path = path
        # NOT `_root or self`: Params is a dict subclass, so an empty dict
        # is falsy - the top-level Params object is still empty while its
        # own __init__ is constructing nested Params for its first
        # dict-valued key below, which made that one child's `_root`
        # silently point at itself instead of the true root. Writes into
        # just that one nested sub-dict then saved only that fragment to
        # disk, clobbering the rest of params.json.
        self._root = self if _root is None else _root

        if initial:
            for k, v in initial.items():
                self[k] = v

    def __setitem__(self, key, value):
        if isinstance(value, dict) and not isinstance(value, Params):
            value = Params(self._path, value, _root=self._root)

        super().__setitem__(key, value)
        self._root._save()

    def __delitem__(self, key):
        super().__delitem__(key)
        self._root._save()

    def _save(self):
        if self is not self._root:
            return
        with self._path.open("w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=2)

    def to_dict(self):
        result = {}
        for k, v in self.items():
            if isinstance(v, Params):
                result[k] = v.to_dict()
            else:
                result[k] = v
        return result

    @classmethod
    def load(cls, path: Path):
        if not path.exists():
            return cls(path, DEFAULTS)

        data = json.loads(path.read_text())
        version = data.get("params version", 1)
        if version < PARAMS_VERSION:
            # This file is the calibration of a physical installation and
            # is about to be rewritten in different units. Keep the
            # original next to it: re-deriving it means going back to the
            # rig with the bodies.
            backup = path.with_name(f"{path.name}.v{version}.bak")
            backup.write_text(path.read_text(), encoding="utf-8")

        # Constructing writes the migrated file back out - every
        # __setitem__ saves.
        return cls(path, migrate(data))
