from colloquy.base_thread import BaseThread
from datetime import datetime
from time import time

COLORS = (
    ("red", dict(red=255, green=0, blue=0, white=0)),
    ("green", dict(red=0, green=255, blue=0, white=0)),
    ("blue", dict(red=0, green=0, blue=255, white=0)),
    ("white", dict(red=0, green=0, blue=0, white=255)),
)


class TestNeopixels(BaseThread):
    """Cycles every neopixel segment on every body (each female's head/
    bodyO/bodyP/feet, each male's ring/up ring/o drive level/p drive
    level - 20 segments total) through red/green/blue/white, one segment
    and color at a time, so each physical LED segment can be visually
    confirmed to light up in the right place with the right color.

    Also exposes every real segment object as a child (safe - these are
    real Base objects, not bare callables) for manual poking - any RGBW/
    brightness combination via its own existing controls - independent
    of the automated sequence.
    """

    STEP_DURATION = 0.8  # seconds each segment/color combination stays lit

    def __init__(self, owner, result_folder):
        super().__init__(owner=owner)

        # Neopixel.name is a fixed literal per segment type ("head",
        # "ring", ...), shared across every female/male instance - keying
        # by it directly here would collide across bodies (same class of
        # bug as ReadPattern.name/TurnBackAndForth.name fixed earlier).
        self._segments = {}
        for female in self.hardware.females:
            for attr in ("head", "body_o", "body_p", "feet"):
                segment = getattr(female.neopixels, attr)
                self._segments[f"{female.name} {segment.name}"] = segment
        for male in self.hardware.males:
            for attr in ("ring", "up_ring", "o_drive_level", "p_drive_level"):
                segment = getattr(male.neopixels, attr)
                self._segments[f"{male.name} {segment.name}"] = segment

        self._dir_path = result_folder / self.name
        if not self._dir_path.exists():
            self._dir_path.mkdir()

        self._file = None
        self._start_time = None
        self._sequence = None
        self._current = None
        self._step_deadline = None

    @property
    def name(self):
        return "test neopixels"

    def run(self):
        now = datetime.now()
        file_path = (
            self._dir_path
            / f"{now.year}_{now.month:02}_{now.day:02}_{now.hour:02}h_{now.minute:02}min_{now.second:02}s.txt"
        )
        run_with = self._file = file_path.open("a")
        super().run(run_with=run_with)

    def setup(self):
        self._start_time = time()
        self._file.write("seconds, segment, color\n")
        self._sequence = [
            (label, segment, color_name, color)
            for label, segment in self._segments.items()
            for color_name, color in COLORS
        ]
        self._current = None
        self._advance()

    def setdown(self):
        self._start_time = None
        self._current = None
        for segment in self._segments.values():
            segment.off()
        self._file.close()

    def _advance(self):
        if self._current is not None:
            _, segment, _, _ = self._current
            segment.off()

        if not self._sequence:
            self._current = None
            return

        label, segment, color_name, color = self._sequence.pop(0)
        segment.color = color
        segment.on()
        self._current = (label, segment, color_name, color)
        self._step_deadline = time() + self.STEP_DURATION

        timestamp = time() - self._start_time
        self._file.write(f"{timestamp}, {label}, {color_name}\n")

    def loop(self):
        if self._current is None:
            self.stop()
            return
        if time() >= self._step_deadline:
            self._advance()

    @property
    def snapshot_children(self):
        return dict(self._segments)

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        if self._current is not None:
            label, _, color_name, _ = self._current
            states["current"] = {
                "path": path + ("current",),
                "name": "current",
                "value": f"{label}: {color_name} ({len(self._sequence)} left)",
            }
        return states
