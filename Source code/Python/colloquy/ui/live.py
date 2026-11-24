"""The server's half of the live page: a stream of what changed.

The page used to be as old as its last request, with a "Refresh values"
link for when that mattered. Now every console page opens one
`EventSource` on `/live/<root>/<node path>`, and this generator answers
it for as long as the page is open:

- `commands` - the presses in flight (`ui/in_flight.py`), sent the moment
  the set changes, so a button spins while its command is queued or
  running, on every open page and not only the one that pressed it.
- `tree` - the node's controls, rendered exactly as the page renders
  them, sent only when that HTML changed. Its `id` is the revision the
  page holds, so a reconnecting `EventSource` (which sends it back as
  `Last-Event-ID`) is not sent what it already has.
- `trouble` - the render raised; the text, once, and empty once it
  recovers. A stream must never raise (nothing would be left to report it
  to), and must never stop the installation either: it is a view.
- `gone` - the node no longer exists, or the main PCB is noted out. The
  page reloads and the ordinary routes say where it went.

**The command lock is only ever tried, never waited on.** Rendering walks
the tree, and the walk must not overlap a command (`Colloquy.get_states`),
so each render takes the lock with no wait at all and skips the tick when
a command holds it - the spinner is what the page shows meanwhile. A
render takes the lock for one snapshot, which delays a press by at most
that long, and the interval stretches so rendering never takes more than
a `RENDER_SHARE`th of the time (a page of charts on the laptop).

The stream ends with the server: it watches `shutdown_event`, because
`server_close()` joins every connection still open (`block_on_close`),
and a restart would otherwise wait for every open tab to be closed.
"""
import hashlib
import json
from time import monotonic

from colloquy.ui.in_flight import IN_FLIGHT

# How often the stream looks at the commands in flight and the clock.
TICK = 0.25
# The shortest time between two renders of the same node.
LIVE_INTERVAL = 1.0
# A render may take at most 1/RENDER_SHARE of the stream's time.
RENDER_SHARE = 4
# After a render that raised, wait this long before the next.
TROUBLE_BACKOFF = 5.0
# A comment line this often when nothing else was sent, so a page that is
# gone (a phone asleep) is noticed by a failed write and its thread ends.
HEARTBEAT = 5.0
# What the browser waits before reconnecting after the stream drops.
RETRY_MS = 2000

BUSY = ("busy",)
GONE = ("gone",)

HEADERS = [
    ("Content-Type", "text/event-stream; charset=utf-8"),
    ("Cache-Control", "no-store"),
]


def revision_of(html):
    """What the page and the stream compare: the same bytes, the same name."""
    return hashlib.sha1(html.encode("utf-8")).hexdigest()[:16]


def event(name, data="", ident=None):
    """One server-sent event. Every line of `data` gets its own prefix."""
    lines = [f"event: {name}"]
    if ident:
        lines.append(f"id: {ident}")
    lines.extend(f"data: {line}" for line in (data.splitlines() or [""]))
    return ("\n".join(lines) + "\n\n").encode("utf-8")


def stream(render, stop, revision="", in_flight=IN_FLIGHT, clock=monotonic):
    """Events for one open page until `stop` is set.

    `render()` answers `("tree", html, revision)`, `BUSY`, `GONE` or
    `("trouble", text)`, and must not raise; `stop` is an Event.
    """
    yield f"retry: {RETRY_MS}\n\n".encode()
    seen_commands = None
    trouble = None
    next_render = 0.0
    beat = clock()
    while not stop.is_set():
        now = clock()
        if in_flight.revision != seen_commands:
            seen_commands = in_flight.revision
            yield event("commands", json.dumps(in_flight.snapshot()))
            beat = now
        if now >= next_render:
            outcome = render()
            took = clock() - now
            kind = outcome[0]
            if kind == "gone":
                yield event("gone")
                return
            if kind == "busy":
                next_render = now + TICK
            elif kind == "trouble":
                next_render = now + TROUBLE_BACKOFF
                if outcome[1] != trouble:
                    trouble = outcome[1]
                    yield event("trouble", trouble)
                    beat = now
            else:
                _, html, fresh = outcome
                next_render = now + max(LIVE_INTERVAL, RENDER_SHARE * took)
                if trouble is not None:
                    trouble = None
                    yield event("trouble")
                if fresh != revision:
                    revision = fresh
                    yield event("tree", html, fresh)
                    beat = now
        if clock() - beat >= HEARTBEAT:
            yield b": beat\n\n"
            beat = clock()
        stop.wait(TICK)
