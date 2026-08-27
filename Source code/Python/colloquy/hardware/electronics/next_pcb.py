# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/electronics/next_pcb.py

"""The next PCB as data: every part, every net, every terminal.

`NEXT_PCB.md` says what the board should do and why. This says what it
*is*, in the one form a schematic can be drawn from without anybody
retyping a table - and it is generated rather than written because the
numbers it needs already exist in two places and retyping them is exactly
how a board comes back wrong.

**It reads `drivers/audio.py`.** Which body speaks at which pitch, out of
which timer pin, and into which analyser module is one table, and the
firmware and the four Python nodes already share it. The board now shares
it too, so a channel cannot be laid out against a pin the sketch does not
drive. That is the same arrangement as `drivers/arduino/firmware.py`
reading the baud rate straight out of the `.ino`: the copy that would
have drifted does not exist.

**It reads the connectors as they are.** The four DSUBs and the harness
behind them are fixed by the supplier (`NEXT_PCB.md` section 5), so
`_CONNECTORS` below is the existing pinout, transcribed from the netlist
of `CAD/KiCad/electronic box/` - with exactly one substitution per body,
the speaker pair becoming the line out and its return, since the
amplifier now lives at the body.

**What it deliberately does not know.** Two groups of component values
are not in this repository and are not this file's to invent:

- the MSGEQ7's support network, because the analyser array is five
  ready-made modules today and nobody here has drawn the chip; and
- whatever is fitted across `J11`/`J12` for each light sensor, which
  `as built` says to go and look at before pulling one out.

Both are carried as parts with `confirm=True`, which puts them in their
own section of the BOM instead of letting a plausible-looking number pass
for a known one. `pytest_tests/hardware/test_next_pcb.py` fails if that
section ever silently empties.
"""
from colloquy.drivers import audio

# --- what the board is made of -------------------------------------------


class Part:
    """One component, or one connector, or one test pad."""

    def __init__(self, ref, value, kind, description, confirm=False):
        self.ref = ref
        self.value = value
        self.kind = kind
        self.description = description
        # True when the value is a placeholder that has to be read off a
        # datasheet or off the existing board before anything is ordered.
        self.confirm = confirm

    def __repr__(self):
        return f"Part({self.ref} {self.value})"


class Net:
    """One net: a name and every terminal that sits on it."""

    def __init__(self, name, terminals):
        self.name = name
        # (ref, pin) pairs. `pin` is a number where the part has numbered
        # pins and a name where it does not - the MSGEQ7 is named, since
        # its footprint has not been chosen and inventing pin numbers for
        # it would be inventing the part.
        self.terminals = list(terminals)

    def __repr__(self):
        return f"Net({self.name}, {len(self.terminals)} terminals)"


# --- the fixed facts ------------------------------------------------------

# Passive second-order low-pass per channel, R1 = R2 and C1 = C2, keyed by
# the pitch it is the channel for. Thomas's board, measured: the first
# harmonic comes out more than 20 dB down.
FILTER_VALUES = {
    6250: ("2K2", "10nF"),
    2500: ("1K8", "47nF"),
    1000: ("1K2", "150nF"),
    400: ("2K", "220nF"),
    160: ("2K2", "470nF"),
}

# Series resistor between the filter output and the body connector. Not in
# the signal path in any meaningful sense - it limits the current if a body
# cable shorts the filter output to ground, and damps the cable. A link if
# it turns out not to be wanted.
BUILD_OUT = "100R"

# On each NeoPixel line, at the driving end. Not on the board that exists;
# standard practice for a bit-banged line that leaves a PCB, and seven
# resistors is a cheap way not to find out why it was standard.
NEOPIXEL_SERIES = "330R"

# Holds the amplifier-shutdown net at "enabled" while nothing drives D2.
# Firmware 3 leaves that pin an input, and the default of a pin nobody
# drives must be five bodies that can speak. See NEXT_PCB.md section 4.
SHUTDOWN_PULLUP = "10K"

