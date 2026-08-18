# -*- coding: utf-8 -*-
# ../workspace2/Colloquy/exposition/Source code/Python/colloquy/hardware/female/light_sensor/emulate_read_pattern/__init__.py

from colloquy.base_thread import BaseThread
from colloquy.light_pattern_timing import BIT_DURATION, BITS, CYCLE_DURATION
from threading import Lock
from collections import deque
from time import time
from bisect import bisect_left
from colloquy.ui import leaves


class ReadPattern(BaseThread):
    def __init__(self, owner):
        super().__init__(owner=owner)
        self._lock = Lock()

        self.sample_rate = 0.01  # nominal seconds between internal samples
        # One bit of the pattern, and how many of them there are - the
        # male's clock, not a number of her own (light_pattern_timing.py).
        # She samples as fast as the Arduino will answer rather than at
        # TJ's 50ms: the binning below is by wall clock, so more samples
        # per bit is only ever a better vote.
        self.step_duration = BIT_DURATION
        self.steps = BITS
        self.max_mismatches = 1  # how many bit-differences we tolerate
        self.detection_cooldown = 2.0  # seconds before reporting same pattern again
        self.offset_substeps = 10  # how many start-time offsets to try per step

        # Samples are timestamped and binned by measured wall-clock time
        # rather than by a fixed samples-per-step count: the thread loop
        # can't actually sustain `sample_rate` exactly (loop overhead, the
        # blocking arduino round-trip), and that drift accumulates enough
        # over one full pattern (steps * step_duration) to desync a
        # fixed-count binning from the real bit boundaries.
        self._buffer_seconds = self.step_duration * (self.steps + 1)
        self.sample_buffer = deque()  # stores (timestamp, 0/1) samples

        self._last_sample_time = 0.0
        self._last_detection_time = 0.0
        self._last_match = None
        self.last_match_time = None

    @property
    def match_validity(self):
        """How long a detection stays current. A match describes what the
        sensor saw over the preceding few seconds, so it goes stale as soon
        as the female (or the bar) has moved on.

        Two burst cycles, not two pattern lengths: a male sends for 2s and
        is then dark for 2.35s, so a match can only be refreshed once every
        4.35s. Expiring sooner than that would blank her answer for most of
        every gap and report "nothing seen" at a male who is transmitting
        perfectly well."""
        return CYCLE_DURATION * 2

    @property
    def last_match(self):
        """The (male, drive) currently being seen, or None. Deliberately not
        a plain attribute holding the last hit forever: a failed attempt
        leaves the previous value untouched, so without this expiry a single
        detection stands as "what she sees" indefinitely - long after she has
        turned away - and anything counting it reads a rising number where
        nothing is happening."""
        if self._last_match is None:
            return None
        if (time() - self.last_match_time) > self.match_validity:
            return None
        return self._last_match

    @property
    def light_sensor(self):
        return self.owner.owner.light_sensor

    @property
    def name(self):
        return f"read pattern {self.owner.owner.name}"

    def loop(self):
        """
        Called frequently by the thread framework (~20ms in your setup).
        We only sample when sample_rate elapsed.
        """
        now = time()
        if (now - self._last_sample_time) < self.sample_rate:
            return

        state = self.light_sensor.read_as_bool()
        self.sample_buffer.append((now, 1 if state else 0))
        self._last_sample_time = now

        cutoff = now - self._buffer_seconds
        while self.sample_buffer and self.sample_buffer[0][0] < cutoff:
            self.sample_buffer.popleft()

        needed_duration = self.step_duration * self.steps
        span = self.sample_buffer[-1][0] - self.sample_buffer[0][0]
        if span >= needed_duration:
            match = self._try_match()
            if match:
                male, drive = match
                self._last_match = match
                self.last_match_time = now
                if (now - self._last_detection_time) > self.detection_cooldown:
                    self.log(f"Pattern detected: {male} drive={drive}")
                    self._last_detection_time = now

    def setup(self):
        # This object lives as long as the process, so everything below
        # outlives a single run. Start each run from nothing: otherwise the
        # buffer still holds samples from whenever the sensor was last read,
        # and the first seconds report a detection made during an earlier run
        # entirely - minutes or hours ago, possibly against a different male.
        self.sample_buffer.clear()
        self._last_sample_time = 0.0
        self._last_detection_time = 0.0
        self._last_match = None
        self.last_match_time = None

    def setdown(self):
        print(f"Set down {self=}")

    def _try_match(self):
        """
        Try different start-time offsets (rather than sample-count offsets,
        which drift out of sync with real bit boundaries once the loop
        can't sustain `sample_rate` exactly), bin each candidate's samples
        by majority vote per step, then compare to every LIGHT_PATTERNS
        entry and rotation. Return (male, drive) on success.
        """
        buf = list(self.sample_buffer)
        if not buf:
            return None

        timestamps = [t for t, _bit in buf]
        bits = [bit for _t, bit in buf]
        t_end = timestamps[-1]
        needed_duration = self.step_duration * self.steps
        sub_step = self.step_duration / self.offset_substeps

        # For each start-time offset inside one step (handles unknown alignment)
        for offset_index in range(self.offset_substeps):
            t0 = t_end - needed_duration - offset_index * sub_step

            candidate = []
            for i in range(self.steps):
                bin_start = t0 + i * self.step_duration
                bin_end = bin_start + self.step_duration
                lo = bisect_left(timestamps, bin_start)
                hi = bisect_left(timestamps, bin_end)
                if hi <= lo:
                    candidate = None
                    break
                bin_bits = bits[lo:hi]
                avg = sum(bin_bits) / len(bin_bits)
                candidate.append(1 if avg > 0.5 else 0)

            if candidate is None:
                continue

            # compare candidate to every pattern a male can actually send,
            # and all rotations. The gap between bursts is what really
            # settles the phase - a window that straddles the silence reads
            # dark where the pattern says lit and fails - but she can still
            # start sampling mid-burst, and the patterns carry no start
            # marker of their own (all eight open on the same 1,1,0,0), so
            # every rotation is still worth testing. TJ covers the same
            # ground one alignment per tick through his circular buffer.
            for male, patterns in self.colloquy.readable_light_patterns.items():
                for drive, ref in patterns.items():
                    ref_list = list(ref)
                    # test every circular rotation of reference (pattern is periodic)
                    for rot in range(self.steps):
                        if rot == 0:
                            rotated = ref_list
                        else:
                            rotated = ref_list[-rot:] + ref_list[:-rot]

                        mismatches = sum(
                            1 for a, b in zip(candidate, rotated) if a != b
                        )

                        if mismatches <= self.max_mismatches:
                            return (male, drive)

        return None

    @property
    def snapshot_children(self):
        children = {}
        return children

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        if self._last_match is not None:
            male, drive = self._last_match
            seconds_ago = round(time() - self.last_match_time, 1)
            # Shown even once expired, with the difference spelled out: the
            # age alone doesn't tell a reader where the cut-off is.
            expired = "" if self.last_match else ", expired - not what she sees now"
            states["last match"] = leaves.value(
                path,
                "last match",
                f"{male} drive={drive} ({seconds_ago}s ago{expired})",
            )
        return states
