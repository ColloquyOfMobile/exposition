# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/installation_sol2/pictures.py

"""A small drawing per step, where one helps: what to look at, where the
probes go, which way a board goes on. Pure: strings of SVG.

Drawn, not photographed, and schematic on purpose: each shows only what
its step's text says (the same pins, the same LEDs, the same numbers),
so a picture can never claim more than the documents behind the text.
Animations are SMIL inside the SVG - no script, as everywhere on this
page - and loop, so a picture opened late still shows the whole move.

Colours are the console's own (`console.css`: ink #202a2a, paper
#f5f5ee, muted #566561), plus an LED's green and yellow.
"""
import json
from functools import lru_cache
from pathlib import Path

INK = "#202a2a"
PAPER = "#f5f5ee"
MUTED = "#566561"
BOARD = "#2f6b4f"
GREEN = "#38c172"
YELLOW = "#f2c230"
DARK = "#c9cfc7"
RED = "#b8322a"

W, H = 360, 190


def _svg(body, title):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" role="img" aria-label="{title}" '
        f'style="max-width:100%;height:auto;font-family:Arial,sans-serif">'
        f"<title>{title}</title>"
        f'<rect width="{W}" height="{H}" rx="8" fill="{PAPER}"/>'
        f"{body}</svg>"
    )


def _text(x, y, words, size=11, fill=INK, anchor="middle", weight="normal"):
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" fill="{fill}" '
        f'text-anchor="{anchor}" font-weight="{weight}">{words}</text>'
    )


# --- the backplane's eight LEDs ------------------------------------------

def _led(x, y, colour, lit, label, blink=None):
    fill = colour if lit else DARK
    anim = ""
    if blink is not None:
        values, times, dur = blink
        anim = (
            f'<animate attributeName="fill" values="{values}" keyTimes="{times}" '
            f'dur="{dur}" calcMode="discrete" repeatCount="indefinite"/>'
        )
    glow = f'<circle cx="{x}" cy="{y}" r="11" fill="{colour}" opacity=".25"/>' if lit else ""
    return (
        f"{glow}<circle cx='{x}' cy='{y}' r='7' fill='{fill}' stroke='{INK}' "
        f"stroke-width='1'>{anim}</circle>{_text(x, y + 24, label, 9)}"
    )


def leds(power_lit, chase, caption):
    """The three green supply LEDs and the five yellow TONE LEDs, as on the
    backplane's front (`shields` 6a). `chase`: TONE 1-5 one at a time for
    1 s each, then all five for 2 s, as `teensy_check`'s `l` does."""
    parts = [
        f'<rect x="14" y="40" width="{W - 28}" height="80" rx="6" fill="{BOARD}" opacity=".12" stroke="{BOARD}"/>',
        _text(W / 2, 28, caption, 12, weight="bold"),
    ]
    for i, name in enumerate(("BOARD 5V", "12V", "MEGA 5V")):
        parts.append(_led(42 + i * 46, 72, GREEN, name in power_lit, name))
    for slot in range(5):
        x = 190 + slot * 34
        if chase:
            # 7 s cycle: slot n alone during second n, all five in 5-7 s.
            steps = [(0.0, DARK), (slot / 7, YELLOW), ((slot + 1) / 7, DARK), (5 / 7, YELLOW)]
            # Keep the last word at each instant and drop repeats, so the
            # times strictly increase (slot 1 starts lit, slot 5 runs
            # straight into all five).
            timeline = {}
            for at, colour in steps:
                timeline[round(at, 4)] = colour
            kept = []
            for at, colour in sorted(timeline.items()):
                if not kept or kept[-1][1] != colour:
                    kept.append((at, colour))
            values = ";".join(colour for _, colour in kept)
            times = ";".join(f"{at:.4f}" for at, _ in kept)
            parts.append(_led(x, 72, YELLOW, False, str(slot + 1), (values, times, "7s")))
        else:
            parts.append(_led(x, 72, YELLOW, False, str(slot + 1)))
    parts.append(_text(258, 112, "TONE", 9, MUTED))
    legend = (
        "TONE 1 to 5 one at a time, then all five" if chase else "every TONE dark"
    )
    parts.append(_text(W / 2, 150, legend, 11, MUTED))
    return _svg("".join(parts), caption)


