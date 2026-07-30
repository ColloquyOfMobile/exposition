# -*- coding: utf-8 -*-
# ../workspace2/Colloquy/exposition/Source code/Python/colloquy/hardware/female/light_sensor/emulate_read_pattern/__init__.py

from colloquy.base_thread import BaseThread
from time import sleep
from threading import Lock
from pathlib import Path
from collections import deque
from time import time
from .html import HTML
# from colloquy import LIGHT_PATTERNS


class ReadPattern(BaseThread):
    def __init__(self, owner):
        super().__init__(owner=owner)
        self._lock = Lock()
        self._html = HTML(owner=self)
        self[self.html.name] = self.html.handle_request

        self.sample_rate = 0.01  # seconds between internal samples
        self.step_duration = 0.5  # duration of one pattern step (your blink step)
        self.steps = 10  # number of steps in pattern (10 in LIGHT_PATTERNS)
        self.max_mismatches = 1  # how many bit-differences we tolerate
        self.detection_cooldown = 2.0  # seconds before reporting same pattern again

        # how many samples per one pattern step (should be >= 2)
        self.samples_per_step = int(round(self.step_duration / self.sample_rate))
        if self.samples_per_step < 2:
            # make sample_rate smaller or step_duration larger
            self.samples_per_step = max(2, self.samples_per_step)

        # buffer length: keep one extra step's worth so we can try different offsets
        self.buffer_len = self.samples_per_step * (self.steps + 1)
        self.sample_buffer = deque(maxlen=self.buffer_len)  # stores 0/1 samples

        self._last_sample_time = 0.0
        self._last_detection_time = 0.0

    @property
    def light_sensor(self):
        return self.owner.owner.light_sensor

    @property
    def html(self):
        return self._html

    @property
    def name(self):
        return "read pattern"

    def loop(self):
        """
        Called frequently by the thread framework (~20ms in your setup).
        We only sample when sample_rate elapsed.
        """
        now = time()
        if (now - self._last_sample_time) < self.sample_rate:
            return

        # raw = self.hardware.female1.sensor.read()  # analog reading
        state = self.light_sensor.read_as_bool()
        self.sample_buffer.append(state)
        self._last_sample_time = now

        # Only attempt detection when we have enough samples to form
        # steps * samples_per_step plus (samples_per_step - 1) extra for offsets.
        needed = self.samples_per_step * self.steps + (self.samples_per_step - 1)
        if len(self.sample_buffer) >= needed:
            match = self._try_match()
            if match:
                male, drive = match
                if (now - self._last_detection_time) > self.detection_cooldown:
                    # print(f"Pattern detected: {male}  drive={drive}")
                    self._last_detection_time = now

    def setup(self):
        pass

    def setdown(self):
        print(f"Set down {self=}")

    def _try_match(self):
        """
        Try different sub-step offsets to build candidate 10-bit sequences,
        convert each bin to 0/1 by majority (>0.5), then compare to every
        LIGHT_PATTERNS entry and rotations. Return (male, drive) on success.
        """
        buf = list(self.sample_buffer)
        s = self.samples_per_step
        needed = s * self.steps + (s - 1)
        if len(buf) < needed:
            return None

        # Take the last `needed` samples so we can shift offsets from 0..s-1
        chunk = buf[-needed:]
        # print(f"{chunk=}")

        best_candidate = None
        best_mismatches = self.steps + 1

        # For each offset inside one step (handles unknown alignment)
        for offset in range(s):
            block = chunk[offset : offset + s * self.steps]  # contiguous block
            # build the candidate 10-bit pattern by averaging each bin
            candidate = []
            for i in range(self.steps):
                start = i * s
                avg = sum(block[start : start + s]) / float(s)
                bit = 1 if avg > 0.5 else 0
                candidate.append(bit)

            # compare candidate to all known patterns and all rotations
            for male, patterns in self.colloquy.light_patterns.items():
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

                        # remember best so far for debug/logging
                        if mismatches < best_mismatches:
                            best_mismatches = mismatches
                            best_candidate = (
                                male,
                                drive,
                                candidate,
                                rotated,
                                offset,
                                mismatches,
                            )

                        # early accept if within tolerance
                        if mismatches <= self.max_mismatches:
                            # if self.debug:
                            # print(f"Good match: {male} drive={drive} rot={rot} offset={offset} mismatches={mismatches}")
                            return (male, drive)

        return None

    # def snapshot(self, path):
    # path = path + (self.name, )
    # states = {
    # "path": path,
    # "name": self.name,
    # "close": self.close,
    # "open": self.open,
    # "opened": self._is_opened,
    # "start": self.start,
    # }
    # return states

    @property
    def snapshot_children(self):
        children = {}
        return children


