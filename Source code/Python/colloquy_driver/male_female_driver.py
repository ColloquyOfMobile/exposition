from .shared_driver import SharedDriver
from .neopixel_driver import NeopixelDriver
from .speaker_driver import SpeakerDriver
from .drives_handler import DrivesHandler
from pathlib import Path
from threading import Event
from threading import Timer
import traceback




class FemaleMaleDriver(SharedDriver):

    def __init__(self, **kwargs):
        dxl_manager = kwargs["dynamixel manager"]
        SharedDriver.__init__(self, **kwargs)
        self.colloquy = kwargs["colloquy"]
        self.arduino_manager = kwargs["arduino manager"]
        self._neopixel_memory = None
        self._speaker_memory = None
        self.interaction_event = Event()
        self.drives = DrivesHandler()

        self.neopixel = NeopixelDriver(owner=self, arduino_manager=self.arduino_manager)
        self.speaker = SpeakerDriver(owner=self, arduino_manager=self.arduino_manager)


    def run(self, **kwargs):
        print(f"Running {self.name}...")
        try:
            self._run_setup()
            self._run_loop()
            self._run_setdown()
        except Exception:
            msg = traceback.format_exc()
            self.log(msg)
            self.colloquy.stop_event.set()
            self._run_setdown()
            raise


    def _run_setup(self):
        raise NotImplementedError("""Possible implementation:
self.stop_event.clear()
self.drives.start()
self.turn_on_neopixel()""")

    def _run_loop(self):
        raise NotImplementedError("""Possible implementation:
while not self.stop_event.is_set():

    if not self.is_moving:
        self.toggle_position()

    if self.interaction_event.is_set():
        self._interact()
    self.sleep_min()""")

    def _run_setdown(self):
        raise NotImplementedError("""Possible implementation:
self.drives.stop()
self.turn_off_neopixel()""")

    @property
    def drive_state(self):
        raise NotImplementedError
        return "O or P"

    @property
    def neopixel_state(self):
        raise NotImplementedError
        return self._neopixel_memory

    @property
    def speaker_state(self):
        return self._speaker_memory

    def turn_to_left_position(self):
        self.turn_to_max_position()

    def turn_to_right_position(self):
        self.turn_to_min_position()

    def turn_on_speaker(self):
        self.speaker.on()

    def turn_off_speaker(self):
        self.speaker.off()

    def toggle_speaker(self):
        self.speaker.toggle()

    def toggle_neopixel(self):
        self.neopixel.toggle()

    # def set_neopixel(self, neopixel_on_off):
        # raise NotImplementedError
        # self.neopixel.set(neopixel_on_off)

    def turn_on_neopixel(self):
        self.neopixel.on()

    def turn_off_neopixel(self):
        self.neopixel.off()