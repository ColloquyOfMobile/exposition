# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_teensy/first_run.py

"""What has to be true before `test teensy` can work, as steps to tick off.

Each step is a fact about *this machine* or *this Teensy*, so its "done"
is remembered in params (`params["teensy"]["first run done"]`, step key ->
when it was pressed), and a done step stays on the page for
`HIDE_AFTER` seconds - long enough to see the press took - and then goes.
`show the first-run steps again` forgets them all. Pure: no node, no port.
"""

# How long a step marked done stays drawn, in seconds.
HIDE_AFTER = 10.0

# (key, what to do). The key is what params stores and what the page's
# link names, so it is short and never reworded; the text may be.
STEPS = (
    (
        "install the teensy core",
        "In the Arduino IDE: File > Preferences, add "
        "https://www.pjrc.com/teensy/package_teensy_index.json to "
        "'Additional boards manager URLs', then Tools > Board > Boards "
        "Manager, search 'Teensy' and install it. Without it 'flash "
        "firmware' cannot compile.",
    ),
    (
        "find the teensy's port",
        "Open 'com port'. A Teensy is listed by name only if the sketch on "
        "it uses USB serial. If it is not there: press the white button on "
        "the Teensy, and flash once from the Arduino IDE (Tools > Board > "
        "Teensy 4.1, Tools > Port, a 'teensy' port, open "
        "Source code/Arduino/teensy_check/ and Upload). From then on it has "
        "a COM port and this page does the rest.",
    ),
    (
        "expect the teensy loader",
        "A small 'Teensy' window (PJRC's Teensy Loader) opens during every "
        "flash. That is how the Teensy tools upload - leave it alone, it "
        "can stay open.",
    ),
)

KEYS = tuple(key for key, _ in STEPS)


def done_link(key):
    """The page link that marks one step done."""
    return f"done: {key}"


def visible(done, now):
    """The steps still to draw: (key, text, seconds left or None).

    `seconds left` is None for a step not done yet, and the seconds until
    it hides for one that was just pressed. A step done longer ago than
    `HIDE_AFTER` is left out. `done` is params' dict; a value that is not
    a number (hand-edited params) counts as not done, since a render must
    never raise.
    """
    shown = []
    for key, text in STEPS:
        when = done.get(key) if isinstance(done, dict) else None
        if not isinstance(when, (int, float)):
            shown.append((key, text, None))
            continue
        left = HIDE_AFTER - (now - when)
        if left > 0:
            shown.append((key, text, left))
    return shown
