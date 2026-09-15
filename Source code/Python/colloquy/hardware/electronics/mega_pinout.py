# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/electronics/mega_pinout.py

"""The Mega, to scale, with what reaches each of its pins written beside it.

    py export_mega_pinout.py

Writes `mega-pinout.svg` under `server2/static/hardware/`, which `as built`
shows under section 2.

**Why a second drawing of a board that already has one.** The layout
drawing shows the copper and the silkscreen, and the silkscreen is the
problem: of the seven headers around the Mega only `J11` and `J12` have
their names printed on the board. `J3`, `J4`, `J8`, `J9` and `J10` are
hidden in the KiCad file, so a person standing at the rack looking for
where male1's microphone lands is looking at rows of unlabelled pins, and
the table in section 2 names them by designators nothing on the board
spells out. This draws the same pins in the same places - front of the
board, the Mega's USB socket at the top - and writes the signal beside
every one.

**Read out of the board file, not restated**, for `harness.py`'s reason.
Every position is a pad's own coordinate turned through its footprint's
rotation, every label is that pad's net, and which header names are
printed is read off each footprint's `Reference` property. Where a net
also reaches something off the drawing (a DSUB, an amplifier, the state
LED's resistor) that is named too, since "which cable" is usually the
next question.

**One thing is not in the board file**, and it is kept here as a constant
rather than guessed: the five tracks the dirty rework cut. The copper
still has them. `CUT_IN_THE_REWORK` is `DIRTY_REWORK.md` section 3's table,
and `pytest_tests` holds the two to each other.

**It imports nothing from the `colloquy` package on purpose.** Importing
the package runs `logger.py`, which wipes `local/logs` - and on a machine
where the server is running those are its logs. So the root script puts
this folder on the path and imports this module and `harness` by
themselves, and the fallback import below is what lets that work.
"""
import math
from pathlib import Path
from xml.sax.saxutils import escape

try:
    from . import harness
except ImportError:  # loaded by path from export_mega_pinout.py
    import harness

BOARD = harness.KICAD / "electronic box" / "electronic box.kicad_pcb"
FILE_NAME = "mega-pinout.svg"
# electronics -> hardware -> colloquy
STATIC = Path(__file__).resolve().parents[2] / "server2" / "static" / "hardware"

MEGA = "A1"
LEFT_HEADERS = ("J3", "J11", "J12")
RIGHT_HEADERS = ("J4", "J8", "J10")
BOTTOM_HEADERS = ("J9",)
HEADERS = LEFT_HEADERS + RIGHT_HEADERS + BOTTOM_HEADERS
# Each row two nets, the body on the odd pin and the Mega on the even.
BREAK_POINTS = ("J11", "J12")

# DIRTY_REWORK.md section 3: the shield-pad tracks cut on the installation.
# Not in the copper, which still has every one of them.
CUT_IN_THE_REWORK = ("D11", "D10", "D6", "D5", "D4")

# The part of the board drawn, in board millimetres, and at what scale.
X0, X1 = 126.0, 206.0
Y0, Y1 = 44.0, 164.0
SCALE = 7.0
LEFT = 330.0
TOP = 150.0
# Rough advance of one monospace character, per pixel of font size, used
# only to keep brackets and notes clear of the longest label.
CHAR = 0.6

INK = "#222"
MUTED = "#777"
KINDS = {
    # kind: (colour, legend)
    "microphone": ("#c2185b", "microphone"),
    "photosensor": ("#b26a00", "light sensor"),
    "audio": ("#1565c0", "tone out"),
    "neopixel": ("#2e7d32", "NeoPixels"),
    "power": ("#6d4c41", "power"),
    "free": ("#9e9e9e", "free"),
}
CUT_COLOUR = "#d32f2f"
MONO = "ui-monospace, 'Cascadia Mono', Consolas, monospace"
SANS = "system-ui, 'Segoe UI', sans-serif"

_POWER_NAMES = {
    "5V1": "Mega 5 V",
    "5V3": "Mega 5 V",
    "5V4": "Mega 5 V",
    "+3.3V": "3.3 V",
    "GND": "GND",
    "GND2": "GND",
    "GND3": "GND",
    "GND5": "GND",
    "GND6": "GND",
    "RST1": "RESET",
    "IOREF": "IOREF",
    "AREF": "AREF",
}


