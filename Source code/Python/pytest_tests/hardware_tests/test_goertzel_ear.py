# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/hardware_tests/test_goertzel_ear.py

"""The Goertzel ear, with no board and no sound card.

The run itself needs a Mega with a microphone on it and a room with
speakers in it. What can be checked here is everything that is not those
two things, and after the arithmetic moved off the board that is now most
of the test rather than a parser:

- **the Goertzel itself**, against a signal generated right here. This is
  the part that could not be checked at all while it lived on an AVR, and
  it is the reason the move is worth more than a tidier wire. A sine of a
  known frequency goes in and the bin it belongs in has to be the one
  that rises.
- **the parsing** of what the sampler board sends, which is pure text
  work, exactly as it was before.
- **the tone's arithmetic**, which is free of the sound library on
  purpose so it can be checked on a machine with no speakers at all.
- **the refusals**, which now ask about the lead rather than the machine.

The sketch is `Source code/Arduino/microphone_sampler/`, and the lines
below are its own output format verbatim.
"""
from math import pi, sin
from types import SimpleNamespace

from colloquy.tests.test_goertzel_ear import goertzel, protocol, tone

SAMPLE_RATE = 19230.8
COUNT = 512


def sine(hz, count=COUNT, sample_rate=SAMPLE_RATE, amplitude=100, offset=512):
    """A block of samples like the board's: whole numbers around mid-rail."""
    return [
        int(offset + amplitude * sin(2 * pi * hz * i / sample_rate))
        for i in range(count)
    ]


# --- the arithmetic ------------------------------------------------------


def test_a_tone_lands_in_its_own_bin_and_not_in_the_others():
    """The whole claim of the test, checked against a signal we made.

    The five pitches were chosen so that each is its own bin here; a tone
    at one of them must lift that bin far above the four it is not.
    """
    levels = goertzel.magnitudes(sine(1000), protocol.PITCHES, SAMPLE_RATE)

    # A sine of amplitude 100 reads about 50 in these units, less what
    # scalloping takes: 1000 Hz is not exactly a basis frequency of a
    # 512-sample window at this rate, so the bin sits 2.5 Hz off it.
    assert 30 < levels[1000] < 55
    for hz in (160, 400, 2500, 6250):
        assert levels[hz] < levels[1000] / 10


def test_the_level_follows_the_amplitude():
    """Twice the signal is twice the level, which is what makes the rise
    over a floor mean anything at all."""
    quiet = goertzel.magnitude(sine(1000, amplitude=50), 1000, SAMPLE_RATE)
    loud = goertzel.magnitude(sine(1000, amplitude=100), 1000, SAMPLE_RATE)

    assert 1.9 < loud / quiet < 2.1


def test_the_dc_the_microphone_sits_at_is_taken_out():
    """A MAX9814 rests near mid-rail, so every sample is around 512 and
    none of that is signal. Moving the whole block must not move the
    level."""
    low = goertzel.magnitude(sine(1000, offset=300), 1000, SAMPLE_RATE)
    high = goertzel.magnitude(sine(1000, offset=800), 1000, SAMPLE_RATE)

    assert abs(low - high) < 0.01


def test_silence_reads_as_nothing():
    assert goertzel.magnitude([512] * COUNT, 1000, SAMPLE_RATE) < 0.001


def test_an_empty_block_is_zero_rather_than_a_division_by_zero():
    assert goertzel.magnitude([], 1000, SAMPLE_RATE) == 0.0
    assert goertzel.magnitude(sine(1000), 1000, 0) == 0.0


def test_the_bin_is_the_nearest_whole_number_of_cycles_in_the_window():
    """Which is what `bin_hz` reports rather than hiding: a tone falling
    between two bins reads low in both, and that looks exactly like a
    microphone that could not hear it."""
    measured = goertzel.bin_hz(1000, SAMPLE_RATE, COUNT)

    assert abs(measured - 1000) < goertzel.bin_width(SAMPLE_RATE, COUNT)
    assert measured != 1000


def test_the_bin_is_narrow_enough_to_separate_the_pitches():
    """512 samples at the rate a Mega's ADC gives is about 37 Hz, and the
    closest two pitches the piece uses are 160 Hz apart."""
    width = goertzel.bin_width(SAMPLE_RATE, COUNT)

    assert 30 < width < 45
    closest = min(b - a for a, b in zip(protocol.PITCHES, protocol.PITCHES[1:]))
    assert closest > width * 3