# --- a meter ---------------------------------------------------------------

def _meter(x, y, reading):
    return (
        f'<rect x="{x}" y="{y}" width="92" height="58" rx="6" fill="#e6e3d3" stroke="{INK}"/>'
        f'<rect x="{x + 8}" y="{y + 8}" width="76" height="24" rx="3" fill="#cfd8c4" stroke="{MUTED}"/>'
        f"{_text(x + 46, y + 25, reading, 12, weight='bold')}"
        f'<circle cx="{x + 28}" cy="{y + 46}" r="4" fill="{RED}"/>'
        f'<circle cx="{x + 64}" cy="{y + 46}" r="4" fill="{INK}"/>'
    )


def probes_on_test_pins():
    """Red and black probes walking the five pairs the step lists."""
    pins = ("5V", "12V", "USB", "GND")
    xs = {name: 40 + i * 62 for i, name in enumerate(pins)}
    parts = [_text(W / 2, 22, "power row (USB = MEGA 5V), everything unpowered", 12, weight="bold")]
    for name, x in xs.items():
        parts.append(f'<rect x="{x - 4}" y="104" width="8" height="22" fill="#c8a24a" stroke="{INK}"/>')
        parts.append(_text(x, 142, name, 10))
    pairs = (("5V", "GND"), ("12V", "GND"), ("USB", "GND"), ("12V", "5V"), ("5V", "USB"))
    red = ";".join(str(xs[a]) for a, _ in pairs)
    black = ";".join(str(xs[b]) for _, b in pairs)
    for colour, values in ((RED, red), (INK, black)):
        parts.append(
            f'<g><line x1="0" y1="40" x2="0" y2="100" stroke="{colour}" stroke-width="4" stroke-linecap="round"/>'
            f'<polygon points="-3,100 3,100 0,106" fill="{colour}"/>'
            f'<animateTransform attributeName="transform" type="translate" values="'
            + ";".join(f"{v} 0" for v in values.split(";"))
            + '" dur="10s" calcMode="discrete" repeatCount="indefinite"/></g>'
        )
    parts.append(_meter(260, 40, "no short"))
    parts.append(_text(W / 2, 170, "beeps and stays near 0 ohm = short: stop", 11, RED))
    return _svg("".join(parts), "where the probes go")


def mic_direct_pins():
    parts = [_text(W / 2, 22, "MIC DIRECT 1-5, microphones plugged, powered", 12, weight="bold")]
    for i in range(5):
        x = 34 + i * 44
        parts.append(f'<rect x="{x - 4}" y="96" width="8" height="22" fill="#c8a24a" stroke="{INK}"/>')
        parts.append(_text(x, 134, f"DIRECT {i + 1}", 8))
    parts.append(f'<rect x="{34 + 5 * 44 - 4}" y="96" width="8" height="22" fill="#c8a24a" stroke="{INK}"/>')
    parts.append(_text(34 + 5 * 44, 134, "AGND", 9))
    parts.append(
        f'<g><line x1="0" y1="36" x2="0" y2="92" stroke="{RED}" stroke-width="4" stroke-linecap="round"/>'
        f'<animateTransform attributeName="transform" type="translate" '
        f'values="34 0;78 0;122 0;166 0;210 0" dur="10s" calcMode="discrete" repeatCount="indefinite"/></g>'
        f'<line x1="254" y1="36" x2="254" y2="92" stroke="{INK}" stroke-width="4" stroke-linecap="round"/>'
    )
    parts.append(_meter(262, 40, "~1.23 V"))
    parts.append(_text(W / 2, 162, "0 V: that microphone unplugged  &#183;  5 V: wired to the supply, all off", 10, MUTED))
    return _svg("".join(parts), "where to meter the microphones")


