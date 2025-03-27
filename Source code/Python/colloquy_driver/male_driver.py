from .male_female_driver import FemaleMaleDriver
from .thread_driver import ThreadDriver
from time import time, sleep
from threading import Event, Thread
from collections import deque
import traceback

# During search the male blinks.
# The blink pattern define 2 things:
# - the male identity: 1 or 2
# - which kind of interation the male is look for (drive state): "O" or "P" or both
# Extracted from TJ's arduino code "logic35_system.ino, line 87."
LIGHT_PATTERNS = {
    "male1": {
        None:     (1, 1, 0, 0, 1, 1, 0, 0, 0, 1),
        "O":      (1, 1, 0, 0, 0, 0, 0, 1, 1, 1),
        "P":      (1, 1, 0, 0, 0, 0, 1, 1, 1, 0),
        "O or P": (1, 1, 0, 0, 0, 1, 0, 1, 0, 1),
    },
    "male2": {
        None:     (1, 1, 0, 0, 1, 1, 1, 0, 0, 0),
        "O":      (1, 1, 0, 0, 0, 1, 1, 1, 0, 0),
        "I":      (1, 1, 0, 0, 1, 0, 0, 0, 1, 1),
        "O or P": (1, 1, 0, 0, 1, 0, 1, 0, 1, 0),
    }
}


class MaleDriver(FemaleMaleDriver):

    def __init__(self, **kwargs):
        dxl_manager = kwargs["dynamixel manager"]
        FemaleMaleDriver.__init__(
            self,
            **kwargs,
            )
        self.light_patterns = {}
        for k, v in LIGHT_PATTERNS[self.name].items():
            # The deque with max_len will act as circular list
            self.light_patterns[k] = deque(v, maxlen=len(v))

        self._search_thread = None
        self.neopixel.configure(
            red = 0,
            green = 0,
            blue = 0,
            white = 255,
            brightness = 255,)

    def set_neopixel(self, neopixel_on_off):
        if neopixel_on_off:
            self.neopixel.on()
        else:
            self.neopixel.off()

    def _run_setup(self):
        self.stop_event.clear()
        self._search_thread = search = Thread(target=self._search, name=f"{self.name}/search")
        search.start()

    def _run_loop(self):
        search = self._search_thread
        while not self.stop_event.is_set():

            if not self.is_moving:
                self.toggle_position()
            self.sleep_min()

            if self.interaction_event.is_set():
                search.join()
                self._interact()
                search = self._search_thread = Thread(target=self._search, name=f"{self.name}/search")
                search.start()

    def _run_setdown(self):
        self.turn_off_neopixel()
        print(f"Joining thread {self._search_thread.name}...")
        self._search_thread.join()

    def _search(self):
        try:
            light_pattern = self.light_patterns[self.drives.state]

            neopixel_start = time()
            neopixel_on_off = light_pattern.popleft()
            light_pattern.append(neopixel_on_off)
            self.set_neopixel(neopixel_on_off)

            while not self.stop_event.is_set():
                if (time() - neopixel_start) > 0.5:
                    neopixel_on_off = light_pattern.popleft()
                    light_pattern.append(neopixel_on_off)
                    self.set_neopixel(neopixel_on_off)
                    neopixel_start = time()

                if self.interaction_event.is_set():
                    break
                self.sleep_min()
        except Exception:
            msg = traceback.format_exc()
            self.log(msg)
            self.colloquy.stop_event.set()
            raise

    def _interact(self):
        neopixel_state = self._neopixel_memory
        if not neopixel_state:
            self.turn_on_neopixel()

        iterations = 5
        self.turn_to_origin_position()
        for i in range(iterations):
            if self.stop_event.is_set():
                break
            print(f"{self.name} interacting... ({(i+1)/iterations:.0%})")
            sleep(1)
        self.interaction_event.clear()

        self.turn_on_speaker()
        sleep(0.5)
        self.turn_off_speaker()

        if neopixel_state != self._neopixel_memory:
            self.toggle_neopixel()