# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/electronics/next_pcb_report.py

"""Reading `next_pcb.py` back out: the netlist and the bill of materials.

Separate from the design itself for the reason the three electronics
documents are separate from each other - one of these files says what the
board *is* and this one says how to look at it, and mixing them means
every change to a table's layout touches the design.

Both outputs are generated into `CAD/KiCad/electronic box v2/` by
`next_pcb.py` at the repo root, and both say so at the top: a generated
file that does not announce itself gets edited by hand exactly once.
"""
from colloquy.drivers import audio

from . import next_pcb_mechanical as mechanical
from .next_pcb import (
    ANALYSER_RESET_PIN,
    ANALYSER_STROBE_PIN,
    BUILD_OUT,
    FILTER_VALUES,
    RESERVED_PINS,
    Design,
    _CONNECTORS,
    channel_numbers,
)


def _pin_sort_key(pin):
    """Mega pins in the order somebody reads a pin header: D before A,
    numerically within each."""
    letter, number = pin[0], pin[1:]
    return (0 if letter == "D" else 1, int(number) if number.isdigit() else 0, pin)


def mega_pins(design=None):
    """Every Mega pin this board uses, and the net(s) on it.

    The one view that answers "is this pin free" without reading the whole
    netlist, and what the checks are written against. `5V` and `GND` are
    left out - they are rails, not signals, and they are the only two
    terminals of A1 that are legitimately on a net with many others.
    """
    design = design or Design()
    used = {}
    for net in design.nets:
        for ref, pin in net.terminals:
            if ref == "A1" and pin not in ("5V", "GND"):
                used.setdefault(pin, []).append(net.name)
    return {
        pin: nets
        for pin, nets in sorted(used.items(), key=lambda item: _pin_sort_key(item[0]))
    }


def _table(headers, rows):
    out = [
        "| " + " | ".join(headers) + " |",
        "|" + "|".join("---" for _ in headers) + "|",
    ]
    out += ["| " + " | ".join(str(cell) for cell in row) + " |" for row in rows]
    return "\n".join(out)


_GENERATED = (
    "**Generated. Do not edit.** Run `py next_pcb.py` from the repo root "
    "after changing `colloquy/hardware/electronics/next_pcb.py`."
)