# Which Mega pin each NeoPixel line is on after the rework. Kept exactly,
# so that one sketch runs on the reworked board and on this one.
#
# Note the two up-rings: the board calls D16's net male1's and D17's
# male2's, and the sketch has driven them the other way round since long
# before any of this (`as built` section 5). The net names here are the
# board's. If the up-rings come out on the wrong male, the fix is to swap
# two `#define`s and the names were right all along.
NEOPIXEL_PINS = {
    "female1/neopixel": "D14",
    "female2/neopixel": "D7",
    "female3/neopixel": "D8",
    "male1/neopixel": "D9",
    "male2/neopixel": "D15",
    "male1/bar neopixel": "D16",
    "male2/bar neopixel": "D17",
}

# Light sensors, unchanged: three females on A5-A7, four per male on
# A8-A15. `as built` section 2.
PHOTOSENSOR_PINS = {
    "female1/photosensor": "A5",
    "female2/photosensor": "A6",
    "female3/photosensor": "A7",
    "male1/photosensor/A": "A8",
    "male1/photosensor/B": "A9",
    "male1/photosensor/C": "A10",
    "male1/photosensor/D": "A11",
    "male2/photosensor/A": "A12",
    "male2/photosensor/B": "A13",
    "male2/photosensor/C": "A14",
    "male2/photosensor/D": "A15",
}

# The three pins in section 1 that have a claim on them nothing else may
# take, and the reason. Checked rather than merely written down.
RESERVED_PINS = {
    "D0": "USB serial to the driver",
    "D1": "USB serial to the driver",
    "D13": "the Mega's own LED - the bootloader blinks it at every reset",
    "D20": "shares silicon with the SDA pad",
    "D21": "shares silicon with the SCL pad",
}

ANALYSER_STROBE_PIN = "D4"
ANALYSER_RESET_PIN = "D3"
SHUTDOWN_PIN = "D2"
AUX_PINS = {"male1": "D24", "male2": "D25"}

# The four DSUBs exactly as they are, because they are fixed by the
# supplier. Transcribed from the netlist of the board that exists, with
# one substitution per body: `<body>/speaker +/out` is now the line out
# and `<body>/speaker -/out` its return, the amplifier having moved to
# the body. Pin 0 is the shell.
_CONNECTORS = {
    "J5": {  # female1
        0: "GND",
        1: "female1/spare1", 2: "female1/spare2", 3: "female1/spare3",
        4: "female1/audio return",
        5: "female1/photosensor",
        6: "female1/microphone",
        7: "+12V",
        8: "GND",
        9: "female1/spare4", 10: "female1/spare5", 11: "female1/spare6",
        12: "female1/line out",
        13: "female1/neopixel",
        14: "dxl_data",
        15: "+5V",
    },
    "J1": {  # female2
        0: "GND",
        1: "female2/spare1", 2: "female2/spare2", 3: "female2/spare3",
        4: "female2/audio return",
        5: "female2/photosensor",
        6: "female2/microphone",
        7: "+12V",
        8: "GND",
        9: "female2/spare4", 10: "female2/spare5", 11: "female2/spare6",
        12: "female2/line out",
        13: "female2/neopixel",
        14: "dxl_data",
        15: "+5V",
    },
    "A-J3": {  # female3, and male1's power and signals bar its audio
        0: "GND",
        1: "GND",
        2: "+12V",
        3: "female3/microphone",
        4: "female3/photosensor",
        5: "female3/audio return",
        6: "male1/neopixel",
        7: "male1/photosensor/B",
        8: "male1/photosensor/D",
        9: "+5V",
        10: "dxl_data",
        11: "female3/neopixel",
        12: "female3/line out",
        13: "male1/microphone",
        14: "male1/photosensor/A",
        15: "male1/photosensor/C",
    },
    "B-J4": {  # male1's audio, male2's everything. No power on it at all.
        0: "GND",
        1: "male1/aux",
        2: "male1/audio return",
        3: "male2/neopixel",
        4: "male2/photosensor/B",
        5: "male2/photosensor/D",
        6: "male2/line out",
        7: "centre/spare1",
        8: "male2/bar neopixel",
        9: "male1/line out",
        10: "male2/microphone",
        11: "male2/photosensor/A",
        12: "male2/photosensor/C",
        13: "male2/aux",
        14: "male2/audio return",
        15: "male1/bar neopixel",
    },
}

