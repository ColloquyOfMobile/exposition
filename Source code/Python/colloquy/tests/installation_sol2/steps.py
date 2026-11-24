# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/installation_sol2/steps.py

"""The installation of PCB solution 2, step by step. Pure: text only.

**Solution 2 (sol2)** is the shields backplane with the Teensy 4.1 adapter
in its computing slot and the analyser slot empty: `shields` section 0's
step 2 and section 10's bring-up, done in the room. What it leaves out on
purpose is anything that needs **firmware 5** (the Teensy's port of the
installation's firmware), which is not written yet: NeoPixels, photo-
sensors, voices and hearing cannot be driven from the Teensy until it
is. The last step says so, so the guide never looks finished early.

Every number is a document's, named where it is used: `shields` (SHIELDS.md
under `hardware > electronics`), the backplane's copper (`circuit.json`),
the body boards' READMEs, `params["audio"]["amplifier max supply volts"]`.
A step that needs a measurement nobody has a source for says to measure
and write it down, not what it should be.

The **key** of a step is what the record stores, so it is never reworded;
the title and the text may be. Order is the tuple's order.
"""
from typing import NamedTuple
from urllib.parse import quote


class Step(NamedTuple):
    key: str
    phase: str
    text: str  # markdown


def page(path, text=None):
    """A markdown link to a node of the tree, by its path under /app."""
    return f"[{text or path.split('/')[-1]}](/app/{quote(path)})"


TEST_TEENSY = page("tests/manual tests/test teensy")
CONFIGURATION = page("hardware/main pcb/configuration", "hardware > main pcb > configuration")
MOTORS = page("hardware/motors", "hardware > motors")
SHIELDS = page("hardware/electronics/shields", "shields")

NEVER_12V_ON_J2 = (
    "**Never 12 V into `J2`.** The backplane's `+5V` feeds every NeoPixel, "
    "every body's amplifier and every microphone. The amplifier module is "
    "recorded at **5.0 V maximum** (`params[\"audio\"][\"amplifier max supply "
    "volts\"]`) and a GF1002 has already been destroyed by a supply above it."
)

POWER_OFF = (
    "Everything unpowered first: the rack supply out of `J2`, the Teensy's "
    "USB lead out, the servo supply off. `shields` section 10: change "
    "anything only with both off, and power both back up together."
)