def test_the_rise_is_what_decides_and_not_the_level():
    """A MAX9814's gain control makes the absolute level meaningless, so
    a loud floor with a louder tone over it is heard and a quiet one that
    did not move is not."""
    assert goertzel.is_heard(level=48.0, floor=40.0)
    assert not goertzel.is_heard(level=48.0, floor=47.0)


def test_the_five_pitches_are_the_installations():
    assert protocol.PITCHES == (160, 400, 1000, 2500, 6250)


# --- reading what the board sends ----------------------------------------


def block_line(samples, sample_rate=SAMPLE_RATE):
    return (
        f"block n={len(samples)} fs={sample_rate:.1f} "
        + " ".join(str(s) for s in samples)
    )


def test_a_block_reads_back_whole():
    block = protocol.parse_block(block_line([512, 511, 514, 509]))

    assert block.samples == (512, 511, 514, 509)
    assert block.count == 4
    assert block.sample_rate == SAMPLE_RATE


def test_anything_that_is_not_a_block_is_skipped_rather_than_raised():
    """The reply arrives among the board's greeting and whatever half
    line was in the buffer when the port opened."""
    for line in (
        "microphone_sampler firmware=1 mic_pin=A0 n=512 fs=19230.8 baud=1000000",
        "status firmware=1 mic_pin=A0 n=512 fs=19230.8",
        "error commands: b | ?",
        "",
    ):
        assert protocol.parse_block(line) is None


def test_a_truncated_block_is_dropped_rather_than_measured_short():
    """The one shape a broken line takes here. 512 numbers do not cross in
    one read, so a read that gives up early yields a line that parses
    perfectly and is missing its end - and a short window silently widens
    every bin."""
    line = block_line([512] * 512).rsplit(" ", 40)[0]

    assert protocol.parse_block(line) is None


def test_a_block_with_something_unreadable_in_it_is_dropped():
    assert protocol.parse_block("block n=3 fs=19230.8 512 51x 514") is None


def test_the_span_catches_a_dead_pin_and_a_clipped_one():
    """Neither of which a bin level would say anything about."""
    assert protocol.parse_block(block_line([512] * 8)).span == 0
    assert protocol.parse_block(block_line([0, 1023] * 4)).span == 1023


def test_fields_reads_name_value_pairs():
    assert protocol.fields("status firmware=1 n=512")["n"] == "512"


# --- and the summary the page shows --------------------------------------


def readings(*specs):
    return [
        protocol.Reading(hz, 0.0, 1.0, 1.0 + rise, rise >= 4.0, SAMPLE_RATE)
        for hz, rise in specs
    ]


def test_a_clean_walk_names_the_weakest():
    """Which is the number worth watching: the one closest to not being
    heard at all next time."""
    summary = protocol.summarise(readings((160, 40.0), (1000, 9.0), (6250, 22.0)))

    assert "all 3 heard" in summary
    assert "1000 Hz" in summary
    assert "+9.0" in summary


def test_a_partial_walk_names_what_was_missing():
    summary = protocol.summarise(readings((160, 40.0), (6250, 0.5)))

    assert "1/2 heard" in summary
    assert "6250 Hz" in summary


def test_nothing_heard_anywhere_says_so_outright():
    assert "nothing heard" in protocol.summarise(readings((160, 0.1), (400, 0.2)))


def test_a_pitch_nobody_played_is_an_open_question_not_a_failure():
    """One tone sounds at a time and the links are pressed in whatever
    order somebody likes, so the summary is over what was tried."""
    assert "no pitch played yet" in protocol.summarise([])


# --- the tone this computer makes ----------------------------------------


def test_the_loop_holds_a_whole_number_of_cycles():
    """A buffer that does not close on a cycle boundary clicks once per
    wrap, and a click is broadband - it would lift all five bins at once
    and read as a room that had suddenly got louder."""
    data, played = tone.cycle_bytes(1000)

    cycles = played * tone.LOOP_SECONDS
    assert abs(cycles - round(cycles)) < 1e-6
    assert abs(played - 1000) < 5
    # And it ends where it began, which is what "whole cycles" buys.
    assert data[:2] == data[-2:] or int.from_bytes(data[:2], "little",
                                                   signed=True) == 0


