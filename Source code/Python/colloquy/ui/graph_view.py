# -*- coding: utf-8 -*-
# Source code/Python/colloquy/ui/graph_view.py

"""A graph you page through with nothing but links.

Every control is an `href`, one link is one action, and the server draws
a fresh SVG for each. There is no script in the picture and none behind
it: this is the whole of the charting the page does, since uPlot was
retired on 2026-09-09.

**Why it is the server's job.** Two reasons, and the second is the one
that matters.

- A page that works with scripting off, on a tablet in a rack, in a
  browser nobody chose, is a page that works.
- **The server keeps hold of the data.** A client-side chart is sent
  every point and decides for itself what to draw; here the *window* is
  known before anything is rendered, so the decimation happens against
  the data rather than against the picture. Ten thousand samples do not
  cross the wire so that a browser can throw nine thousand of them away.
  On a machine that is also driving servos over a serial bus, that is not
  nothing.

**Two numbers, and they are different questions.** Confusing them is the
easiest thing to do here, so the page names them apart:

- **page size** - how many *samples* are in the window. This is the x
  axis: a smaller page is zoomed in, and `next page` walks along.
- **points** - how many of that page's samples are actually *drawn*.

Set the page at or below the points asked for and every sample in it is
drawn, one for one, with nothing thinned away - which is the way to look
closely at a pulse without asking a browser to hold, or a request to
carry, a hundred thousand points to do it. That is the whole reason the
page size is a control rather than a constant.

**Marks are moments worth coming back to**, drawn as a dashed rule across
the picture with its name at the top - `marks=` is `(seconds, label)`
pairs. They are how you find something in a run rather than paging past
it: `next mark` and `previous mark` step from the edge of this page to
the next one either way, and a `marks` child node carries one link per
mark that turns straight to its page. That listing is its own node
because a run can carry a great many, and the controls somebody presses
on every view must not be lost in the middle of a list of moments they
press once. A mark is a time and a page is a range of rows, so `_row_at`
bisects to turn one into the other - a linear search would read the run
to find a mark, which is the cost all of this exists to avoid. Only the
marks on the page are drawn; a label that would sit on top of the one
beside it is dropped and its line kept, since an unreadable name is worse
than none and the line is the half that says where it is.

**Nothing is copied, and only the page is materialised.** A series is any
sequence of `(x, y)` - a list, or `Columns`, which is a lazy view over two
columns that are already in memory somewhere else (a dataframe, say). The
view holds the sequence, never a copy of it, and each render asks it for
the few hundred indices it is going to draw. So the cost of a request is
the size of the *picture*, not the size of the run: a forty-minute log
and a ten-second one render in the same time.

**Nothing in the browser can move it.** The picture goes out as
`leaves.image` rather than `leaves.svg`, so it gets no `data-svg-zoom`
handle and `svg_zoom.js` binds no wheel, drag or double-click to it. That
is not only for the no-script claim: browser-side zoom would scale the
*picture* while the window stayed where it was, so the readings beside it
- which page this is, how much of it is drawn - would describe a window
the reader was no longer looking at, and the thinned samples would be
stretched instead of re-drawn. One of the two has to be in charge of the
view, and here it is the server.

**One line or several.** `points=` is one unlabelled line, drawn in
`currentColor` so it follows whatever theme the page is in. `series=` is
label-to-points, and those get colours off matplotlib's tab10 with a
legend along the top, because once there are three lines on a graph
"which is which" is the first thing to know. The colours are the ones the
matplotlib SVGs already use, so a female is the same colour in every
picture of her. **The points asked for are a density per line**, not a
budget split between them: three lines at four hundred points each is
three readable lines, where three at a hundred and thirty is none.

**Pages are index ranges, not time ranges**, and they are applied to
every line at once. Every line on one of these graphs comes off one clock
- three females sampled in the same loop - so row *n* means the same
moment on all of them, and paging by row keeps them in step. A line that
runs out early simply stops being drawn rather than taking the others off
the picture.

**This is the graph the app draws with.** `test_with_everything_moving`'s
`full measurement` - three females' light sensors over a several-minute
run - comes through here, over the dataframe the run already holds. It
hangs there as a child *node* rather than a leaf, because it has commands
on it and that is how the tree draws a thing you can act on.

**The dummy data is deterministic** - a slow sweep with pulses on it and
a little noise, from a fixed seed, shaped like the light-sensor logs the
real graphs draw. Generated once and held, so paging around it is paging
around one dataset rather than a new one each time.
"""
import math
from functools import partial
from html import escape
from random import Random