# --- reading ----------------------------------------------------------------


class Pad:
    def __init__(self, ref, number, x, y, net):
        self.ref = ref
        self.number = number
        self.x = x
        self.y = y
        self.net = net

    def __repr__(self):
        return f"Pad({self.ref} {self.number} {self.net})"


def net_name(raw):
    """KiCad's `/male1{slash}microphone{slash}1` as `male1/microphone/1`."""
    return raw.replace("{slash}", "/").lstrip("/")


def _place(at, local):
    """A footprint-local point on the board. KiCad's y points down and a
    positive angle turns anticlockwise as drawn."""
    x0, y0 = float(at[1]), float(at[2])
    angle = math.radians(float(at[3])) if len(at) > 3 else 0.0
    c, s = round(math.cos(angle), 9), round(math.sin(angle), 9)
    x, y = float(local[0]), float(local[1])
    return round(x0 + x * c + y * s, 3), round(y0 - x * s + y * c, 3)


def _name_is_printed(footprint):
    for item in harness.children(footprint, "property"):
        if len(item) > 1 and item[1] == "Reference":
            hidden = "hide" in item or any(
                isinstance(c, list) and c[:2] == ["hide", "yes"] for c in item
            )
            layer = harness.children(item, "layer")
            on_silk = bool(layer) and layer[0][1].endswith("SilkS")
            return on_silk and not hidden
    return False


class Board:
    """The pads, nets and outline this drawing needs, out of one file."""

    def __init__(self, path=BOARD):
        tree = harness.parse(Path(path).read_text(encoding="utf-8"))
        self.footprints = {}
        self.pads = {}  # ref -> [Pad]
        self.printed = {}  # ref -> bool
        self.mega_outline = []  # (x1, y1, x2, y2)
        self.mega_rects = []  # (x1, y1, x2, y2)
        self.mega_texts = []  # (text, x, y)
        for footprint in harness.children(tree, "footprint"):
            ref = harness._property(footprint, "Reference")
            at = harness.children(footprint, "at")[0]
            self.footprints[ref] = footprint
            self.printed[ref] = _name_is_printed(footprint)
            pads = []
            for pad in harness.children(footprint, "pad"):
                nets = harness.children(pad, "net")
                if not nets:
                    continue
                x, y = _place(at, harness.children(pad, "at")[0][1:3])
                pads.append(Pad(ref, pad[1], x, y, net_name(nets[0][-1])))
            self.pads[ref] = pads
            if ref == MEGA:
                self._read_mega_graphics(footprint, at)

        self.by_net = {}
        for pads in self.pads.values():
            for pad in pads:
                self.by_net.setdefault(pad.net, []).append(pad)

    def _read_mega_graphics(self, footprint, at):
        for line in harness.children(footprint, "fp_line"):
            layer = harness.children(line, "layer")[0][1]
            start = _place(at, harness.children(line, "start")[0][1:3])
            end = _place(at, harness.children(line, "end")[0][1:3])
            if layer in ("B.SilkS", "B.Fab"):
                self.mega_outline.append(start + end)
        for rect in harness.children(footprint, "fp_rect"):
            start = _place(at, harness.children(rect, "start")[0][1:3])
            end = _place(at, harness.children(rect, "end")[0][1:3])
            self.mega_rects.append(
                (
                    min(start[0], end[0]),
                    min(start[1], end[1]),
                    max(start[0], end[0]),
                    max(start[1], end[1]),
                )
            )
        for text in harness.children(footprint, "fp_text"):
            layer = harness.children(text, "layer")[0][1]
            if layer == "B.Fab" and text[1] == "user":
                x, y = _place(at, harness.children(text, "at")[0][1:3])
                self.mega_texts.append((text[2], x, y))

    def pad(self, ref, number):
        for pad in self.pads[ref]:
            if pad.number == number:
                return pad
        raise KeyError(f"{ref} {number}")

    def mega_pad_on(self, net):
        for pad in self.by_net.get(net, ()):
            if pad.ref == MEGA:
                return pad
        return None

    def elsewhere(self, net):
        """What else the net reaches, off this drawing. Ground and the
        rails reach everything, so they name nothing."""
        if kind(net) == "power" or net.startswith("+"):
            return []
        return [
            pad
            for pad in self.by_net.get(net, ())
            if pad.ref != MEGA and pad.ref not in HEADERS
        ]


