# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_audio_loop/verdicts.py

"""What one ear made of one voice, in a word.

Split out of the test for the same reason `test_audio_subsystem/
protocol.py` is: this is the part worth being sure about, and none of it
touches a port, a thread or a clock. It takes two tuples of numbers and
returns a word.

The words are the same three that test carries - `heard`, `wrong band`,
`silent` - so a person reading both runs is reading one vocabulary. The
fourth, `own voice`, is new here and exists because this test knows
something Thomas's board cannot: which body is which. A body hearing
itself is not a result, it is the arrangement.
"""

from colloquy.drivers import audio


def verdict(floor, heard, singer, margin):
    """Did this ear hear this voice, and hear it in the right band?

    Four ways it can go, and they mean different things in the room:

    - **heard** - the singer's own band rose by at least `margin` over the
      silent floor, and rose more than any other band did. The whole chain
      worked: timer, pin, filter, amplifier, speaker, air, microphone,
      MSGEQ7, ADC.
    - **wrong band** - something rose, but the loudest rise was elsewhere.
      That is a tone coming out at a frequency other than the one the
      firmware believes, or an ear wired to the wrong analog input, or a
      body wired to another body's filter channel. Rarer, and more
      interesting than a silence.
    - **silent** - nothing rose. Either the tone is not being made, or
      that ear is not hearing it.
    - **no reading** - the sweep did not come back at all, which is a
      broken link rather than a broken chain.

    `singer` and the ear are allowed to be the same body, and it is
    reported rather than skipped: nobody listens while they speak
    (CODE_DOCUMENTATION 9.12), so what a body hears of itself is the one
    reading here that measures the *room* rather than the wiring, and it
    is worth seeing.
    """
    if not floor or not heard:
        return "no reading"

    expected = audio.band_of_body(singer)
    rises = [after - before for before, after in zip(floor, heard)]
    best = max(range(len(rises)), key=lambda index: rises[index])

    # "Did anything rise" is asked before "did the right thing rise", and
    # the order matters: testing the expected band first makes a tone
    # coming out at the wrong frequency report as silence, which sends
    # somebody looking at the amplifier when the fault is in the timer.
    if rises[best] < margin:
        return "silent"
    if best != expected:
        return f"wrong band ({audio.BANDS_HZ[best]} Hz rose instead)"
    return "heard"


def summarise(all_verdicts):
    """One line for the page: all of them, or the ones that were not."""
    heard = sum(1 for value in all_verdicts.values() if value == "heard")
    total = len(all_verdicts)
    if not total:
        return "nothing was measured"
    if heard == total:
        return f"all {total} voice/ear pairs heard"
    bad = sorted(
        f"{singer} -> {listener}: {value}"
        for (singer, listener), value in all_verdicts.items()
        if value != "heard"
    )
    return f"{heard}/{total} heard - " + "; ".join(bad)
