# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_goertzel_ear/tone.py

"""The tone, played out of this computer's own speakers.

The board used to make it: a hardware timer toggling `OC1A` in CTC mode,
which meant a square wave, on one fixed pin, into an amplifier and a
loudspeaker somebody had to wire up. All of that was a workaround for the
board being the only thing in the room that could make a sound. It is
not - the machine running this has a sound card in it.

**A sine, and that is an improvement rather than a preference.** The
board's square was the right call *for a timer*: a compare output can
only toggle, its fundamental is 4/pi of its peak and so 2.1 dB louder
than a sine of the same peak, and the harmonics land in bins nobody is
looking at. But "nobody is looking at" is not "nowhere". Sampled at
19.2 kSPS with no anti-alias filter in front of the ADC, a 6250 Hz square
has a third harmonic at 18750 Hz that folds back to about 480 Hz - which
is one of the five bins this test reads, and a tone would then appear at
a pitch nobody played. A sine has no third harmonic to fold. See
`hardware > electronics > one board per body`, "And a square wave suits
it better than a sine", which is about a body's amplifier and reaches the
opposite conclusion for reasons that do not apply here.

**One buffer of whole cycles, played round and round.** The wave is built
once, of a whole number of cycles, and the sound card's callback copies
out of it with a rolling offset that wraps. Whole cycles is what makes
the wrap silent: a buffer that does not close on a cycle boundary clicks
once per repeat, and a click is broadband - it would lift all five bins
at once and read as a room that had suddenly got louder. The frequency
actually played is therefore the nearest one that fits the buffer a whole
number of times, and it is returned rather than hidden, the same way
`goertzel.bin_hz` is.

It also means the callback does no arithmetic at all - two slice copies -
which matters because it runs on the sound device's own thread while this
process is reading a serial port on another.

**`sounddevice` is a real dependency of this test**, in
`requirements.txt`. It was `winsound` out of the standard library first,
and that ran into two walls worth recording: CPython refuses
`SND_MEMORY | SND_ASYNC` outright (`RuntimeError: Cannot play
asynchronously from memory`), so a looping tone had to be written to a
temporary file and played by name; and it is Windows only, which put a
platform gate on a test whose entire question is acoustic. This has
neither problem and needs no numpy.

**There is no fallback and no silent no-op.** A test whose whole question
is whether a sound was heard must not be able to report anything at all
on a machine that could not make one - five flat bins is exactly what a
deaf microphone looks like. So `is_available` is False where the library
or a sound device is missing, and the play links refuse in a sentence.
`cycle_bytes` below is free of all of it on purpose, so the arithmetic
can still be checked anywhere.
"""
from math import pi, sin

try:
    import sounddevice
except Exception:  # pragma: no cover - an import error, or PortAudio missing
    sounddevice = None

# CD rate. Nothing here needs more, and every sound device has it.
SAMPLE_RATE = 44100

# Roughly a quarter of a second of audio, played round and round. Long
# enough that the snapped frequency is within a fraction of a hertz of
# what was asked for, short enough to build in no time at all.
LOOP_SECONDS = 0.25

# Full scale invites clipping from anything in the chain that adds a
# little gain, and a clipped sine is a square again - which is the one
# thing this module exists to avoid. The loudness knob is the operating
# system's, where somebody can reach it.
AMPLITUDE = 0.3

# Two bytes a frame, mono, signed little-endian - what `dtype="int16"`
# means to the stream below.
BYTES_PER_FRAME = 2


def cycle_bytes(hz, seconds=LOOP_SECONDS, sample_rate=SAMPLE_RATE,
                amplitude=AMPLITUDE):
    """A mono 16-bit sine, and the frequency it actually holds.

    Returns `(data, played_hz)`. `played_hz` is `hz` snapped to the
    nearest frequency with a whole number of cycles in the buffer, so it
    wraps silently - see the module docstring.
    """
    count = max(2, int(round(seconds * sample_rate)))
    cycles = max(1, int(round(count * hz / sample_rate)))
    played_hz = cycles * sample_rate / count

    peak = int(32767 * amplitude)
    frames = bytearray()
    for index in range(count):
        value = int(peak * sin(2.0 * pi * cycles * index / count))
        frames += value.to_bytes(2, "little", signed=True)
    return bytes(frames), played_hz


class Tone:
    """One tone at a time, out of the default sound device.

    Not a `Base` node: it has no page of its own and nothing addresses it
    by path. The test owns one and offers a link per pitch.
    """

    def __init__(self):
        self._hz = None
        self._played_hz = None
        self._stream = None
        self._buffer = b""
        self._offset = 0

    @property
    def is_available(self):
        """Can this machine make a sound at all?

        The library *and* a device: a machine with `sounddevice` installed
        and no output (a headless one, or a container) would otherwise
        fail on the first press rather than saying so on the page.
        """
        if sounddevice is None:
            return False
        try:
            sounddevice.query_devices(kind="output")
        except Exception:
            return False
        return True

    @property
    def hz(self):
        """The pitch asked for, or None if nothing is sounding."""
        return self._hz

    @property
    def played_hz(self):
        """The pitch actually sounding - `hz` snapped to the buffer."""
        return self._played_hz

    def _callback(self, outdata, frames, time_info, status):
        """Fill the device's buffer from ours, wrapping at the end.

        No arithmetic, on purpose: this runs on the sound device's own
        thread while the rest of this process is reading a serial port,
        and a callback that is late is a gap in the tone.
        """
        needed = frames * BYTES_PER_FRAME
        size = len(self._buffer)
        written = 0
        while written < needed:
            chunk = min(needed - written, size - self._offset)
            outdata[written:written + chunk] = self._buffer[
                self._offset:self._offset + chunk
            ]
            written += chunk
            self._offset = (self._offset + chunk) % size

    def play(self, hz):
        """Start `hz` and leave it sounding. Returns the frequency played.

        Starting a second tone replaces the first, which is what this test
        wants: a reading is only a reading if the room holds the one thing
        being measured.
        """
        if sounddevice is None:
            raise RuntimeError(
                "this machine has no `sounddevice`, so nothing here can "
                "make a sound - pip install sounddevice"
            )
        self.stop()

        self._buffer, played_hz = cycle_bytes(hz)
        self._offset = 0
        self._stream = sounddevice.RawOutputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype="int16",
            callback=self._callback,
        )
        self._stream.start()

        self._hz = hz
        self._played_hz = played_hz
        return played_hz

    def stop(self):
        """Silence, and safe to call when nothing is sounding.

        Called from `setdown` as well as from the link, because a run that
        ends - or throws - while a tone is sounding would leave the room
        making a noise with no page left saying why. The device is handed
        back rather than held open and fed silence: this test is idle most
        of the time and something else may want the speakers.
        """
        self._hz = None
        self._played_hz = None

        stream, self._stream = self._stream, None
        if stream is None:
            return
        try:
            stream.stop()
            stream.close()
        except Exception:
            # Silence is what the caller asked for, and it has it - the
            # buffer is gone either way. A device that will not close
            # tidily must not be what fails a stop.
            pass