# --- connectors -------------------------------------------------------------

def centre_positive_jack():
    parts = [
        _text(W / 2, 24, "the rack supply into J2: 5 V, centre-positive", 12, weight="bold"),
        # The usual polarity symbol: - ( C ) - (o) - +
        _text(70, 98, "&#8722;", 28),
        f'<line x1="84" y1="90" x2="118" y2="90" stroke="{INK}" stroke-width="2"/>',
        f'<path d="M140 74 A20 20 0 1 0 140 106" fill="none" stroke="{INK}" stroke-width="3"/>',
        f'<circle cx="152" cy="90" r="6" fill="{INK}"/>',
        f'<line x1="158" y1="90" x2="196" y2="90" stroke="{INK}" stroke-width="2"/>',
        _text(212, 99, "+", 28),
        _text(150, 132, "sleeve &#8722;    centre +", 11, MUTED),
        _meter(250, 62, "4.75-5.25"),
        _text(W / 2, 168, "never a 12 V adapter here", 12, RED, weight="bold"),
    ]
    return _svg("".join(parts), "centre-positive jack")


def screw_terminal_j6():
    """J6's six holes as the front is seen, the power row on their left,
    and the two ways a two-way terminal goes in: RED on +5V, BLACK on GND."""
    from .steps import J6_ROWS

    parts = [_text(W / 2, 20, "J6 seen from the front: no marking on the board", 12, weight="bold")]
    # The power row's GND and USB pins, to the left, for orientation.
    parts.append(f'<rect x="22" y="44" width="8" height="18" fill="#c8a24a" stroke="{INK}"/>')
    parts.append(_text(26, 76, "GND", 9, MUTED))
    parts.append(_text(26, 88, "test pin", 8, MUTED))
    parts.append(f'<line x1="300" y1="30" x2="300" y2="160" stroke="{INK}" stroke-width="3"/>')
    parts.append(_text(306, 60, "board", 9, MUTED, anchor="start"))
    parts.append(_text(306, 72, "edge", 9, MUTED, anchor="start"))
    xs = (90, 150, 210)
    ys = (54, 124)
    for i, x in enumerate(xs, 1):
        parts.append(_text(x, 36, f"col {i}", 9, MUTED))
    # The two ways in, each with its two wires:
    # top row cols 2-3, bottom row cols 1-2.
    for x_red, x_black, y in ((xs[1], xs[2], ys[0]), (xs[0], xs[1], ys[1])):
        for x, colour, word in ((x_red, RED, "RED"), (x_black, INK, "BLACK")):
            parts.append(f'<line x1="{x}" y1="{y}" x2="{x}" y2="{y + 34}" stroke="{colour}" stroke-width="4" stroke-linecap="round"/>')
            parts.append(_text(x, y + 46, word, 10, colour, weight="bold"))
    for row, y in zip(J6_ROWS, ys):
        for net, x in zip(row, xs):
            colour = RED if net == "+5V" else INK
            parts.append(f'<circle cx="{x}" cy="{y}" r="8" fill="#c8a24a" stroke="{colour}" stroke-width="3"/>')
            parts.append(f'<circle cx="{x}" cy="{y}" r="3.5" fill="{PAPER}"/>')
            parts.append(_text(x + 12, y - 9, net, 9, colour, anchor="start", weight="bold"))
    parts.append(_text(W / 2, 186, "top row cols 2-3, or bottom row cols 1-2: RED nearer the test pins", 10, MUTED))
    return _svg("".join(parts), "where RED and BLACK go on J6")


