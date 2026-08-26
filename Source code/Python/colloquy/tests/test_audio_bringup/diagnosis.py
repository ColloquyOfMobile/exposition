# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_audio_bringup/diagnosis.py

"""Readings in, the next thing to check out. No board, no thread, no port.

`test_audio_loop` answers *does it work*. This answers *which link is
broken*, which is a different question and a harder one, because the
whole chain is one measurement: timer, pin, filter, divider, amplifier,
speaker, air, microphone, MSGEQ7, ADC. Nine things, one number at the
end.

The way to take a chain like that apart is not to measure it harder, it
is to **arrange for the faults to have different shapes**, and two facts
about this setup provide the shapes:

- **Every ear hears every voice.** The bodies are in one room, so a voice
  that is being made at all should reach *both* microphones. A tone heard
  by nobody is therefore a speaking fault, and a module that hears
  nothing while another module hears everything is a hearing fault. That
  separates the two halves of the chain with no extra hardware, and it
  needs at least two channels wired - which is exactly what there is.
- **A tone lands in a band.** Which band is a fact about frequency, not
  about geometry or level, so it survives a bench where everything is
  30 cm from everything else. A tone in the wrong band is a wiring error
  that no amount of listening would reveal.

**Where the software runs out.** Three faults it cannot separate on its
own, all of which a person separates in one second by listening, so it
says so instead of guessing:

- a voice not being generated, and a voice being generated into a dead
  amplifier - both are silence in the room;
- no sound arriving at a microphone, and a strobe line that never pulses
  (the MSGEQ7's multiplexer then sits on one band and all seven reads
  return it) - both are a flat reading. There is a partial tell, and
  `_mux_looks_frozen` uses it: if the *overall* level rises with a tone
  but no single band stands out, sound is arriving and the bands are not
  separating, which is the strobe.

Nothing here decides anything. It returns sentences, and the person
holding the scope decides.
"""

from __future__ import annotations

from typing import NamedTuple

from colloquy.drivers import audio

# How far a band must rise over its own silent level to count as heard.
# Blunt on purpose: the MSGEQ7's range is 0-1023 off the ADC and a tone in
# its own band is not subtle. This rejects drift and room noise; it does
# not measure anything.
MARGIN = 60

# An ADC pin reading at either rail is not a quiet room, it is a pin that
# is not connected to a working module output.
CEILING = 1000
BASEMENT = 3

# With a tone playing, the loudest band should stand well clear of the
# quietest. If it does not, the seven reads are not seven different
# bands - see _mux_looks_frozen.
FLAT_SPREAD = 40

# ...and "the overall level rose" is what tells that case apart from
# nothing arriving at all.
LEVEL_RISE = 25


class Health(NamedTuple):
    """One ear, before anything has been asked to sing."""

    body: str
    module: int
    ok: bool
    verdict: str


class Reading(NamedTuple):
    """What one ear made of one voice.

    Three numbers rather than one, because the diagnosis needs to tell
    three situations apart: `rise` is how far the singer's *own* band
    came up (did the right thing happen), `peak_rise` is how far the
    band that came up most came up (did *anything* happen), and
    `level_rise` is the mean across all seven (did the overall level
    move). A tone in the wrong band has a big peak and a small rise; a
    multiplexer that is not advancing has a peak no bigger than its own
    mean.
    """

    singer: str
    listener: str
    verdict: str
    rise: float
    best_band: int
    level_rise: float
    peak_rise: float

    @property
    def heard(self) -> bool:
        return self.verdict == "heard"


def mean_bands(sweeps):
    """The mean of each band over however many sweeps came back.

    Averaged rather than sampled once because the MSGEQ7's internal scan
    is fast enough to catch individual points on the *waveform* of the two
    lowest tones, so one reading of a steady 160 Hz varies with where in
    the cycle it landed.
    """
    if not sweeps:
        return None
    width = len(audio.BANDS_HZ)
    return [sum(sweep[band] for sweep in sweeps) / len(sweeps) for band in range(width)]


