# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_read_pattern/readings.py

"""What a female decoded, in words.

The run already recorded every second of it - sender, receiver, expected
drive, detected male, detected drive, match - but as tuples in a CSV,
which answers "how many were wrong" and not "wrong *how*". Those are
different questions, and the second one is the one somebody watching a
glitch is asking.

A wrong reading fails in one of three ways and they mean different
things at the rig:

- **the wrong male, right appetite** - one flipped bit is enough to tip
  the answer onto a neighbouring male's pattern, so this is the light
  reaching her, not the pattern table;
- **the right male, wrong appetite** - the same, one band over;
- **both wrong** - she is not really seeing him at all, and what she
  decoded is closer to noise than to a message.

Naming each reading is also what turns a tally into evidence: three
wrong readings that are all "male2 wanting P" is a systematic
mis-decode, and three that disagree with each other is a poor view.

**One thing to know before believing a wrong reading.** What is expected
is read at the moment of comparison, and the burst she decoded was sent
up to 4.35 seconds earlier. So a male whose appetites cross the
frustrated mark mid-run genuinely changes what he is asking for, and for
a few seconds afterwards her correct reading of the *old* message is
recorded as wrong. That shows up as a short unbroken run of the same
mismatch, right where the drive state changed - which is exactly what a
systematic mis-decode looks like too. The CSV's expected-drive column is
what tells them apart: if it changes at that moment, the readings were
right and the comparison was late.

Pure functions, no node and no hardware: everything here takes what was
decoded and gives back a string.
"""

# The drive-state vocabulary, as which_is_frustated() returns it.
DRIVE_LABELS = {
    tuple(): "nothing",
    ("O",): "O",
    ("P",): "P",
    ("O", "P"): "both",
}

NOTHING_SEEN = "nothing seen"


def drive_label(drives):
    """('O', 'P') -> "both". Unknown shapes are shown rather than hidden:
    a drive tuple this does not recognise is a fact worth seeing."""
    if drives is None:
        return "nothing"
    return DRIVE_LABELS.get(tuple(drives), "/".join(drives) or "nothing")


def describe(expected_male, expected_drive, detected_male, detected_drive):
    """One reading, said out loud.

        male1 wanting P - as expected
        male2 wanting P - expected male1
        male1 wanting O - expected P
        male2 wanting O - expected male1 wanting P
        nothing seen

    Only what actually differs is named after the dash, so the sentence
    is as short as the fault is.
    """
    if detected_male is None and detected_drive is None:
        return NOTHING_SEEN

    read = f"{detected_male} wanting {drive_label(detected_drive)}"

    wrong_male = detected_male != expected_male
    wrong_drive = tuple(detected_drive or ()) != tuple(expected_drive or ())

    if not wrong_male and not wrong_drive:
        return f"{read} - as expected"
    if wrong_male and not wrong_drive:
        return f"{read} - expected {expected_male}"
    if wrong_drive and not wrong_male:
        return f"{read} - expected {drive_label(expected_drive)}"
    return (
        f"{read} - expected {expected_male} wanting {drive_label(expected_drive)}"
    )


def is_correct(reading):
    return reading.endswith("- as expected")


def is_blank(reading):
    return reading == NOTHING_SEEN


def episodes(readings):
    """Consecutive identical readings collapsed into one, with how many
    seconds it stood.

    This is not tidying, it is the difference between one fault and
    three. `read_pattern.last_match` is *held* - until it expires or a
    newer decode replaces it - and this run samples it once a second. So
    a single bad decode appears as a run of identical wrong readings, and
    counting seconds would report it as three separate faults. Seen
    exactly that way: three consecutive "male2 wanting both" from one
    mis-decode.
    """
    collapsed = []
    for reading in readings:
        if collapsed and collapsed[-1][0] == reading:
            collapsed[-1] = (reading, collapsed[-1][1] + 1)
        else:
            collapsed.append((reading, 1))
    return collapsed


def tally(readings):
    """The wrong decodes, by what they said: (reading, times, seconds).

    Counted per decode rather than per second, for the reason above.
    Sorted commonest first, because the shape of the list is the answer:
    one reading that keeps coming back is a pattern being mistaken for
    its neighbour every time, and a scatter of different ones is a poor
    view of him - which is the aiming, the distance or the room, not the
    pattern table.
    """
    counts = {}
    for reading, seconds in episodes(readings):
        if is_correct(reading) or is_blank(reading):
            continue
        entry = counts.setdefault(reading, [0, 0])
        entry[0] += 1
        entry[1] += seconds

    return sorted(
        ((reading, times, seconds) for reading, (times, seconds) in counts.items()),
        key=lambda row: (-row[1], -row[2], row[0]),
    )


def tally_lines(readings):
    lines = []
    for reading, times, seconds in tally(readings):
        how_often = "once" if times == 1 else f"{times} times"
        lines.append(f"{how_often}, {seconds}s in all  |  {reading}")
    return lines
