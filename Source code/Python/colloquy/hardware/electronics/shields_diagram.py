# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/electronics/shields_diagram.py

"""The shields backplane, simplified: its slots, what each can hold, and
the two configurations `shields` builds.

    py export_shields_diagram.py

Writes `shields-configurations.svg` under `server2/static/hardware/`,
which `shields` shows under section 0 and `main pcb > configuration`
shows while the shields backplane is the board in the rack.

**Simplified, and to scale.** The front of the board as somebody at the
rack sees it - the Mega's USB end at the top, the DSUBs along the bottom
and the sides - with the copper, the passives and the test pins left out
and the slots, the shields and the parts every setup shares left in.
Three boards side by side: the slots on their own, step 1 (the Mega),
step 2 (the Teensy); and under them a key of what each slot can hold.

**Read out of the board files, not restated**, for `harness.py`'s reason.
Every slot, connector and hole is a footprint in `backplane.kicad_pcb`;
every shield's outline is its own project's Edge.Cuts, placed by its
connector onto the backplane's - which is checked rather than assumed:
`pytest_tests` holds each card's and the carrier's retention holes to the
backplane's, and the Teensy adapter's to the computing slot's. Which body
each DSUB and each analyser module serves is read off their nets.

**The slots, their choices and the two steps are `main pcb >
configuration`'s** (`configuration/table.py`), so the presses on the page
and this picture cannot name different things.

**It imports no package `__init__`.** Importing the `colloquy` package
runs `logger.py`, which wipes `local/logs` - on a machine where the
server is running, its logs. The three modules below are imported by
their full names, and `export_shields_diagram.py` loads each of them by
path under that name first, so nothing above them ever runs.
"""
import math
from pathlib import Path
from xml.sax.saxutils import escape

from colloquy.drivers.audio import BODIES
from colloquy.hardware.electronics.harness import KICAD, _property, children, parse
from colloquy.hardware.main_pcb.configuration.table import (
    ANALYSER_SLOT,
    COMPUTING_SLOT,
    EMPTY,
    MEGA,
    MSGEQ7_CARRIER,
    REVALUED_CARD,
    SHIELD_STEPS,
    TEENSY_ADAPTER,
    THOMAS_CARD,
    VOICE_SLOTS,
)

SHIELDS = KICAD / "shields"
BACKPLANE = SHIELDS / "backplane" / "backplane.kicad_pcb"
CARRIER = SHIELDS / "analyser-carrier" / "analyser-carrier.kicad_pcb"
ADAPTER = SHIELDS / "teensy-adapter" / "teensy-adapter.kicad_pcb"
CARD = SHIELDS / "voice-thomas" / "voice-thomas.kicad_pcb"

STATIC = Path(__file__).resolve().parents[2] / "server2" / "static" / "hardware"
FILE_NAME = "shields-configurations.svg"

# Which backplane footprint each slot is.
COMPUTING_FOOTPRINT = "A1"
ANALYSER_FOOTPRINT = "JA1"
VOICE_FOOTPRINTS = {slot.name: f"JV{n}" for n, slot in enumerate(VOICE_SLOTS, start=1)}
U2D2_FOOTPRINT = "M1"
DSUBS = ("J1", "J5", "A-J3", "B-J4")
# A shield's connector is its pin 1, and so is the slot's header: the
# offset between the two is where the shield sits.
CARD_SOCKET = "JV1"
CARRIER_SOCKET = "JA1"
TEENSY_SOCKETS = ("JT1", "JT2")
# A Teensy's pins sit half a pitch in from its edges, all round.
HALF_PITCH = 1.27

COURTYARD = ("F.CrtYd", "B.CrtYd")


# --- reading the boards ---------------------------------------------------


def net_name(raw):
    """KiCad's `/male1{slash}microphone` as `male1/microphone`."""
    return raw.replace("{slash}", "/").lstrip("/")


def _place(at, local):
    """A footprint-local point on the board. KiCad's y points down and a
    positive angle turns anticlockwise as drawn."""
    x0, y0 = float(at[1]), float(at[2])
    angle = math.radians(float(at[3])) if len(at) > 3 else 0.0
    c, s = round(math.cos(angle), 9), round(math.sin(angle), 9)
    x, y = float(local[0]), float(local[1])
    return round(x0 + x * c + y * s, 3), round(y0 - x * s + y * c, 3)