def test_it_says_what_it_actually_played_rather_than_what_was_asked():
    """The same honesty `bin_hz` shows, and for the same reason: the
    frequency snapped to is close to the one asked for but is generally
    not it, and the page prints the one that came out."""
    for asked in tone_pitches():
        _, played = tone.cycle_bytes(asked)

        assert abs(played - asked) < 10


def tone_pitches():
    from colloquy.tests.test_goertzel_ear import protocol

    return protocol.PITCHES


def test_what_it_makes_is_what_the_stream_is_opened_for():
    """Mono signed 16-bit at the rate the stream declares. The buffer is
    handed to a raw output stream, so nothing checks this at run time -
    a mismatch would come out as a tone at the wrong speed."""
    data, _ = tone.cycle_bytes(1000)

    frames = len(data) / tone.BYTES_PER_FRAME
    assert frames == round(tone.LOOP_SECONDS * tone.SAMPLE_RATE)
    assert max(
        abs(int.from_bytes(data[i:i + 2], "little", signed=True))
        for i in range(0, len(data), 2)
    ) <= 32767


def test_the_tone_is_kept_clear_of_full_scale():
    """A clipped sine is a square again, which is the one thing this
    module exists to avoid - see tone.py on folded harmonics."""
    assert 0 < tone.AMPLITUDE < 0.9


# --- what it refuses to do -----------------------------------------------


def why_not(chosen, available):
    """`_why_not_open` against a double.

    Called unbound rather than on a constructed node: the real one builds
    a port picker, and putting properties onto the class to fake it would
    leave them there for every test after this one.
    """
    from colloquy.tests.test_goertzel_ear import TestGoertzelEar

    fake = SimpleNamespace(
        params={
            "goertzel ear": {"communication port": chosen, "baudrate": 1000000}
        },
        com_port=SimpleNamespace(ports=available),
    )
    return TestGoertzelEar._why_not_open(fake)


def test_it_refuses_when_no_port_is_chosen():
    assert "no port chosen" in why_not(None, ["COM3"])


def test_it_refuses_a_port_remembered_from_another_machine():
    """params outlives the machine that wrote it, and a stale name opens
    nothing while failing with a pyserial error nobody recognises."""
    refusal = why_not("COM9", ["COM3", "COM7"])

    assert "not a port on this machine" in refusal
    assert "COM3" in refusal


def test_a_port_that_is_there_is_allowed_wherever_the_machine_is():
    """The question is the lead, not the hostname. This asked `is_bench`
    while the board was Thomas's neighbour on one desk; it is one Mega
    with a microphone on it and it travels."""
    assert why_not("COM3", ["COM3", "COM7"]) is None


def test_it_refuses_to_play_where_it_cannot_make_a_sound():
    """Asked separately from the lead on purpose: a machine that cannot
    play reports five flat bins, which is exactly what a deaf microphone
    reports."""
    from colloquy.tests.test_goertzel_ear import TestGoertzelEar

    fake = SimpleNamespace(_tone=SimpleNamespace(is_available=False))

    refusal = TestGoertzelEar._why_no_sound(fake)

    assert "cannot play a sound" in refusal
    assert "no silent fallback" in refusal


# --- the run, recorded and drawn -----------------------------------------


def recorded(marks=(), blocks=40, hz=1000, rise_from=20):
    """A run: `blocks` blocks of levels, with `marks` pressed along the way.

    One pitch lifts partway through and the other four do not, which is
    the shape the whole test exists to produce. Times are handed in, so
    this needs no clock and no board.
    """
    from colloquy.tests.test_goertzel_ear.recording import Recording

    recording = Recording(protocol.PITCHES)
    recording.start(1000.0)
    pressed = list(marks)
    for index in range(blocks):
        now = 1000.0 + index * 0.25
        while pressed and pressed[0][0] <= index:
            _, label = pressed.pop(0)
            recording.mark(now, label)
        levels = {pitch: 1.0 for pitch in protocol.PITCHES}
        if index >= rise_from:
            levels[hz] = 30.0
        recording.add(now, levels)
    return recording


