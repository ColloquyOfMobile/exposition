# -*- coding: utf-8 -*-
# Source code/Python/colloquy/virtual_drivers/top_view.py

"""The simulated room, seen from above, to scale. Pure: a scene in, SVG out.

The simulator holds every number the piece is made of - where each body
points, what every pixel was told, what each sensor last served, who is
singing - and `simulation` lists them as text. Text cannot show the one
thing that matters most here: who is facing whom. This draws it.

**Where things are, and what they look like**, is TJ's Rhino model
(`room.py`, `room.json`): each female's shell with the mirror and the
sensor in front of it, each male's body box with the NeoPixel ring on
its front and the ring light on his top, the bar and its plate. Which
female is which, and which way round the room is drawn, is `room.place`.

**Which way things point**: a female at her origin faces the pivot, a
male at his faces out, so a pair at a meeting face each other. Her sight
line runs from her sensor the way she faces, yellow when her sensor last
read lit; a lit ring sends a beam the way he faces. Neither is drawn at
its true spread - the model has the sensor between two "barn doors", but
not where in its mount the sensor sits, and nothing says how wide the
ring's light goes - they show direction, not field of view.

**The mirror** tilts about a horizontal axis across her front (a
parallel linkage from the servo inside her; TJ's firmware calls its move
a vertical wiggle), so from above it is an edge when level and a strip
as deep as the tilt makes it otherwise.

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

from . import room as room_module

INK = "#202a2a"
PAPER = "#f5f5ee"
MUTED = "#566561"
FAINT = "#d8ddd4"
DARK = "#c9cfc7"
LIT = "#f2c230"
GLASS = "#8fa3b5"

W, H = 800, 500
CX, CY = 250, 255
SCALE = 0.1  # pixels per millimetre
LEGEND_X = 520

FEMALE_PIXELS = ("head", "bodyO", "bodyP", "feet")
MALE_PIXELS = ("ring", "up ring", "o drive level", "p drive level")
# What the legend calls each, short enough for a row.
SHORT = {"o drive level": "O level", "p drive level": "P level"}
FEMALES = room_module.FEMALES
MALES = room_module.MALES


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
    group = f'<g transform="rotate({_fmt(now)} {_fmt(cx)} {_fmt(cy)})">'
    if _fmt(now) != _fmt(then):
        group += (
            f'<animateTransform attributeName="transform" type="rotate" '
            f'from="{_fmt(now)} {_fmt(cx)} {_fmt(cy)}" '
            f'to="{_fmt(then)} {_fmt(cx)} {_fmt(cy)}" '
            f'dur="{_fmt(LIVE_INTERVAL)}s" fill="freeze"/>'
        )
    return group + inner + "</g>"


def _turn(angle, then=None):
    return {"angle": angle, "next": angle if then is None else then}


def _counter(part):
    """The opposite turn, so a label inside a turning group stays upright."""
    return {"angle": -part["angle"], "next": -part.get("next", part["angle"])}


def _combined(*parts):
    return {
        "angle": sum(p["angle"] for p in parts),
        "next": sum(p.get("next", p["angle"]) for p in parts),
    }


def _text(x, y, words, size=11, fill=INK, anchor="middle", weight="normal", halo=False):
    outline = (
        f' stroke="{PAPER}" stroke-width="3" paint-order="stroke"' if halo else ""
    )
    return (
        f'<text x="{_fmt(x)}" y="{_fmt(y)}" font-size="{size}" fill="{fill}" '
        f'text-anchor="{anchor}" font-weight="{weight}"{outline}>'
        f"{escape(str(words))}</text>"
    )


class _Local:
    """A body's own frame on the page: its axis at (ox, oy), millimetres
    in, the way it faces up the page (the turn is the caller's)."""

    def __init__(self, ox, oy):
        self.ox, self.oy = ox, oy

    def point(self, x, y):
        return self.ox + x * SCALE, self.oy - y * SCALE

    def points(self, outline):
        return " ".join(
            f"{_fmt(px)},{_fmt(py)}" for px, py in (self.point(x, y) for x, y in outline)
        )

    def wedge(self, forward, length, half_angle):
        """A cone from (0, forward) running `length` the way it faces."""
        spread = length * tan(radians(half_angle))
        return self.points(
            [(0, forward), (-spread, forward + length), (spread, forward + length)]
        )


def _quarters(cx, cy, r, colours):
    """Four pixel groups as quarters of a disk, head to feet clockwise."""
    drawn = ""
    for index, colour in enumerate(colours):
        start, end = radians(index * 90), radians((index + 1) * 90)
        x1, y1 = cx + r * sin(start), cy - r * cos(start)
        x2, y2 = cx + r * sin(end), cy - r * cos(end)
        drawn += (
            f'<path d="M{_fmt(cx)} {_fmt(cy)} L{_fmt(x1)} {_fmt(y1)} '
            f'A{r} {r} 0 0 1 {_fmt(x2)} {_fmt(y2)} Z" fill="{colour or DARK}" '
            f'stroke="{PAPER}" stroke-width="1"/>'
        )
    return drawn


def _singing(cx, cy, size):
    return (
        f'<circle cx="{_fmt(cx)}" cy="{_fmt(cy)}" r="{size}" fill="none" '
        f'stroke="{INK}" stroke-width="1.5">'
        f'<animate attributeName="r" values="{size};{size + 20}" dur="1s" '
        f'repeatCount="indefinite"/>'
        f'<animate attributeName="opacity" values="0.8;0" dur="1s" '
        f'repeatCount="indefinite"/></circle>'
    )


def _reach(place):
    """How far a sight line or a beam is drawn: from her sensor to his
    ring when they meet."""
    female = place.females["female1"]
    male = place.males["male1"]
    return (
        place.radius("female1")
        - female["sensor"]["forward"]
        - place.radius("male1")
        - male["ring"]["forward"]
    )


def _female(name, body, mirror, place):
    """One female, at the top of the circle; the caller turns her into her
    place. Locally she faces the way her outline does - up - and is turned
    half a turn so that, at her origin, that is toward the pivot."""
    record = place.females[name]
    x, y = CX, CY - place.radius(name) * SCALE
    local = _Local(x, y)
    sensor = record["sensor"]["forward"]

    lit = body.get("sees light", False)
    drawn = (
        f'<polygon points="{local.wedge(sensor, _reach(place), 3)}" '
        f'fill="{LIT if lit else FAINT}" fill-opacity="{0.8 if lit else 0.6}"/>'
    )
    drawn += (
        f'<polygon points="{local.points(record["shell"])}" fill="{PAPER}" '
        f'stroke="{INK}" stroke-width="1.2"/>'
    )

    glass = record["mirror"]
    tilt = abs(sin(radians(mirror.get("angle", 0.0)))) * glass["height"] / 2
    depth = max(tilt, 4)  # an edge, when level: still a line on the page
    drawn += (
        f'<polygon points="'
        + local.points(
            [
                (glass["left"], glass["forward"] - depth),
                (glass["right"], glass["forward"] - depth),
                (glass["right"], glass["forward"] + depth),
                (glass["left"], glass["forward"] + depth),
            ]
        )
        + f'" fill="{GLASS}" stroke="{INK}" stroke-width="0.6"/>'
    )
    sx, sy = local.point(0, sensor)
    drawn += f'<circle cx="{_fmt(sx)}" cy="{_fmt(sy)}" r="2" fill="{LIT if lit else INK}"/>'

    colours = [pixel_colour(body["pixels"].get(p, {})) for p in FEMALE_PIXELS]
    drawn += _quarters(x, y, 10, colours)

    turned = _spin(
        _turn(180 + body["angle"], 180 + body.get("next", body["angle"])), x, y, drawn
    )
    if body.get("speaker"):
        turned += _singing(x, y, 46)
    return turned


def _male(name, body, place, frame):
    """One male, at the top of his circle; locally he faces up, out from
    the pivot. `frame` is every turn he is inside, for his upright label."""
    record = place.males[name]
    x, y = CX, CY - place.radius(name) * SCALE
    local = _Local(x, y)

    ring = pixel_colour(body["pixels"].get("ring", {}))
    up = pixel_colour(body["pixels"].get("up ring", {}))
    front = max(py for _, py in record["body"])
    half = record["ring"]["across"] / 2

    drawn = ""
    if ring:
        # Edged, because the commonest light here is white, on paper.
        drawn += (
            f'<polygon points="{local.wedge(front, _reach(place), 6)}" '
            f'fill="{ring}" fill-opacity="0.4" stroke="{MUTED}" '
            f'stroke-width="0.6" stroke-opacity="0.7"/>'
        )
    drawn += (
        f'<polygon points="{local.points(record["body"])}" fill="{PAPER}" '
        f'stroke="{INK}" stroke-width="1.2"/>'
    )
    (ax, ay), (bx, by) = local.point(-half, front), local.point(half, front)
    for colour, width in ((INK, 5), (ring or DARK, 3)):
        drawn += (
            f'<line x1="{_fmt(ax)}" y1="{_fmt(ay)}" x2="{_fmt(bx)}" y2="{_fmt(by)}" '
            f'stroke="{colour}" stroke-width="{width}" stroke-linecap="round"/>'
        )
    ux, uy = local.point(0, record["up ring"]["forward"])
    drawn += (
        f'<circle cx="{_fmt(ux)}" cy="{_fmt(uy)}" '
        f'r="{_fmt(record["up ring"]["across"] / 2 * SCALE)}" fill="none" '
        f'stroke="{up or MUTED}" stroke-width="{2 if up else 0.8}"/>'
    )

    lx, ly = local.point(0, -170)
    drawn += _spin(
        _counter(_combined(frame, body)),
        lx,
        ly,
        _text(lx, ly + 4, name[-1], size=11, weight="bold", halo=True),
    )

    turned = _spin(body, x, y, drawn)
    if body.get("speaker"):
        turned += _singing(x, y, 20)
    return turned


def _bar(place, inside):
    """The bar and its plate, male1's end up the page."""
    local = _Local(CX, CY)
    drawn = ""
    plate = place.bar.get("plate")
    if plate:
        drawn += (
            f'<polygon points="{local.points(plate)}" fill="{FAINT}" '
            f'stroke="{MUTED}" stroke-width="0.6"/>'
        )
    (ax, ay) = local.point(0, place.radius("male1"))
    (bx, by) = local.point(0, -place.radius("male2"))
    drawn += (
        f'<line x1="{_fmt(ax)}" y1="{_fmt(ay)}" x2="{_fmt(bx)}" y2="{_fmt(by)}" '
        f'stroke="{MUTED}" stroke-width="3" stroke-linecap="round"/>'
    )
    return drawn + inside


def _legend_row(y, name, body, pixel_names, notes):
    angle = body["angle"]
    goal = body.get("goal", angle)
    reading = f"{_fmt(angle)}°"
    if _fmt(goal) != _fmt(angle):
        reading += f" → {_fmt(goal)}°"
    row = _text(LEGEND_X, y, name, anchor="start", weight="bold")
    row += _text(LEGEND_X + 70, y, reading, anchor="start")
    x = LEGEND_X
    for pixel in pixel_names:
        colour = pixel_colour(body["pixels"].get(pixel, {}))
        row += (
            f'<rect x="{x}" y="{y + 6}" width="12" height="12" rx="2" '
            f'fill="{colour or DARK}" stroke="{MUTED}" stroke-width="0.5"/>'
        )
        label = SHORT.get(pixel, pixel)
        row += _text(x + 15, y + 16, label, size=9, fill=MUTED, anchor="start")
        x += 15 + 5 * len(label) + 8
    if body.get("sensor") is not None:
        notes = [f"sensor {body['sensor']}"] + notes
    if body.get("speaker"):
        notes.append("singing")
    if not body.get("torque", True):
        notes.append("torque off")
    if notes:
        row += _text(
            LEGEND_X, y + 32, ", ".join(notes), size=10, fill=MUTED, anchor="start"
        )
    return row


def draw(scene, place):
    """The whole picture, from a scene of plain values and a `room.place`:

    - `females`, `males`: name -> {angle, next, goal (degrees of the body
      from its origin), pixels (name -> rgbw), sensor, sees light (her),
      speaker, torque}
    - `mirrors`: female name -> {angle, torque} (degrees of tilt)
    - `bar`: {angle, next, goal}
    """
    mirrors = scene.get("mirrors", {})
    body = ""

    for name in FEMALES:
        female = scene["females"].get(name)
        if female is None:
            continue
        mirror = mirrors.get(name, {})
        body += _spin(
            _turn(place.at[name]), CX, CY, _female(name, female, mirror, place)
        )
        # Her name past the back of her shell, upright.
        a = radians(place.at[name])
        r = (place.radius(name) - min(y for _, y in place.females[name]["shell"]) + 60) * SCALE
        side = sin(a)
        anchor = "start" if side > 0.3 else "end" if side < -0.3 else "middle"
        body += _text(CX + r * side, CY - r * cos(a) + 4, name, size=11, anchor=anchor)

    bar = scene["bar"]
    turn = _turn(bar["angle"] - place.anchor, bar.get("next", bar["angle"]) - place.anchor)
    on_bar = ""
    for name in MALES:
        male = scene["males"].get(name)
        if male is None:
            continue
        where = _turn(place.offset[name])
        on_bar += _spin(where, CX, CY, _male(name, male, place, _combined(turn, where)))
    body += _spin(turn, CX, CY, _bar(place, on_bar))
    body += f'<circle cx="{CX}" cy="{CY}" r="4" fill="{INK}"/>'

    # The legend: every number the picture is drawn from.
    y = 30
    body += _text(LEGEND_X, y - 12, "bar", anchor="start", weight="bold")
    bar_reading = f"{_fmt(bar['angle'])}°"
    if _fmt(bar.get("goal", bar["angle"])) != _fmt(bar["angle"]):
        bar_reading += f" → {_fmt(bar['goal'])}°"
    body += _text(LEGEND_X + 70, y - 12, bar_reading, anchor="start")
    y += 16
    for name in FEMALES:
        if name in scene["females"]:
            mirror = mirrors.get(name, {})
            notes = []
            if mirror.get("torque") or _fmt(mirror.get("angle", 0.0)) != "0":
                notes.append(f"mirror {_fmt(mirror.get('angle', 0.0))}°")
            body += _legend_row(y, name, scene["females"][name], FEMALE_PIXELS, notes)
            y += 52
    for name in MALES:
        if name in scene["males"]:
            body += _legend_row(y, name, scene["males"][name], MALE_PIXELS, [])
            y += 52
    for offset, line in enumerate(
        (
            "angles: degrees of the body from its origin",
            "to scale, from TJ's Rhino model; the bar's",
            "positive turn is drawn clockwise",
        )
    ):
        body += _text(
            LEGEND_X, H - 40 + 13 * offset, line, size=9, fill=MUTED, anchor="start"
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