def _box(points, grow=0.0):
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    return (min(xs) - grow, min(ys) - grow, max(xs) + grow, max(ys) + grow)


def _shift(box, dx, dy):
    return (box[0] + dx, box[1] + dy, box[2] + dx, box[3] + dy)


def _at(footprint):
    at = children(footprint, "at")[0]
    return float(at[1]), float(at[2])


def _local_graphics(footprint, layers):
    points = []
    for kind in ("fp_line", "fp_rect", "fp_poly", "fp_circle", "fp_arc"):
        for item in children(footprint, kind):
            layer = children(item, "layer")
            if not layer or layer[0][1] not in layers:
                continue
            points += [p[1:3] for key in ("start", "end", "mid") for p in children(item, key)]
            for pts in children(item, "pts"):
                points += [p[1:3] for p in children(pts, "xy")]
    return [(float(x), float(y)) for x, y in points]


def _graphics(footprint, layers):
    """Every point of a footprint's drawing on these layers, on the board."""
    at = children(footprint, "at")[0]
    return [_place(at, point) for point in _local_graphics(footprint, layers)]


def _pads(footprint):
    at = children(footprint, "at")[0]
    return [_place(at, children(pad, "at")[0][1:3]) for pad in children(footprint, "pad")]


def _nets(footprint):
    return {
        net_name(net[0][-1])
        for pad in children(footprint, "pad")
        if (net := children(pad, "net"))
    }


def _bodies(footprint):
    """The bodies a footprint's nets name, in body order."""
    nets = _nets(footprint)
    return [body for body in BODIES if any(n.startswith(body + "/") for n in nets)]


def _footprints(tree):
    return {_property(fp, "Reference"): fp for fp in children(tree, "footprint")}


def _outline(tree):
    """Edge.Cuts as a box, and its corner radius (0 for square corners)."""
    points, radius = [], 0.0
    for kind in ("gr_line", "gr_rect", "gr_arc"):
        for item in children(tree, kind):
            layer = children(item, "layer")
            if not layer or layer[0][1] != "Edge.Cuts":
                continue
            ends = [(float(p[1]), float(p[2])) for key in ("start", "end") for p in children(item, key)]
            points += ends
            if kind == "gr_arc" and len(ends) == 2:
                radius = max(radius, abs(ends[0][0] - ends[1][0]))
    return _box(points), radius


def _read(path):
    return parse(Path(path).read_text(encoding="utf-8"))


class Geometry:
    """What the drawing needs, in backplane millimetres, out of four files."""

    def __init__(self):
        board = _read(BACKPLANE)
        self.outline, self.corner = _outline(board)
        fps = _footprints(board)
        self.backplane = fps

        mega = fps[COMPUTING_FOOTPRINT]
        self.computing = _box(_graphics(mega, ("F.SilkS",)))
        self.mega_pads = _pads(mega)
        self.mega_overhangs = _overhangs(mega)
        self.u2d2 = _box(_graphics(fps[U2D2_FOOTPRINT], ("F.SilkS",)))
        self.dsubs = {
            ref: (_box(_graphics(fps[ref], COURTYARD)), _bodies(fps[ref])) for ref in DSUBS
        }
        self.supply = _box(_graphics(fps["J2"], COURTYARD))
        self.screw_bridge = _box(_graphics(fps["J6"], COURTYARD))
        self.servo_bus = _box(_graphics(fps["J7"], COURTYARD))
        self.holes = {ref: _at(fp) for ref, fp in fps.items() if ref[:2] in ("HM", "HV", "HA")}
        self.leds = {ref: _at(fp) for ref, fp in fps.items() if ref[:2] in ("DT", "DP")}

        # The carrier: its own outline, moved so its socket meets JA1.
        carrier = _read(CARRIER)
        cfps = _footprints(carrier)
        dx, dy = _minus(_at(fps[ANALYSER_FOOTPRINT]), _at(cfps[CARRIER_SOCKET]))
        self.carrier = _shift(_outline(carrier)[0], dx, dy)
        self.modules = [
            (_shift(_box(_graphics(cfps[ref], ("F.Fab",))), dx, dy), _bodies(cfps[ref])[0])
            for ref in sorted(r for r in cfps if r.startswith("M"))
        ]
        self.carrier_holes = [
            _plus(_at(cfps[ref]), (dx, dy)) for ref in sorted(cfps) if ref.startswith("H")
        ]

        # A card, moved onto each voice slot the same way.
        card = _read(CARD)
        kfps = _footprints(card)
        card_box = _outline(card)[0]
        socket = _at(kfps[CARD_SOCKET])
        hole = _at(kfps["H1"])
        self.cards, self.card_holes = {}, {}
        for slot, ref in VOICE_FOOTPRINTS.items():
            dx, dy = _minus(_at(fps[ref]), socket)
            self.cards[slot] = _shift(card_box, dx, dy)
            self.card_holes[slot] = _plus(hole, (dx, dy))

        # The adapter is drawn in the backplane's own coordinates already.
        adapter = _read(ADAPTER)
        afps = _footprints(adapter)
        self.adapter = _outline(adapter)[0]
        self.adapter_holes = {ref: _at(fp) for ref, fp in afps.items() if ref.startswith("HM")}
        socket_pads = [p for ref in TEENSY_SOCKETS for p in _pads(afps[ref])]
        self.teensy = _box(socket_pads, grow=HALF_PITCH)
        self.teensy_pads = socket_pads


