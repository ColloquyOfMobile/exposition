"""What a reading says, in words.

The run always recorded every second of itself, but as tuples in a CSV -
which answers "how many were wrong" and not "wrong *how*". These pin the
second answer, because it is the one somebody watching a glitch is
asking, and because a sentence that names the wrong thing is worse than
no sentence at all.

Pure functions, no node and no hardware.
"""
from colloquy.tests.test_read_pattern import readings


# --- the drive vocabulary -------------------------------------------------


def test_a_drive_state_reads_as_the_word_the_rest_of_the_app_uses():
    assert readings.drive_label(("O",)) == "O"
    assert readings.drive_label(("P",)) == "P"
    assert readings.drive_label(("O", "P")) == "both"
    assert readings.drive_label(()) == "nothing"


def test_a_missing_drive_state_is_not_a_crash():
    assert readings.drive_label(None) == "nothing"


def test_a_drive_shape_nobody_expected_is_shown_rather_than_hidden():
    # If which_is_frustated() ever grows a third appetite, a reading that
    # silently said "nothing" would be worse than one that looks odd.
    assert readings.drive_label(("Q",)) == "Q"
    assert readings.drive_label(("P", "O")) == "P/O"


# --- the four ways a reading can come out ---------------------------------


def test_the_right_male_wanting_the_right_thing():
    assert (
        readings.describe("male1", ("P",), "male1", ("P",))
        == "male1 wanting P - as expected"
    )


def test_the_wrong_male_wanting_the_right_thing():
    # The case that prompted this: one flipped bit tips the answer onto a
    # neighbouring male's pattern, and the tally is what shows whether it
    # keeps happening the same way.
    assert (
        readings.describe("male1", ("P",), "male2", ("P",))
        == "male2 wanting P - expected male1"
    )


def test_the_right_male_wanting_the_wrong_thing():
    assert (
        readings.describe("male1", ("P",), "male1", ("O",))
        == "male1 wanting O - expected P"
    )


def test_both_wrong_names_both():
    assert (
        readings.describe("male1", ("P",), "male2", ("O",))
        == "male2 wanting O - expected male1 wanting P"
    )


def test_nothing_seen_is_its_own_answer():
    # Not a wrong reading. She saw no pattern at all that second, which
    # is what the gap between his bursts looks like from here.
    assert readings.describe("male1", ("P",), None, None) == "nothing seen"


def test_only_what_differs_is_named():
    # The sentence should be as short as the fault is - a reader scanning
    # sixty of them is looking for the ones with more words.
    correct = readings.describe("male1", ("O", "P"), "male1", ("O", "P"))
    both_wrong = readings.describe("male1", ("O", "P"), "male2", ())

    assert correct == "male1 wanting both - as expected"
    assert both_wrong == "male2 wanting nothing - expected male1 wanting both"


def test_a_list_and_a_tuple_of_the_same_appetites_are_the_same_answer():
    # The two sides come from different places - which_is_frustated() on
    # the male, and a key out of the pattern table on the female - so
    # they are compared as tuples rather than as written. Both build in
    # the same fixed order, so this is about the container and not about
    # ordering: ("P", "O") would still read as a mismatch, correctly.
    assert readings.is_correct(
        readings.describe("male1", ("O", "P"), "male1", ["O", "P"])
    )


# --- reading a run back ---------------------------------------------------


def test_correct_and_blank_are_told_apart_from_wrong():
    assert readings.is_correct("male1 wanting P - as expected")
    assert not readings.is_correct("male2 wanting P - expected male1")
    assert readings.is_blank("nothing seen")
    assert not readings.is_blank("male1 wanting P - as expected")


def test_a_held_reading_counts_once_however_long_it_stood():
    """The correction this tally exists for.

    read_pattern holds last_match until it expires or a newer decode
    replaces it, and the run samples it once a second. So one bad decode
    shows up as a run of identical wrong readings - three in the run that
    prompted this - and counting seconds would report three faults where
    there was one.
    """
    run = ["male2 wanting both - expected male1"] * 3

    assert readings.tally(run) == [("male2 wanting both - expected male1", 1, 3)]


def test_the_same_fault_twice_with_something_between_counts_twice():
    # Broken by a good reading, so these really are two decodes.
    run = [
        "male2 wanting P - expected male1",
        "male1 wanting P - as expected",
        "male2 wanting P - expected male1",
    ]

    assert readings.tally(run) == [("male2 wanting P - expected male1", 2, 2)]


def test_the_tally_counts_only_the_wrong_ones():
    run = [
        "male1 wanting P - as expected",
        "male2 wanting P - expected male1",
        "nothing seen",
        "male2 wanting P - expected male1",
        "male1 wanting O - expected P",
    ]

    assert readings.tally(run) == [
        ("male2 wanting P - expected male1", 2, 2),
        ("male1 wanting O - expected P", 1, 1),
    ]


def test_the_commonest_fault_comes_first():
    """Which is the whole point of the tally.

    One reading that keeps coming back is a pattern being mistaken for
    its neighbour every time. A scatter of different ones is a poor view
    of him, and no amount of pattern logic fixes that. The shape of this
    list is what tells the two apart at a glance.
    """
    run = []
    for reading, times in (("b - expected a", 1), ("c - expected a", 3), ("d - expected a", 2)):
        for _ in range(times):
            run.extend([reading, "x - as expected"])

    assert [times for _reading, times, _seconds in readings.tally(run)] == [3, 2, 1]


def test_episodes_collapse_only_neighbours():
    assert readings.episodes(["a", "a", "b", "a"]) == [("a", 2), ("b", 1), ("a", 1)]


def test_a_run_with_nothing_wrong_tallies_to_nothing():
    assert readings.tally(["male1 wanting P - as expected", "nothing seen"]) == []


def test_the_tally_lines_say_how_many_decodes_and_how_long():
    held = ["male2 wanting P - expected male1"] * 3

    assert readings.tally_lines(held) == [
        "once, 3s in all  |  male2 wanting P - expected male1"
    ]


def test_the_tally_lines_pluralise_when_it_really_happened_twice():
    run = [
        "male2 wanting P - expected male1",
        "male1 wanting P - as expected",
        "male2 wanting P - expected male1",
    ]

    assert readings.tally_lines(run) == [
        "2 times, 2s in all  |  male2 wanting P - expected male1"
    ]