from colloquy.base import Base
from colloquy.ui import leaves

# The picture, in user units. A viewBox rather than pixels so it scales
# with whatever box the page puts it in.
WIDTH = 720
HEIGHT = 340
LEFT = 54          # room for the y labels
BOTTOM = 28        # room for the x labels
TOP = 18           # room for the legend, when there is more than one line
RIGHT = 12

PLOT_WIDTH = WIDTH - LEFT - RIGHT
PLOT_HEIGHT = HEIGHT - TOP - BOTTOM

# How much dummy data there is, and how long it runs. Far more than any
# one view draws, which is the point: the server is choosing what to send.
SAMPLES = 12000
SPAN_SECONDS = 600.0

# What a view opens on. 400 points across 720 units is a little under two
# units a point - dense enough to read a shape, sparse enough that the
# markup stays small and every point is a real sample rather than a pixel
# nobody can see.
DEFAULT_POINTS = 400
POINT_CHOICES = (50, 100, 200, 400, 800, 1600, 3200)

# Samples to a page. `None` is the whole run on one page and is what a
# view opens on, because the first thing anybody wants is the shape of
# the lot; the smaller sizes are for looking closely, and the ones at or
# under DEFAULT_POINTS are the sizes at which nothing is thinned at all.
PAGE_CHOICES = (100, 250, 500, 1000, 2500, 5000, 10000, 25000, None)
DEFAULT_PAGE = None

# One press of a y zoom link. 2x is coarse enough to get somewhere in a
# few presses and fine enough not to overshoot what you were looking at.
ZOOM_STEP = 2.0
MAX_ZOOM = 4096.0

# Two mark labels closer together than this on screen: the second is
# dropped and only its line drawn. A mark whose label is unreadable under
# the one beside it is worse than a mark with no label, and the line is
# the half that says where it is.
MARK_LABEL_GAP = 10

# Colours for a graph with more than one line. Matplotlib's tab10, which
# is what `test_light_sensor_values/utils.py` already draws its SVGs in,
# so female2 is the same orange whichever picture you are looking at.
# A single unlabelled line is drawn in `currentColor` instead and follows
# the page's own theme, which is what it did before there were several.
SERIES_COLOURS = (
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd", "#8c564b",
)


class Columns:
    """Two columns already in memory, seen as a sequence of (x, y) pairs.

    The point is the pair that is never built. A run's readings are a
    dataframe; turning them into a list of tuples to draw them would hold
    the whole log twice, and the graph only ever looks at a few hundred
    of the rows. So this indexes into what is already there, and `pandas`
    is nowhere in this module.

    `y_range` is here for the same reason: the y axis needs the whole
    column's extent, and a numpy array can say so without Python touching
    every value.
    """

    def __init__(self, xs, ys):
        self._xs = xs
        self._ys = ys

    def __len__(self):
        return min(len(self._xs), len(self._ys))

    def __getitem__(self, index):
        return self._xs[index], self._ys[index]

    def y_range(self):
        ys = self._ys
        if hasattr(ys, "min"):
            return float(ys.min()), float(ys.max())
        return float(min(ys)), float(max(ys))