def _minus(a, b):
    return a[0] - b[0], a[1] - b[1]


def _plus(a, b):
    return a[0] + b[0], a[1] + b[1]


def _overhangs(footprint):
    """What sticks out past the Mega's own edge - its USB socket and its
    barrel jack - as boxes on the board, named by the Fab text nearest.

    The outline is 0..101.6 in the footprint; the two sockets are the Fab
    lines drawn at negative x, in two runs along the edge - split where the
    gap between them is widest, since a socket's own outline has gaps too.
    """
    at = children(footprint, "at")[0]
    outside = sorted(
        {(x, y) for x, y in _local_graphics(footprint, ("F.Fab",)) if x < -0.3},
        key=lambda point: point[1],
    )
    if len(outside) < 2:
        return []
    gaps = [outside[i + 1][1] - outside[i][1] for i in range(len(outside) - 1)]
    split = gaps.index(max(gaps)) + 1
    runs = [outside[:split], outside[split:]]

    labels = []
    for text in children(footprint, "fp_text"):
        layer = children(text, "layer")
        if layer and layer[0][1] == "F.Fab" and text[1] == "user":
            x, y = children(text, "at")[0][1:3]
            labels.append((text[2], float(y)))

    found = []
    for run in runs:
        local = (min(p[0] for p in run), min(p[1] for p in run), 0.0, max(p[1] for p in run))
        corners = [_place(at, (local[0], local[1])), _place(at, (local[2], local[3]))]
        middle = (local[1] + local[3]) / 2
        name = min(labels, key=lambda label: abs(label[1] - middle))[0] if labels else ""
        found.append((_box(corners), "USB" if "USB" in name else name.lower()))
    return found


# --- drawing --------------------------------------------------------------

SCALE = 1.5  # px to the millimetre
MARGIN = 28
GAP = 48
TOP = 146

SANS = "system-ui, 'Segoe UI', sans-serif"
MONO = "ui-monospace, 'Cascadia Mono', Consolas, monospace"
INK = "#1f2933"
MUTED = "#6b7280"
PAPER = "#ffffff"
BOARD = ("#e4efe0", "#2f5d3a")
FIXED = ("#d5d8dd", "#6b7280")
MEGA_COLOURS = ("#cdeaeb", "#00838a")
ADAPTER_COLOURS = ("#e7e0f1", "#6a4c93")
TEENSY_COLOURS = ("#cfe6cf", "#2e7d32")
CARRIER_COLOURS = ("#f7e8c9", "#a8741a")
MODULE_COLOURS = ("#d6e2f3", "#2f5f9e")
CARD_COLOURS = ("#fbdfcc", "#c2571a")
SLOT_DASH = "5 3"


def _f(value):
    return f"{value:.1f}".rstrip("0").rstrip(".")


def _rect(x, y, w, h, fill="none", stroke=INK, width=1.0, dash=None, rx=0.0):
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    if rx:
        extra += f' rx="{_f(rx)}"'
    return (
        f'<rect x="{_f(x)}" y="{_f(y)}" width="{_f(w)}" height="{_f(h)}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="{_f(width)}"{extra}/>'
    )


