# -*- coding: utf-8 -*-
# Source code/Python/colloquy/ui/leaves.py

"""The kinds of leaf a node can put in its snapshot, one constructor each.

A leaf is something the page draws but cannot open: a reading, a rendered
document, a graph. It is a dict of exactly three things - where it is
(`path`), what it is called (`name`), and one payload key naming its kind.
The renderer (`server2/wsgi2.py`) dispatches on that payload key, which is
why the key *is* the kind and why there is one constructor per kind here.

Not leaves, and so not here:

- **Children** - other nodes, dicts carrying "opened"; they come from
  `snapshot_children` and the tree walk builds them.
- **Commands** - bare callables put straight into the snapshot dict
  (`states["turn to origin"] = self.turn_to_origin`). The page draws them
  as links that call them through the "call" path segment.

`into()` is for the common case of a node with several readings to show:

    leaf = leaves.into(states, path)
    leaf("angle", f"{self.get():.1f} deg")
    leaf("goal", f"{self.goal:.1f} deg")

and the constructors are for one-offs:

    states["rendered"] = leaves.html(path, "rendered", self.render_html())
"""

# Every payload key the renderer knows how to draw, in the order it tries
# them. A kind not in here is a leaf nothing can render - the page shows
# the dict's own repr, which is how missing kinds have shown up before.
KINDS = ("value", "editor", "html", "chart", "pre", "svg")


def leaf(path, key, kind, payload):
    """One leaf of any kind. The constructors below are this, named."""
    assert kind in KINDS, f"{kind!r} is not a kind the page can draw: {KINDS}"
    return {"path": path + (key,), "name": key, kind: payload}


def value(path, key, value):
    """A reading, shown as "key: value". Anything with a str().

    Formatting belongs to whoever knows what the number means - a degree
    sign, a percentage, seconds - so this takes what it is given.
    """
    return leaf(path, key, "value", value)


def html(path, key, markup):
    """A block of ready-made HTML, dropped into the page as it is - a
    rendered markdown document, a rendered timeline, a traceback."""
    return leaf(path, key, "html", markup)


def chart(path, key, data):
    """An interactive chart: JSON in uPlot's aligned-data shape (see
    `tests/test_light_sensor_values/utils.py`'s dataframe_to_chart_json).
    Zoomable and pannable in the browser, unlike `svg` below."""
    return leaf(path, key, "chart", data)


def svg(path, key, markup):
    """A picture already drawn, inlined - what matplotlib wrote. The page
    gives it scroll-to-zoom and drag-to-pan, but the pixels are fixed."""
    return leaf(path, key, "svg", markup)


def pre(path, key, text):
    """Preformatted text, wrapped and scrollable - a log file."""
    return leaf(path, key, "pre", text)


def editor(path, key, content):
    """A textarea and a save button. The save posts back to the node's own
    "save" command (see wsgi2's _parse_post), so a node offering this must
    register one."""
    return leaf(path, key, "editor", content)


def into(states, path):
    """Return a `leaf(key, value)` that files value leaves into `states`.

    For the common shape: a node with a handful of readings to show, all
    under its own path.
    """

    def add(key, reading):
        states[key] = value(path, key, reading)
        return states[key]

    return add