def jst_j7():
    parts = [_text(W / 2, 24, "J7  SERVO BUS · 12 V  (JST EH 3)", 12, weight="bold")]
    parts.append(f'<rect x="60" y="56" width="150" height="54" rx="4" fill="#ffffff" stroke="{INK}" stroke-width="2"/>')
    for i, (pin, net) in enumerate((("1", "GND"), ("2", "+12V"), ("3", "dxl_data"))):
        x = 85 + i * 50
        parts.append(f'<rect x="{x - 6}" y="72" width="12" height="22" fill="#c8a24a" stroke="{INK}"/>')
        parts.append(_text(x, 66, pin, 10, MUTED))
        parts.append(_text(x, 128, net, 11, RED if net == "+12V" else INK, weight="bold"))
    parts.append(_meter(250, 50, "12 V"))
    parts.append(_text(296, 128, "between 2 and 1", 10, MUTED))
    parts.append(_text(W / 2, 160, "pin 3 must read nothing", 11, MUTED))
    return _svg("".join(parts), "J7 pins")


def three_wire_cable():
    """End to end, then each against the others."""
    parts = [_text(W / 2, 22, "microphone cable, both ends unplugged", 12, weight="bold")]
    wires = (("GND", INK), ("+5V", RED), ("OUT", "#2864a2"))
    for i, (name, colour) in enumerate(wires):
        y = 56 + i * 28
        parts.append(f'<line x1="70" y1="{y}" x2="290" y2="{y}" stroke="{colour}" stroke-width="5"/>')
        parts.append(_text(52, y + 4, name, 11, anchor="end"))
        parts.append(_text(308, y + 4, name, 11, anchor="start"))
    # First half of the cycle: end to end on each wire (beep). Second:
    # across pairs at one end (silence).
    parts.append(
        f'<g><circle cx="70" cy="0" r="5" fill="{RED}"/><circle cx="290" cy="0" r="5" fill="{INK}"/>'
        f'<animateTransform attributeName="transform" type="translate" values="0 56;0 84;0 112" '
        f'dur="9s" calcMode="discrete" repeatCount="indefinite"/></g>'
    )
    parts.append(_text(W / 2, 148, "each wire end to end: beeps", 11))
    parts.append(_text(W / 2, 166, "+5V against OUT, +5V against GND, OUT against GND: silence", 10, RED))
    return _svg("".join(parts), "testing the cable")


def shunts():
    parts = [_text(W / 2, 22, "microphone holder selectors, power off", 12, weight="bold")]
    for j, (name, on, says) in enumerate((("JP1", (2, 3), "40 dB"), ("JP2", (1, 2), "1:500"))):
        x0 = 60 + j * 160
        parts.append(_text(x0 + 30, 50, name, 12, weight="bold"))
        for p in range(3):
            x = x0 + p * 30
            parts.append(f'<rect x="{x - 5}" y="70" width="10" height="10" fill="#c8a24a" stroke="{INK}"/>')
            parts.append(_text(x, 98, str(p + 1), 10, MUTED))
        a = x0 + (on[0] - 1) * 30
        parts.append(f'<rect x="{a - 10}" y="62" width="50" height="26" rx="4" fill="{INK}" opacity=".85"/>')
        parts.append(_text(x0 + 30, 122, f"shunt on {on[0]}-{on[1]}: {says}", 11))
    parts.append(_text(W / 2, 152, "pad 1 = GND, pad 3 = VDD on both", 10, MUTED))
    return _svg("".join(parts), "shunt positions")


# --- boards moving ----------------------------------------------------------

