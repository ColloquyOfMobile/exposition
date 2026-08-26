"""The table that says which body speaks at which pitch, and who hears it.

Five facts wanted in four places, and every way of getting one of them
wrong is silent: a tone still comes out, a band still rises, and only the
*judging* is wrong. So they are pinned here rather than trusted.

Two of them are not this repo's to choose and the tests say so - the
pitches have to be five different analyser bands, and the pins have to be
five different timers. The third, that module N is body N, is luck rather
than design: the electronics box already had female1..male2's microphone
pairs on A0..A4 and the analyser modules took their places. Luck worth a
test, because the whole loop is readable by one number only while it
holds.
"""
import re
from pathlib import Path

import pytest

from colloquy.drivers import audio

SKETCH = (
    Path(__file__).resolve().parents[3]
    / "Arduino"
    / "colloquy_of_mobiles"
    / "colloquy_of_mobiles.ino"
)


# --- the shape of the table ----------------------------------------------


def test_every_body_has_a_voice():
    assert set(audio.VOICES) == {"female1", "female2", "female3", "male1", "male2"}


def test_the_pitch_order_is_the_body_order():
    """`BODIES_BY_PITCH` is what a sweep walks and what the firmware's
    thirty-five numbers are split by, so it climbing is not cosmetic."""
    pitches = [audio.VOICES[name]["hz"] for name in audio.BODIES_BY_PITCH]

    assert pitches == sorted(pitches)
    assert set(audio.BODIES_BY_PITCH) == set(audio.VOICES)


# --- the three things that must all be different -------------------------


def test_no_two_bodies_share_a_band():
    """The whole design: five bodies, five voices, no two competing for
    one band. Two in one band and which body is speaking stops being
    readable from the analyser at all."""
    bands = [audio.band_of_body(name) for name in audio.VOICES]

    assert len(set(bands)) == len(bands)


def test_no_two_bodies_share_a_timer():
    """A timer makes one frequency. Two voices on one timer is not a
    wiring mistake that can be corrected later - it is two bodies that
    can never sing different notes."""
    timers = [voice["timer"] for voice in audio.VOICES.values()]

    assert len(set(timers)) == len(timers)


def test_no_two_bodies_share_a_module():
    modules = [voice["module"] for voice in audio.VOICES.values()]

    assert sorted(modules) == [0, 1, 2, 3, 4]


def test_the_unused_bands_are_the_two_at_the_edges():
    """63 Hz and 16 kHz are left out on purpose: a typical electret
    microphone is only specified from 100 Hz to 10 kHz, and a good part of
    any audience cannot hear 16 kHz anyway."""
    used = {audio.band_of_body(name) for name in audio.VOICES}

    assert used == {1, 2, 3, 4, 5}
    assert audio.BANDS_HZ[0] == 63
    assert audio.BANDS_HZ[6] == 16000


# --- module N is body N --------------------------------------------------


def test_the_modules_are_in_body_order():
    """One number identifies a body all the way round the loop - out of
    the timer, through the room, back into the ADC. `AllAudio.read_all`
    splits the firmware's thirty-five numbers on exactly this."""
    for index, name in enumerate(audio.BODIES_BY_PITCH):
        assert audio.module_of(name) == index


# --- and the firmware on the other end -----------------------------------


def _sketch_define(name):
    match = re.search(rf"^#define {name} (\d+)", SKETCH.read_text(), re.MULTILINE)
    assert match is not None, f"no #define {name} in the sketch"
    return int(match.group(1))


@pytest.mark.parametrize(
    "body, define",
    [
        ("female1", "FEMALE1_TONE_PIN"),
        ("female2", "FEMALE2_TONE_PIN"),
        ("female3", "FEMALE3_TONE_PIN"),
        ("male1", "MALE1_TONE_PIN"),
        ("male2", "MALE2_TONE_PIN"),
    ],
)
def test_the_pins_here_are_the_pins_the_sketch_toggles(body, define):
    """Read out of the .ino rather than restated, the same trick
    firmware.py and virtual_serial_port.py already use.

    These pins are on the page so that somebody whose body has gone mute
    knows where to put a scope probe. A pin named here that the firmware
    does not drive sends them to the wrong header, and nothing else in the
    software would ever notice.
    """
    assert audio.VOICES[body]["pin"] == f"D{_sketch_define(define)}"


def test_a_tone_pin_is_never_also_a_neopixel_pin():
    """The conflict the whole rework was about. A NeoPixel line can be any
    pin and a timer output cannot, so when the two wanted the same pin the
    lights moved - and nothing but this stops one moving back."""
    text = SKETCH.read_text()
    lights = {
        int(match)
        for match in re.findall(r"^#define \w*NEOPIXEL_PIN (\d+)", text, re.MULTILINE)
    }
    tones = {
        int(match)
        for match in re.findall(r"^#define \w*TONE_PIN (\d+)", text, re.MULTILINE)
    }

    assert lights & tones == set()
    # And neither may collide with the analyser's two control lines.
    strobe = _sketch_define("ANALYSER_STROBE_PIN")
    reset = _sketch_define("ANALYSER_RESET_PIN")
    assert strobe not in lights | tones
    assert reset not in lights | tones
    assert strobe != reset


def test_the_two_usb_serial_pins_are_left_alone():
    """D0 and D1 are the link to the driver. A NeoPixel strip on either
    would take the installation off the air entirely, and the symptom
    would be a board that greets and then says nothing."""
    text = SKETCH.read_text()
    assigned = {
        int(match)
        for match in re.findall(
            r"^#define \w*(?:NEOPIXEL|TONE)_PIN (\d+)", text, re.MULTILINE
        )
    }

    assert 0 not in assigned
    assert 1 not in assigned
