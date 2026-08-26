import json
from pathlib import Path
import re
from time import sleep
from colloquy.base import Base
from colloquy.drivers.angle.conversion import REDUCTIONS, ticks_to_degrees
from colloquy.drivers import audio
from colloquy.drivers.arduino import firmware
from random import Random

from .dxl_ids import BAR_DXL_ID, FEMALE_DXL_IDS, MALE_DXL_IDS

# Where the firmware lives. Named once, in the driver that has to agree
# with it - this reads it for the list of paths, firmware.py reads it for
# the baud rate and the protocol version.
_ARDUINO_SKETCH = firmware.SKETCH_PATH


# One command and its reply over the real link. Replying instantly is not
# neutral - ReadPattern bins its samples by wall clock, so a simulator
# with no latency feeds it 2-3x more samples per pattern step than the rig
# ever will, and a decode that works here can fail there for reasons that
# have nothing to do with the decoding.
#
# At 1 Mbaud the wire is no longer what costs: ~75 characters each way is
# under a millisecond, and what is left is the sketch's own work - about
# 0.2ms to parse the JSON, then either 2ms of NeoPixel.show() for a pixel
# group or 0.1ms of analogRead() for a sensor. One number covers both, and
# it is the slower one, which errs towards handing a female fewer samples
# than the rig will rather than more.
#
# It was 15ms while the link ran at 57600, where the wire *was* the cost:
# ~70 characters at 57600 is about 12ms on its own. TimingNode still
# offers that as a preset, so a decode can be compared across the change.
REALISTIC_LATENCY = 0.003
OLD_57600_LATENCY = 0.015


def _kind_of(name):
    """"female2" -> "female", "bar" -> "bar" - which reduction and which
    threshold this body uses."""
    return name.rstrip("123")


