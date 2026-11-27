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
    before_picture: str = ""
    # A test beside the guide (by its name in `manual tests`) whose
    # presses and readings the step's page carries, so the check it asks
    # for is done from the step itself.
    tool: str = ""


def page(path, text=None):
    """A markdown link to a node of the tree, by its path under /app."""
    return f"[{text or path.split('/')[-1]}](/app/{quote(path)})"


TEST_TEENSY = page("tests/manual tests/test teensy")
CONFIGURATION = page("hardware/main pcb/configuration", "hardware > main pcb > configuration")
MOTORS = page("hardware/motors", "hardware > motors")
SHIELDS = page("hardware/electronics/shields", "shields")

# The power row, as its silkscreen names it. `shields` 6b calls the third
# pin `MEGA 5V`; the board prints `USB`, and prints "MEGA 5V (COMPUTING
# USB)" in the middle of the board beside TP32, a bare pad next to JP1
# (2026-11-24: probed there, it read as a short to GND).
POWER_ROW = (
    "The power test pins are the row top right, under the three green "
    "LEDs, printed **`5V`, `12V`, `USB`, `GND`**: `USB` is MEGA 5V, the "
    "computing shield's own 5 V. **Not** the `MEGA 5V (COMPUTING USB)` "
    "label in the middle of the board: that names `TP32`, a bare pad, and "
    "4 mm from it is `JP1`, the AGND-GND bond, which is GND - a probe on it "
    "reads a short."
)

NEVER_12V_ON_J2 = (
    "**Never 12 V into `J2` or `J6`.** The backplane's `+5V` feeds every NeoPixel, "
    "every body's amplifier and every microphone. The amplifier module is "
    "recorded at **5.0 V maximum** (`params[\"audio\"][\"amplifier max supply "
    "volts\"]`) and a GF1002 has already been destroyed by a supply above it."
)

# J6, the screw terminal's landing (`J2`'s twin, in parallel with it: the
# board's only other way in for the rack's 5 V). It has no silkscreen at
# all, so the guide names its holes: rows top then bottom as the front is
# seen, columns from the power row's side to the board's right edge. Held
# to the copper by a test (`backplane-front.json`'s `holes`).
J6_ROWS = (
    ("+5V", "+5V", "GND"),
    ("+5V", "GND", "GND"),
)

