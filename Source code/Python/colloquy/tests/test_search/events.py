# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_search/events.py

"""What happened, in words - and what counts as a miss.

`test_read_pattern` logs one row per second: a level, sampled. This test
logs *events*, because nothing here is standing still. A female sways,
the bar slides, and a male is only in her view for a few seconds at a
time - so "she read male1 at 41.2s, having had him in view for 6s" is the
sentence somebody wants, and "she had him in view for 11s and read
nothing" is the other one.

Three kinds:

- **read** - `read_pattern` produced a fresh decode. Right or wrong is a
  separate column, because a wrong read and no read at all are different
  faults: one is the light reaching her badly, the other is her not
  looking at him.
- **miss** - she had a blinking male in view for long enough to have
  decoded him, and did not. This is the event `test_read_pattern` cannot
  produce at all, since it holds the pair still and the answer is always
  "yes, eventually".
- **found** - her search recognised a male asking for something she is
  short of and ended itself. Logged and then undone (the test restarts
  her), because what follows a find is reinforcement, and there is none.

**What "long enough" means.** A male sends for 2s and is then dark for
2.35s, so the worst case is that she arrives just as a burst ends and
waits a full cycle for the next one, plus the 2s of it she has to see.
`MISS_AFTER` is two whole cycles, which is comfortably past that - the
point is to count the times she plainly should have read him, not to
argue about the marginal ones.

**One thing to know before believing an expected-male column.** The burst
she decoded was sent up to 4.35s before she reported it, and in that time
the bar has moved. So the male named as "in view" is the one in view when
she *answered*, which for a bar crossing quickly may not be the one she
heard. That is a real limit of measuring this on a moving rig, not a
fault in the reading - see the note in `readings.py` about the same lag
in the drive column.

Pure functions, no node and no hardware.
"""
from colloquy.light_pattern_timing import CYCLE_DURATION

# How long a female must have a blinking male in view, with nothing
# decoded, before the run calls it a miss. Two full send cycles: one for
# the burst she may have arrived too late for, one for the next.
MISS_AFTER = CYCLE_DURATION * 2

READ = "read"
MISS = "miss"
FOUND = "found"

# The drive-state vocabulary, as which_is_frustated() returns it. Same
# table as test_read_pattern's readings.py, kept here rather than
# imported across tests: they are two runs of a different shape and
# neither should be able to break the other by editing a label.
DRIVE_LABELS = {
    tuple(): "nothing",
    ("O",): "O",
    ("P",): "P",
    ("O", "P"): "both",
}


def drive_label(drives):
    """('O', 'P') -> "both". An unrecognised shape is shown, not hidden."""
    if drives is None:
        return "nothing"
    return DRIVE_LABELS.get(tuple(drives), "/".join(drives) or "nothing")


def describe_read(female, in_view, expected_drive, detected_male, detected_drive):
    """One decode, said out loud.

        female1 read male1 wanting P - as expected
        female1 read male1 wanting O - expected P
        female1 read male2 wanting P - expected male1
        female1 read male1 wanting P - nobody was in view
    """
    read = f"{female} read {detected_male} wanting {drive_label(detected_drive)}"

    if in_view is None:
        # She decoded something with no male lined up on her at all.
        # Worth its own sentence: it is either the geometry being wrong
        # about what she can see, or light from somewhere unintended.
        return f"{read} - nobody was in view"

    wrong_male = detected_male != in_view
    wrong_drive = tuple(detected_drive or ()) != tuple(expected_drive or ())

    if not wrong_male and not wrong_drive:
        return f"{read} - as expected"
    if wrong_male and not wrong_drive:
        return f"{read} - expected {in_view}"
    if wrong_drive and not wrong_male:
        return f"{read} - expected {drive_label(expected_drive)}"
    return f"{read} - expected {in_view} wanting {drive_label(expected_drive)}"


def describe_miss(female, male, seconds):
    return (
        f"{female} had {male} in view for {seconds:.0f}s and read nothing"
    )


def describe_found(female, male, drive):
    # No comma. Every one of these sentences is written into a CSV as its
    # last column, and a comma in it splits the row - which is exactly how
    # test_read_pattern lost a column to ('O', 'P') once already. There is
    # a test below this file's own logic that holds every describe_* to
    # it, because the failure is silent until somebody tries to read the
    # results months later.
    return f"{female} found {male} sharing the {drive} drive - search restarted"


def is_correct(reading):
    return reading.endswith("- as expected")


def tally_lines(rows):
    """The events that were not clean reads, commonest first.

    `rows` is (kind, reading). The shape of this list is the answer: one
    sentence coming back over and over is systematic - a pattern read as
    its neighbour every time, or one female who never reads anybody - and
    a scatter of different ones is a poor view, which is aiming and
    lighting rather than the pattern table.
    """
    counts = {}
    for kind, reading in rows:
        if kind == READ and is_correct(reading):
            continue
        counts[reading] = counts.get(reading, 0) + 1

    ordered = sorted(counts.items(), key=lambda row: (-row[1], row[0]))
    return [
        f"{'once' if times == 1 else f'{times} times'}  |  {reading}"
        for reading, times in ordered
    ]