STEPS = (
    # --- where things stand -------------------------------------------
    Step(
        "check the present state",
        "where things stand",
        "The state below was written from memory. Check each line against the "
        "room and **write in the note what differs**, then mark this done.\n\n"
        "- The sol2 backplane has the Teensy adapter in its computing slot and "
        "is connected to the laptop by the Teensy's USB lead, but is **not "
        "mounted** in the enclosure (mounting it needs the USB unplugged).\n"
        "- The analyser slot `JA1` is empty (sol2 has no MSGEQ7 carrier).\n"
        "- The voice slots `JV1`-`JV5`: write down which hold a card. The PCB "
        "orders record the voice cards as received, not soldered.\n"
        "- female1, female2, female3 are **mounted** (screwed on) but **not "
        "plugged in**.\n"
        "- male1 and male2 are **not mounted**.\n"
        "- The microphones are **not mounted**.\n"
        "- **One cable is broken**: write in the note which one (which DSUB, "
        "which body, which end, which conductor if known).\n"
        "- The U2D2: where it is, whether its servo supply is connected, and "
        f"what {MOTORS} says (plugged in or not).",
    ),
    Step(
        "record the configuration",
        "where things stand",
        f"On {CONFIGURATION}: board **shields backplane**, computing slot "
        "**Teensy 4.1 adapter**, analyser slot **empty**, and each voice slot "
        "as the previous step found it. It drives nothing; it is the record "
        "the other pages compare against (`audio > wired bodies` is one).",
    ),
    Step(
        "test teensy passes",
        "where things stand",
        f"With the board as it is now (only the Teensy's USB in), press "
        f"`flash firmware` then `start` on {TEST_TEENSY}. Every check ok, the "
        "Teensy's own LED flickers, and **TONE 1 to TONE 5 light one at a "
        "time, in order**: that proves the five tone pins, the adapter's "
        "translators and the backplane's LEDs before anything is moved.\n\n"
        "On the backplane: green `MEGA 5V` lit (the Teensy's USB through the "
        "adapter's Schottky), `+5V` and `+12V` dark (no rack supply).",
    ),
    # --- the bare backplane ------------------------------------------
    Step(
        "unplug and take the adapter off",
        "the bare backplane",
        "Unplug the Teensy's USB lead: it is the only power on the board. "
        "Then lift the adapter straight off the computing slot, both ends "
        "evenly. Nothing on the backplane is powered now.",
    ),
    Step(
        "meter the bare backplane unpowered",
        "the bare backplane",
        "Meter on resistance / continuity, every supply off, nothing plugged "
        "in. On the power test pins (`+5V`, `+12V`, `MEGA 5V`, `GND`):\n\n"
        "- `+5V` to `GND`, `+12V` to `GND`, `MEGA 5V` to `GND`: **no short**. "
        "A reading that climbs as the 470 uF charges is normal; one that beeps "
        "and stays near 0 ohm is a short - stop here.\n"
        "- `+12V` to `+5V` and `+5V` to `MEGA 5V`: **no connection at all**. "
        "The two 5 V rails are kept apart by design (the rack's and the "
        "computing shield's own).\n"
        "- Every LED, diode and electrolytic against the `+` / `-` beside its "
        "pads (`mark_polarity.py` put them there).\n"
        "- The slot keys: the removed pin on each voice slot and on `JA1`, and "
        "the blocked cavity on each card, so no card can go in the wrong way.\n\n"
        "Write any surprise in the note.",
    ),
    Step(
        "power the bare backplane",
        "the bare backplane",
        f"{NEVER_12V_ON_J2}\n\n"
        "Before plugging the rack supply in: meter its plug unloaded. The jack "
        "is **centre-positive**; the reading should be the rail's 4.75-5.25 V "
        "(the range `shields` section 2e works its corners at). Then plug it "
        "into `J2`, nothing else connected:\n\n"
        "- LEDs: `+5V` lit, `+12V` dark (12 V comes in only through `J7`), "
        "`MEGA 5V` dark, every `TONE` dark.\n"
        "- `+5V` test pin: 4.75-5.25 V. `+12V`: 0 V. `MEGA 5V`: 0 V - if it "
        "reads 5 V the two rails are bridged: unplug and stop.\n"
        "- `LINE 1`-`LINE 5` and `MIC DIRECT 1`-`MIC DIRECT 5`: 0 V, held by "
        "their pull-downs (`shields` section 10, step 1).\n\n"
        "Write the `+5V` reading in the note, then unplug the supply.",
    ),
    Step(
        "servo supply through J7",
        "the bare backplane",
        "The servo supply reaches the backplane only through `J7` (`SERVO "
        "BUS · 12 V`, JST EH 3: pin 1 `GND`, pin 2 `+12V`, pin 3 `dxl_data`). "
        "Before plugging its lead in, meter the lead with its supply on: 12 V "
        "between pins 2 and 1, and **nothing on pin 3**. Supply off, plug it "
        "in, supply on:\n\n"
        "- `+12V` LED lit, `+12V` test pin about 12 V (write it in the note).\n"
        "- `+5V` LED dark and `+5V` test pin at 0 V: 12 V has not found the 5 V "
        "rail.\n\n"
        "Servo supply off again.",
    ),
    # --- mounting ------------------------------------------------------
    Step(
        "refit the adapter",
        "mounting",
        f"{POWER_OFF}\n\n"
        "The adapter goes on the DSUB face, the way the Mega would: its female "
        "headers onto the backplane, **the Teensy facing out**, its USB at the "
        "top edge. Every header fully seated and none offset by a column - "
        "look along each row. Spacers at `HM1`-`HM4`: **round, 4 mm outside "
        "diameter at most, on the front, screw heads on the back** (wider hex "
        "standoffs hit the headers at `HM2`/`HM3`; ASSEMBLY.md).",
    ),
    Step(
        "mount the backplane",
        "mounting",
        "Into the enclosure on its four 8 mm mounts (the original box's "
        "pattern, `backplane/ENCLOSURE_MOUNTING.md`). Check nothing on the "
        "back touches metal, and that the test pins and the eight LEDs can "
        "still be reached and seen. Then the leads: the Teensy's USB and the "
        "U2D2's USB to the laptop, the rack supply to `J2`, the servo supply "
        "to `J7` - all still switched off.",
    ),
    Step(
        "power up the mounted rack",
        "mounting",
        "Rack supply and Teensy USB on together. `+5V` and `MEGA 5V` lit, "
        "`+12V` lit when the servo supply is on, every `TONE` dark. Then "
        f"{TEST_TEENSY} `start` again: every check ok and TONE 1-5 in order. "
        "A difference from before mounting is a header pushed out of line or "
        "a lead pinched by the enclosure.",
    ),
    # --- the harness -----------------------------------------------------
    Step(
        "repair the broken cable",
        "the harness",
        "The cable named in the first step's note. After the repair, **both "
        "ends unplugged**, meter it:\n\n"
        "- every conductor end to end, the shell included;\n"
        "- then each conductor against every other: **no connection**. Above "
        "all the `+12V` conductor (pin 7 on female1's `J5` and female2's "
        "`J1`, pin 2 on `A-J3`) and the `+5V` one (pin 15 on `J5`/`J1`, pin 9 "
        "on `A-J3`) against everything else: 12 V on a signal or on the 5 V "
        "conductor reaches a NeoPixel strip, an amplifier or the Teensy's "
        "translators. `B-J4` carries no power.\n\n"
        "The pin tables are in `thomas or teensy` section 2 (\"The four body "
        "connectors\"). Write what was broken and how it was repaired in the "
        "note.",
    ),
    # --- the bodies, one at a time -------------------------------------
    *(
        Step(
            f"plug in {body}",
            "the bodies",
            f"{POWER_OFF}\n\n"
            f"Plug {body}'s harness in (`{connector}` on the backplane). Its "
            "body board is the female base v2: the GF1002 amplifier sits in "
            "its socket on 5 V only, the servo on 12 V.\n\n"
            "Power up and, for the first minute:\n\n"
            "- `+5V` test pin still 4.75-5.25 V (write it in the note: each body "
            "adds load).\n"
            "- Nothing warm: touch the amplifier module and the servo after a "
            "minute. A smell or a hot part: everything off.\n"
            "- Its NeoPixels **stay dark**: the line is held low by its 100 K "
            "pull-down until firmware 5 drives it.\n"
            f"- Its servo: `drivers > u2d2 > {body}` `init hardware` answers "
            "without an error. Its turn count was lost with its power: "
            "before any move, compare its `angle` with where the body really "
            "is; if they disagree, turn it to its origin by hand and press "
            "`set current position as dxl origin`.",
        )
        for body, connector in (("female1", "J5"), ("female2", "J1"), ("female3", "A-J3"))
    ),
    *(
        Step(
            f"mount and plug in {body}",
            "the bodies",
            f"{POWER_OFF}\n\n"
            f"Mount {body} (male static v2 board), then plug in its harness. "
            f"{body}'s conductors arrive on {connectors}. Then, as for the "
            "females: `+5V` in range (note it), nothing warm after a minute, "
            "its rings dark, its servo answering, its angle checked against "
            "the room before any move.",
        )
        for body, connectors in (
            ("male1", "`A-J3` (power, shared with female3) and `B-J4`"),
            ("male2", "`B-J4`, which carries no power: find on the `harness` "
             "page where male2's 5 V and 12 V reach it, and write it in the note"),
        )
    ),
    Step(
        "the bar",
        "the bodies",
        "The bar's servo travels 2.4 servo turns, so its calibration is the "
        "one most easily lost (`hardware > motors` explains). Check its angle "
        f"against the room before it moves; and before unplugging anything "
        f"later, use {MOTORS} `unplug the motors`, which homes first.",
    ),
    # --- the microphones ------------------------------------------------
    Step(
        "mount the microphones",
        "the microphones",
        f"{POWER_OFF}\n\n"
        "Each on its Rev C flex holder, one MAX9814 module per holder in the "
        "chosen socket. Shunts as first assembled: **JP1 2-3 (40 dB), JP2 1-2 "
        "(1:500)**, and only ever moved with the power off "
        "(`microphone-flex/README.md`). Holder `J1` is GND / +5V / OUT, pin 1 "
        "to pin 1 with the harness.\n\n"
        "Power up. On the backplane, `MIC DIRECT 1`-`MIC DIRECT 5` (one per "
        "body, in body order): **about 1.23 V at rest**, 0 V when that "
        "microphone is unplugged (`shields` section 6b). Write the five "
        "readings in the note. A pin at 5 V is a microphone wired to the "
        "supply: everything off.",
    ),
    # --- the voices ------------------------------------------------------
    Step(
        "solder the voice cards",
        "the voices",
        "Five voice-thomas cards, by hand, each with its body's values "
        "(`voice-thomas/variants`, ASSEMBLY.md): R1/R2 metal film at 7.62 mm, "
        "C1/C2 film (no ceramic) at 5 mm, R3 100 K. Write the pitch and the "
        "body in the box on the front, tick the table on the back.",
    ),
    Step(
        "fit the voice cards",
        "the voices",
        f"{POWER_OFF}\n\n"
        "Card N in `JVN` (slot N is body N, in body order). The key stops a "
        f"card going in reversed. Update {CONFIGURATION}. Power up: every "
        "`TONE` still dark and every `LINE` pin at 0 V - nothing sings until "
        "a tone is sent.",
    ),
    # --- what has to wait -----------------------------------------------
    Step(
        "firmware 5",
        "what waits",
        "What sol2 cannot test yet: the Teensy has no port of the "
        "installation's firmware (firmware 5), so its NeoPixels, photo-"
        "sensors, voices and hearing cannot be driven or read. When it "
        f"exists: `shields` section 10, step 3 - `MEGA 5V` lit, the Teensy's "
        "LED flickering with each command, each `TONE` LED with its body, "
        "then polled capture and `goertzel.py`, every tone on its own bin. "
        "Mark this done only then.",
    ),
)

KEYS = tuple(step.key for step in STEPS)