def adapter(off):
    """Side view: the backplane, the adapter on its headers, the Teensy
    facing out, USB at the top edge. `off`: unplug USB, then lift."""
    lift = "0 0;0 0;0 -46;0 -46" if off else "0 -46;0 -46;0 0;0 0"
    usb = "0 0;50 0;50 0;50 0" if off else "50 0;50 0;50 0;0 0"
    title = "USB out first, then lift straight off" if off else "headers onto the backplane, Teensy facing out"
    parts = [
        _text(W / 2, 20, title, 12, weight="bold"),
        f'<rect x="30" y="150" width="300" height="10" fill="{BOARD}"/>',
        _text(180, 178, "backplane (DSUB face)", 10, MUTED),
        f'<g><animateTransform attributeName="transform" type="translate" values="{lift}" '
        f'keyTimes="0;.3;.7;1" dur="6s" repeatCount="indefinite"/>'
        f'<rect x="80" y="128" width="200" height="20" fill="#3c3c3c"/>'
        f'<rect x="70" y="118" width="220" height="10" fill="{BOARD}" opacity=".8"/>'
        f'<rect x="100" y="96" width="160" height="22" rx="2" fill="#2c4f8c"/>'
        f"{_text(180, 111, 'Teensy 4.1, facing out', 10, '#ffffff')}"
        f'<g><animateTransform attributeName="transform" type="translate" values="{usb}" '
        f'keyTimes="0;.3;.7;1" dur="6s" repeatCount="indefinite"/>'
        f'<rect x="262" y="100" width="34" height="14" fill="#9aa1a3" stroke="{INK}"/>'
        f'<line x1="296" y1="107" x2="340" y2="107" stroke="{INK}" stroke-width="4"/></g>'
        f"</g>",
        _text(180, 44, "USB at the top edge" if not off else "the USB lead is its only power", 10, MUTED),
    ]
    return _svg("".join(parts), title)


def spacers():
    parts = [
        _text(W / 2, 22, "computing-slot spacers HM1-HM4", 12, weight="bold"),
        f'<circle cx="100" cy="90" r="20" fill="#d9d9d9" stroke="{INK}" stroke-width="2"/>',
        f'<circle cx="100" cy="90" r="7" fill="{PAPER}" stroke="{INK}"/>',
        _text(100, 132, "round, &#8804; 4 mm OD", 11, BOARD, weight="bold"),
        f'<polygon points="240,64 263,77 263,103 240,116 217,103 217,77" fill="#d9d9d9" stroke="{INK}" stroke-width="2"/>',
        f'<circle cx="240" cy="90" r="7" fill="{PAPER}" stroke="{INK}"/>',
        f'<line x1="214" y1="64" x2="266" y2="116" stroke="{RED}" stroke-width="4"/>',
        _text(240, 132, "hex: hits the headers", 11, RED, weight="bold"),
        _text(W / 2, 162, "on the front; screw heads on the back", 11, MUTED),
    ]
    return _svg("".join(parts), "spacers")


def plug_in(connector):
    parts = [
        _text(W / 2, 22, f"power off, then plug into {connector}", 12, weight="bold"),
        f'<rect x="250" y="60" width="16" height="70" fill="{BOARD}"/>',
        _text(258, 150, "backplane", 10, MUTED),
        f'<path d="M232 68 L250 72 L250 118 L232 122 Z" fill="#9aa1a3" stroke="{INK}"/>',
        _text(240, 52, connector, 11, weight="bold"),
        f'<g><animateTransform attributeName="transform" type="translate" values="-70 0;0 0;0 0" '
        f'keyTimes="0;.5;1" dur="4s" repeatCount="indefinite"/>'
        f'<path d="M190 70 L230 74 L230 116 L190 120 Z" fill="#c9c9c9" stroke="{INK}"/>'
        f'<line x1="40" y1="95" x2="190" y2="95" stroke="{INK}" stroke-width="8"/></g>',
        f'<g transform="translate(40 136)"><circle r="11" fill="none" stroke="{RED}" stroke-width="2.5"/>'
        f'<line x1="0" y1="-14" x2="0" y2="-2" stroke="{RED}" stroke-width="2.5"/></g>',
        _text(58, 140, "everything off", 10, RED, anchor="start"),
    ]
    return _svg("".join(parts), f"plugging into {connector}")