def _text(x, y, content, size=10, colour=INK, anchor="middle", weight=400,
          family=SANS, rotate=None, italic=False):
    extra = f' transform="rotate({rotate} {_f(x)} {_f(y)})"' if rotate else ""
    if italic:
        extra += ' font-style="italic"'
    return (
        f'<text x="{_f(x)}" y="{_f(y)}" font-family="{family}" font-size="{_f(size)}" '
        f'font-weight="{weight}" fill="{colour}" text-anchor="{anchor}"{extra}>'
        f"{escape(content)}</text>"
    )


def _circle(x, y, r, fill, stroke, width=0.8):
    return (
        f'<circle cx="{_f(x)}" cy="{_f(y)}" r="{_f(r)}" fill="{fill}" '
        f'stroke="{stroke}" stroke-width="{_f(width)}"/>'
    )


class View:
    """Board millimetres onto the picture: one box of the board, placed."""

    def __init__(self, left, top, origin, scale=SCALE):
        self.left, self.top = left, top
        self.x0, self.y0 = origin
        self.scale = scale

    def x(self, mm):
        return self.left + (mm - self.x0) * self.scale

    def y(self, mm):
        return self.top + (mm - self.y0) * self.scale

    def point(self, point):
        return self.x(point[0]), self.y(point[1])

    def rect(self, box, fill="none", stroke=INK, width=1.0, dash=None, rx=0.0):
        return _rect(
            self.x(box[0]), self.y(box[1]),
            (box[2] - box[0]) * self.scale, (box[3] - box[1]) * self.scale,
            fill, stroke, width, dash, rx * self.scale,
        )

    def centre(self, box):
        return self.x((box[0] + box[2]) / 2), self.y((box[1] + box[3]) / 2)


def _height(box):
    return box[3] - box[1]


# --- the shields, each drawn in its own box -------------------------------


def _mega(view, geo, labels=True):
    box = geo.computing
    out = [view.rect(overhang, FIXED[0], FIXED[1], 0.8) for overhang, _ in geo.mega_overhangs]
    out.append(view.rect(box, MEGA_COLOURS[0], MEGA_COLOURS[1], 1.4, rx=1.0))
    pad = 1.2 * view.scale
    out += [
        _rect(view.x(x) - pad / 2, view.y(y) - pad / 2, pad, pad, MEGA_COLOURS[1], "none", 0)
        for x, y in geo.mega_pads
    ]
    if labels:
        for overhang, name in geo.mega_overhangs:
            if name == "USB":
                cx, _ = view.centre(overhang)
                out.append(_text(cx, view.y(overhang[1]) - 3, "USB", 8, MUTED))
        cx, cy = view.centre(box)
        out.append(_text(cx, cy - 4, MEGA, 11, MEGA_COLOURS[1], weight=700))
        out.append(_text(cx, cy + 10, "firmware 4", 9, INK))
    return out


def _teensy_adapter(view, geo, labels=True):
    box = geo.adapter
    out = [view.rect(box, ADAPTER_COLOURS[0], ADAPTER_COLOURS[1], 1.4, rx=1.0)]
    out.append(view.rect(geo.teensy, TEENSY_COLOURS[0], TEENSY_COLOURS[1], 1.2, rx=0.8))
    pad = 1.1 * view.scale
    out += [
        _rect(view.x(x) - pad / 2, view.y(y) - pad / 2, pad, pad, TEENSY_COLOURS[1], "none", 0)
        for x, y in geo.teensy_pads
    ]
    if labels:
        cx, cy = view.centre(geo.teensy)
        out.append(_text(cx + 3.5, cy, "Teensy 4.1", 10, TEENSY_COLOURS[1], weight=700, rotate=-90))
        below = (box[0], geo.teensy[3], box[2], box[3])
        bx, by = view.centre(below)
        out.append(_text(bx, by - 2, "adapter", 10, ADAPTER_COLOURS[1], weight=700))
        out.append(_text(bx, by + 11, "firmware 5", 9, INK))
    return out