def test_a_block_is_kept_with_the_seconds_it_arrived_at():
    """The x axis is seconds since the run began, so the recording holds
    the offset rather than the wall clock - a run started at lunchtime
    would otherwise be drawn from 1.7 billion to 1.7 billion."""
    recording = recorded(blocks=3)

    assert len(recording) == 3
    assert recording.seconds == [0.0, 0.25, 0.5]
    assert recording.span == 0.5


def test_every_pitch_is_a_line_even_the_ones_nobody_played():
    """A flat line under a rule marked `1000 Hz on` is the evidence that
    the tone went where it was meant to and nowhere else. Dropping it
    would take away the half of the picture that says so."""
    lines = dict(recorded().series())

    assert list(lines) == [f"{hz} Hz" for hz in protocol.PITCHES]
    assert [value for _, value in lines["1000 Hz"]][-1] == 30.0
    assert set(value for _, value in lines["160 Hz"]) == {1.0}


def test_a_line_is_a_view_of_the_two_lists_and_not_a_copy_of_them():
    """`Columns`, for the reason `test_with_everything_moving` hands one
    over its dataframe: the graph reads the few hundred rows it draws and
    no pair is built for the rest."""
    from colloquy.ui.graph_view import Columns

    line = recorded().line(1000)

    assert isinstance(line, Columns)
    assert line[0] == (0.0, 1.0)


def test_a_mark_lands_at_the_moment_the_link_was_pressed():
    """Known here rather than worked out from the numbers later - this end
    is what started the sound. That is what makes the graph an answer
    rather than another thing to interpret."""
    recording = recorded(marks=[(20, "1000 Hz on")])

    assert recording.marks == [(5.0, "1000 Hz on")]


def test_marks_before_the_run_are_dropped_rather_than_given_a_time():
    """The play links work whether the test is running or not, and a tone
    pressed with it stopped is somebody checking their speakers."""
    from colloquy.tests.test_goertzel_ear.recording import Recording

    recording = Recording(protocol.PITCHES)
    recording.mark(500.0, "1000 Hz on")
    recording.add(500.0, {hz: 1.0 for hz in protocol.PITCHES})

    assert recording.marks == []
    assert len(recording) == 0


def test_starting_a_run_throws_the_last_one_away():
    """A graph whose marks belong to a session that ended, beside live
    readings that do not, is worse than no graph."""
    recording = recorded(marks=[(1, "1000 Hz on")])
    recording.start(2000.0)

    assert len(recording) == 0
    assert recording.marks == []


def ear_with(recording):
    """`_draw_the_recording` against a double, called unbound.

    The real node builds a port picker and a tone; what is under test is
    one method that turns a finished recording into a graph node.
    """
    from colloquy.tests.test_goertzel_ear import TestGoertzelEar

    fake = SimpleNamespace(
        _recording=recording, _graph=None, owner=None, owners=[]
    )
    TestGoertzelEar._draw_the_recording(fake)
    return fake._graph


def test_the_graph_is_drawn_when_the_run_ends_and_carries_its_marks():
    """Built at the end rather than as blocks arrive: `GraphView` takes
    its marks once, so one built at the first block would carry none of
    the presses that came after it."""
    graph = ear_with(recorded(marks=[(20, "1000 Hz on"), (30, "silence")]))

    assert graph.name == "recording"
    assert graph.marks == [(5.0, "1000 Hz on"), (7.5, "silence")]
    assert [label for label, _ in graph.series] == [
        f"{hz} Hz" for hz in protocol.PITCHES
    ]


def test_the_marks_are_offered_as_links_to_turn_to():
    """A run is pressed a few times and each press is a moment worth
    coming back to, which is what `GraphView`'s marks node is for."""
    graph = ear_with(recorded(marks=[(20, "1000 Hz on")]))

    assert "marks" in graph.snapshot_children
    assert list(graph["marks"].snapshot_children) == ["5.0s 1000 Hz on"]


def test_a_run_that_read_nothing_leaves_no_graph_at_all():
    """A refusal, or a lead pulled before the first block. An empty
    picture with controls that cannot move is not worth a node."""
    assert ear_with(recorded(blocks=0)) is None