def health(body, sweeps):
    """Is this ear answering at all? Asked in silence, before any tone.

    Note what is deliberately *not* checked here: whether the seven bands
    differ from each other. In a quiet room they legitimately do not - the
    MSGEQ7 outputs sit at much the same low level across all seven - so
    "all bands alike" is normal in silence and only means something while
    a tone is playing. Checking it here would fail a working board in a
    quiet room, which is the worst possible first stage.
    """
    module = audio.module_of(body)
    values = mean_bands(sweeps)
    if values is None:
        return Health(body, module, False, "no reading came back")

    lowest, highest = min(values), max(values)
    if highest >= CEILING:
        return Health(
            body,
            module,
            False,
            f"pinned high ({highest:.0f}) - A{module} is not on a working "
            "module output. A floating input reads like this.",
        )
    if highest <= BASEMENT:
        return Health(
            body,
            module,
            False,
            f"pinned low ({highest:.0f}) - no supply to the module, or its "
            f"output is not reaching A{module}.",
        )
    if len(sweeps) > 1 and all(sweep == sweeps[0] for sweep in sweeps):
        return Health(
            body,
            module,
            False,
            "identical on every sweep - the reading is frozen, which a live "
            "analyser never is.",
        )
    return Health(body, module, True, f"alive, floor {lowest:.0f}-{highest:.0f}")


def read(singer, listener, floor_sweeps, tone_sweeps):
    """What one ear made of one voice, against its own silent floor."""
    floor = mean_bands(floor_sweeps)
    tone = mean_bands(tone_sweeps)
    if floor is None or tone is None:
        return Reading(singer, listener, "no reading", 0.0, -1, 0.0, 0.0)

    rises = [after - before for before, after in zip(floor, tone)]
    best = max(range(len(rises)), key=lambda index: rises[index])
    expected = audio.band_of_body(singer)
    level = sum(rises) / len(rises)

    if rises[best] < MARGIN:
        verdict = "silent"
    elif best != expected:
        verdict = f"wrong band - arrived at {audio.BANDS_HZ[best]} Hz"
    else:
        verdict = "heard"

    return Reading(singer, listener, verdict, rises[expected], best, level, rises[best])


def _mux_looks_frozen(readings):
    """Sound arriving, but the seven reads not separating into bands.

    The one strobe symptom that can be told from plain silence. If the
    *overall* level across all seven bands rose while a tone played, sound
    reached the microphone; if no single band then stands clear of the
    rest, the multiplexer is not advancing and every read is returning the
    same band. Strobe (D4) and reset (D3) are commoned to every module, so
    this is never a fault in one ear.
    """
    lively = [r for r in readings if r.level_rise >= LEVEL_RISE]
    if not lively:
        return False
    # `peak_rise`, not `rise`: the question is whether *any* band stood
    # out, not whether the right one did. Asking it of the expected band
    # made a pair of crossed channels - where both tones plainly arrive,
    # just in each other's bands - report as a dead strobe.
    return all(r.peak_rise - r.level_rise < FLAT_SPREAD for r in lively)