def netlist_markdown(design=None):
    """The whole board, in the order somebody draws a schematic in."""
    design = design or Design()
    channels = channel_numbers()
    parts = {part.ref: part for part in design.parts}

    lines = [
        "# The next PCB — netlist",
        "",
        _GENERATED,
        "",
        "Why it is generated: which body speaks at which pitch, out of which",
        "timer pin and into which analyser module is one table, and the",
        "firmware and four Python nodes already read it",
        "(`colloquy/drivers/audio.py`). This reads the same one, so a channel",
        "cannot be laid out against a pin the sketch does not drive.",
        "",
        "`NEXT_PCB.md` is the specification and the reasoning; this is the",
        "wiring. `AS_BUILT.md` is the board that exists today.",
        "",
        "---",
        "",
        "## 1. Every Mega pin",
        "",
        _table(
            ("Pin", "Net"),
            [
                (f"**{pin}**", ", ".join(f"`{net}`" for net in nets))
                for pin, nets in mega_pins(design).items()
            ],
        ),
        "",
        "Reserved, and deliberately on nothing:",
        "",
        _table(
            ("Pin", "Why"),
            [(f"**{pin}**", why) for pin, why in RESERVED_PINS.items()],
        ),
        "",
        "---",
        "",
        "## 2. The five voices",
        "",
        "Each tone pin feeds the filter channel of its own frequency and no",
        "other. This is the one fault the whole design cannot detect: a",
        "low-pass passes anything below its corner, so a tone in the wrong",
        "channel still comes out, still lands in its own band and still",
        'reports "heard". What is lost is the filtering, and the symptom is',
        "poor detection in a noisy room months later. Silkscreen every stage",
        "with its frequency and its pin.",
        "",
        _table(
            ("Body", "Pitch", "Timer", "Pin", "Filter R", "Filter C",
             "Build-out", "Test pad"),
            [
                (
                    f"**{body}**",
                    f"{audio.VOICES[body]['hz']} Hz",
                    audio.VOICES[body]["timer"],
                    f"`{audio.VOICES[body]['pin']}`",
                    f"R{channels[body]}01 = R{channels[body]}02 = "
                    f"{FILTER_VALUES[audio.VOICES[body]['hz']][0]}",
                    f"C{channels[body]}01 = C{channels[body]}02 = "
                    f"{FILTER_VALUES[audio.VOICES[body]['hz']][1]}",
                    f"R{channels[body]}03 = {BUILD_OUT}",
                    f"TP{channels[body]}",
                )
                for body in audio.BODIES_BY_PITCH
            ],
        ),
        "",
        "---",
        "",
        "## 3. The five ears",
        "",
        "Strobe and reset are commoned across all five, so one cycle through",
        "the seven bands reads every module at once — and reads them at the",
        "same moment, which is the whole reason `read every microphone` is",
        "one command rather than five.",
        "",
        _table(
            ("Body", "Ref", "Module", "ADC", "Its own band", "Test pad"),
            [
                (
                    f"**{body}**",
                    f"U{channels[body]}",
                    f"module {audio.VOICES[body]['module']}",
                    f"`A{audio.VOICES[body]['module']}`",
                    f"band {audio.band_of_body(body)}",
                    f"TP{channels[body] + 10}",
                )
                # Module order, not pitch order: this is the table about
                # the modules, and reading it 0,1,2,3,4 is the whole point
                # of module N being body N.
                for body in audio.BODIES
            ],
        ),
        "",
        f"`analyser/strobe` on **{ANALYSER_STROBE_PIN}**, `analyser/reset` on "
        f"**{ANALYSER_RESET_PIN}**, both commoned to all five modules.",
        "",
        "Module N is body N. Silkscreen the body name beside each module:",
        "that mapping is the whole reason one number identifies a body all",
        "the way round the loop, out of the timer, through the room and back",
        "into the ADC.",
        "",
        "---",
        "",
        "## 4. The connectors, as the supplier fixes them",
        "",
        "One substitution per body against `as built`: `speaker +/out` is now",
        "the line out and `speaker -/out` its return, the amplifier having",
        "moved to the body. Nothing else moves, and nothing is asked of the",
        "supplier. Pin 0 is the shell.",
        "",
    ]

    for ref, pins in _CONNECTORS.items():
        lines += [
            f"### `{ref}` — {parts[ref].description}",
            "",
            _table(
                ("Pin", "Net"),
                [
                    ("shell" if pin == 0 else pin, f"`{net}`")
                    for pin, net in sorted(pins.items())
                ],
            ),
            "",
        ]

    lines += [
        "---",
        "",
        "## 5. Every net",
        "",
        "A net with one terminal is a mistake, and so is a Mega pin on two",
        "signals. There are none of either here, and",
        "`pytest_tests/hardware/test_next_pcb.py` fails if one appears.",
        "",
        _table(
            ("Net", "Terminals", "On"),
            [
                (
                    f"`{net.name}`",
                    len(net.terminals),
                    ", ".join(f"{ref}.{pin}" for ref, pin in net.terminals),
                )
                for net in sorted(design.nets, key=lambda net: net.name)
            ],
        ),
        "",
    ]
    return "\n".join(lines)


def bom_markdown(design=None):
    """What to order, with the two groups that are not ours to choose kept
    apart from the ones that are."""
    design = design or Design()

    def grouped(parts):
        buckets = {}
        for part in parts:
            buckets.setdefault((part.kind, part.value), []).append(part.ref)
        return [
            (kind, f"**{value}**", len(refs), ", ".join(sorted(refs)))
            for (kind, value), refs in sorted(buckets.items())
        ]

    known = [part for part in design.parts if not part.confirm]
    confirm = [part for part in design.parts if part.confirm]

    return "\n".join([
        "# The next PCB — bill of materials",
        "",
        _GENERATED,
        "",
        "## Decided",
        "",
        _table(("Kind", "Value", "Qty", "References"), grouped(known)),
        "",
        "---",
        "",
        "## Not decided here — confirm before ordering",
        "",
        "Neither group below is recorded in this repository, and neither is",
        "the generator's to invent. They are kept apart rather than mixed in",
        "above, because a plausible-looking number passing for a known one is",
        "exactly how a board comes back wrong.",
        "",
        "- **The MSGEQ7 support network.** The analyser array is five",
        "  ready-made modules today (`HARDWARE_SETUP.md` section 4) and",
        "  nobody here has drawn the chip. The values below are its",
        "  datasheet's typical application, carried so the schematic has",
        "  something to place. Read them off the datasheet before ordering,",
        "  and take the pin numbering from it too — this netlist names the",
        "  chip's terminals rather than numbering them, on purpose.",
        "- **The light-sensor dividers.** `as built` records that the KiCad",
        "  files do not say whether what sits across `J11`/`J12` is a shunt",
        "  or a resistor, and that the light sensors work, so it is",
        "  something. Measure one and put the number here.",
        "",
        _table(("Kind", "Value", "Qty", "References"), grouped(confirm)),
        "",
    ])

