from colloquy.base_thread import BaseThread
from colloquy.light_pattern_timing import (
    BIT_DURATION,
    BITS,
    BURST_DURATION,
    CYCLE_DURATION,
)
from time import time


class Blink(BaseThread):
    """A male sending his identity pattern on his ring.

    One burst, then silence, then the next burst - TJ's shape
    (`act_transmit_light()` in act_light.ino, timed by Logic_male.ino's
    `timer_search`). The ten bits go out in order from the first, 0.2s
    each, and the ring then stays dark for the rest of the 4.35s cycle.
    See colloquy/light_pattern_timing.py for where those numbers come
    from, and why the silence is part of the message rather than a pause
    between messages.

    This used to rotate a deque forever at 0.5s a step: no gap, no start,
    2.5x too slow, and every rotation of it as plausible as the real one
    to whoever was reading.

    Which pattern goes out is read once, when the burst starts, and not
    again until the next one. A drive state that changes halfway through
    would otherwise splice two messages into one nobody can read - the
    same reason TJ calls `MALE_setSearchLight()` at the cycle boundary
    and nowhere else.
    """

    def __init__(self, owner):
        self._name = f"blink {owner.male.name}"
        super().__init__(owner=owner)
        self._cycle_start = 0
        self._bits = ()
        self._lit = None

    @property
    def male(self):
        return self.owner.male

    @property
    def name(self):
        return self._name

    @property
    def white(self):
        return dict(red=0, green=0, blue=0, white=255)

    @property
    def is_transmitting(self):
        """True while the burst is going out, False during the silence."""
        return (time() - self._cycle_start) < BURST_DURATION

    @property
    def pattern(self):
        """The bits this burst is sending, empty before the first one."""
        return self._bits

    def loop(self):
        elapsed = time() - self._cycle_start
        if elapsed >= CYCLE_DURATION:
            self._start_burst()
            return

        index = int(elapsed // BIT_DURATION)
        self._show(self._bits[index] if index < BITS else 0)

    def _start_burst(self):
        self._cycle_start = time()
        self._bits = tuple(self.male.get_blink_pattern())
        self._show(self._bits[0])

    def _show(self, value):
        # The thread ticks every ~10ms and every ring write is a serial
        # round trip to the Arduino, so only send what changes - at 200ms
        # a bit, writing per tick would be twenty times the traffic for
        # the same light.
        if value == self._lit:
            return
        self.male.ring.set(value)
        self._lit = value

    def setup(self):
        self.male.ring.color = self.white
        self.male.ring.on()
        # Zero rather than now, so the first loop() finds a whole cycle
        # elapsed and opens with a burst instead of a silence - TJ enters
        # search with `timer_search = 9999` for the same reason
        # (Logic_male.ino:342).
        self._cycle_start = 0
        self._bits = ()
        self._lit = None

    def setdown(self):
        self.male.ring.off()
        self._lit = 0

    @property
    def snapshot_children(self):
        return {}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        if not self.is_started:
            return states

        def leaf(key, value):
            states[key] = {"path": path + (key,), "name": key, "value": value}

        # Worth spelling out at the rig: a ring that sits dark for 2.35s
        # of every 4.35s is the pattern working, not a light that failed.
        leaf("sending", "".join(str(bit) for bit in self._bits))
        leaf("ring", "transmitting" if self.is_transmitting else "dark (gap)")
        return states