def kind(net):
    if net.startswith("unconnected"):
        return None
    for name in ("microphone", "photosensor", "audio", "neopixel"):
        if name in net:
            return name
    if net in _POWER_NAMES or net.startswith("Net-(J3") or net.startswith("+"):
        return "power"
    return "free"


def pretty(net):
    if net.startswith("unconnected"):
        return "not connected"
    if net in _POWER_NAMES:
        return _POWER_NAMES[net]
    if net.startswith("Net-(J3"):
        return "VIN"
    return net


# --- drawing ----------------------------------------------------------------


def X(x):
    return LEFT + (x - X0) * SCALE


def Y(y):
    return TOP + (y - Y0) * SCALE


def _f(value):
    return f"{value:.1f}"


def _text(x, y, content, size=11, colour=INK, anchor="start", weight=400,
          family=MONO, extra=""):
    return (
        f'<text x="{_f(x)}" y="{_f(y)}" font-family="{family}" '
        f'font-size="{size}" font-weight="{weight}" fill="{colour}" '
        f'text-anchor="{anchor}"{extra}>{escape(content)}</text>'
    )


def _colour(net):
    found = kind(net)
    return KINDS[found][0] if found else "#bdbdbd"


def _off_board(board, net):
    others = board.elsewhere(net)
    if not others:
        return ""
    return "  → " + ", ".join(f"{p.ref} pin {p.number}" for p in others[:2])


def _pad_mark(pad, radius=3.2):
    colour = _colour(pad.net)
    if pad.number == "1" and pad.ref in HEADERS:
        return (
            f'<rect x="{_f(X(pad.x) - radius)}" y="{_f(Y(pad.y) - radius)}" '
            f'width="{_f(2 * radius)}" height="{_f(2 * radius)}" '
            f'fill="white" stroke="{colour}" stroke-width="1.6"/>'
        )
    return (
        f'<circle cx="{_f(X(pad.x))}" cy="{_f(Y(pad.y))}" r="{radius}" '
        f'fill="white" stroke="{colour}" stroke-width="1.6"/>'
    )


def _bracket(board, ref, pads, side, x):
    ys = [Y(p.y) for p in pads]
    top, bottom = min(ys) - 7, max(ys) + 7
    tick = 6 if side == "left" else -6
    parts = [
        f'<path d="M {_f(x + tick)} {_f(top)} H {_f(x)} V {_f(bottom)} '
        f'H {_f(x + tick)}" fill="none" stroke="{MUTED}" stroke-width="1.2"/>'
    ]
    anchor = "end" if side == "left" else "start"
    tx = x - 8 if side == "left" else x + 8
    middle = (top + bottom) / 2
    parts.append(_text(tx, middle, ref, size=14, weight=700, anchor=anchor,
                       family=SANS))
    parts.append(_text(tx, middle + 14, _printed(board, ref), size=9,
                       colour=MUTED, anchor=anchor, family=SANS))
    return parts


def _printed(board, ref):
    return "name printed" if board.printed.get(ref) else "no name printed"


def _cross(x, y):
    return (
        f'<path d="M {_f(x - 5)} {_f(y - 5)} L {_f(x + 5)} {_f(y + 5)} '
        f'M {_f(x - 5)} {_f(y + 5)} L {_f(x + 5)} {_f(y - 5)}" '
        f'stroke="{CUT_COLOUR}" stroke-width="2.2"/>'
    )