def mechanical_markdown():
    """Where the edges and the connectors have to be, and what is free.

    Everything here is read out of the board that exists. The enclosure
    was cut for it, so a replacement that is a millimetre out anywhere in
    section 1 is a replacement that does not go in the rack.
    """
    board = mechanical.outline()
    freed = mechanical.freed_region()

    rows = []
    for reference, place in mechanical.fixed_placements().items():
        edge, distance = mechanical.edges_of(reference)
        rows.append((
            f"`{reference}`",
            f"{place['x']:.2f}, {place['y']:.2f}",
            f"{place['rotation']:.0f}°",
            f"{edge}, {distance:.2f} mm in",
            place["why"],
        ))

    return "\n".join([
        "# The next PCB — mechanical envelope",
        "",
        _GENERATED,
        "",
        "Read out of `CAD/KiCad/electronic box/electronic box.kicad_pcb`, not",
        "remembered. The enclosure was cut for that board; a replacement that",
        "is a millimetre out in section 1 does not go in the rack.",
        "",
        "---",
        "",
        "## 1. The outline, which does not change",
        "",
        _table(
            ("", "Value"),
            [
                ("Size", f"**{board['width']:.0f} × {board['height']:.0f} mm** (A4)"),
                ("Corner radius", f"{board['corner_radius']:.0f} mm, all four"),
                ("Extent, x", f"{board['left']:.2f} … {board['right']:.2f} mm"),
                ("Extent, y", f"{board['top']:.2f} … {board['bottom']:.2f} mm"),
            ],
        ),
        "",
        "Keep the same origin as well as the same size. Every coordinate",
        "below is in that file's frame, and a new board drawn at 0,0 would",
        "make all of them arithmetic somebody has to redo by hand.",
        "",
        "## 2. What the panel has a hole for",
        "",
        "These positions are the enclosure's, not the layout's. Everything",
        "else on the board is free.",
        "",
        _table(("Ref", "x, y", "Rot", "Edge", "What it is"), rows),
        "",
        "Three edges carry connectors — two DSUBs on the bottom, one on the",
        "left, one on the right — and the DC jack is on the right near the",
        "top. The Mega and the U2D2 both sit along the top, because both of",
        "their USB sockets have to be reachable.",
        "",
        "## 3. Mounting holes: there are none",
        "",
        "The exported NPTH drill file has a header, an `M30`, and not one",
        "coordinate between them, and there is no `MountingHole` footprint on",
        "the board either. An A4 board carrying a Mega 2560 as a shield, five",
        "DSUB housings and a DC jack is held by nothing but those housings'",
        "own jackscrews.",
        "",
        "**Decide this on purpose for the next one.** It is four holes and a",
        "keep-out, and the board is large enough to flex against a shield",
        "with forty-odd pins in it.",
        "",
        "## 4. The room the amplifiers free",
        "",
        f"Ten parts leave the board — five TPA2005D1 breakouts and their five",
        f"volume pots — because the amplifier moved to the body. They occupied",
        f"a band **{freed['width']:.0f} mm wide and "
        f"{freed['height']:.0f} mm tall** across the middle of the board:",
        "",
        _table(
            ("", "Value"),
            [
                ("x", f"{freed['left']:.2f} … {freed['right']:.2f} mm"),
                ("y", f"{freed['top']:.2f} … {freed['bottom']:.2f} mm"),
                ("Parts removed", freed["parts"]),
            ],
        ),
        "",
        "That is a bounding box of what was there, not a keep-out and not a",
        "promise — the parts around it have not moved. But the filter stages",
        "and the analyser array have to go somewhere, and this is the room",
        "that appeared, in the half of the board nearest the body connectors.",
        "",
        "## 5. What the placement has to respect",
        "",
        "Not a layout — that is a person's job in front of a screen — but the",
        "constraints the netlist and `NEXT_PCB.md` between them impose:",
        "",
        "- **One analogue ground region** under the five filters and the five",
        "  analysers, bonded to power ground at a single point (`JP1`).",
        "- **The +5 V that leaves on the body connectors, and its return,",
        "  must not run under the filter stages.** That rail now carries an",
        "  amplifier's peaks at the far end of every cable.",
        "- **Each filter channel next to the connector it feeds**, so the",
        "  track from a tone pin to its own stage is short and unambiguous.",
        "  The one fault this design cannot detect is a tone in the wrong",
        "  channel, and a layout where that is obvious to the eye is worth",
        "  more than a note about it.",
        "- **The five analysers together**, since strobe and reset are",
        "  commoned across all five and their outputs land on A0–A4.",
        "- **Test pads reachable with the board in the rack**, or they are",
        "  test pads for a board on a bench, which is not where it fails.",
        "",
    ])
