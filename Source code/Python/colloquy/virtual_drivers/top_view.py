# -*- coding: utf-8 -*-
# Source code/Python/colloquy/virtual_drivers/top_view.py

"""The simulated room, seen from above. Pure: a scene in, SVG out.

The simulator holds every number the piece is made of - where each body
points, what every pixel was told, what each sensor last served, who is
singing - and `simulation` lists them as text. Text cannot show the one
thing that matters most here: who is facing whom. This draws it.

**Where things are** comes from the calibration, not from a drawing of
the rig. A female's place on the circle is where the bar must turn to
put male1 in front of her (`interaction_origins`), so the picture and
`Bar.set_male_in_front_of_female()` can never disagree. Male2 sits on
the bar at the mean of his own meeting points minus hers (about 180°:
the other end). Which way round the circle runs is a convention of this
drawing - 0° at the top, the bar's positive turn clockwise - and is not
a fact about the room; nor are the radii. The mirrors are not drawn:
nothing records where they hang.

**Which way things point**: a female at her origin faces the centre, a
male at his faces out, so a pair at a meeting point face each other.
Her sight is drawn as the window the simulator's sensor model allows
(`near origin threshold`), filled when her sensor last read lit.

**Motion between redraws.** The page redraws a node about once a second
(`ui/live.py`). Each moving part carries a SMIL rotation from where it
is now to where its servo will be one interval later - toward its goal,
at its configured speed - so a sweep glides rather than jumps, with no
script. A still scene draws identically every time, which is what lets
the live stream skip sending it.
"""
from html import escape
from math import cos, radians, sin, tan

from colloquy.ui.live import LIVE_INTERVAL

INK = "#202a2a"
PAPER = "#f5f5ee"
MUTED = "#566561"
FAINT = "#d8ddd4"
DARK = "#c9cfc7"
LIT = "#f2c230"

W, H = 680, 440
CX, CY = 215, 220
FEMALE_RADIUS = 175
MALE_RADIUS = 110
FEMALE_SIZE = 17
MALE_SIZE = 13
BEAM_LENGTH = 60

FEMALE_PIXELS = ("head", "bodyO", "bodyP", "feet")
MALE_PIXELS = ("ring", "up ring", "o drive level", "p drive level")
# What the legend calls each, short enough for a row.
SHORT = {"o drive level": "O level", "p drive level": "P level"}

# What the drawing needs, with the values it falls back to: params are
# hand-editable and a render must never raise.
_DEFAULT_ORIGINS = {
    "male1": {"female1": 0, "female2": 64.453, "female3": 125.977},
    "male2": {"female1": 181.641, "female2": 246.094, "female3": 304.688},
}
FEMALES = ("female1", "female2", "female3")
MALES = ("male1", "male2")


def _number(value, fallback):
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return number if number == number else fallback  # NaN


def layout(params):
    """Where each female sits and where each male sits on the bar, as
    world angles in degrees - read defensively from `params`."""
    try:
        origins = params["bar"]["interaction_origins"]
    except (KeyError, TypeError):
        origins = _DEFAULT_ORIGINS
    if not isinstance(origins, dict):
        origins = _DEFAULT_ORIGINS

    def origin(male, female):
        try:
            return _number(origins[male][female], _DEFAULT_ORIGINS[male][female])
        except (KeyError, TypeError):
            return _DEFAULT_ORIGINS[male][female]

    females = {female: origin("male1", female) for female in FEMALES}
    males = {"male1": 0.0}
    gaps = [females[f] - origin("male2", f) for f in FEMALES]
    males["male2"] = sum(gaps) / len(gaps)
    return females, males


def travel(now, goal, speed, seconds=LIVE_INTERVAL):
    """Where a part at `now` heading for `goal` at `speed` degrees per
    second will be `seconds` later: there, or as far as it gets."""
    step = abs(speed) * seconds
    if abs(goal - now) <= step:
        return goal
    return now + step if goal > now else now - step


