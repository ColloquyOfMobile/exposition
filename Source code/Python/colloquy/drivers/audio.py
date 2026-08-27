# -*- coding: utf-8 -*-
# Source code/Python/colloquy/drivers/audio.py

"""Which body speaks at which pitch, and which ear hears it.

One table, because the same five facts are needed in four places - the
speaker node, the microphone node, the loop test and the simulator - and
because getting one of them out of step with the firmware is silent: a
tone still comes out, a band still rises, and only the *judging* is
wrong.

The numbers are not this port's to choose. Each is fixed by something
outside the software:

- **The pitches** are Thomas Erforth's five, chosen so that each lands in
  a different one of the MSGEQ7's seven bands. That is the design: five
  bodies, five voices, no two competing for one band. 63 Hz and 16 kHz
  are left out because a typical electret microphone is only specified
  from 100 Hz to 10 kHz - and a good part of any audience cannot hear
  16 kHz anyway.
- **The pins** are fixed by the silicon. Timer n toggles its own OCnA pin
  and no other, so a body's pitch and a body's pin are one decision.
- **The modules** are fixed by the board that already exists. The
  electronics box had female1..male2's microphone pairs on A0..A4, and
  the analyser modules took their places, so module N is body N. That is
  luck rather than design, and it is worth keeping: one number identifies
  a body all the way round the loop, out of the timer, through the room
  and back into the ADC.

**The males have the two low voices and the females the three high
ones**, which is the artist's decision and it is also the sense TJ's
firmware ran in (`act_tone_index = 5 - UNIT_ID`, CODE_DOCUMENTATION
9.10). It went the other way here until 2026-08-27.

What it costs is worth understanding, because it is not what it looks
like. A pitch cannot simply be moved to another body: the pitch belongs
to the *timer*, and Thomas's OCR values are indexed by timer
(`AudioAnalyzer.h`, `OCRVALS16`). 6250 Hz is on timer 2 because timer 2
is the 8-bit one - at its prescaler of 8 it cannot reach anywhere near
160 Hz, and putting it there would mean a different prescaler and a
different OCR. So the pitches stay on their timers, and the **bodies move
across the pins** instead. Every OCR value, every prescaler and every
filter channel is untouched; what changes is which body's amplifier each
filter output feeds. `dirty rework` predicted the price exactly: five
re-jumperings, not a rebuild.

**Two orders live here now, and they are no longer the same.** They were
identical until this change, which hid the difference and let at least
one caller name one and use the other:

- `BODIES` is body order, which is module order, which is A0..A4. It is
  how the firmware's thirty-five numbers come back and the only right way
  to split them.
- `BODIES_BY_PITCH` is what a sweep walks, so somebody listening hears it
  climb rather than jump about.
"""

from typing import Final, TypedDict

# The MSGEQ7's seven bands, in the order the chip walks them under the
# strobe - which is the order the firmware returns them in.
BANDS_HZ: Final = (63, 160, 400, 1000, 2500, 6250, 16000)


class Voice(TypedDict):
    """One body's row of the table below.

    Spelled out rather than left as a bare dict because three of these
    four are small integers that read alike at a glance and mean entirely
    different things - a pitch in hertz, an index into `BANDS_HZ`, and an
    analyser module number - and the checker had no way to tell them
    apart while the dict's values were `object`.
    """

    hz: int
    timer: str
    pin: str
    module: int


# body name -> everything about its voice and its ear.
#
# "timer" and "pin" are here to be *shown*, not used: nothing in Python
# touches a register. They are on the page because when a body turns out
# to be mute, the first question is which pin to put a scope on, and the
# person asking it is standing in front of the installation rather than
# in front of this file.
# In body order, so that a body's position here is its module number.
VOICES: Final[dict[str, Voice]] = {
    "female1": {"hz": 1000, "timer": "T4", "pin": "D6", "module": 0},
    "female2": {"hz": 2500, "timer": "T5", "pin": "D46", "module": 1},
    "female3": {"hz": 6250, "timer": "T2", "pin": "D10", "module": 2},
    "male1": {"hz": 160, "timer": "T1", "pin": "D11", "module": 3},
    "male2": {"hz": 400, "timer": "T3", "pin": "D5", "module": 4},
}

# Body order, which is module order, which is A0..A4. This is how the
# firmware's thirty-five numbers arrive - module-major - and so the only
# right thing to split them on. Named separately from the dict because
# "iterate the table" and "iterate the modules in order" are two
# intentions, and one of them has a wrong answer.
BODIES: Final = tuple(VOICES)

# In the order a sweep should walk them: by pitch, so somebody listening
# hears it climb rather than jump about.
#
# NOT the same as `BODIES` any more - the males hold the two low voices.
# Anything that means "the five modules, in module order" wants `BODIES`;
# only a sweep wants this. They were the same tuple's worth of names in
# the same order until 2026-08-27, which is exactly why the difference is
# spelled out twice.
BODIES_BY_PITCH: Final = ("male1", "male2", "female1", "female2", "female3")


def band_of(hz: int) -> int:
    """Which of the seven bands a tone of this pitch shows up in."""
    return BANDS_HZ.index(hz)


def band_of_body(body: str) -> int:
    """Which band this body's own voice should arrive in."""
    return band_of(VOICES[body]["hz"])


def module_of(body: str) -> int:
    """Which analyser module - and so which ADC input - is this body's
    ear. Module N is body N; see this module's docstring for why."""
    return VOICES[body]["module"]


def describe(body: str) -> str:
    """One line for the page: pitch, the pin it comes out of, the band it
    should come back in."""
    voice = VOICES[body]
    return (
        f"{voice['hz']} Hz on {voice['pin']} ({voice['timer']}), "
        f"heard in band {band_of(voice['hz'])}"
    )