def _carrier(view, geo, labels=True):
    out = [view.rect(geo.carrier, CARRIER_COLOURS[0], CARRIER_COLOURS[1], 1.4, rx=1.0)]
    for box, body in geo.modules:
        out.append(view.rect(box, MODULE_COLOURS[0], MODULE_COLOURS[1], 1.0, rx=0.8))
        if labels:
            cx, cy = view.centre(box)
            out.append(_text(cx, cy - 1, "MSGEQ7", 7.5, MODULE_COLOURS[1], weight=700))
            out.append(_text(cx, cy + 10, body, 8, INK))
    if labels:
        right = max(box[2] for box, _ in geo.modules)
        top = min(box[1] for box, _ in geo.modules)
        out.append(
            _text(view.x(right), view.y(top) - 4, MSGEQ7_CARRIER, 9,
                  CARRIER_COLOURS[1], anchor="end", weight=700)
        )
    return out


def _card(view, box, slot, revalued=False, labels=True):
    out = [view.rect(box, CARD_COLOURS[0], CARD_COLOURS[1], 1.2, rx=0.8)]
    if revalued:
        out.append(view.rect(box, "url(#revalued)", "none", 0, rx=0.8))
    if labels:
        reference, body = slot.split(" ", 1)
        cx = view.centre(box)[0]
        top = view.y(box[1])
        out.append(_text(cx, top + 13, reference, 9, CARD_COLOURS[1], weight=700, family=MONO))
        out.append(_text(cx, top + 25, body, 8, INK))
        words = ("re-valued", "card") if revalued else ("Thomas", "card")
        out.append(_text(cx, top + 42, words[0], 8, INK))
        out.append(_text(cx, top + 52, words[1], 8, INK))
    return out


def _empty(view, box, title, note=None, labels=True):
    out = [view.rect(box, "none", MUTED, 1.0, dash=SLOT_DASH, rx=0.8)]
    if labels:
        cx, cy = view.centre(box)
        if title:
            out.append(_text(cx, cy - 4, title, 9, MUTED, weight=700))
        out.append(_text(cx, cy + 9, note or EMPTY, 8.5, MUTED, italic=True))
    return out


def _empty_card(view, box, slot, labels=True):
    out = [view.rect(box, "none", MUTED, 1.0, dash=SLOT_DASH, rx=0.8)]
    if labels:
        reference, body = slot.split(" ", 1)
        cx = view.centre(box)[0]
        top = view.y(box[1])
        out.append(_text(cx, top + 13, reference, 9, MUTED, weight=700, family=MONO))
        out.append(_text(cx, top + 25, body, 8, MUTED))
        out.append(_text(cx, top + 45, EMPTY, 8.5, MUTED, italic=True))
    return out


def _computing(view, geo, held, labels=True):
    if held == MEGA:
        return _mega(view, geo, labels)
    if held == TEENSY_ADAPTER:
        return _teensy_adapter(view, geo, labels)
    return _empty(view, geo.computing, "computing slot", labels=labels)


def _analyser(view, geo, held, labels=True):
    if held == MSGEQ7_CARRIER:
        return _carrier(view, geo, labels)
    return _empty(view, geo.carrier, "analyser slot JA1", labels=labels)


def _voice(view, geo, slot, held, labels=True):
    box = geo.cards[slot]
    if held in (THOMAS_CARD, REVALUED_CARD):
        return _card(view, box, slot, revalued=held == REVALUED_CARD, labels=labels)
    return _empty_card(view, box, slot, labels)


# --- the board ------------------------------------------------------------