def voice_card():
    parts = [
        _text(W / 2, 22, "card N into JVN: the key stops it reversed", 12, weight="bold"),
        f'<rect x="60" y="140" width="240" height="10" fill="{BOARD}"/>',
    ]
    for i in range(3):
        for row in range(2):
            x = 150 + i * 20
            if (i, row) == (2, 1):
                parts.append(f'<rect x="{x - 3 + row * 6}" y="126" width="6" height="14" fill="none" stroke="{RED}" stroke-dasharray="2 2"/>')
                continue
            parts.append(f'<rect x="{x - 3 + row * 6}" y="126" width="6" height="14" fill="#c8a24a" stroke="{INK}"/>')
    parts.append(
        f'<g><animateTransform attributeName="transform" type="translate" values="0 -22;0 0;0 0" '
        f'keyTimes="0;.5;1" dur="4s" repeatCount="indefinite"/>'
        f'<rect x="120" y="66" width="120" height="58" rx="3" fill="{BOARD}" opacity=".85"/>'
        f"{_text(180, 90, 'voice card', 11, '#ffffff')}"
        f"{_text(180, 106, 'pitch / body', 9, '#ffffff')}</g>"
    )
    parts.append(_text(250, 175, "pin 6 removed = the key", 10, RED))
    return _svg("".join(parts), "fitting a voice card")


PICTURES = {
    "test teensy passes": lambda: leds({"MEGA 5V"}, True, "only the Teensy's USB in"),
    "unplug and take the adapter off": lambda: adapter(off=True),
    "meter the bare backplane unpowered": probes_on_test_pins,
    "power the bare backplane": lambda: centre_positive_jack() + leds({"BOARD 5V"}, False, "rack supply alone, no shield"),
    "solder the screw terminal at J6": screw_terminal_j6,
    "servo supply through J7": lambda: jst_j7() + leds({"12V"}, False, "servo supply alone: BOARD 5V must stay dark"),
    "refit the adapter": lambda: adapter(off=False) + spacers(),
    "power up the mounted rack": lambda: leds({"BOARD 5V", "MEGA 5V", "12V"}, True, "mounted, all on, test teensy running"),
    "repair the broken cable": three_wire_cable,
    "plug in female1": lambda: plug_in("J5"),
    "plug in female2": lambda: plug_in("J1"),
    "plug in female3": lambda: plug_in("A-J3"),
    "mount and plug in male1": lambda: plug_in("A-J3 and B-J4"),
    "mount and plug in male2": lambda: plug_in("B-J4"),
    "mount the microphones": lambda: shunts() + mic_direct_pins(),
    "fit the voice cards": voice_card,
}


# --- the real board ---------------------------------------------------------
#
# KiCad's own plot of the backplane's front (`export_backplane_front.py`),
# served as a static file, with rings drawn over it in board millimetres:
# an overview to find the place, then a close-up to find the pin. Every
# label is the silkscreen's, so what the page says is what the board says.

HARDWARE = Path(__file__).resolve().parents[2] / "server2" / "static" / "hardware"
PLOT_URL = "/static/hardware/backplane-front.svg"
PCB_GREEN = "#1d3b2f"
RING = "#ffd23f"


@lru_cache(maxsize=None)
def _plot():
    return json.loads((HARDWARE / "backplane-front.json").read_text(encoding="utf-8"))


def _box(ref):
    part = _plot()["parts"][ref]
    x0, y0, x1, y1 = part["box"]
    pad = 1.1 if part["pads"] == 1 else 1.6
    return x0 - pad, y0 - pad, x1 + pad, y1 + pad


