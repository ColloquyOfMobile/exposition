import json
from pathlib import Path

# Bumped whenever the shape or the units of this file change, so an older
# file can be recognised and converted rather than misread. See migrate().
PARAMS_VERSION = 5

DEFAULTS = {
    "params version": PARAMS_VERSION,
    "photosensor_threashold": 300,
    # How far off its own origin a body can be and still count as facing
    # forward, in degrees of the body. Only the simulated sensor geometry
    # uses it (virtual_drivers/virtual_serial_port.py). It began as one
    # number of servo units for everyone, and it is written per kind so
    # that one of them can be narrowed on its own; now that every body
    # runs at 1:3 the three come out at the same angle again.
    "near origin threshold": {"female": 11.719, "male": 11.719, "bar": 11.719},
    "emulate light sensor": False,
    # Is the board carrying the Arduino and the U2D2 actually in the
    # installation? Written by the "unmount the main PCB" command
    # (colloquy/hardware/main_pcb/) so that the next start knows not to
    # reach for two serial ports that have been physically taken out,
    # instead of failing to open them and saying something about COM4.
    #
    # Nothing sets this back on its own: a board that is out stays out
    # until somebody says it is back, because the alternative is an
    # installation that quietly decides it has hardware when it has not.
    "main pcb": {"mounted": True, "unmounted at": ""},
    # The installation's own Arduino. The baud rate is not a
    # calibration and never was - it is a copy of a number that lives in
    # the sketch (SERIAL_BAUDRATE in colloquy_of_mobiles.ino), kept here
    # only so the port can be opened before the board has said anything.
    # Arduino.open() refuses to open a link where the two disagree; see
    # drivers/arduino/firmware.py, which reads the sketch's own number.
    "arduino": {
        "baudrate": 1000000,
        "communication port": None,
        # What arduino-cli calls this board. Only the flasher reads it,
        # and it is here rather than in the code because the day it is
        # wrong is a day somebody is standing in front of the rack and
        # cannot edit a source file.
        "fqbn": "arduino:avr:mega",
        # Where arduino-cli is, when it is somewhere this cannot guess.
        # Left None on every machine that has the Arduino IDE installed
        # in the usual place, or arduino-cli on PATH - see
        # drivers/arduino/flasher/toolchain.py, which says where it looks.
        "arduino-cli": None,
    },
    # Thomas's audio subsystem tester: a second Mega 2560, on its own USB
    # lead, running Source code/Thomas/AudioAnalyzerTest.cpp. Nothing in
    # the installation talks to it - only the bench test under
    # colloquy/tests/test_audio_subsystem does. 9600 is the baud rate its
    # firmware sets (AudioAnalyzer.h: BAUDRATE) and is not ours to pick.
    "audio subsystem": {
        "baudrate": 9600,
        "communication port": None,
    },
    # Which bodies have their audio channel physically wired, in the order
    # they were done. The sound hardware arrived one pair of channels at a
    # time and the software has to cope with that honestly: an unwired
    # analyser input is a floating ADC pin, and a floating ADC pin does
    # not read silence, it reads garbage. So a test that assumed five
    # would bury the two real answers under three fictional ones.
    #
    # Add a body here the moment its amplifier and its analyser are in.
    # Nothing else needs changing - the pitch, the pin and the module are
    # already decided for all five in drivers/audio.py.
    "audio": {
        "wired bodies": ["female1", "male1"],
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
    # The bench's Goertzel ear board - `Source code/Arduino/goertzel_ear/`
    # and `colloquy/tests/test_goertzel_ear/`. Its own section because it
    # is its own Mega on its own lead, the same way Thomas's board has
    # one: a port remembered for one board opens nothing for the other.
    "goertzel ear": {"baudrate": 115200, "communication port": None},
    # How much one round of reinforcement takes off the appetite a pair
    # shares, per body, on this port's 0-100 scale.
    #
    # The three females are TJ's, converted: `FEMALE_reinforcement_decrement`
    # is 1200, 600 and 1200 on his 0-4800 scale (UNIT.ino), so 25, 12.5 and
    # 25 here. They are *not* all the same on purpose - female2 takes half
    # what her sisters do, so she needs twice as many rounds and holds a
    # partner twice as long.
    #
    # The two males are a **stand-in**. His is not a fixed number at all:
    # it is `sense_light_reinforce_sum * 10`, the light he actually
    # collected off her mirror that round, which at the 80-tick maximum is
    # about 17 here (CODE_DOCUMENTATION 9.7). Nothing drives a mirror yet,
    # so 17 stands for "he collected all of it" until one does.
    "reinforcement decrement": {
        "female1": 25,
        "female2": 12.5,
        "female3": 25,
        "male1": 17,
        "male2": 17,
    },
    # One per female, on the servos between them.
    #
    # **The range is TJ's, and it did not need measuring.** His OpenCM
    # servo controller drove these, and every one of the ten deployed
    # versions of it carries the same two lines
    # (`local/Code/Code/Servos/deploy*_fem_OCM`):
    #
    #     goal_position_mirror_MAX = (1023 + 512) - 50   //512==45
    #     goal_position_mirror_MIN = (1023 - 512) + 50
    #
    # 924 units end to end, and his own comment fixes the scale: 512 units
    # is 45 degrees, which is 4096 to a turn - the same convention as
    # `angle/conversion.py`, and `ticks_to_degrees(512, 1)` here returns
    # exactly 45.0. A mirror turns with its own servo (no reduction), so
    # 924 units is **81.211 degrees**, or 40.6 either side of centre. His
    # wiggle sweeps the whole of it, flipping when the *present* position
    # reaches a limit.
    #
    # **The origin is not his and cannot be.** His centre is 1023 because
    # that is where his servo sat in his mechanism; `dxl origin` here is
    # the reading a mirror gives when it points where it should, and that
    # is a fact about this installation. It still has to be measured at
    # the rig - the range no longer does.
    "mirror1": {"dxl origin": 0, "motion range": 81.211},
    "mirror2": {"dxl origin": 0, "motion range": 81.211},
    "mirror3": {"dxl origin": 0, "motion range": 81.211},
}


# Frozen on purpose: what a v1 file's servo units meant when it was
# written. The live conversion lives in drivers/angle/conversion.py and
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


# What v3 files say the Arduino's link runs at: the rate the sketch used
# from the first version of this repo until the pattern reading needed the
# samples.
_V3_ARDUINO_BAUDRATE = 57600


def _to_v4(data):
    """v3 opened the Arduino at 57600; the sketch now runs at 1 Mbaud.

    This number is not a calibration - it is a copy of what the firmware
    sets, kept here only so the port can be opened before the board has
    said anything - so it moves when the firmware moves. Left alone
    otherwise: a file saying something other than the old 57600 was typed
    that way for a reason, and Arduino.open() will say so if the reason
    has expired rather than quietly overruling it.
    """
    arduino = data.get("arduino")
    if arduino and arduino.get("baudrate") == _V3_ARDUINO_BAUDRATE:
        arduino["baudrate"] = DEFAULTS["arduino"]["baudrate"]

    data["params version"] = 4
    return data


# What a mirror's range said before anybody looked: not a measurement but
# a placeholder, and one chosen so that a mirror nobody had calibrated
# would stay where it is rather than sweep into whatever it fouls.
_V4_MIRROR_RANGE = 0.0
_MIRRORS = ("mirror1", "mirror2", "mirror3")


def _to_v5(data):
    """v4 left every mirror's motion range at zero, meaning "unmeasured".

    It did not need measuring. TJ's OpenCM sketch drove these, and all ten
    deployed versions of it carry the same limits - 924 servo units end to
    end, and his own comment fixes the scale at 512 units to 45 degrees,
    which is this repository's convention too. A mirror turns with its own
    servo, so that is 81.211 degrees. See `DEFAULTS` below, and
    `pytest_tests/test_mirror_range.py`.

    **Only a zero moves.** A range somebody measured at the rig and typed
    in is a fact about this installation and outranks a number read off
    somebody else's firmware, exactly as v3's baud rate left a
    deliberately-typed value alone.

    **And `dxl origin` is not touched at all.** His centre is 1023 because
    that is where his servo sat in his mechanism; ours is the reading a
    mirror gives when it points where it should, and no amount of reading
    his source produces it.
    """
    for name in _MIRRORS:
        mirror = data.get(name)
        if mirror and mirror.get("motion range") == _V4_MIRROR_RANGE:
            mirror["motion range"] = DEFAULTS[name]["motion range"]

    data["params version"] = 5
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
    if data["params version"] < 4:
        data = _to_v4(data)
    if data["params version"] < 5:
        data = _to_v5(data)
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