class DetectPattern:
    """
    Sample the photosensor at a high rate, bin the samples into N steps
    (step_duration each), then match the resulting N-bit pattern against
    LIGHT_PATTERNS (trying all circular rotations and allowing a few mismatches).
    """

    def __init__(
        self,
        owner,
        threshold=300,  # analog threshold for raw -> digital
        sample_rate=0.05,  # seconds between internal samples
        step_duration=0.5,  # duration of one pattern step (your blink step)
        steps=10,  # number of steps in pattern (10 in LIGHT_PATTERNS)
        max_mismatches=1,  # how many bit-differences we tolerate
        detection_cooldown=2.0,  # seconds before reporting same pattern again
        debug=False,
    ):
        super().__init__(owner=owner, name="pattern_detector")

        self.threshold = threshold
        self.sample_rate = sample_rate
        self.step_duration = step_duration
        self.steps = steps
        self.max_mismatches = max_mismatches
        self.detection_cooldown = detection_cooldown
        self.debug = debug

        # how many samples per one pattern step (should be >= 2)
        self.samples_per_step = int(round(self.step_duration / self.sample_rate))
        if self.samples_per_step < 2:
            # make sample_rate smaller or step_duration larger
            self.samples_per_step = max(2, self.samples_per_step)

        # buffer length: keep one extra step's worth so we can try different offsets
        self.buffer_len = self.samples_per_step * (self.steps + 1)
        self.sample_buffer = deque(maxlen=self.buffer_len)  # stores 0/1 samples

        self._last_sample_time = 0.0
        self._last_detection_time = 0.0

    def _loop(self, **kwargs):
        """
        Called frequently by the thread framework (~20ms in your setup).
        We only sample when sample_rate elapsed.
        """
        now = time()
        if (now - self._last_sample_time) < self.sample_rate:
            return

        raw = self.hardware.female1.sensor.read()  # analog reading
        state = 1 if raw > self.threshold else 0
        self.sample_buffer.append(state)
        self._last_sample_time = now

        # Only attempt detection when we have enough samples to form
        # steps * samples_per_step plus (samples_per_step - 1) extra for offsets.
        needed = self.samples_per_step * self.steps + (self.samples_per_step - 1)
        if len(self.sample_buffer) >= needed:
            match = self._try_match()
            if match:
                male, drive = match
                if (now - self._last_detection_time) > self.detection_cooldown:
                    # print(f"Pattern detected: {male}  drive={drive}")
                    self._last_detection_time = now

    def _try_match(self):
        """
        Try different sub-step offsets to build candidate 10-bit sequences,
        convert each bin to 0/1 by majority (>0.5), then compare to every
        LIGHT_PATTERNS entry and rotations. Return (male, drive) on success.
        """
        buf = list(self.sample_buffer)
        s = self.samples_per_step
        needed = s * self.steps + (s - 1)
        if len(buf) < needed:
            return None

        # Take the last `needed` samples so we can shift offsets from 0..s-1
        chunk = buf[-needed:]

        best_candidate = None
        best_mismatches = self.steps + 1

        # For each offset inside one step (handles unknown alignment)
        for offset in range(s):
            block = chunk[offset : offset + s * self.steps]  # contiguous block
            # build the candidate 10-bit pattern by averaging each bin
            candidate = []
            for i in range(self.steps):
                start = i * s
                avg = sum(block[start : start + s]) / float(s)
                bit = 1 if avg > 0.5 else 0
                candidate.append(bit)

            # compare candidate to all known patterns and all rotations
            for male, patterns in LIGHT_PATTERNS.items():
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

                        # remember best so far for debug/logging
                        if mismatches < best_mismatches:
                            best_mismatches = mismatches
                            best_candidate = (
                                male,
                                drive,
                                candidate,
                                rotated,
                                offset,
                                mismatches,
                            )

                        # early accept if within tolerance
                        if mismatches <= self.max_mismatches:
                            if self.debug:
                                pass
                                # print(f"Good match: {male} drive={drive} rot={rot} offset={offset} mismatches={mismatches}")
                            return (male, drive)

        return None
