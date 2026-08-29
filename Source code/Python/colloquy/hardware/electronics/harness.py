# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/electronics/harness.py

"""The four boards between the electronic box and the bodies.

`as built` and `next pcb` describe one board - the one in the rack - and
both of them say the harness behind its connectors is **fixed**. These
are that harness. Four small PCBs, no active components on any of them,
nothing but connectors and copper:

    electronic box  A-J3 ─┐
                    B-J4 ─┴→ center ─┬→ female static → female base → body
                                     ├→ male 1 ──────→ male static ─→ body
                                     └→ male 2 ──────→ male static ─→ body

    electronic box  J5 ────────────→ female static → female base → body
                    J1 ────────────→ female static → female base → body

**Read out of the KiCad files, not restated.** Every pinout below is
parsed from the four `.kicad_pcb` files each time this is opened, for the
reason `next_pcb_mechanical.py` gives about the envelope: a second copy
of a number is a number that can be wrong. What the module adds is the
topology, which is not in any one of the four files - each board knows
only its own connectors.

**Why they matter beyond being documented.** They answer, on their own
copper, the question `next pcb` calls the one that could block the
build: where male2's 5 V comes from. It comes through here. `center`
takes the single +5 V conductor on `A-J3` pin 9 and fans it out to three
cables - female static, male 1 and male 2 - so male2 does have a supply
from the box, just not on `B-J4`. See NEXT_PCB.md section 5.
"""
from functools import lru_cache
from pathlib import Path

# Five directories up from here is the repo root: electronics -> hardware
# -> colloquy -> Python -> Source code -> repo.
KICAD = Path(__file__).resolve().parents[5] / "CAD" / "KiCad"


class Board:
    """One of the four, and what it is for."""

    def __init__(self, folder, title, what, where):
        self.folder = folder
        self.title = title
        self.what = what
        self.where = where

    @property
    def path(self):
        return KICAD / self.folder / f"{self.folder}.kicad_pcb"

    def __repr__(self):
        return f"Board({self.folder})"


BOARDS = (
    Board(
        "center",
        "center",
        "Splits the box's two shared connectors into one cable per body, "
        "and taps the bar's own Dynamixel.",
        "on the bar, at the centre of the piece",
    ),
    Board(
        "female static",
        "female static",
        "A straight pass-through of all fifteen conductors, tapping the "
        "female's own Dynamixel where the body turns.",
        "at a female's joint - the part that does not turn with her",
    ),
    Board(
        "female base",
        "female base",
        "The far end: the DSUB becomes one JST per thing in the body, plus "
        "the mirror's Dynamixel.",
        "inside a female",
    ),
    Board(
        "male static",
        "male static",
        "The whole of a male on one board: four light sensors, two NeoPixel "
        "lines, microphone, speaker, state LED and his Dynamixel.",
        "inside a male",
    ),
)

BOARDS_BY_FOLDER = {board.folder: board for board in BOARDS}


# --- reading a .kicad_pcb -------------------------------------------------


def parse(text):
    """KiCad's s-expressions as nested lists.

    A reader rather than a regex, because a pad's net sits three levels
    inside a footprint and the file is tab-indented with CRLF line
    endings - both of which a pattern gets wrong quietly.
    """
    tokens = []
    index, end = 0, len(text)
    while index < end:
        character = text[index]
        if character in "()":
            tokens.append(character)
            index += 1
        elif character == '"':
            cursor = index + 1
            piece = []
            while cursor < end and text[cursor] != '"':
                if text[cursor] == "\\":
                    piece.append(text[cursor + 1])
                    cursor += 2
                else:
                    piece.append(text[cursor])
                    cursor += 1
            tokens.append(("".join(piece),))
            index = cursor + 1
        elif character.isspace():
            index += 1
        else:
            cursor = index
            while cursor < end and not text[cursor].isspace() and text[cursor] not in '()"':
                cursor += 1
            tokens.append((text[index:cursor],))
            index = cursor

    def build(position):
        out = []
        while position < len(tokens):
            token = tokens[position]
            if token == "(":
                child, position = build(position + 1)
                out.append(child)
            elif token == ")":
                return out, position + 1
            else:
                out.append(token[0])
                position += 1
        return out, position

    tree, _ = build(0)
    return tree[0] if tree else []


def children(node, name):
    return [c for c in node if isinstance(c, list) and c and c[0] == name]


def _property(node, name, default=None):
    for item in children(node, "property"):
        if len(item) > 2 and item[1] == name:
            return item[2]
    return default


class Connector:
    """One connector on one board, and what each of its pins carries."""

    def __init__(self, ref, label, footprint, pins):
        self.ref = ref
        self.label = label
        self.footprint = footprint
        # pin name -> net name. Pin "0" on a DSUB is its shell.
        self.pins = pins

    @property
    def kind(self):
        """DSUB-15, JST EH 3 - what somebody has to plug into it."""
        name = self.footprint.split(":")[-1]
        if "DSUB-15" in name:
            gender = "male" if "_Male_" in name else "female"
            return f"DSUB-15 {gender}"
        if "B3B-EH" in name:
            return "JST EH 3"
        if "B2B-EH" in name:
            return "JST EH 2"
        return name