def _mega(board):
    parts = []
    for x1, y1, x2, y2 in board.mega_outline:
        parts.append(
            f'<line x1="{_f(X(x1))}" y1="{_f(Y(y1))}" x2="{_f(X(x2))}" '
            f'y2="{_f(Y(y2))}" stroke="#4a6b4a" stroke-width="1.4"/>'
        )
    for x1, y1, x2, y2 in board.mega_rects:
        parts.append(
            f'<rect x="{_f(X(x1))}" y="{_f(Y(y1))}" '
            f'width="{_f((x2 - x1) * SCALE)}" height="{_f((y2 - y1) * SCALE)}" '
            f'fill="none" stroke="#9bb59b" stroke-width="1"/>'
        )
    for content, x, y in board.mega_texts:
        parts.append(_text(X(x), Y(y) + 4, content, size=10, colour="#4a6b4a",
                           anchor="middle", family=SANS))
    # The name of the thing, in the empty middle of it.
    mega = board.pads[MEGA]
    cx = X((min(p.x for p in mega) + max(p.x for p in mega)) / 2)
    cy = Y((min(p.y for p in mega) + max(p.y for p in mega)) / 2) - 40
    parts.append(_text(cx, cy, "Arduino Mega 2560", size=15, weight=700,
                       colour="#4a6b4a", anchor="middle", family=SANS))
    parts.append(_text(cx, cy + 18, MEGA, size=11, colour="#4a6b4a",
                       anchor="middle", family=SANS))
    return parts


def _joins(board):
    """A header pin and the Mega pad on the same net, drawn as the track
    the copper makes of them. Ground joins everything and is left out."""
    parts = []
    for ref in HEADERS:
        for pad in board.pads[ref]:
            mega = board.mega_pad_on(pad.net)
            if mega is None or kind(pad.net) is None or pad.net.startswith("GND"):
                continue
            if math.dist((pad.x, pad.y), (mega.x, mega.y)) > 16:
                continue
            parts.append(
                f'<line x1="{_f(X(pad.x))}" y1="{_f(Y(pad.y))}" '
                f'x2="{_f(X(mega.x))}" y2="{_f(Y(mega.y))}" '
                f'stroke="{_colour(pad.net)}" stroke-width="1.6" opacity="0.7"/>'
            )
            if mega.number in CUT_IN_THE_REWORK:
                parts.append(_cross((X(pad.x) + X(mega.x)) / 2, Y(pad.y)))
    return parts


def _break_points(board):
    """J11 and J12: odd pin the body's wire, even pin the Mega's input,
    joined by nothing in the copper."""
    parts = []
    for ref in BREAK_POINTS:
        for pad in board.pads[ref]:
            if int(pad.number) % 2 == 0:
                continue
            even = board.pad(ref, str(int(pad.number) + 1))
            parts.append(
                f'<line x1="{_f(X(pad.x))}" y1="{_f(Y(pad.y))}" '
                f'x2="{_f(X(even.x))}" y2="{_f(Y(even.y))}" '
                f'stroke="{_colour(pad.net)}" stroke-width="1.6" '
                f'stroke-dasharray="2 2.5"/>'
            )
    return parts


def from_the_body(board, net):
    """`male1/microphone/1` as `male1 microphone ← A-J3 pin 13`."""
    *body, _end = net.split("/")
    label = " ".join(body)
    others = board.elsewhere(net)
    if others:
        label += " ← " + ", ".join(f"{p.ref} pin {p.number}" for p in others[:2])
    return label


def left_rows(board):
    """(pad, label) for every pin on the left that gets words, top down."""
    rows = []
    for ref in LEFT_HEADERS:
        for pad in board.pads[ref]:
            if ref in BREAK_POINTS:
                if int(pad.number) % 2 == 0:
                    continue
                rows.append((pad, from_the_body(board, pad.net)))
            else:
                rows.append((pad, pretty(pad.net)))
    return rows


