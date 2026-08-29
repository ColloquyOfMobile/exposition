# -*- coding: utf-8 -*-
# Source code/Python/colloquy/ui/graph_view.py

"""A graph you can zoom and scroll with nothing but links.

The page already has an interactive chart, and it is JavaScript: uPlot,
scroll to zoom, drag to pan (`server2/static/uplot_chart.js`, and
`test graph zoom` for a dummy-data demo of it). This is the other way of
doing the same job - **no script at all**. Every control is an `href`,
one link is one action, and the server draws a fresh SVG for each.

**Why bother.** Two reasons, and the second is the one that matters.

- A page that works with scripting off, on a tablet in a rack, in a
  browser nobody chose, is a page that works.
- **The server keeps hold of the data.** A client-side chart is sent
  every point and decides for itself what to draw; here the *window* is
  known before anything is rendered, so the decimation happens against
  the data rather than against the picture. Ten thousand samples do not
  cross the wire so that a browser can throw nine thousand of them away.
  On a machine that is also driving servos over a serial bus, that is not
  nothing.

**What the reader can do**, each one link: more points, fewer points,
zoom either axis or both, scroll either way, and reset. The state is the
node's, not the URL's, which is what the tree's `call` convention already
gives - a command mutates, `update()` re-renders, and the picture that
comes back is the new one.

**The data is dummy and deterministic** - a slow sweep with pulses on it
and a little noise, from a fixed seed, shaped like the light-sensor logs
the real charts draw. It is generated once and held, so paging around it
is paging around one dataset rather than a new one each time.
"""
import math
from random import Random

from colloquy.base import Base
from colloquy.ui import leaves

# The picture, in user units. A viewBox rather than pixels so it scales
# with whatever box the page puts it in.
WIDTH = 720
HEIGHT = 340
LEFT = 54          # room for the y labels
BOTTOM = 28        # room for the x labels
TOP = 12
RIGHT = 12

PLOT_WIDTH = WIDTH - LEFT - RIGHT
PLOT_HEIGHT = HEIGHT - TOP - BOTTOM

# How much data there is behind the window, and how long it runs. Far
# more than any one view draws, which is the point: the server is
# choosing what to send.
SAMPLES = 12000
SPAN_SECONDS = 600.0

# What a view opens on. 400 points across 720 units is a little under two
# units a point - dense enough to read a shape, sparse enough that the
# markup stays small and every point is a real sample rather than a pixel
# nobody can see.
DEFAULT_POINTS = 400
POINT_CHOICES = (50, 100, 200, 400, 800, 1600, 3200)

# One press of a zoom link. 2x is coarse enough to get somewhere in a few
# presses and fine enough not to overshoot what you were looking at.
ZOOM_STEP = 2.0
MAX_ZOOM = 4096.0

# One press of a scroll link, as a fraction of the window. Not a whole
# window: an overlap is what lets the eye carry across the join.
SCROLL_FRACTION = 0.4


def dummy_series(samples=SAMPLES, span=SPAN_SECONDS, seed=7):
    """Something with structure at more than one scale.

    Zooming is only worth having if there is something to find, so this
    has a slow sweep to see when zoomed out, pulses to find in the middle,
    and noise that only resolves at the bottom. Deterministic: the same
    dataset every view, and the same one on both computers.
    """
    random = Random(seed)
    points = []
    for index in range(samples):
        seconds = span * index / (samples - 1)
        slow = 500 + 380 * math.sin(2 * math.pi * seconds / 240.0)
        ripple = 60 * math.sin(2 * math.pi * seconds / 11.0)
        pulse = 260 if (int(seconds) % 47) < 2 else 0
        noise = random.uniform(-18, 18)
        points.append((seconds, max(0.0, slow + ripple + pulse + noise)))
    return points