class VirtualSerialPort(Base):
    """Stands in for the Arduino's pyserial connection when simulated.

    Replies are shaped like the real firmware's, which answers every
    command with `Serial.println(response)`: a decimal number for a light
    sensor read, an empty string for anything else, both CRLF-terminated -
    and they take about as long to arrive.
    """

    def __init__(self, owner, port=None):
        super().__init__(owner=owner)
        assert port is None, f"Port should be none to avoid opening! ({port=})"

        self._path_handlers = {
            "f1/head": self._set_female_neopixel,
            "f1/bodyO": self._set_female_neopixel,
            "f1/bodyP": self._set_female_neopixel,
            "f1/feet": self._set_female_neopixel,
            "f1/light sensor": self._read_female_sensor,
            "f2/head": self._set_female_neopixel,
            "f2/bodyO": self._set_female_neopixel,
            "f2/bodyP": self._set_female_neopixel,
            "f2/feet": self._set_female_neopixel,
            "f2/light sensor": self._read_female_sensor,
            "f3/head": self._set_female_neopixel,
            "f3/bodyO": self._set_female_neopixel,
            "f3/bodyP": self._set_female_neopixel,
            "f3/feet": self._set_female_neopixel,
            "f3/light sensor": self._read_female_sensor,
            "m1/ring": self._set_male_neopixel,
            "m1/up ring": self._set_male_neopixel,
            "m1/p drive level": self._set_male_neopixel,
            "m1/o drive level": self._set_male_neopixel,
            "m1/light sensor/a": self._read_sensor,
            "m1/light sensor/b": self._read_sensor,
            "m1/light sensor/c": self._read_sensor,
            "m1/light sensor/d": self._read_sensor,
            "m2/ring": self._set_male_neopixel,
            "m2/up ring": self._set_male_neopixel,
            "m2/p drive level": self._set_male_neopixel,
            "m2/o drive level": self._set_male_neopixel,
            "m2/light sensor/a": self._read_sensor,
            "m2/light sensor/b": self._read_sensor,
            "m2/light sensor/c": self._read_sensor,
            "m2/light sensor/d": self._read_sensor,
            "f1/speaker": self._set_speaker,
            "f2/speaker": self._set_speaker,
            "f3/speaker": self._set_speaker,
            "m1/speaker": self._set_speaker,
            "m2/speaker": self._set_speaker,
            "f1/microphone": self._read_microphone,
            "f2/microphone": self._read_microphone,
            "f3/microphone": self._read_microphone,
            "m1/microphone": self._read_microphone,
            "m2/microphone": self._read_microphone,
            "microphones": self._read_microphones,
            "speakers/off": self._silence_speakers,
            "version": self._greet,
        }

        self._port = port
        self._is_open = False
        self._possible_paths = set()
        self._load_possible_paths()
        self._to_return = None
        # Seeded explicitly so a simulated run can be repeated: sensor
        # noise is the only randomness in here, and a decode experiment
        # that can't be replayed is hard to argue about.
        self._random = Random(0)
        self.latency = REALISTIC_LATENCY
        self._states = states = {}
        for i in range(3):
            states[f"female{i + 1}"] = female = {}
            for name in ("head", "bodyO", "bodyP", "feet"):
                female[name] = dict(r=0, g=0, b=0, w=0)

            female["light sensor"] = 0

        for i in range(2):
            states[f"male{i + 1}"] = male = {}
            for name in ("ring", "p drive level", "o drive level", "up ring"):
                male[name] = dict(r=0, g=0, b=0, w=0)

            male["light sensor"] = sensors = {}
            for name in "abcd":
                sensors[name] = 0

        for name in audio.BODIES_BY_PITCH:
            states[name]["speaker"] = False

    def readline(self):
        """Always bytes, and always shaped like a real reply.

        This used to hand back a made-up b'{"status": "success"}' for
        writes and a bare Python int for sensor reads. Neither is anything
        the firmware can produce (it sends an empty line and a decimal
        number respectively), so simulated code took a path no rig would
        ever take - and any caller that decoded or JSON-parsed a reply
        would have worked here and failed on the hardware.
        """
        to_return, self._to_return = self._to_return, None
        if to_return is None:
            return self._as_reply("")
        return to_return

    def write(self, data):
        if not self._is_open:
            raise AssertionError("Port should be open before using it.")
        data = data.decode()
        data = json.loads(data)
        path = data["path"]
        # Loud on purpose: an unknown path means the firmware and this
        # simulator have drifted apart (a renamed pixel group, a new
        # sensor), and quietly answering it would hide that until the
        # next time somebody stood in front of the real installation.
        assert path in self._possible_paths, f"{path=}, {self._possible_paths=}"
        self._to_return = self._path_handlers[path](data)
        # Charged on the write, which is where the caller is blocked on the
        # real link: Arduino._send_unsafe() writes and reads back-to-back
        # while holding the port lock.
        if self.latency:
            sleep(self.latency)

    @property
    def is_open(self):
        return self._is_open

    @property
    def port(self):
        return self._port

    @port.setter
    def port(self, value):
        self._port = value

    @property
    def name(self):
        return self._port

    @property
    def colloquy(self):
        return self.owner.colloquy

    def close(self):
        self._is_open = False

    def open(self):
        assert not self.is_open
        assert self._port is not None
        self._to_return = self._greeting_line()
        self._is_open = True

    def _greeting_line(self):
        """What the sketch would say on reboot, taken from the sketch.

        Read out of the .ino rather than written here, so that a simulated
        board announces the same firmware and the same baud rate a flashed
        one does. Copied by hand it would be right until the first time
        either number changed - which is exactly the drift the greeting
        exists to catch.
        """
        return self._as_reply(json.dumps(firmware.sketch_greeting()))

    def _greet(self, data):
        """The "version" path: the same line, on demand."""
        return self._greeting_line()

    @staticmethod
    def _as_reply(value):
        """One firmware reply line: Serial.println() terminates with CRLF."""
        return f"{value}\r\n".encode()

    def _set_female_neopixel(self, data):
        states = self._states
        female, name = Path(data["path"]).parts
        female = female.replace("f", "female")
        neopixel = states[female][name]

        neopixel["r"] = data["r"]
        neopixel["g"] = data["g"]
        neopixel["b"] = data["b"]
        neopixel["w"] = data["w"]

    def _set_male_neopixel(self, data):
        states = self._states
        male, name = Path(data["path"]).parts
        male = male.replace("m", "male")
        neopixel = states[male][name]

        neopixel["r"] = data["r"]
        neopixel["g"] = data["g"]
        neopixel["b"] = data["b"]
        neopixel["w"] = data["w"]

    def _read_sensor(self, data):
        """The sensors with no model behind them: the males' four each.

        A steady dark reading, expressed relative to the threshold rather
        than as a bare constant, so that changing the threshold doesn't
        silently turn "dark" into "lit"."""
        male, _, letter = Path(data["path"]).parts
        return self._as_reply(
            self._record(self._states[male.replace("m", "male")]["light sensor"], letter)
        )

    def _read_female_sensor(self, data):
        """A female's own sensor: lit only when she is facing a lit male.

        Used by all three females - it used to be female1 only, with the
        other two returning the same constant darkness as an unmodelled
        male sensor, so nothing involving female2 or female3 could
        ever produce a reading to decode.
        """
        female = Path(data["path"]).parts[0].replace("f", "female")
        dxl = self.owner.dxls[FEMALE_DXL_IDS[female]]

        return self._as_reply(
            self._record(self._states[female], "light sensor", self._sensor_value(female, dxl))
        )

    def _sensor_value(self, female, dxl):
        if not self._is_near_origin(name=female, dxl=dxl):
            return self._dark_value()

        male = self._get_nearest_male(female=female)
        if male is None:
            return self._dark_value()

        if self._states[male]["ring"]["w"] != 0:
            return self._lit_value()
        return self._dark_value()

    # --- the sound channel, such as it is here ----------------------------
    #
    # A room this simulator does not have. It models one thing and says so:
    # a body that is singing puts energy into its own band, on every
    # module, and nothing else does. That is enough to exercise the whole
    # command path - the paths exist, the numbers are the right shape and
    # in the right order - and it is *not* enough to say anything about
    # anybody's wiring.
    #
    # Note in particular what it cannot produce. There is no distance and
    # no directionality, so every ear hears every voice equally; a real
    # bench will not. A green run here means the driver drives the
    # firmware correctly and nothing whatever about the hardware, which is
    # the same caveat test_audio_subsystem carries against Thomas's
    # stand-in board.

    # What a band reads with nothing in it, and with a tone in it. Off the
    # ADC the MSGEQ7's range is 0-1023; a tone in its own band is not
    # subtle, which is why these two are so far apart.
    QUIET_BAND = 60
    LOUD_BAND = 700

    def _set_speaker(self, data):
        body = self._body_of(data["path"])
        self._states[body]["speaker"] = bool(data.get("on", 0))
        return self._as_reply(1 if self._states[body]["speaker"] else 0)

    def _silence_speakers(self, data):
        for name in audio.BODIES_BY_PITCH:
            self._states[name]["speaker"] = False

    def _read_microphone(self, data):
        # The body in the path is not consulted, and that is the model
        # rather than an oversight: with no room in it, every module hears
        # the same thing.
        return self._as_reply(" ".join(str(v) for v in self._bands()))

    def _read_microphones(self, data):
        bands = self._bands()
        return self._as_reply(
            " ".join(
                str(value) for _ in audio.BODIES_BY_PITCH for value in bands
            )
        )

    def _bands(self):
        """One module's seven bands. Every module reads the same thing
        here, which is the whole of what this simulator does not know."""
        singing = {
            audio.band_of_body(name)
            for name in audio.BODIES_BY_PITCH
            if self._states[name]["speaker"]
        }
        return [
            (self.LOUD_BAND if index in singing else self.QUIET_BAND)
            + self._random.randrange(20)
            for index in range(len(audio.BANDS_HZ))
        ]

    @staticmethod
    def _body_of(path):
        """"f2/speaker" -> "female2", "m1/speaker" -> "male1".

        Written as a branch rather than two chained replaces, which is
        what it was: "f2".replace("f", "female") is "female2", and
        replacing "m" in *that* gives "femaleale2".
        """
        prefix = Path(path).parts[0]
        kind = "female" if prefix.startswith("f") else "male"
        return f"{kind}{prefix[1:]}"

    def _record(self, states, key, value=None):
        """Keep the last value actually served, so the simulated state the
        web UI shows is what the app was told - not a fresh roll of the
        sensor noise taken by the act of looking at it. These slots existed
        from the start and were never written to."""
        if value is None:
            value = self._dark_value()
        states[key] = value
        return value

    def _noise(self):
        return 100 + self._random.randrange(10)

    def _lit_value(self):
        return self.colloquy.params["photosensor_threashold"] + self._noise()

    def _dark_value(self):
        return self.colloquy.params["photosensor_threashold"] - self._noise()

    def _angle_of(self, name, dxl):
        """How far this body has turned from its own origin, in degrees of
        the body - through its own reduction, so that the window the
        sensor geometry below allows is an angle in the room and not a
        count of servo units."""
        origin = self.colloquy.params[name]["dxl origin"]
        return ticks_to_degrees(dxl.position - origin, REDUCTIONS[_kind_of(name)])

    def _near_origin_threshold(self, name):
        return self.colloquy.params["near origin threshold"][_kind_of(name)]

    def _is_near_origin(self, name, dxl):
        return abs(self._angle_of(name, dxl)) < self._near_origin_threshold(name)

    def _get_nearest_male(self, female):
        """Which male, if any, is currently in front of this female.

        Both males are considered. This used to `break` out of the loop at
        the first male facing his own origin, so if male1 happened to be
        facing forward the answer was always "male1 or nobody" - with the
        bar parked exactly at male2's meeting point, the female still read
        darkness.
        """
        params = self.colloquy.params
        threashold = self._near_origin_threshold("bar")
        bar_angle = self._angle_of("bar", self.owner.dxls[BAR_DXL_ID])

        for male, dxl_id in MALE_DXL_IDS.items():
            if not self._is_near_origin(male, self.owner.dxls[dxl_id]):
                continue

            # The same angle Bar.set_male_in_front_of_female() turns to.
            # Both sides are measured from the bar's own origin, which is
            # what keeps the simulated meeting points on top of the real
            # ones once the bar is calibrated.
            meeting = params["bar"]["interaction_origins"][male][female]
            if abs(bar_angle - meeting) < threashold:
                return male
        return None

    def _load_possible_paths(self):
        """Read arduino code to extract the possible paths."""
        # Resolved from this file, not the working directory: the app used
        # to be unimportable from anywhere but the repo root.
        text = _ARDUINO_SKETCH.read_text()

        # Expression régulière pour capturer les valeurs de path == "..."
        paths = re.findall(r'if\s*\(\s*path\s*==\s*"([^"]+)"\s*\)', text)

        # Stocker les chemins extraits
        self._possible_paths = sorted(paths)