def dummy_series(samples=SAMPLES, span=SPAN_SECONDS, seed=7):
    """Something with structure at more than one scale.

    Paging in is only worth having if there is something to find, so this
    has a slow sweep to see on one page, pulses to find a few pages in,
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


def dummy_marks(span=SPAN_SECONDS, every=47.0):
    """One mark on each of the dummy data's pulses.

    The pulses are what there is to find in it, so marking them gives the
    `go to` links something to actually arrive at - and they are every 47
    seconds, which is often enough to page between and rare enough that
    the labels are not a wall.
    """
    count = int(span // every) + 1
    return [(every * index, f"pulse {index + 1}") for index in range(count)]


class Marks(Base):
    """One link per mark: press it and the graph pages to it.

    Their own node rather than commands on the graph itself, because a
    run can carry a great many and the controls somebody presses on every
    view - the page size, the next page - must not be lost in the middle
    of a list of moments they press once. `next mark` and `previous mark`
    stay on the graph, since those are the ones you press repeatedly.
    """

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._graph = owner
        for key, command in self._entries().items():
            self[key] = command

    @property
    def name(self):
        return "marks"

    def _entries(self):
        entries = {}
        for index, (seconds, label) in enumerate(self._graph.marks):
            key = self._key(seconds, label)
            if key in entries:
                # Two marks at the same moment with the same name: one
                # key would hide the other, and the page would offer a
                # link that went to the wrong one.
                key = f"{key} ({index})"
            entries[key] = partial(self._graph.go_to_mark, index)
        return entries

    @staticmethod
    def _key(seconds, label):
        # The key is a path segment, and the tree splits a request on
        # "/": a label carrying one would route to a child that is not
        # there. The time goes in front because it is what tells two
        # marks of the same kind apart.
        return f"{seconds:.1f}s {str(label).replace('/', '-')}"

    @property
    def snapshot_children(self):
        return dict(self._entries())


class GraphView(Base):
    """One or more lines, drawn as SVG, paged through with links."""

    def __init__(self, owner, points=None, series=None, marks=None, name="graph"):
        super().__init__(owner=owner)
        self._name = name
        self._series = self._as_series(points, series)
        self._marks = sorted(marks or (), key=lambda mark: mark[0])
        self._full_y = None       # scanned once, on first draw

        self._wanted = DEFAULT_POINTS
        self._page_size = DEFAULT_PAGE
        self._page = 0
        self._y_zoom = 1.0
        self._y_centre = 0.5      # 0..1 across the whole value range

        for key, command in self._commands().items():
            self[key] = command

        # Only when there are any: a `marks` node listing nothing is a
        # link that opens an empty page, and the two commands beside it
        # would be controls that can never move.
        self._marks_node = Marks(owner=self) if self._marks else None
        if self._marks_node is not None:
            self[self._marks_node.name] = self._marks_node

    @staticmethod
    def _as_series(points, series):
        """One line or several, held as (label, sequence) pairs either way.

        The sequence is kept **as it was handed over** - not copied into a
        list - so a caller holding a dataframe can hand a `Columns` view
        of it and the log stays in one place. `points=` is the one-line
        case and stays *unlabelled*, which is what keeps it drawing in
        `currentColor` with no legend over it.
        """
        if series is not None:
            items = series.items() if hasattr(series, "items") else series
            return [(label, line) for label, line in items]
        return [(None, points if points is not None else dummy_series())]

    @property
    def name(self):
        return self._name

    @property
    def series(self):
        """Each line as (label, sequence). The label is None for the
        one-line case, which is what leaves it in `currentColor`."""
        return list(self._series)

    @property
    def marks(self):
        """Moments worth jumping to, as (seconds, label), in time order."""
        return list(self._marks)

    def marks_on_page(self):
        """The ones inside the window, which are the ones drawn."""
        low, high = self.x_window
        return [mark for mark in self._marks if low <= mark[0] <= high]

    @property
    def held(self):
        """Every sample behind the window, across every line."""
        return sum(len(points) for _, points in self._series)

    @property
    def length(self):
        """Rows, as the pages count them - the longest line's."""
        return max((len(points) for _, points in self._series), default=0)

    # --- which page ---------------------------------------------------------

    @property
    def page_size(self):
        """Samples to a page, or None for the whole run on one."""
        return self._page_size

    @property
    def page_count(self):
        if self._page_size is None:
            return 1
        return max(1, math.ceil(self.length / self._page_size))

    @property
    def page(self):
        """Clamped on read rather than on write: the count changes when
        the page size does, and a reader who was at the end should land
        at the new end rather than off it."""
        return max(0, min(self._page, self.page_count - 1))

    def page_range(self):
        """The half-open range of row indices this page covers."""
        if self._page_size is None:
            return 0, self.length
        start = self.page * self._page_size
        return start, min(start + self._page_size, self.length)

    # --- what the reader is looking at --------------------------------------

    @property
    def full_x(self):
        """The whole run's span, from the endpoints alone - never a scan.

        Not what is drawn (that is `x_window`, which is this page's), but
        what paging moves about inside.
        """
        edges = [
            (points[0][0], points[len(points) - 1][0])
            for _label, points in self._series
            if len(points)
        ]
        if not edges:
            return 0.0, 1.0
        low = min(first for first, _ in edges)
        high = max(last for _, last in edges)
        if high == low:
            high = low + 1.0
        return low, high

    @property
    def x_window(self):
        """The page's own span, taken from its first and last row.

        Never zero-width: a page holding one sample would otherwise divide
        by zero on the first tick drawn, and a run that recorded a single
        row is exactly the sort of thing that happens to a real graph
        before it happens to a demo.
        """
        start, stop = self.page_range()
        edges = []
        for _label, points in self._series:
            end = min(stop, len(points))
            if end > start:
                edges.append((points[start][0], points[end - 1][0]))
        if not edges:
            return 0.0, 1.0
        low = min(first for first, _ in edges)
        high = max(last for _, last in edges)
        if high == low:
            high = low + 1.0
        return low, high

    @property
    def full_y(self):
        """Every line's whole extent, scanned once and kept.

        The whole extent rather than this page's, so the picture means the
        same thing from page to page - a peak that fills the box on page
        three has to be a peak, not merely the largest thing near it.
        """
        if self._full_y is None:
            self._full_y = self._scan_y()
        low, high = self._full_y
        margin = (high - low) * 0.05
        return low - margin, high + margin

    def _scan_y(self):
        ranges = []
        for _label, points in self._series:
            if not len(points):
                continue
            if hasattr(points, "y_range"):
                ranges.append(points.y_range())
            else:
                values = [value for _, value in points]
                ranges.append((min(values), max(values)))
        if not ranges:
            return 0.0, 1.0
        low = min(bottom for bottom, _ in ranges)
        high = max(top for _, top in ranges)
        if high == low:
            high = low + 1.0
        return low, high

    @property
    def y_window(self):
        low, high = self.full_y
        span = (high - low) / self._y_zoom
        middle = low + (high - low) * self._y_centre
        start = max(low, min(middle - span / 2, high - span))
        return start, start + span

    # --- the decimation, which is the whole point ---------------------------

    def window_counts(self):
        """How many samples each line has on this page.

        Counted from the index range rather than by looking at them, so
        the number the page prints costs nothing to produce.
        """
        start, stop = self.page_range()
        return [
            max(0, min(stop, len(points)) - start) for _label, points in self._series
        ]

    @property
    def in_window(self):
        return sum(self.window_counts())

    def _indices(self, first, last):
        """At most `wanted` row numbers, evenly spaced.

        Every one is a real sample rather than an average: a mean would
        hide the pulses, which are the thing worth finding. Thinning
        instead of averaging is a choice, and it is the honest one for a
        view that says how many of how many it is showing.
        """
        count = last - first
        if count <= 0:
            return []
        if count <= self._wanted:
            return range(first, last)
        step = count / float(self._wanted)
        return [first + int(index * step) for index in range(self._wanted)]

    def drawn_series(self):
        """Each line's page, thinned - and the only rows anything reads.

        `wanted` is a density *per line*, not a budget split between them:
        three lines at four hundred points each is three readable lines,
        where three at a hundred and thirty is none.
        """
        start, stop = self.page_range()
        drawn = []
        for label, points in self._series:
            end = min(stop, len(points))
            drawn.append((label, [points[i] for i in self._indices(start, end)]))
        return drawn

    def drawn(self):
        return [p for _, points in self.drawn_series() for p in points]

    # --- one link, one action ------------------------------------------------

    def _commands(self):
        commands = {
            "more points": self.more_points,
            "fewer points": self.fewer_points,
            "smaller page": self.smaller_page,
            "bigger page": self.bigger_page,
            "first page": self.first_page,
            "previous page": self.previous_page,
            "next page": self.next_page,
            "last page": self.last_page,
        }
        if self._marks:
            # Beside the page turns, since walking between marks is the
            # other way of moving along x and gets pressed as often.
            commands["previous mark"] = self.previous_mark
            commands["next mark"] = self.next_mark
        commands["zoom in y"] = self.zoom_in_y
        commands["zoom out y"] = self.zoom_out_y
        commands["reset"] = self.reset
        return commands

    def more_points(self, request=None):
        bigger = [n for n in POINT_CHOICES if n > self._wanted]
        self._wanted = bigger[0] if bigger else POINT_CHOICES[-1]

    def fewer_points(self, request=None):
        smaller = [n for n in POINT_CHOICES if n < self._wanted]
        self._wanted = smaller[-1] if smaller else POINT_CHOICES[0]

    def page_choices(self):
        """The page sizes worth offering for this much data.

        A size at or above the whole run holds all of it, which is the
        view `None` already is under another name - so offering both puts
        presses of `smaller page` in the way that visibly do nothing. On
        a short run this can come down to `None` alone, and that is the
        honest answer: there is nothing to page.
        """
        smaller = tuple(n for n in PAGE_CHOICES if n is not None and n < self.length)
        return smaller + (None,)

    def _resize_page(self, step):
        """Change the page size and stay where you were looking.

        The first row on screen is the anchor, not the page *number*:
        halving the page size would otherwise leave "page 3" showing the
        first half of what page 3 used to be, and the reader somewhere
        they did not ask to go.
        """
        first_row, _stop = self.page_range()
        choices = self.page_choices()
        index = choices.index(self._page_size) if self._page_size in choices else len(choices) - 1
        index = max(0, min(index + step, len(choices) - 1))
        self._page_size = choices[index]
        self._page = 0 if self._page_size is None else first_row // self._page_size

    def smaller_page(self, request=None):
        self._resize_page(-1)

    def bigger_page(self, request=None):
        self._resize_page(+1)

    def _row_at(self, seconds):
        """The row nearest that moment, by bisection.

        A mark is a time and a page is a range of rows, so something has
        to turn one into the other. Bisection rather than a scan because
        the whole arrangement here is that nothing reads rows it is not
        going to draw - a linear search for a mark would read the run to
        find it, which is the cost the paging exists to avoid.
        """
        points = self._longest()
        low, high = 0, len(points)
        while low < high:
            middle = (low + high) // 2
            if points[middle][0] < seconds:
                low = middle + 1
            else:
                high = middle
        return max(0, min(low, len(points) - 1))

    def _longest(self):
        """The line the pages are counted against - see `length`."""
        if not self._series:
            return []
        return max((points for _label, points in self._series), key=len)

    def go_to(self, seconds, request=None):
        """Turn to the page holding that moment.

        Nothing to do when the whole run is on one page: it is already on
        screen. The page says so rather than leaving a link that quietly
        does nothing.
        """
        if self._page_size is None or not self.length:
            return
        row = self._row_at(seconds)
        self._page = max(0, min(row // self._page_size, self.page_count - 1))

    def go_to_mark(self, index, request=None):
        if 0 <= index < len(self._marks):
            self.go_to(self._marks[index][0])

    def next_mark(self, request=None):
        """The first mark past the right-hand edge of this page."""
        _start, end = self.x_window
        for index, (seconds, _label) in enumerate(self._marks):
            if seconds > end:
                self.go_to_mark(index)
                return

    def previous_mark(self, request=None):
        """The last mark before the left-hand edge of this page."""
        start, _end = self.x_window
        for index in reversed(range(len(self._marks))):
            if self._marks[index][0] < start:
                self.go_to_mark(index)
                return

    def first_page(self, request=None):
        self._page = 0

    def previous_page(self, request=None):
        self._page = max(0, self.page - 1)

    def next_page(self, request=None):
        self._page = min(self.page_count - 1, self.page + 1)

    def last_page(self, request=None):
        self._page = self.page_count - 1

    def zoom_in_y(self, request=None):
        self._y_zoom = min(self._y_zoom * ZOOM_STEP, MAX_ZOOM)

    def zoom_out_y(self, request=None):
        self._y_zoom = max(self._y_zoom / ZOOM_STEP, 1.0)

    def reset(self, request=None):
        self._wanted = DEFAULT_POINTS
        self._page_size = DEFAULT_PAGE
        self._page = 0
        self._y_zoom = 1.0
        self._y_centre = 0.5

    # --- drawing -------------------------------------------------------------

    @staticmethod
    def _placer(x_window, y_window):
        """A (seconds, value) -> (x, y) for one drawing of one picture.

        The windows are passed in rather than read per point, because
        `x_window` reads rows off the series to find the page's edges and
        a picture places four hundred points: asking it each time turned
        one render into a thousand reads of data that had not moved.
        """
        x0, x1 = x_window
        y0, y1 = y_window

        def place(seconds, value):
            return (
                LEFT + (seconds - x0) / (x1 - x0) * PLOT_WIDTH,
                TOP + PLOT_HEIGHT - (value - y0) / (y1 - y0) * PLOT_HEIGHT,
            )

        return place

    @staticmethod
    def _ticks(low, high, count=5):
        return [low + (high - low) * i / count for i in range(count + 1)]

    def _colour(self, index):
        """One line and no label is the page's own colour - a graph that
        follows the theme it is drawn in, which is what this was before
        it could hold several."""
        label, _ = self._series[index]
        if len(self._series) == 1 and label is None:
            return "currentColor"
        return SERIES_COLOURS[index % len(SERIES_COLOURS)]

    def _mark_lines(self, place, x_window, y_bottom):
        """A dashed rule at each mark on this page, labelled where there
        is room.

        `currentColor` at half opacity rather than a colour of its own:
        the coloured strokes are the lines, and a mark is a note about
        where you are, not another reading to compare them with.
        """
        low, high = x_window
        parts = []
        last_label_end = None
        for seconds, label in self._marks:
            if not low <= seconds <= high:
                continue
            x, _ = place(seconds, y_bottom)
            parts.append(
                f'<line x1="{x:.1f}" y1="{TOP}" x2="{x:.1f}" '
                f'y2="{TOP + PLOT_HEIGHT}" stroke="currentColor" '
                f'stroke-opacity="0.5" stroke-dasharray="4 3"/>'
            )
            text = escape(str(label))
            # 6 units a character is monospace at this font size.
            width = 6 * len(text)
            start = x - width / 2
            if last_label_end is not None and start < last_label_end + MARK_LABEL_GAP:
                continue
            last_label_end = x + width / 2
            parts.append(
                f'<text x="{x:.1f}" y="{TOP + 10}" text-anchor="middle" '
                f'fill="currentColor" fill-opacity="0.75">{text}</text>'
            )
        return parts

    def _legend(self):
        """Which line is which, along the top. Nothing at all when there
        is only the one, since naming it says no more than the node's own
        title already does."""
        labelled = [
            (index, label)
            for index, (label, _) in enumerate(self._series)
            if label is not None
        ]
        if not labelled:
            return []

        parts = []
        x = LEFT
        for index, label in labelled:
            colour = self._colour(index)
            parts.append(
                f'<line x1="{x:.1f}" y1="{TOP - 7}" x2="{x + 10:.1f}" '
                f'y2="{TOP - 7}" stroke="{colour}" stroke-width="2"/>'
            )
            parts.append(
                f'<text x="{x + 14:.1f}" y="{TOP - 4}" fill="currentColor" '
                f'fill-opacity="0.8">{escape(str(label))}</text>'
            )
            # 6 units a character is monospace at this font size, near
            # enough to keep entries apart without measuring text.
            x += 14 + 6 * len(str(label)) + 12
        return parts

    def svg(self):
        """The whole picture, as markup, with no script anywhere in it."""
        x0, x1 = self.x_window
        y0, y1 = self.y_window
        drawn = self.drawn_series()
        place = self._placer((x0, x1), (y0, y1))

        parts = [
            f'<svg viewBox="0 0 {WIDTH} {HEIGHT}" width="100%" '
            f'role="img" aria-label="graph" '
            f'style="font-family: monospace; font-size: 10px;">',
            f'<rect x="{LEFT}" y="{TOP}" width="{PLOT_WIDTH}" '
            f'height="{PLOT_HEIGHT}" fill="none" stroke="currentColor" '
            f'stroke-opacity="0.35"/>',
        ]

        for value in self._ticks(y0, y1):
            _, y = place(x0, value)
            parts.append(
                f'<line x1="{LEFT}" y1="{y:.1f}" x2="{LEFT + PLOT_WIDTH}" '
                f'y2="{y:.1f}" stroke="currentColor" stroke-opacity="0.12"/>'
            )
            parts.append(
                f'<text x="{LEFT - 6}" y="{y + 3:.1f}" text-anchor="end" '
                f'fill="currentColor" fill-opacity="0.7">{value:.0f}</text>'
            )

        for seconds in self._ticks(x0, x1):
            x, _ = place(seconds, y0)
            parts.append(
                f'<line x1="{x:.1f}" y1="{TOP}" x2="{x:.1f}" '
                f'y2="{TOP + PLOT_HEIGHT}" stroke="currentColor" '
                f'stroke-opacity="0.12"/>'
            )
            parts.append(
                f'<text x="{x:.1f}" y="{HEIGHT - 10}" text-anchor="middle" '
                f'fill="currentColor" fill-opacity="0.7">{seconds:.1f}s</text>'
            )

        # Before the lines, so a reading is never hidden under a note
        # about where it is.
        parts.extend(self._mark_lines(place, (x0, x1), y0))
        parts.extend(self._legend())

        for index, (_label, points) in enumerate(drawn):
            if len(points) < 2:
                continue
            steps = " ".join(
                f"{x:.1f},{y:.1f}"
                for x, y in (place(s, v) for s, v in points)
            )
            parts.append(
                f'<polyline points="{steps}" fill="none" '
                f'stroke="{self._colour(index)}" '
                f'stroke-width="1.2" stroke-linejoin="round"/>'
            )

        if not any(len(points) >= 2 for _, points in drawn):
            parts.append(
                f'<text x="{LEFT + PLOT_WIDTH / 2}" y="{TOP + PLOT_HEIGHT / 2}" '
                f'text-anchor="middle" fill="currentColor">nothing on this '
                f'page</text>'
            )

        parts.append("</svg>")
        return "".join(parts)

    # --- the page ------------------------------------------------------------

    @property
    def snapshot_children(self):
        children = dict(self._commands())
        if self._marks_node is not None:
            children[self._marks_node.name] = self._marks_node
        return children

    def _page_reading(self):
        if self._page_size is None:
            return f"one page - the whole of it, {self.length} samples"
        return (
            f"page {self.page + 1} of {self.page_count} - "
            f"{self._page_size} samples a page"
        )

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        states.update(self._commands())

        leaf = leaves.into(states, path)
        x0, x1 = self.x_window
        y0, y1 = self.y_window
        inside = self.in_window
        shown = len(self.drawn())

        leaf("page", self._page_reading())

        # The number this exists to keep hold of, said out loud. Said per
        # line where there is more than one, because the points asked for
        # are a density rather than a budget and a total would read as
        # though the lines were sharing it out.
        lines = len(self._series)
        prefix = f"{lines} lines: " if lines > 1 else ""
        per_line = " a line" if lines > 1 else ""
        leaf(
            "points",
            f"{prefix}drawing {shown} of {inside} on this page, out of "
            f"{self.held} held - asked for {self._wanted}{per_line}",
        )
        if inside and shown >= inside:
            # Worth saying outright: this is the state the page size is a
            # control for, and it is not obvious from two numbers matching.
            leaf("density", "every sample on this page is drawn")
        if self._marks:
            here = len(self.marks_on_page())
            if self._page_size is None:
                # Nothing to jump to when it is all on screen already, and
                # saying which press changes that beats a link that looks
                # broken.
                leaf(
                    "marks",
                    f"{len(self._marks)}, all on this page - "
                    f'press "smaller page" to walk between them',
                )
            else:
                leaf("marks", f"{here} on this page, {len(self._marks)} in all")
        leaf("x", f"{x0:.1f}s to {x1:.1f}s")
        leaf("y", f"{y0:.0f} to {y1:.0f}  (zoom x{self._y_zoom:g})")
        # `image`, not `svg`: the page must not hang a wheel-zoom and a
        # drag-pan on this one. Those would move the picture without
        # moving the window, so the readings above - which page this is
        # and how much of it is drawn - would describe something other
        # than what is on screen. The links are the only way this moves.
        states["graph"] = leaves.image(path, "graph", self.svg())
        return states