def _left_labels(board):
    parts = []
    right = X(X0 + 4.2)
    rows = left_rows(board)
    longest = max(len(label) for _pad, label in rows)
    bracket = right - 24 - 11 * CHAR * longest - 14
    for ref in LEFT_HEADERS:
        parts += _bracket(board, ref, board.pads[ref], "left", bracket)
        if ref in BREAK_POINTS:
            for pad in board.pads[ref]:
                if int(pad.number) % 2 == 0:
                    parts.append(_text(X(pad.x) + 5, Y(pad.y) - 5, pad.number,
                                       size=8, colour=MUTED))
    for pad, label in rows:
        weight = 700 if kind(pad.net) == "microphone" else 400
        parts.append(_text(right - 24, Y(pad.y) + 4, label, weight=weight,
                           colour=_colour(pad.net), anchor="end"))
        parts.append(_text(right - 8, Y(pad.y) + 4, pad.number, size=10,
                           colour=MUTED, anchor="end"))
    return parts


def right_rows(board):
    """(pad, label, cut note) for every pin on the right, top down."""
    rows = []
    for ref in RIGHT_HEADERS:
        for pad in board.pads[ref]:
            mega = board.mega_pad_on(pad.net)
            label = pretty(pad.net) + _off_board(board, pad.net)
            cut = mega is not None and mega.number in CUT_IN_THE_REWORK
            note = f"   {mega.number} cut in the rework" if cut else ""
            rows.append((pad, label, note))
    return rows


def _right_labels(board):
    """The labels, and how far right they reach."""
    parts = []
    left = X(X1) + 2
    rows = right_rows(board)
    longest = max(len(label) + len(note) for _pad, label, note in rows)
    bracket = left + 10 + 11 * CHAR * longest + 20
    for ref in RIGHT_HEADERS:
        parts += _bracket(board, ref, board.pads[ref], "right", bracket)
    for pad, label, note in rows:
        parts.append(_text(left, Y(pad.y) + 4, pad.number, size=10,
                           colour=MUTED, anchor="end"))
        tail = (
            f'<tspan fill="{CUT_COLOUR}" font-weight="700">{escape(note)}</tspan>'
            if note
            else ""
        )
        parts.append(
            f'<text x="{_f(left + 10)}" y="{_f(Y(pad.y) + 4)}" '
            f'font-family="{MONO}" font-size="11" fill="{_colour(pad.net)}" '
            f'xml:space="preserve">{escape(label)}{tail}</text>'
        )
    return parts, bracket + 120


def _mega_pad_names(board):
    parts = []
    mega = board.pads[MEGA]
    left_column = min(p.x for p in mega)
    right_column = max(p.x for p in mega)
    # The double row along the bottom is named on J9 instead; there is no
    # room between its pads for a name.
    double_row = max(p.y for p in mega) - 3
    for pad in mega:
        if kind(pad.net) is None or pad.y > double_row:
            continue
        if abs(pad.x - left_column) < 0.1:
            parts.append(_text(X(pad.x) + 7, Y(pad.y) + 3.5, pad.number,
                               size=9, colour=_colour(pad.net)))
        elif abs(pad.x - right_column) < 0.1:
            parts.append(_text(X(pad.x) - 7, Y(pad.y) + 3.5, pad.number,
                               size=9, colour=_colour(pad.net), anchor="end"))
    return parts


def bottom_rows(board):
    """(pad, label) for J9, which runs along x in two rows - so two
    downward labels side by side per column, lower pin number first."""
    (ref,) = BOTTOM_HEADERS
    rows = []
    for pad in sorted(board.pads[ref], key=lambda p: (p.x, int(p.number))):
        mega = board.mega_pad_on(pad.net)
        name = pretty(pad.net)
        if mega is not None and kind(pad.net) != "power" and mega.number != name:
            name = f"{name} ({mega.number})"
        rows.append((pad, f"{pad.number}  {name}{_off_board(board, pad.net)}"))
    return rows