class GraphView(Base):
    """One series, drawn as SVG, moved about with links."""

    def __init__(self, owner, points=None, name="graph"):
        super().__init__(owner=owner)
        self._name = name
        self._points = points if points is not None else dummy_series()

        self._wanted = DEFAULT_POINTS
        self._x_zoom = 1.0
        self._y_zoom = 1.0
        self._x_centre = 0.5      # 0..1 across the whole span
        self._y_centre = 0.5      # 0..1 across the whole value range

        for key, command in self._commands().items():
            self[key] = command

    @property
    def name(self):
        return self._name

    # --- what the reader is looking at ------------------------------------

    @property
    def full_x(self):
        """The whole span, and never a zero-width one.

        A dataset of one point would otherwise divide by zero on the
        first tick drawn - which is what a graph handed a run that
        recorded a single sample is, and the sort of thing that happens
        to a real one before it happens to a demo.
        """
        low, high = self._points[0][0], self._points[-1][0]
        if high == low:
            high = low + 1.0
        return low, high

    @property
    def full_y(self):
        values = [value for _, value in self._points]
        low, high = min(values), max(values)
        if high == low:
            high = low + 1.0
        margin = (high - low) * 0.05
        return low - margin, high + margin

    def _window(self, low, high, zoom, centre):
        """The visible slice of an axis, clamped inside its full range."""
        span = (high - low) / zoom
        middle = low + (high - low) * centre
        start = middle - span / 2
        start = max(low, min(start, high - span))
        return start, start + span

    @property
    def x_window(self):
        return self._window(*self.full_x, self._x_zoom, self._x_centre)

    @property
    def y_window(self):
        return self._window(*self.full_y, self._y_zoom, self._y_centre)

    # --- the decimation, which is the whole point -------------------------

    def visible(self):
        """The points inside the window, before thinning."""
        start, end = self.x_window
        return [p for p in self._points if start <= p[0] <= end]

    def drawn(self):
        """At most `wanted` of them, evenly spaced.

        Every one is a real sample rather than an average: a mean would
        hide the pulses, which are the thing worth finding. Thinning
        instead of averaging is a choice, and it is the honest one for a
        view that says how many of how many it is showing.
        """
        inside = self.visible()
        if len(inside) <= self._wanted:
            return inside
        step = len(inside) / float(self._wanted)
        return [inside[int(index * step)] for index in range(self._wanted)]

    # --- one link, one action ---------------------------------------------

    def _commands(self):
        return {
            "more points": self.more_points,
            "fewer points": self.fewer_points,
            "zoom in x": self.zoom_in_x,
            "zoom out x": self.zoom_out_x,
            "zoom in y": self.zoom_in_y,
            "zoom out y": self.zoom_out_y,
            "zoom in": self.zoom_in,
            "zoom out": self.zoom_out,
            "scroll left": self.scroll_left,
            "scroll right": self.scroll_right,
            "reset": self.reset,
        }

    def more_points(self, request=None):
        bigger = [n for n in POINT_CHOICES if n > self._wanted]
        self._wanted = bigger[0] if bigger else POINT_CHOICES[-1]

    def fewer_points(self, request=None):
        smaller = [n for n in POINT_CHOICES if n < self._wanted]
        self._wanted = smaller[-1] if smaller else POINT_CHOICES[0]

    def zoom_in_x(self, request=None):
        self._x_zoom = min(self._x_zoom * ZOOM_STEP, MAX_ZOOM)

    def zoom_out_x(self, request=None):
        self._x_zoom = max(self._x_zoom / ZOOM_STEP, 1.0)

    def zoom_in_y(self, request=None):
        self._y_zoom = min(self._y_zoom * ZOOM_STEP, MAX_ZOOM)

    def zoom_out_y(self, request=None):
        self._y_zoom = max(self._y_zoom / ZOOM_STEP, 1.0)

    def zoom_in(self, request=None):
        self.zoom_in_x()
        self.zoom_in_y()

    def zoom_out(self, request=None):
        self.zoom_out_x()
        self.zoom_out_y()

    def _scroll(self, direction):
        # By a fraction of what is on screen, so the amount a press moves
        # you shrinks as you zoom in - which is what makes it usable at
        # every scale from one press to the next.
        self._x_centre = min(
            1.0, max(0.0, self._x_centre + direction * SCROLL_FRACTION / self._x_zoom)
        )

    def scroll_left(self, request=None):
        self._scroll(-1)

    def scroll_right(self, request=None):
        self._scroll(+1)

    def reset(self, request=None):
        self._wanted = DEFAULT_POINTS
        self._x_zoom = self._y_zoom = 1.0
        self._x_centre = self._y_centre = 0.5

    # --- drawing -----------------------------------------------------------

    def _place(self, seconds, value):
        x0, x1 = self.x_window
        y0, y1 = self.y_window
        x = LEFT + (seconds - x0) / (x1 - x0) * PLOT_WIDTH
        y = TOP + PLOT_HEIGHT - (value - y0) / (y1 - y0) * PLOT_HEIGHT
        return x, y

    @staticmethod
    def _ticks(low, high, count=5):
        return [low + (high - low) * i / count for i in range(count + 1)]

    def svg(self):
        """The whole picture, as markup, with no script anywhere in it."""
        x0, x1 = self.x_window
        y0, y1 = self.y_window
        drawn = self.drawn()

        parts = [
            f'<svg viewBox="0 0 {WIDTH} {HEIGHT}" width="100%" '
            f'role="img" aria-label="graph" '
            f'style="font-family: monospace; font-size: 10px;">',
            f'<rect x="{LEFT}" y="{TOP}" width="{PLOT_WIDTH}" '
            f'height="{PLOT_HEIGHT}" fill="none" stroke="currentColor" '
            f'stroke-opacity="0.35"/>',
        ]

        for value in self._ticks(y0, y1):
            _, y = self._place(x0, value)
            parts.append(
                f'<line x1="{LEFT}" y1="{y:.1f}" x2="{LEFT + PLOT_WIDTH}" '
                f'y2="{y:.1f}" stroke="currentColor" stroke-opacity="0.12"/>'
            )
            parts.append(
                f'<text x="{LEFT - 6}" y="{y + 3:.1f}" text-anchor="end" '
                f'fill="currentColor" fill-opacity="0.7">{value:.0f}</text>'
            )

        for seconds in self._ticks(x0, x1):
            x, _ = self._place(seconds, y0)
            parts.append(
                f'<line x1="{x:.1f}" y1="{TOP}" x2="{x:.1f}" '
                f'y2="{TOP + PLOT_HEIGHT}" stroke="currentColor" '
                f'stroke-opacity="0.12"/>'
            )
            parts.append(
                f'<text x="{x:.1f}" y="{HEIGHT - 10}" text-anchor="middle" '
                f'fill="currentColor" fill-opacity="0.7">{seconds:.1f}s</text>'
            )

        if len(drawn) >= 2:
            steps = " ".join(
                f"{x:.1f},{y:.1f}" for x, y in (self._place(s, v) for s, v in drawn)
            )
            parts.append(
                f'<polyline points="{steps}" fill="none" stroke="currentColor" '
                f'stroke-width="1.2" stroke-linejoin="round"/>'
            )
        else:
            parts.append(
                f'<text x="{LEFT + PLOT_WIDTH / 2}" y="{TOP + PLOT_HEIGHT / 2}" '
                f'text-anchor="middle" fill="currentColor">nothing in this '
                f'window</text>'
            )

        parts.append("</svg>")
        return "".join(parts)

    # --- the page ----------------------------------------------------------

    @property
    def snapshot_children(self):
        return dict(self._commands())

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        states.update(self._commands())

        leaf = leaves.into(states, path)
        x0, x1 = self.x_window
        y0, y1 = self.y_window
        inside = len(self.visible())
        shown = len(self.drawn())

        # The number this exists to keep hold of, said out loud.
        leaf(
            "points",
            f"drawing {shown} of {inside} in this window, out of "
            f"{len(self._points)} held - asked for {self._wanted}",
        )
        leaf("x", f"{x0:.1f}s to {x1:.1f}s  (zoom x{self._x_zoom:g})")
        leaf("y", f"{y0:.0f} to {y1:.0f}  (zoom x{self._y_zoom:g})")
        states["graph"] = leaves.svg(path, "graph", self.svg())
        return states