def _board_svg(view, width, marks, avoid, label_size, title):
    """One view of the plot: `view` is (x0, y0, x1, y1) in board mm."""
    ox, oy = _plot()["offset mm"]
    sw, sh = _plot()["size mm"]
    x0, y0, x1, y1 = view
    height = round(width * (y1 - y0) / (x1 - x0))
    stroke = (x1 - x0) / width * 2.2
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0} {y0} {x1 - x0} {y1 - y0}" '
        f'width="{width}" height="{height}" role="img" aria-label="{title}" '
        f'style="max-width:100%;height:auto;font-family:Arial,sans-serif;margin:0 8px 8px 0">'
        f"<title>{title}</title>"
        f'<rect x="{x0}" y="{y0}" width="{x1 - x0}" height="{y1 - y0}" fill="{PCB_GREEN}"/>'
        f'<image href="{PLOT_URL}" x="{-ox}" y="{-oy}" width="{sw}" height="{sh}"/>'
    ]
    every = [(r, l, RING) for r, l in marks] + [(r, l, "#ff5a4f") for r, l in avoid]
    for index, (refs, label, colour) in enumerate(every):
        refs = (refs,) if isinstance(refs, str) else refs
        boxes = [_box(ref) for ref in refs]
        bx0 = min(b[0] for b in boxes)
        by0 = min(b[1] for b in boxes)
        bx1 = max(b[2] for b in boxes)
        by1 = max(b[3] for b in boxes)
        parts.append(
            f'<rect x="{bx0}" y="{by0}" width="{bx1 - bx0}" height="{by1 - by0}" '
            f'rx="{min(bx1 - bx0, by1 - by0) / 2}" fill="none" stroke="{colour}" stroke-width="{stroke}">'
            f'<animate attributeName="stroke-opacity" values="1;.35;1" dur="1.6s" repeatCount="indefinite"/></rect>'
        )
        if label_size:
            # Neighbours alternate above and below: test pins sit 2.54 mm
            # apart, closer than a label is wide.
            y = by0 - label_size * 0.4 if index % 2 == 0 else by1 + label_size * 1.1
            parts.append(
                f'<text x="{(bx0 + bx1) / 2}" y="{y}" font-size="{label_size}" '
                f'text-anchor="middle" fill="{colour}" stroke="{PCB_GREEN}" stroke-width="{label_size / 5}" '
                f'paint-order="stroke" font-weight="bold">{label}</text>'
            )
    parts.append("</svg>")
    return "".join(parts)


def board(title, marks, zooms=(), avoid=()):
    """The whole board with the marks ringed (and where each close-up is),
    then each close-up, labelled. `marks` and `avoid` are (refs, label);
    `zooms` are (x0, y0, x1, y1) in board mm."""
    ox, oy = _plot()["offset mm"]
    sw, sh = _plot()["size mm"]
    whole = (-ox, -oy, -ox + sw, -oy + sh)
    overview = _board_svg(whole, 170, marks, avoid, 0, f"{title}: where on the board")
    # The close-ups' outlines on the overview.
    frames = "".join(
        f'<rect x="{z[0]}" y="{z[1]}" width="{z[2] - z[0]}" height="{z[3] - z[1]}" '
        f'fill="none" stroke="#ffffff" stroke-width="0.8" stroke-dasharray="2 1.5"/>'
        for z in zooms
    )
    overview = overview.replace("</svg>", frames + "</svg>")
    close = "".join(
        _board_svg(z, 360, marks, avoid, min((z[2] - z[0]) / 22, 2.2), f"{title}: close-up")
        for z in zooms
    )
    return (
        f'<div style="display:flex;flex-wrap:wrap;align-items:flex-start">{overview}{close}</div>'
    )


POWER_ROW_MARKS = (("TP31", "5V"), ("TP33", "12V"), ("TPUSB", "USB = MEGA 5V"), ("TP34", "GND"))
POWER_LEDS = (("DP5", "BOARD 5V"), ("DP12", "12V"), ("DPUSB", "MEGA 5V"))
TONE_LEDS = tuple((f"DT{n}", f"TONE {n}") for n in range(1, 6))
NOT_HERE = (("TP32", "TP32: not this"), ("JP1", "JP1 = GND"))
POWER_CORNER = (198, 78, 230, 99)
MIC_ROW = (92, 314, 158, 328)
# Slot 1 only: the five slots are alike, and the row is too wide to read.
FIRST_SLOT = (74, 185, 100, 208)