def _fixed(view, geo):
    """What every setup shares: the board, its holes, its connectors."""
    out = [view.rect(geo.outline, BOARD[0], BOARD[1], 1.6, rx=geo.corner)]
    out += [view.rect(box, FIXED[0], FIXED[1], 0.8) for box in (geo.supply, geo.screw_bridge, geo.servo_bus)]

    cx, cy = view.centre(geo.u2d2)
    out.append(view.rect(geo.u2d2, FIXED[0], FIXED[1], 1.0, rx=1.0))
    out.append(_text(cx, cy - 2, "U2D2", 11, INK, weight=700))
    out.append(_text(cx, cy + 11, "every setup", 8.5, MUTED))

    sx = view.x(geo.servo_bus[2]) + 4
    sy = view.centre(geo.servo_bus)[1] + 3
    out.append(_text(sx, sy, "J7 servo bus", 8, MUTED, anchor="start"))
    py_ = view.centre(geo.supply)[1] + 3
    out.append(_text(view.x(geo.supply[0]) - 4, py_, "J2 5 V in", 8, MUTED, anchor="end"))

    for ref, (box, bodies) in geo.dsubs.items():
        out.append(view.rect(box, FIXED[0], FIXED[1], 1.0, rx=1.0))
        cx, cy = view.centre(box)
        upright = _height(box) > (box[2] - box[0])
        rotate = -90 if upright else None
        out.append(_text(cx - (0 if not upright else 3), cy - (6 if not upright else 0),
                         ref, 9, INK, weight=700, family=MONO, rotate=rotate))
        out.append(_text(cx + (0 if not upright else 9), cy + (6 if not upright else 0),
                         " ".join(bodies), 7.5, INK, rotate=rotate))

    for ref, (x, y) in sorted(geo.leds.items()):
        colour = "#f2c94c" if ref.startswith("DT") else "#6fcf97"
        out.append(_circle(view.x(x), view.y(y), 2.2, colour, "#4b5563", 0.6))
    for x, y in geo.holes.values():
        out.append(_circle(view.x(x), view.y(y), 1.6 * view.scale, PAPER, MUTED))
    return out


def _slots(view, geo):
    """The board with every slot empty and named."""
    out = []
    out += _empty(view, geo.computing, "computing slot", "the Mega footprint")
    out += _empty(view, geo.carrier, "analyser slot JA1", "takes the carrier")
    for slot in VOICE_SLOTS:
        box = geo.cards[slot.name]
        out += _empty_card(view, box, slot.name, labels=False)
        reference, body = slot.name.split(" ", 1)
        cx = view.centre(box)[0]
        top = view.y(box[1])
        out.append(_text(cx, top + 18, reference, 9, MUTED, weight=700, family=MONO))
        out.append(_text(cx, top + 30, body, 8, MUTED))

    # The LEDs, named once: the yellow row is each voice slot's TONE LED,
    # the green three the rails (`shields` section 6a).
    tones = sorted(xy for ref, xy in geo.leds.items() if ref.startswith("DT"))
    out.append(_text(view.x(tones[0][0]) - 7, view.y(tones[0][1]) + 3,
                     "TONE LEDs", 8, MUTED, anchor="end"))
    rails = sorted(xy for ref, xy in geo.leds.items() if ref.startswith("DP"))
    out.append(_text(view.x(rails[-1][0]) - 2, view.y(rails[0][1]) + 14,
                     "power LEDs", 8, MUTED, anchor="end"))
    return out


def _fitted(view, geo, fitted):
    out = []
    out += _computing(view, geo, fitted[COMPUTING_SLOT.name])
    out += _analyser(view, geo, fitted[ANALYSER_SLOT.name])
    for slot in VOICE_SLOTS:
        out += _voice(view, geo, slot.name, fitted[slot.name])
    return out


def _board_width(geo):
    return (geo.outline[2] - geo.outline[0]) * SCALE


def _board_height(geo):
    return _height(geo.outline) * SCALE


def _wrap(text, width):
    lines, line = [], ""
    for word in text.split():
        if line and len(line) + 1 + len(word) > width:
            lines.append(line)
            line = word
        else:
            line = f"{line} {word}".strip()
    if line:
        lines.append(line)
    return lines


def _column(left, title, caption):
    out = [_text(left, 88, title.upper(), 12, INK, anchor="start", weight=700)]
    for index, line in enumerate(_wrap(caption, 60)):
        out.append(_text(left, 106 + 13 * index, line, 10, MUTED, anchor="start"))
    return out


# --- the key --------------------------------------------------------------


def _key(geo, left, top, slot, swatches):
    """One slot's choices, each drawn small with its name under it."""
    out = [_text(left, top, slot, 11, INK, anchor="start", weight=700)]
    x = left
    for name, box, draw in swatches:
        scale = 0.55 if _height(box) > 60 else (0.5 if box[2] - box[0] > 100 else 1.0)
        view = View(x, top + 14, (box[0], box[1]), scale)
        out += draw(view)
        width = (box[2] - box[0]) * scale
        out.append(_text(x + width / 2, top + 14 + _height(box) * scale + 14, name, 9.5, INK))
        x += max(width, 70) + 26
    return out