POWER_OFF = (
    "Everything unpowered first: the rack supply out of `J2` (or out of "
    "the jack adapter on `J6`'s lead), the Teensy's "
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
        "adapter's Schottky), `BOARD 5V` and `12V` dark (no rack supply).",
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
        f"in. {POWER_ROW}\n\n"
        "- `5V` to `GND`, `12V` to `GND`, `USB` to `GND`: **no short**. "
        "A reading that climbs as the 470 uF charges is normal; one that beeps "
        "and stays near 0 ohm is a short - stop here.\n"
        "- `12V` to `5V` and `5V` to `USB`: **no connection at all**. "
        "The two 5 V rails are kept apart by design (the rack's and the "
        "computing shield's own).\n"
        "- If `USB` to `GND` beeps here too, the short is real. On the copper "
        "`MEGA_5V` reaches GND only through `RLPUSB` (2.2 K) and its LED, "
        "which cannot beep, so look for a solder bridge where a `MEGA_5V` "
        "joint sits one pitch from a GND one: `USB` and `GND` themselves "
        "(2.54 mm apart), and `JA1` pin 19 between its pins 20 and 21 (the "
        "empty analyser slot, lower left).\n"
        "- Every LED, diode and electrolytic against the `+` / `-` beside its "
        "pads (`mark_polarity.py` put them there).\n"
        "- The slot keys: the removed pin on each voice slot and on `JA1`, and "
        "the blocked cavity on each card, so no card can go in the wrong way.\n\n"
        "Write any surprise in the note.",
    ),
    Step(
        "solder the screw terminal at J6",
        "the bare backplane",
        "Without the DC jack `J2`, the rack's 5 V comes in on a **screw "
        "terminal soldered into `J6`**: the board's second power landing, "
        "wired in parallel with `J2` (`+5V` and `GND` only, nothing else). "
        "Skip this step if `J2` is fitted.\n\n"
        "`J6` has **no marking on the silkscreen**. It is the six large holes "
        "in two rows of three just **right of the power row's `GND` test "
        "pin**, below `J2`. Seen from the front (the side where `5V 12V USB "
        "GND` read the right way up), columns counted from the power row "
        "towards the board's right edge:\n\n"
        "| | column 1 (power-row side) | column 2 | column 3 (edge side) |\n"
        "|---|---|---|---|\n"
        f"| **top row** (level with the test pins) | {' | '.join(f'**{n}**' for n in J6_ROWS[0])} |\n"
        f"| **bottom row** | {' | '.join(f'**{n}**' for n in J6_ROWS[1])} |\n\n"
        "The `+5V` holes make an L at the top left, the `GND` holes an L at "
        "the bottom right. **The rule: RED wire on the screw whose lug is in a "
        "`+5V` hole, BLACK wire on the screw whose lug is in a `GND` hole.** "
        "For a two-way terminal at 5 mm pitch that is either:\n\n"
        "- **top row, columns 2 and 3**: RED on the column-2 screw (power-row "
        "side), BLACK on the column-3 screw (edge side); or\n"
        "- **bottom row, columns 1 and 2**: RED on the column-1 screw "
        "(power-row side), BLACK on the column-2 screw.\n\n"
        "Either way RED is the screw nearer the power row, BLACK the one "
        "nearer the board's edge. **Not** top row columns 1-2 (both `+5V`) "
        "or bottom row columns 2-3 (both `GND`): the terminal would carry "
        "nothing. Terminal body on the front, wire entries facing out where "
        "the lead can reach them, soldered on the back.\n\n"
        "Then meter on continuity, every supply off, **nothing in the screws "
        "yet**, against the power row's test pins just left of it:\n\n"
        "- the RED screw to the `5V` test pin: **beeps**; the BLACK screw to "
        "the `GND` test pin: **beeps**. Both silent the other way round "
        "(RED to `GND`, BLACK to `5V`). If RED beeps to `GND`, the terminal "
        "is in the wrong holes: stop before any power.\n"
        "- RED screw to BLACK screw: **no short** (a reading that climbs as "
        "the 470 uF charges is normal).\n\n"
        "The lead: with the rack supply plugged into the screw jack adapter "
        "and switched on, the bare RED and BLACK ends apart, meter **red "
        "probe on the RED wire, black probe on the BLACK wire: +4.75 to "
        "+5.25 V**. A minus sign means the adapter is wired the other way "
        "round: supply off and swap the wires in the adapter, not on `J6`. "
        "Supply off and unplugged, then RED into the RED screw, BLACK into "
        "the BLACK screw, tighten, tug each wire.\n\n"
        "Write in the note which holes the terminal went in.",
    ),
    Step(
        "power the bare backplane",
        "the bare backplane",
        "With the bare backplane powered from the chosen input, check:\n\n"
        "- LEDs: `BOARD 5V` lit, `12V` dark (12 V comes in only through "
        "`J7`), `MEGA 5V` dark, every `TONE` dark.\n"
        "- Test pins, against `GND`: `5V` 4.75-5.25 V. `12V`: 0 V. `USB`: "
        "0 V - if it reads 5 V the two rails are bridged: unplug and stop.\n"
        "- `L1`-`L5` (line, beside each `TONE` LED) and `M1`-`M5` (mic direct, "
        "bottom row): 0 V, held by their pull-downs (`shields` section 10, "
        "step 1).\n\n"
        "Write the `5V` reading in the note, then unplug the supply.",
        before_picture=(
            f"{NEVER_12V_ON_J2}\n\n"
            "Leave all other leads and shields disconnected. Meter the rack supply's "
            "unloaded plug with the red probe on the centre and black on the sleeve. "
            "Continue only if it reads **+4.75 to +5.25 V**. Switch the supply off. "
            "Choose the one input you fitted. J6 and J2 share the same rail.\n\n"
            '<details name="rack-input" open><summary><strong>J6 screw terminal '
            '(external jack adapter)</strong></summary>'
            "<p>Use the lead checked in the previous step. Its RED wire goes to "
            "+5V at J6 and BLACK to GND. Plug the rack supply into the external "
            "jack adapter, then switch it on. J2 can be empty.</p></details>\n\n"
            '<details name="rack-input"><summary><strong>J2 board-mounted DC jack'
            "</strong></summary><p>Use this input if the jack is soldered at J2. "
            "Plug the checked centre-positive rack supply directly into J2, "
            "then switch it on.</p></details>"
        ),
    ),
    Step(
        "servo supply through J7",
        "the bare backplane",
        "The servo supply reaches the backplane only through `J7` (`SERVO "
        "BUS · 12 V`, JST EH 3: pin 1 `GND`, pin 2 `+12V`, pin 3 `dxl_data`, "
        "the U2D2's data line). On the copper `dxl_data` goes only to the "
        "body connectors (`J5`, `J1`, `A-J3`), never to the computing slot.\n\n"
        "Before plugging its lead in: **the U2D2's USB out** (with it in, the "
        "U2D2 may hold pin 3 at its own logic level, which is not what this "
        "looks for). Then meter the lead with its supply on:\n\n"
        "- pins 2 to 1: 12 V;\n"
        "- pin 3 to pin 1: **not 12 V**. 12 V there is the servo supply on "
        "the data line: supply off and stop. Nothing documents what it does "
        "read, so write it in the note.\n\n"
        "Supply off, plug it in, supply on:\n\n"
        "- `12V` LED lit, `12V` test pin about 12 V (write it in the note).\n"
        "- `BOARD 5V` LED dark and `5V` test pin at 0 V: 12 V has not found the "
        "5 V rail.\n\n"
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
        "U2D2's USB to the laptop, the rack supply to `J2` (or to the jack "
        "adapter on `J6`'s RED and BLACK lead), the servo supply "
        "to `J7` - all still switched off.",
    ),
    Step(
        "power up the mounted rack",
        "mounting",
        "Rack supply and Teensy USB on together. `BOARD 5V` and `MEGA 5V` "
        "lit, `12V` lit when the servo supply is on, every `TONE` dark.\n\n"
        "Then the Teensy check again, from here: press **`test teensy: "
        "start`** below. Every `test teensy: check` reads ok, then watch "
        "the yellow `TONE` LEDs walk 1 to 5 and press `test teensy: the tone "
        "LEDs lit 1 to 5` or `test teensy: a tone LED stayed dark`. If it "
        f"cannot talk (port, firmware), its own page {TEST_TEENSY} has the "
        "port picker and `flash firmware`.\n\n"
        "A difference from before mounting is a header pushed out of line or "
        "a lead pinched by the enclosure.",
        tool="test teensy",
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
            "- `5V` test pin still 4.75-5.25 V (write it in the note: each body "
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
            "females: `5V` in range (note it), nothing warm after a minute, "
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
        "repair the broken cable",
        "the microphones",
        "Step 1's note: the cable between **female1's microphone and her "
        "base** (the female base v2's `J3 MICROPHONE`). Three conductors: "
        "`GND`, `+5V`, `OUT` - the holder's `J1` order, pin 1 to pin 1 with "
        "the harness (RELEASE_REVIEW.md). After the repair, **both ends "
        "unplugged**, meter it:\n\n"
        "- each conductor end to end: it beeps;\n"
        "- each against the other two, at one end: **silence**. Above all "
        "`+5V` against `OUT`: 5 V on `OUT` reaches `M1` (mic direct 1) and, "
        "through its 4.7 K, Teensy pin 14 (`shields` section 4a; the 4.7 K "
        "limits the current, it does not make the pin 5 V tolerant). `+5V` "
        "against `GND` would short the rack's 5 V rail.\n\n"
        "Write what was broken and how it was repaired in the note. Its "
        "powered check is the next step's `M1` reading.",
    ),
    Step(
        "mount the microphones",
        "the microphones",
        f"{POWER_OFF}\n\n"
        "Each on its Rev C flex holder, one MAX9814 module per holder in the "
        "chosen socket. Shunts as first assembled: **JP1 2-3 (40 dB), JP2 1-2 "
        "(1:500)**, and only ever moved with the power off "
        "(`microphone-flex/README.md`). Holder `J1` is GND / +5V / OUT, pin 1 "
        "to pin 1 with the harness.\n\n"
        "Power up. On the backplane's bottom row, `M1`-`M5` (mic direct, one "
        "per body, in body order; `AGND` at the end of the row): **about 1.23 V at rest**, 0 V when that "
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
        "`TONE` still dark and every `L1`-`L5` pin at 0 V - nothing sings until "
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
