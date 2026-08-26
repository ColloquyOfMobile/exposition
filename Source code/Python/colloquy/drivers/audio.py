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

Note the pitch order that falls out of it - female1 lowest, male2 highest.
TJ's firmware ran the other way (`act_tone_index = 5 - UNIT_ID`, female1
at 2637 Hz down to male2 at 1760, CODE_DOCUMENTATION 9.10), but his five
pitches all sat inside one analyser band and carried no information at
all; here the pitch *is* which body is speaking. Reversing it would cost
five jumpers on the board and buy nothing.
"""

# The MSGEQ7's seven bands, in the order the chip walks them under the
# strobe - which is the order the firmware returns them in.
BANDS_HZ = (63, 160, 400, 1000, 2500, 6250, 16000)

# body name -> everything about its voice and its ear.
#
# "timer" and "pin" are here to be *shown*, not used: nothing in Python
# touches a register. They are on the page because when a body turns out
# to be mute, the first question is which pin to put a scope on, and the
# person asking it is standing in front of the installation rather than
# in front of this file.
VOICES = {
    "female1": {"hz": 160, "timer": "T1", "pin": "D11", "module": 0},
    "female2": {"hz": 400, "timer": "T3", "pin": "D5", "module": 1},
    "female3": {"hz": 1000, "timer": "T4", "pin": "D6", "module": 2},
    "male1": {"hz": 2500, "timer": "T5", "pin": "D46", "module": 3},
    "male2": {"hz": 6250, "timer": "T2", "pin": "D10", "module": 4},
}

# In the order a sweep should walk them: by pitch, so somebody listening
# hears it climb rather than jump about. Same order as the table above,
# named separately so that the table can be reordered without silently
# reordering every test that sweeps it.
BODIES_BY_PITCH = ("female1", "female2", "female3", "male1", "male2")


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