def pixel_colour(pixel):
    """A NeoPixel's RGBW as a CSS colour; white adds to every channel.
    None for a pixel commanded dark (or never commanded)."""
    try:
        r, g, b, w = (int(pixel.get(k, 0)) for k in ("r", "g", "b", "w"))
    except (AttributeError, TypeError, ValueError):
        return None
    if not (r or g or b or w):
        return None
    r, g, b = (max(0, min(255, c + w)) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def _fmt(value):
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _spin(part, cx, cy, inner):
    """`inner` rotated about (cx, cy) by the part's angle now, moving to
    where it will be next if it is moving."""
    now, then = part["angle"], part.get("next", part["angle"])
    group = f'<g transform="rotate({_fmt(now)} {cx} {cy})">'
    if _fmt(now) != _fmt(then):
        group += (
            f'<animateTransform attributeName="transform" type="rotate" '
            f'from="{_fmt(now)} {cx} {cy}" to="{_fmt(then)} {cx} {cy}" '
            f'dur="{_fmt(LIVE_INTERVAL)}s" fill="freeze"/>'
        )
    return group + inner + "</g>"


def _counter(part):
    """The opposite turn, so a label inside a turning group stays upright."""
    return {"angle": -part["angle"], "next": -part.get("next", part["angle"])}


def _combined(*parts):
    return {
        "angle": sum(p["angle"] for p in parts),
        "next": sum(p.get("next", p["angle"]) for p in parts),
    }


def _text(x, y, words, size=11, fill=INK, anchor="middle", weight="normal"):
    return (
        f'<text x="{_fmt(x)}" y="{_fmt(y)}" font-size="{size}" fill="{fill}" '
        f'text-anchor="{anchor}" font-weight="{weight}">{escape(str(words))}</text>'
    )


def _wedge(cx, cy, length, half_angle, pointing_down):
    """A sight or beam cone from (cx, cy), straight up or down."""
    spread = length * tan(radians(min(abs(half_angle), 80)))
    tip_y = cy + length if pointing_down else cy - length
    return (
        f"M{cx} {cy} L{_fmt(cx - spread)} {_fmt(tip_y)} "
        f"L{_fmt(cx + spread)} {_fmt(tip_y)} Z"
    )


def _singing(cx, cy, size):
    return (
        f'<circle cx="{cx}" cy="{cy}" r="{size + 4}" fill="none" stroke="{INK}" '
        f'stroke-width="1.5">'
        f'<animate attributeName="r" values="{size + 4};{size + 22}" dur="1s" '
        f'repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values="0.8;0" dur="1s" '
        f'repeatCount="indefinite"/></circle>'
    )


def _female(name, body, threshold):
    """One female, drawn at the top of the circle: the caller turns her
    into her place. Locally she faces down, toward the centre."""
    x, y = CX, CY - FEMALE_RADIUS
    colours = [pixel_colour(body["pixels"].get(p, {})) for p in FEMALE_PIXELS]
    lit = body.get("sees light", False)
    sight = (
        f'<path d="{_wedge(x, y, MALE_RADIUS * 0.75, threshold, True)}" '
        f'fill="{LIT if lit else FAINT}" fill-opacity="{0.7 if lit else 0.5}"/>'
    )
    # Her four pixel groups as quarters of her disk, head to feet clockwise.
    quarters = ""
    for index, colour in enumerate(colours):
        start, end = index * 90, (index + 1) * 90
        quarters += _quarter(x, y, FEMALE_SIZE - 3, start, end, colour or DARK)
    turning = (
        sight
        + f'<circle cx="{x}" cy="{y}" r="{FEMALE_SIZE}" fill="{PAPER}" '
        f'stroke="{INK}" stroke-width="1.5"/>'
        + quarters
        + f'<path d="M{x - 5} {y + FEMALE_SIZE - 1} L{x} {y + FEMALE_SIZE + 6} '
        f'L{x + 5} {y + FEMALE_SIZE - 1} Z" fill="{INK}"/>'
    )
    drawn = _spin(body, x, y, turning)
    if body.get("speaker"):
        drawn += _singing(x, y, FEMALE_SIZE)
    return drawn


def _quarter(cx, cy, r, start, end, colour):
    def point(angle):
        a = radians(angle)
        return _fmt(cx + r * sin(a)), _fmt(cy - r * cos(a))

    (x1, y1), (x2, y2) = point(start), point(end)
    return (
        f'<path d="M{cx} {cy} L{x1} {y1} A{r} {r} 0 0 1 {x2} {y2} Z" '
        f'fill="{colour}" stroke="{PAPER}" stroke-width="1"/>'
    )


def _male(name, body, place):
    """One male, at the top of his circle; locally he faces up, out."""
    x, y = CX, CY - MALE_RADIUS
    ring = pixel_colour(body["pixels"].get("ring", {}))
    up = pixel_colour(body["pixels"].get("up ring", {}))
    beam = ""
    if ring:
        beam = (
            f'<path d="{_wedge(x, y, BEAM_LENGTH, 8, False)}" fill="{ring}" '
            f'fill-opacity="0.45"/>'
        )
    turning = (
        beam
        + f'<circle cx="{x}" cy="{y}" r="{MALE_SIZE}" fill="{up or PAPER}" '
        f'stroke="{ring or INK}" stroke-width="{5 if ring else 1.5}"/>'
        + f'<path d="M{x - 5} {y - MALE_SIZE + 1} L{x} {y - MALE_SIZE - 6} '
        f'L{x + 5} {y - MALE_SIZE + 1} Z" fill="{INK}"/>'
    )
    label = _spin(
        _counter(_combined(place, body)),
        x,
        y,
        _text(x, y + 4, name[-1], size=11, weight="bold"),
    )
    drawn = _spin(body, x, y, turning + label)
    if body.get("speaker"):
        drawn += _singing(x, y, MALE_SIZE)
    return drawn


def _legend_row(y, name, body, pixel_names):
    angle = body["angle"]
    goal = body.get("goal", angle)
    reading = f"{_fmt(angle)}°"
    if _fmt(goal) != _fmt(angle):
        reading += f" → {_fmt(goal)}°"
    row = _text(440, y, name, anchor="start", weight="bold")
    row += _text(510, y, reading, anchor="start")
    x = 440
    for pixel in pixel_names:
        colour = pixel_colour(body["pixels"].get(pixel, {}))
        row += (
            f'<rect x="{x}" y="{y + 6}" width="12" height="12" rx="2" '
            f'fill="{colour or DARK}" stroke="{MUTED}" stroke-width="0.5"/>'
        )
        label = SHORT.get(pixel, pixel)
        row += _text(x + 15, y + 16, label, size=9, fill=MUTED, anchor="start")
        x += 15 + 5 * len(label) + 8
    notes = []
    if body.get("sensor") is not None:
        notes.append(f"sensor {body['sensor']}")
    if body.get("speaker"):
        notes.append("singing")
    if not body.get("torque", True):
        notes.append("torque off")
    if notes:
        row += _text(440, y + 32, ", ".join(notes), size=10, fill=MUTED, anchor="start")
    return row


def draw(scene):
    """The whole picture, from a scene of plain values:

    - `females`, `males`: name -> {angle, next, goal (degrees of the body
      from its origin), pixels (name -> rgbw), sensor, sees light (her),
      speaker, torque}
    - `bar`: {angle, next, goal}
    - `params`: for the layout and the sight window
    """
    params = scene.get("params", {})
    female_at, male_at = layout(params)
    try:
        threshold = _number(params["near origin threshold"]["female"], 11.719)
    except (KeyError, TypeError):
        threshold = 11.719

    body = (
        f'<circle cx="{CX}" cy="{CY}" r="{FEMALE_RADIUS}" fill="none" '
        f'stroke="{FAINT}" stroke-dasharray="3 5"/>'
        f'<circle cx="{CX}" cy="{CY}" r="{MALE_RADIUS}" fill="none" '
        f'stroke="{FAINT}" stroke-dasharray="3 5"/>'
    )

    for name in FEMALES:
        female = scene["females"].get(name)
        if female is None:
            continue
        place = {"angle": female_at[name]}
        body += _spin(place, CX, CY, _female(name, female, threshold))
        # Her name outside the circle, upright.
        a = radians(female_at[name])
        r = FEMALE_RADIUS + FEMALE_SIZE + 10
        side = sin(a)
        anchor = "start" if side > 0.3 else "end" if side < -0.3 else "middle"
        body += _text(
            CX + r * side, CY - r * cos(a) + 4, name, size=11, anchor=anchor
        )

    bar = scene["bar"]
    on_bar = (
        f'<line x1="{CX}" y1="{CY - MALE_RADIUS}" x2="{CX}" y2="{CY}" '
        f'stroke="{MUTED}" stroke-width="3" stroke-linecap="round" '
        f'transform="rotate({_fmt(male_at["male1"])} {CX} {CY})"/>'
        f'<line x1="{CX}" y1="{CY - MALE_RADIUS}" x2="{CX}" y2="{CY}" '
        f'stroke="{MUTED}" stroke-width="3" stroke-linecap="round" '
        f'transform="rotate({_fmt(male_at["male2"])} {CX} {CY})"/>'
    )
    for name in MALES:
        male = scene["males"].get(name)
        if male is None:
            continue
        place = {"angle": male_at[name]}
        on_bar += _spin(place, CX, CY, _male(name, male, _combined(bar, place)))
    body += _spin(bar, CX, CY, on_bar)
    body += f'<circle cx="{CX}" cy="{CY}" r="5" fill="{INK}"/>'

    # The legend: every number the picture is drawn from.
    y = 30
    body += _text(440, y - 12, "bar", anchor="start", weight="bold")
    bar_reading = f"{_fmt(bar['angle'])}°"
    if _fmt(bar.get("goal", bar["angle"])) != _fmt(bar["angle"]):
        bar_reading += f" → {_fmt(bar['goal'])}°"
    body += _text(510, y - 12, bar_reading, anchor="start")
    y += 16
    for name in FEMALES:
        if name in scene["females"]:
            body += _legend_row(y, name, scene["females"][name], FEMALE_PIXELS)
            y += 52
    for name in MALES:
        if name in scene["males"]:
            body += _legend_row(y, name, scene["males"][name], MALE_PIXELS)
            y += 52
    body += _text(
        440,
        H - 12,
        "angles: degrees of the body from its origin",
        size=9,
        fill=MUTED,
        anchor="start",
    )

    title = "the simulated room, from above"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
        f'width="{W}" height="{H}" role="img" aria-label="{title}" '
        f'style="max-width:100%;height:auto;font-family:Arial,sans-serif">'
        f"<title>{title}</title>"
        f'<rect width="{W}" height="{H}" rx="8" fill="{PAPER}"/>'
        f"{body}</svg>"
    )