BOARD_VIEWS = {
    "test teensy passes": lambda: board(
        "LEDs with only the Teensy's USB in", POWER_LEDS + TONE_LEDS, (POWER_CORNER,)
    ),
    "meter the bare backplane unpowered": lambda: board(
        "where to put the probes",
        POWER_ROW_MARKS,
        (POWER_CORNER, (122, 148, 150, 170)),
        NOT_HERE,
    ),
    "power the bare backplane": lambda: board(
        "J2, the power row and the pins that read 0 V",
        (("J2", "J2"),) + POWER_ROW_MARKS + POWER_LEDS
        + tuple((f"TPL{n}", f"L{n}") for n in range(1, 6))
        + tuple((f"TPD{n}", f"M{n}") for n in range(1, 6)),
        ((234, 52, 256, 78), POWER_CORNER, FIRST_SLOT, MIC_ROW),
    ),
    "servo supply through J7": lambda: board(
        "J7 and the 12V pin", (("J7", "J7 SERVO BUS"), ("TP33", "12V"), ("DP12", "12V LED")),
        ((56, 116, 80, 132), POWER_CORNER),
    ),
    "refit the adapter": lambda: board("the computing slot", (("A1", "computing slot"),)),
    "power up the mounted rack": lambda: board(
        "LEDs, all on", POWER_LEDS + TONE_LEDS, (POWER_CORNER, FIRST_SLOT)
    ),
    "plug in female1": lambda: board("female1's connector", (("J5", "J5"),)),
    "plug in female2": lambda: board("female2's connector", (("J1", "J1"),)),
    "plug in female3": lambda: board("female3's connector", (("A-J3", "A-J3"),)),
    "mount and plug in male1": lambda: board("male1's connectors", (("A-J3", "A-J3"), ("B-J4", "B-J4"))),
    "mount and plug in male2": lambda: board("male2's connector", (("B-J4", "B-J4"),)),
    "mount the microphones": lambda: board(
        "M1-M5 and AGND",
        tuple((f"TPD{n}", f"M{n}") for n in range(1, 6)) + (("TPEG", "AGND"),),
        (MIC_ROW,),
    ),
    "fit the voice cards": lambda: board(
        "JV1-JV5", tuple((f"JV{n}", f"JV{n}") for n in range(1, 6)), ((76, 200, 232, 230),)
    ),
}


J6_CORNER = (206, 84, 244, 115)


def j6_holes():
    """J6 and the power row on the real plot, every J6 hole labelled with
    its net from the copper: the silkscreen says nothing there."""
    drawn = board(
        "J6, the screw terminal's holes",
        (("J6", "J6 (no marking)"), ("TP31", "5V"), ("TP34", "GND")),
        (J6_CORNER,),
    )
    labels = []
    for x, y, net in _plot()["parts"]["J6"]["holes"]:
        colour = "#ff5a4f" if net == "+5V" else "#ffffff"
        labels.append(
            f'<circle cx="{x}" cy="{y}" r="1.6" fill="none" stroke="{colour}" stroke-width="0.45"/>'
            f'<text x="{x}" y="{y + 3.2}" font-size="1.2" text-anchor="middle" fill="{colour}" '
            f'stroke="{PCB_GREEN}" stroke-width="0.3" paint-order="stroke" font-weight="bold">'
            f'{net}</text>'
        )
    head, tail = drawn.rsplit("</svg>", 1)
    return head + "".join(labels) + "</svg>" + tail


BOARD_VIEWS["solder the screw terminal at J6"] = j6_holes


def picture(key):
    """The drawings for a step - the schematic one, then the real board -
    or "" for a step with none. Never raises: it is drawn inside a render,
    and a missing plot only costs its half."""
    drawn = []
    for table in (PICTURES, BOARD_VIEWS):
        make = table.get(key)
        if make is None:
            continue
        try:
            drawn.append(make())
        except Exception:  # noqa: BLE001 - a picture must not stop the installation
            pass
    return "".join(drawn)
