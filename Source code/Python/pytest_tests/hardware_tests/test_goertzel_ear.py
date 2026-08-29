# -*- coding: utf-8 -*-
# Source code/Python/pytest_tests/hardware_tests/test_goertzel_ear.py

"""Reading what the ear board says.

The run itself needs a Mega with a speaker and a microphone on it; what
can be checked here is the parsing, which is pure text work, and the
refusals. Same split as `test_audio_subsystem`'s protocol module and for
the same reason.

The sketch under test is `Source code/Arduino/goertzel_ear/`, and the
lines below are its own output format verbatim.
"""
from types import SimpleNamespace

from colloquy.tests.test_goertzel_ear import protocol

SWEEP_LINE = (
    "test hz=1000 bin=1003.9 floor=1.20 tone=41.80 rise=40.60 heard=1 fs=19230"
)
SILENT_LINE = (
    "test hz=6250 bin=6247.6 floor=2.10 tone=2.60 rise=0.50 heard=0 fs=19230"
)


# --- reading one line ----------------------------------------------------


def test_a_heard_pitch_reads_back_whole():
    reading = protocol.parse_test(SWEEP_LINE)

    assert reading.hz == 1000
    assert reading.bin_hz == 1003.9
    assert reading.floor == 1.20
    assert reading.tone == 41.80
    assert reading.rise == 40.60
    assert reading.heard is True
    assert reading.sample_rate == 19230
    assert reading.verdict == "heard"


def test_a_pitch_that_did_not_rise_is_not_heard():
    assert protocol.parse_test(SILENT_LINE).heard is False


def test_anything_that_is_not_a_reading_is_skipped_rather_than_raised():
    """A sweep's replies are interleaved with the board's own chatter and
    end with `sweep done`. A line that is not a reading is the ordinary
    case, not a fault."""
    for line in ("sweep done", "ok tone=1", "goertzel_ear firmware=1 fs=19230",
                 "error commands: f <hz> | t 0|1 | m | s | w | ?", ""):
        assert protocol.parse_test(line) is None


def test_a_truncated_line_is_skipped_too():
    """Serial gives half lines when a board reboots mid-sentence."""
    assert protocol.parse_test("test hz=1000 bin=1003.9 flo") is None


def test_fields_reads_name_value_pairs():
    assert protocol.fields("test hz=160 heard=0")["hz"] == "160"


# --- and the summary the page shows --------------------------------------


def readings(*specs):
    return [
        protocol.Reading(hz, 0.0, 1.0, 1.0 + rise, rise, rise >= 4.0, 19230.0)
        for hz, rise in specs
    ]


def test_a_clean_sweep_names_the_weakest():
    """Which is the number worth watching: the one closest to not being
    heard at all next time."""
    summary = protocol.summarise(readings((160, 40.0), (1000, 9.0), (6250, 22.0)))

    assert "all 3 heard" in summary
    assert "1000 Hz" in summary
    assert "+9.0" in summary


def test_a_failed_sweep_names_what_was_missing():
    summary = protocol.summarise(readings((160, 40.0), (6250, 0.5)))

    assert "1/2 heard" in summary
    assert "6250 Hz" in summary


def test_no_readings_at_all_says_so_rather_than_claiming_success():
    assert "nothing measured" in protocol.summarise([])


# --- the window ----------------------------------------------------------


def test_the_bin_is_narrow_enough_to_separate_the_pitches():
    """512 samples at the rate a Mega's ADC gives is about 37 Hz, and the
    closest two pitches the piece uses are 160 Hz apart."""
    width = protocol.bin_width(19230.0)

    assert 30 < width < 45
    closest = min(
        b - a for a, b in zip(protocol.PITCHES, protocol.PITCHES[1:])
    )
    assert closest > width * 3


def test_the_sweep_walks_the_installations_five():
    assert protocol.PITCHES == (160, 400, 1000, 2500, 6250)


# --- what it refuses to do -----------------------------------------------


def why_not(chosen, available):
    """`_why_not_open` against a double.

    Called unbound rather than on a constructed node: the real one builds
    a port picker and a results folder, and putting properties onto the
    class to fake it would leave them there for every test after this one.
    """
    from colloquy.tests.test_goertzel_ear import TestGoertzelEar

    fake = SimpleNamespace(
        is_bench=True,
        params={
            "goertzel ear": {"communication port": chosen, "baudrate": 115200}
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


def test_a_port_that_is_there_is_allowed():
    assert why_not("COM3", ["COM3", "COM7"]) is None


def test_it_refuses_anywhere_that_is_not_the_bench():
    """There is no stand-in for this board on purpose: it exists to say
    whether a microphone hears a tone, and a stand-in that answered yes
    would be exactly the false confidence it is against."""
    from colloquy.tests.test_goertzel_ear import TestGoertzelEar

    fake = SimpleNamespace(
        is_bench=False,
        params={"goertzel ear": {"communication port": "COM3"}},
        com_port=SimpleNamespace(ports=["COM3"]),
    )

    refusal = TestGoertzelEar._why_not_open(fake)

    assert "not the bench" in refusal
    assert "no stand-in" in refusal
