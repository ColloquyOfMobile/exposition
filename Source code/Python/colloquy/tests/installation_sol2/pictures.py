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
    for i, name in enumerate(("+5V", "+12V", "MEGA 5V")):
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
    pins = ("+5V", "+12V", "MEGA 5V", "GND")
    xs = {name: 40 + i * 62 for i, name in enumerate(pins)}
    parts = [_text(W / 2, 22, "power test pins, everything unpowered", 12, weight="bold")]
    for name, x in xs.items():
        parts.append(f'<rect x="{x - 4}" y="104" width="8" height="22" fill="#c8a24a" stroke="{INK}"/>')
        parts.append(_text(x, 142, name, 10))
    pairs = (("+5V", "GND"), ("+12V", "GND"), ("MEGA 5V", "GND"), ("+12V", "+5V"), ("+5V", "MEGA 5V"))
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
    "power the bare backplane": lambda: centre_positive_jack() + leds({"+5V"}, False, "rack supply alone, no shield"),
    "servo supply through J7": lambda: jst_j7() + leds({"+12V"}, False, "servo supply alone: +5V must stay dark"),
    "refit the adapter": lambda: adapter(off=False) + spacers(),
    "power up the mounted rack": lambda: leds({"+5V", "MEGA 5V", "+12V"}, True, "mounted, all on, test teensy running"),
    "repair the broken cable": three_wire_cable,
    "plug in female1": lambda: plug_in("J5"),
    "plug in female2": lambda: plug_in("J1"),
    "plug in female3": lambda: plug_in("A-J3"),
    "mount and plug in male1": lambda: plug_in("A-J3 and B-J4"),
    "mount and plug in male2": lambda: plug_in("B-J4"),
    "mount the microphones": lambda: shunts() + mic_direct_pins(),
    "fit the voice cards": voice_card,
}


def picture(key):
    """The drawing for a step, or "" for a step with none. Never raises:
    it is drawn inside a render."""
    make = PICTURES.get(key)
    if make is None:
        return ""
    try:
        return make()
    except Exception:  # noqa: BLE001 - a picture must not stop the installation
        return ""