# The one thing about B-J4 that nobody expects and everybody needs.
UNPOWERED_CONNECTORS = ("B-J4",)


def channel_numbers():
    """Channel 1 is the lowest voice, so reference designators climb with
    pitch and the board reads in the same order the filter board's `IN`
    pads do (160, 400, 1K, 2K5, 6K25)."""
    return {body: index + 1 for index, body in enumerate(audio.BODIES_BY_PITCH)}


# --- building the thing ---------------------------------------------------


class Design:
    """Every part and every net, built once and then read."""

    def __init__(self):
        self.parts = []
        self._nets = {}
        self._build()

    # -- small helpers --

    def _part(self, ref, value, kind, description, confirm=False):
        self.parts.append(Part(ref, value, kind, description, confirm))
        return ref

    def _join(self, net_name, ref, pin):
        self._nets.setdefault(net_name, []).append((ref, pin))

    @property
    def nets(self):
        return [Net(name, terminals) for name, terminals in self._nets.items()]

    def net(self, name):
        return Net(name, self._nets[name])

    # -- the board --

    def _build(self):
        self._build_boards()
        self._build_power()
        self._build_connectors()
        self._build_spares()
        self._build_voices()
        self._build_ears()
        self._build_lights()
        self._build_sensors()
        self._build_control()

    def _build_boards(self):
        self._part("A1", "Arduino Mega 2560", "board",
                   "carried as a shield, as now")
        self._part("M1", "U2D2", "board",
                   "on its own mount; only the Dynamixel data line touches it")
        self._join("dxl_data", "M1", "data")

    def _build_power(self):
        self._part("J2", "DC jack", "connector", "supply in")
        self._part("J6", "screw bridge", "connector", "jack onto the board rail")
        self._part("J7", "JST EH 3", "connector", "GND, +12V and the servo bus in")
        self._part("C1", "470uF", "capacitor", "bulk, on the board's own +5V")
        self._part("C2", "100nF", "capacitor", "decoupling, on the board's own +5V")

        self._join("+5V", "J6", "3")
        self._join("+5V", "C1", "1")
        self._join("+5V", "C2", "1")
        self._join("GND", "J6", "4")
        self._join("GND", "C1", "2")
        self._join("GND", "C2", "2")
        self._join("GND", "J2", "2")
        self._join("GND", "J7", "1")
        self._join("+12V", "J7", "2")
        self._join("dxl_data", "J7", "3")
        self._join("+5V", "J2", "1")

        # The Mega's own regulator output, deliberately a separate net: the
        # amplifiers and the NeoPixels must not draw through it. Silkscreen
        # says which is which, because on the board that exists `J9` 35
        # looks exactly like a convenient 5 V rail.
        self._join("MEGA_5V", "A1", "5V")
        self._join("GND", "A1", "GND")
        # One analogue ground region under the filters and the analysers,
        # joined to the power ground at a single point.
        self._part("JP1", "0R", "link",
                   "the single point where analogue ground meets power ground")
        self._join("AGND", "JP1", "1")
        self._join("GND", "JP1", "2")

    def _build_spares(self):
        """Every spare conductor onto a header, the way the board that
        exists does it.

        A spare that arrives at a DSUB pin and stops is not a spare - it is
        a wire you would have to cut a track to reach. `Extra1` and `Extra2`
        are on the board today for exactly this reason; the third pad is for
        `B-J4`'s single spare, which never had one.
        """
        for body, header in (("female1", "Extra2"), ("female2", "Extra1")):
            self._part(header, "1x6 header", "connector",
                       f"{body}'s six spare conductors")
            for number in range(1, 7):
                self._join(f"{body}/spare{number}", header, str(number))

        self._part("Extra3", "1x1 pad", "connector",
                   "B-J4's single spare conductor - the males have no others")
        self._join("centre/spare1", "Extra3", "1")

    def _build_connectors(self):
        for ref, pins in _CONNECTORS.items():
            note = "DSUB-15, fixed by the supplier"
            if ref in UNPOWERED_CONNECTORS:
                note += " - CARRIES NO POWER, silkscreen it"
            self._part(ref, "DSUB-15", "connector", note)
            for pin, net_name in pins.items():
                self._join(net_name, ref, str(pin))

    def _build_voices(self):
        """Tone pin, filter, build-out resistor, out to the body."""
        channels = channel_numbers()
        for body, voice in audio.VOICES.items():
            channel = channels[body]
            resistor, capacitor = FILTER_VALUES[voice["hz"]]
            hz = voice["hz"]

            tone = f"{body}/tone"
            middle = f"{body}/filter mid"
            output = f"{body}/filter out"

            self._join(tone, "A1", voice["pin"])

            first = self._part(f"R{channel}01", resistor, "resistor",
                               f"{hz} Hz low-pass, first stage")
            second = self._part(f"R{channel}02", resistor, "resistor",
                                f"{hz} Hz low-pass, second stage")
            shunt1 = self._part(f"C{channel}01", capacitor, "capacitor",
                                f"{hz} Hz low-pass, first stage")
            shunt2 = self._part(f"C{channel}02", capacitor, "capacitor",
                                f"{hz} Hz low-pass, second stage")
            damping = self._part(f"R{channel}03", BUILD_OUT, "resistor",
                                 f"{body} build-out into the harness")

            self._join(tone, first, "1")
            self._join(middle, first, "2")
            self._join(middle, shunt1, "1")
            self._join("AGND", shunt1, "2")
            self._join(middle, second, "1")
            self._join(output, second, "2")
            self._join(output, shunt2, "1")
            self._join("AGND", shunt2, "2")
            self._join(output, damping, "1")
            self._join(f"{body}/line out", damping, "2")

            # The voice, before it leaves the board - and now the last
            # point at which it exists on the board at all.
            pad = self._part(f"TP{channel}", "test pad", "test point",
                             f"{body} filter output, {hz} Hz")
            self._join(output, pad, "1")

            # The return for this body's line out and microphone, and
            # for nothing else - the amplifier's supply current goes home
            # on GND. A link rather than the same net, so the layout has
            # to route it as its own conductor and bond it in one place.
            bond = self._part(f"JP{channel + 1}", "0R", "link",
                              f"{body} audio return onto analogue ground")
            self._join(f"{body}/audio return", bond, "1")
            self._join("AGND", bond, "2")

    def _build_ears(self):
        """One MSGEQ7 per body, strobe and reset commoned."""
        channels = channel_numbers()
        self._join("analyser/strobe", "A1", ANALYSER_STROBE_PIN)
        self._join("analyser/reset", "A1", ANALYSER_RESET_PIN)

        for body, voice in audio.VOICES.items():
            channel = channels[body]
            module = voice["module"]
            chip = self._part(
                f"U{channel}", "MSGEQ7", "analyser",
                f"module {module} - {body}. Silkscreen the body name: that "
                "mapping is why one number identifies a body all the way "
                "round the loop.",
            )
            # Named terminals, not numbers. The footprint has not been
            # chosen and inventing pin numbers would be inventing the part.
            self._join(f"{body}/microphone", chip, "IN")
            self._join(f"{body}/analyser out", chip, "OUT")
            self._join("analyser/strobe", chip, "STROBE")
            self._join("analyser/reset", chip, "RESET")
            self._join("MEGA_5V", chip, "VDD")
            self._join("AGND", chip, "GND")

            # The ADC input this module's output lands on. Module N is
            # body N, so this is A<module> and nothing else.
            self._join(f"{body}/analyser out", "A1", f"A{module}")

            pad = self._part(f"TP{channel + 10}", "test pad", "test point",
                             f"{body} analyser output, module {module}")
            self._join(f"{body}/analyser out", pad, "1")

            # The support network. Values are the MSGEQ7's typical
            # application and are NOT taken from anything in this repo -
            # the analyser array is five ready-made modules today and
            # nobody here has drawn the chip. Read them off the datasheet
            # before ordering.
            for suffix, value, kind, what in (
                ("11", "22K", "resistor", "input series"),
                ("12", "10nF", "capacitor", "input coupling"),
                ("13", "200K", "resistor", "oscillator"),
                ("14", "33pF", "capacitor", "oscillator"),
                ("15", "100nF", "capacitor", "decoupling"),
            ):
                prefix = "R" if kind == "resistor" else "C"
                self._part(
                    f"{prefix}{channel}{suffix}", value, kind,
                    f"module {module} {what} - CONFIRM against the datasheet",
                    confirm=True,
                )

        for number, (net_name, label) in enumerate(
            (("analyser/strobe", "STROBE"), ("analyser/reset", "RESET")), start=20
        ):
            pad = self._part(
                f"TP{number}", "test pad", "test point",
                f"{label} - a strobe that never pulses and nothing arriving "
                "read alike, and this is what tells them apart",
            )
            self._join(net_name, pad, "1")

    def _build_lights(self):
        for index, (net_name, pin) in enumerate(NEOPIXEL_PINS.items(), start=1):
            series = self._part(f"RN{index}", NEOPIXEL_SERIES, "resistor",
                                f"series on {net_name}")
            self._join(f"{net_name}/driven", "A1", pin)
            self._join(f"{net_name}/driven", series, "1")
            self._join(net_name, series, "2")

    def _build_sensors(self):
        for index, (net_name, pin) in enumerate(PHOTOSENSOR_PINS.items(), start=1):
            self._join(net_name, "A1", pin)
            # Whatever is fitted across J11/J12 today, which the KiCad
            # files do not say and `as built` says to go and look at. It
            # gets a footprint and a value here rather than a bare pair of
            # pads somebody has to guess at again in three years.
            self._part(
                f"RP{index}", "TBC", "resistor",
                f"{net_name} divider - CONFIRM by measuring what is fitted "
                "across J11/J12 on the board that exists",
                confirm=True,
            )
            self._join(net_name, f"RP{index}", "1")
            self._join("AGND", f"RP{index}", "2")

    def _build_control(self):
        """The amplifier shutdown net, and the two spare male conductors."""
        # RS, not R3xx: channel 3 already owns R301..R303 and a filter
        # resistor quietly becoming a 10K pull-up is not a mistake anybody
        # spots on a schematic.
        pull_up = self._part("RS1", SHUTDOWN_PULLUP, "resistor",
                             "holds the shutdown net at enabled while D2 floats")
        self._part("TP30", "test pad", "test point",
                   "amplifier shutdown - reserved, and where it gets wired from")
        self._join("amp shutdown", "A1", SHUTDOWN_PIN)
        self._join("amp shutdown", pull_up, "1")
        self._join("+5V", pull_up, "2")
        self._join("amp shutdown", "TP30", "1")

        # The two conductors the state LEDs used. The driver chain goes;
        # the wires stay, because they are the way a mute line reaches the
        # males if one is ever wanted. NEXT_PCB.md sections 4 and 7.
        for index, (body, pin) in enumerate(AUX_PINS.items(), start=1):
            series = self._part(f"RA{index}", "330R", "resistor",
                                f"{body} aux conductor - state LED or mute")
            self._join(f"{body}/aux driven", "A1", pin)
            self._join(f"{body}/aux driven", series, "1")
            self._join(f"{body}/aux", series, "2")

        for name, rail in (("TP31", "+5V"), ("TP32", "MEGA_5V"),
                           ("TP33", "GND"), ("TP34", "AGND")):
            self._part(name, "test pad", "test point", f"{rail} rail")
            self._join(rail, name, "1")