def _bottom_labels(board):
    """The labels, and how far down they reach."""
    parts = []
    (ref,) = BOTTOM_HEADERS
    pads = board.pads[ref]
    lowest = Y(max(p.y for p in pads))
    ty = lowest + 12
    rows = bottom_rows(board)
    seen = set()
    for pad, label in rows:
        # Turned a quarter clockwise, a line of text stands to the right
        # of its baseline, so the pair sit one either side of the pad.
        tx = X(pad.x) + (1 if pad.x in seen else -8.5)
        seen.add(pad.x)
        parts.append(_text(tx, ty, label, size=9, colour=_colour(pad.net),
                           extra=f' transform="rotate(90 {_f(tx)} {_f(ty)})"'))
    first = X(min(p.x for p in pads))
    parts.append(
        f'<path d="M {_f(first - 10)} {_f(lowest - 26)} V {_f(lowest + 4)} '
        f'H {_f(first - 16)}" fill="none" stroke="{MUTED}" stroke-width="1.2"/>'
    )
    parts.append(_text(first - 22, lowest - 8, ref, size=14, weight=700,
                       anchor="end", family=SANS))
    parts.append(_text(first - 22, lowest + 6, _printed(board, ref), size=9,
                       colour=MUTED, anchor="end", family=SANS))
    longest = max(len(label) for _pad, label in rows)
    return parts, ty + 9 * CHAR * longest


def _heading():
    parts = [
        _text(40, 44, "The Mega, and what reaches each of its pins", size=22,
              weight=700, family=SANS),
        _text(40, 70, "Electronic box, as built. Seen from the front of the "
              "board, the Mega's USB socket at the top, drawn to scale.",
              size=13, colour="#444", family=SANS),
        _text(40, 90, "Read out of electronic box.kicad_pcb by mega_pinout.py"
              " - regenerate with py export_mega_pinout.py.",
              size=12, colour=MUTED, family=SANS),
    ]
    x = 40
    for colour, legend in KINDS.values():
        parts.append(f'<circle cx="{x + 5}" cy="118" r="5" fill="white" '
                     f'stroke="{colour}" stroke-width="2"/>')
        parts.append(_text(x + 16, 122, legend, size=12, colour=colour,
                           family=SANS))
        x += 34 + 6.6 * len(legend)
    parts.append(_cross(x + 5, 118))
    parts.append(_text(x + 18, 122, "track cut in the dirty rework", size=12,
                       colour=CUT_COLOUR, family=SANS))
    x += 18 + 6.6 * 29 + 28
    parts.append(f'<line x1="{_f(x)}" y1="118" x2="{_f(x + 22)}" y2="118" '
                 f'stroke="{INK}" stroke-width="1.6" stroke-dasharray="3 3"/>')
    parts.append(_text(x + 30, 122, "not joined in the copper", size=12,
                       family=SANS))
    return parts


_NOTES = (
    "J11 and J12 are break points, not headers. Each row is two nets: the "
    "odd pin is the wire from the body, the even pin is the Mega's analog input,",
    "joined only by what is physically fitted across the row (dashed). After "
    "the dirty rework, J11 rows 1-10 go through the analyser array instead.",
    "The names on J4, J8 and J10 are the copper's. A crossed-out track was cut "
    "in the rework, and that pad now carries a tone or the analyser strobe.",
    "See dirty rework, sections 3 and 4.",
)


def svg(board=None):
    board = board or Board()
    body = []
    body += _mega(board)
    body += _joins(board)
    body += _break_points(board)
    for ref in HEADERS:
        body += [_pad_mark(pad) for pad in board.pads[ref]]
    body += [
        _pad_mark(pad, radius=2.6)
        for pad in board.pads[MEGA]
        if kind(pad.net) is not None
    ]
    body += _mega_pad_names(board)
    body += _left_labels(board)
    right, reach = _right_labels(board)
    body += right
    bottom, lowest = _bottom_labels(board)
    body += bottom
    notes_top = lowest + 40
    for index, line in enumerate(_NOTES):
        body.append(_text(40, notes_top + 20 * index, line, size=12,
                          colour="#444", family=SANS))
    width = int(max(reach, 1100))
    height = int(notes_top + 20 * len(_NOTES) + 20)
    return "\n".join(
        [
            f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
            f'role="img" aria-label="The Arduino Mega on the electronic box, to '
            f'scale, with the signal on every header pin around it written '
            f'beside the pin.">',
            f'<rect width="{width}" height="{height}" fill="white"/>',
            *_heading(),
            *body,
            "</svg>",
        ]
    ) + "\n"


def write(folder=STATIC):
    path = Path(folder) / FILE_NAME
    path.write_text(svg(), encoding="utf-8", newline="\n")
    return path