def _keys(geo, columns, top):
    card = geo.cards[VOICE_SLOTS[0].name]
    voice = VOICE_SLOTS[0].name
    computing = [
        (choice.name, geo.computing,
         lambda view, held=choice.name: _computing(view, geo, held, labels=False))
        for choice in COMPUTING_SLOT.choices
    ]
    analyser = [
        (choice.name, geo.carrier,
         lambda view, held=choice.name: _analyser(view, geo, held, labels=False))
        for choice in ANALYSER_SLOT.choices
    ]
    voices = [
        (choice.name, card,
         lambda view, held=choice.name: _voice(view, geo, voice, held, labels=False))
        for choice in VOICE_SLOTS[0].choices
    ]
    first, last = VOICE_SLOTS[0].name.split()[0], VOICE_SLOTS[-1].name.split()[0]
    out = [_text(MARGIN, top, "WHAT EACH SLOT CAN HOLD", 12, INK, anchor="start", weight=700)]
    out += _key(geo, columns[0], top + 26, COMPUTING_SLOT.name, computing)
    out += _key(geo, columns[1], top + 26, f"{ANALYSER_SLOT.name} {ANALYSER_FOOTPRINT}", analyser)
    out += _key(geo, columns[2], top + 26, f"each voice slot, {first}-{last}", voices)
    return out


# --- the whole picture ----------------------------------------------------


def svg(geo=None):
    geo = geo or Geometry()
    width = _board_width(geo)
    columns = [MARGIN + index * (width + GAP) for index in range(3)]
    total_width = columns[-1] + width + MARGIN
    board_bottom = TOP + _board_height(geo)
    key_top = board_bottom + 44
    total_height = key_top + 26 + 14 + 0.55 * _height(geo.computing) + 34 + 34

    body = [
        _rect(0, 0, total_width, total_height, PAPER, "none", 0),
        _text(MARGIN, 34, "The shields backplane: its slots and the two configurations",
              17, INK, anchor="start", weight=700),
        _text(MARGIN, 54,
              "Front view, to scale. Read from CAD/KiCad/shields; the slots and their "
              "choices are main pcb > configuration's.",
              11, MUTED, anchor="start"),
    ]
    origin = (geo.outline[0], geo.outline[1])

    body += _column(columns[0], "the slots",
                    "Dashed: a slot, which takes a shield. Grey: the same in every setup.")
    view = View(columns[0], TOP, origin)
    body += _fixed(view, geo)
    body += _slots(view, geo)

    for column, step in zip(columns[1:], SHIELD_STEPS):
        body += _column(column, step.name, step.says)
        view = View(column, TOP, origin)
        body += _fixed(view, geo)
        body += _fitted(view, geo, step.fitted)

    body += _keys(geo, columns, key_top)
    body.append(
        _text(MARGIN, total_height - 14,
              "Change a shield only with the rack supply and the computing USB unplugged "
              "(shields, section 10), and record it under main pcb > configuration.",
              10, MUTED, anchor="start")
    )

    defs = (
        "<defs>"
        '<pattern id="revalued" patternUnits="userSpaceOnUse" width="6" height="6" '
        'patternTransform="rotate(45)">'
        f'<line x1="0" y1="0" x2="0" y2="6" stroke="{CARD_COLOURS[1]}" '
        'stroke-width="1.2" opacity="0.45"/></pattern>'
        "</defs>"
    )
    label = (
        "The shields backplane drawn three times to scale: with its slots empty and "
        "named; in step 1, with the Mega 2560, the MSGEQ7 carrier and five Thomas "
        "cards; and in step 2, with the Teensy 4.1 adapter, the analyser slot empty and "
        "five Thomas cards. Below, what each slot can hold."
    )
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {_f(total_width)} '
        f'{_f(total_height)}" width="{_f(total_width)}" height="{_f(total_height)}" '
        f'role="img" aria-label="{escape(label)}">\n'
        f"{defs}\n" + "\n".join(body) + "\n</svg>\n"
    )


def write(folder=STATIC):
    path = Path(folder) / FILE_NAME
    path.write_text(svg(), encoding="utf-8", newline="\n")
    return path