@lru_cache(maxsize=None)
def read(folder):
    """Every connector on one board, in reference order."""
    board = BOARDS_BY_FOLDER[folder]
    tree = parse(board.path.read_text(encoding="utf-8", errors="ignore"))

    connectors = []
    for footprint in children(tree, "footprint"):
        pins = {}
        for pad in children(footprint, "pad"):
            nets = children(pad, "net")
            if not nets or len(nets[0]) < 3:
                continue
            pins[pad[1]] = nets[0][2]
        if not pins:
            continue
        connectors.append(
            Connector(
                ref=_property(footprint, "Reference", "?"),
                label=_property(footprint, "Value", ""),
                footprint=footprint[1] if len(footprint) > 1 else "",
                pins=pins,
            )
        )
    return sorted(connectors, key=lambda c: (len(c.ref), c.ref))


def nets(folder):
    """net name -> the terminals on it, for one board."""
    found = {}
    for connector in read(folder):
        for pin, net in connector.pins.items():
            found.setdefault(net, []).append(f"{connector.ref}.{pin}")
    return found


def _is_spare(net):
    """KiCad's own name for a pin nothing is joined to."""
    return net.startswith("unconnected-") or net.startswith("Net-(")


def outline(folder):
    """The board's size in mm, off Edge.Cuts."""
    board = BOARDS_BY_FOLDER[folder]
    tree = parse(board.path.read_text(encoding="utf-8", errors="ignore"))
    xs, ys = [], []
    for kind in ("gr_line", "gr_rect", "gr_arc", "gr_circle", "gr_poly"):
        for item in children(tree, kind):
            layer = children(item, "layer")
            if not layer or layer[0][1] != "Edge.Cuts":
                continue
            for key in ("start", "end", "mid", "center"):
                for point in children(item, key):
                    xs.append(float(point[1]))
                    ys.append(float(point[2]))
    if not xs:
        return None
    return round(max(xs) - min(xs), 1), round(max(ys) - min(ys), 1)


# --- the document ---------------------------------------------------------

_HEADER = """# The harness

**Generated. Do not edit.** Read out of the four KiCad projects under
`CAD/KiCad/` every time this page is opened, so it cannot show a pinout
the boards have moved on from.

Four small PCBs sit between the electronic box and the bodies. None of
them has an active component on it: they are connectors and copper, and
what they do is turn two shared DSUBs at the rack into one cable per
body, and then that cable into one JST per thing inside the body.

```
electronic box  A-J3 -+
                B-J4 -+-> center -+-> female static -> female base -> body
                                  +-> male 1 --------> male static -> body
                                  +-> male 2 --------> male static -> body

electronic box  J5 ---------------> female static -> female base -> body
                J1 ---------------> female static -> female base -> body
```

`as built` and `next pcb` both call this harness **fixed**, and describe
the board in the rack against it. This is the other end of every cable
they mention.
"""

_FINDINGS = """
---

## What these boards settle

**male2's 5 V arrives through `center`.** `next pcb` section 5 calls this
the one open item that could block the build - `B-J4` carries no power at
all and it is male2's only connector at the rack. It does not have to:
`center` takes the single `+5V` conductor arriving on `to electronic
box A` pin 9 and fans it out to three cables, one of which is male 2. So
male2 is supplied from the box after all, by way of this board, and the
conductor it shares is the one `next pcb` already names.

**`B-J4` really does carry no power**, which this confirms from the other
end: `to electronic box B` has no `+5V` and no `+12V` on any pin. It
carries the males' audio, their state LEDs, half their light sensors and
one spare, and nothing else.

**A male fills a DSUB-15 exactly.** `next pcb` section 8 says so as an
argument for a bigger connector; `male static` is the proof, with four
light sensors, two NeoPixel lines, a microphone, a speaker pair, a state
LED, the Dynamixel and both rails leaving **one** pin spare.

**A female has six spares and they are wired end to end.** Pins 1, 2, 3,
9, 10 and 11 run through `female static` untouched, which is what makes
them usable for anything the body ever needs.

**Every body's Dynamixel is tapped where it is used**, not carried to the
end: the bar's at `center`, a female's at her joint, the mirror's at her
base, a male's at his board. One data line reaches all of them, which is
what a Dynamixel bus is.
"""


def _pin_rows(connector):
    """Pins in order, shell last, with KiCad's unnamed nets read as
    spares - which is what they are."""
    def order(pin):
        try:
            return (0, int(pin))
        except ValueError:
            return (1, pin)

    rows = []
    for pin in sorted(set(connector.pins), key=order):
        net = connector.pins[pin]
        name = "shell" if pin == "0" else pin
        if _is_spare(net):
            rows.append((name, "*spare*"))
        else:
            rows.append((name, f"`{net.lstrip('/')}`"))
    return rows


def markdown():
    """The four boards, as the page shows them."""
    lines = [_HEADER]

    for board in BOARDS:
        size = outline(board.folder)
        connectors = read(board.folder)
        lines.append(f"\n---\n\n## {board.title}")
        lines.append(f"\n{board.what}\n")
        lines.append(f"- **Where:** {board.where}")
        if size:
            lines.append(f"- **Size:** {size[0]} x {size[1]} mm")
        lines.append(f"- **Connectors:** {len(connectors)}")
        lines.append(f"- **File:** `CAD/KiCad/{board.folder}/`")

        for connector in connectors:
            label = connector.label or connector.ref
            lines.append(f"\n### {connector.ref} - {label}")
            lines.append(f"\n{connector.kind}\n")
            lines.append("| Pin | Carries |")
            lines.append("|---|---|")
            for pin, net in _pin_rows(connector):
                lines.append(f"| {pin} | {net} |")

    lines.append(_FINDINGS)
    return "\n".join(lines) + "\n"