def diagnose(healths, readings, wired):
    """The whole run, as an ordered list of things to do next.

    **The most specific finding wins and silences the general ones**, and
    that ordering is not cosmetic. A crossed pair of channels produces a
    "silent" verdict on every pair in the grid, so a report built by
    listing symptoms opens with two walls of "scope this pin" and buries
    the one sentence that explains everything at the bottom. Somebody
    holding a scope reads from the top.

    So each stage below returns outright when it fully accounts for what
    was seen, and the stages are ordered by how much they explain rather
    than by how likely they are.
    """
    steps: list[str] = []
    dead = [h for h in healths if not h.ok]

    # 1. An ear that is not answering makes everything after it noise.
    if dead:
        for h in dead:
            steps.append(
                f"{h.body}'s ear is not answering: {h.verdict} "
                f"Check its module's supply, its microphone lead, and "
                f"J11 row {2 * h.module + 1}-{2 * h.module + 2} "
                f"(module {h.module} out -> A{h.module})."
            )
        if len(dead) == len(healths):
            steps.append(
                "Both ears at once points upstream of either: the analyser "
                "supply (J9 35 / J9 1), or reset on D3."
            )
        return steps

    if not readings:
        return ["nothing was measured - no tone was held long enough to read."]

    # 2. Sound arriving but not separating into bands: the commoned strobe.
    #    Explains every "silent" in the grid at once.
    if _mux_looks_frozen(readings):
        return [
            "The level rises when a tone plays but no band stands out - the "
            "multiplexer is not advancing, so all seven reads are the same "
            "band. Check STROBE on D4 and RESET on D3; both are commoned to "
            "every module, which is why this is never one ear."
        ]

    # 3. Two voices in each other's bands. Also explains every "silent",
    #    and it is the one fault here that is invisible by ear: both tones
    #    come out, both land in a real band, and the two are exchanged.
    swap = _crossed(readings, wired)
    if swap is not None:
        first, second = swap
        return [
            f"{first} and {second} arrived in each other's bands - their two "
            "channels are crossed. Swap them at the filter board, at the "
            "amplifier inputs, or at the tone pins, whichever is easiest to "
            "reach.",
            "Nothing else here needs investigating: this alone accounts for "
            "every pair reading silent, since each voice is being judged "
            "against a band the other one is arriving in.",
        ]

    by_singer = {body: [r for r in readings if r.singer == body] for body in wired}

    # A voice whose tone peaked *somewhere* is being generated and is
    # reaching a microphone, whatever band it landed in - so its speaking
    # side works and it must not be sent to a scope. Only a voice that
    # produced no peak anywhere is genuinely absent from the room.
    def made_a_sound(body):
        return any(r.peak_rise >= MARGIN for r in by_singer.get(body, []))

    mute = [b for b in wired if by_singer.get(b) and not made_a_sound(b)]
    audible = [b for b in wired if by_singer.get(b) and made_a_sound(b)]

    # 4. A tone that arrives at the wrong frequency. Reported before the
    #    mute voices, because it is the more specific of the two.
    for reading in readings:
        if not reading.verdict.startswith("wrong band"):
            continue
        arrived = audio.BANDS_HZ[reading.best_band]
        voice = audio.VOICES[reading.singer]
        steps.append(
            f"{reading.singer} arrived at {arrived} Hz instead of {voice['hz']} Hz "
            f"on {reading.listener}'s ear. That is a frequency, so it is not "
            f"the room and not the level: {voice['pin']} is feeding the wrong "
            f"filter channel. It should feed IN {_channel(voice['hz'])}."
        )
        break

    # 5. A voice that is not in the room at all.
    for body in mute:
        voice = audio.VOICES[body]
        heard_instead = ", ".join(audible) if audible else "nothing either"
        steps.append(
            f"{body} was not heard by any ear. **Listen while 'hold {body}' "
            "is on** - that one second splits the chain in two, and no "
            "reading here can."
        )
        steps.append(
            f"  Can hear it: the sound is in the room and not in the numbers, "
            f"so look at the microphones - placement, or the MAX9814 straps. "
            f"The other ears did hear {heard_instead}."
        )
        steps.append(
            f"  Cannot hear it: the speaking side. Scope {voice['pin']} first - "
            f"a {voice['hz']} Hz square wave the whole time that tone is held. "
            f"Then filter IN {_channel(voice['hz'])} -> its output -> the "
            f"22K/3K3 divider -> the GF1002 -> the speaker. Check the volume "
            f"pot before any of them: at minimum it is silent, and at minimum "
            f"is where it should have been left."
        )

    # 6. Every voice missing at once. One cause covers them all, and it is
    #    worth naming before two separate investigations begin.
    if mute and not audible:
        steps.append(
            "No voice reached any ear, and both ears answer. Before chasing "
            "channels one at a time, check what they share: power to the "
            "amplifiers, ground between the filter board and the PCB (J4 4), "
            "and whether the volume pots are still at minimum."
        )

    if not steps:
        steps.append(
            "Every wired channel worked. Run 'test audio loop' for the full "
            "grid once the other three are in."
        )
    return steps


def _crossed(readings, wired):
    """Two bodies each arriving in the other's band, or None."""
    landed = {}
    for reading in readings:
        if reading.best_band < 0 or reading.verdict == "silent":
            continue
        landed.setdefault(reading.singer, set()).add(reading.best_band)

    for first in wired:
        for second in wired:
            if first >= second:
                continue
            first_band = audio.band_of_body(first)
            second_band = audio.band_of_body(second)
            if landed.get(first) == {second_band} and landed.get(second) == {first_band}:
                return first, second
    return None


def _channel(hz):
    """How the filter board's own silkscreen writes this frequency."""
    return {160: "160", 400: "400", 1000: "1K", 2500: "2K5", 6250: "6K25"}[hz]


def summarise(healths, readings, wired):
    """One line: the answer, before any of the detail."""
    if any(not h.ok for h in healths):
        broken = ", ".join(h.body for h in healths if not h.ok)
        return f"{broken}: ear not answering"
    if not readings:
        return "nothing measured"

    heard = sum(1 for r in readings if r.heard)
    total = len(readings)
    if heard == total:
        return f"all {total} voice/ear pairs heard across {len(wired)} wired channels"
    return f"{heard}/{total} heard - see 'next'"
