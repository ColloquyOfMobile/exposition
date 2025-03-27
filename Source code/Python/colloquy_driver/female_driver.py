from .male_female_driver import FemaleMaleDriver
from .mirror_driver import MirrorDriver
from threading import Lock
from time import sleep

class FemaleDriver(FemaleMaleDriver):

    def __init__(self, **kwargs):
        self._lock = Lock()
        dxl_manager = kwargs["dynamixel manager"]
        dxl_id = kwargs["dynamixel id"]
        origin = kwargs["origin"]
        FemaleMaleDriver.__init__(
            self,
            **kwargs,
            )

        mirror_kwargs = kwargs.get("mirror")
        self.mirror = None
        if mirror_kwargs:
            mirror_kwargs["dynamixel manager"] = dxl_manager
            self.mirror = MirrorDriver(**mirror_kwargs)

        orange = dict(red=255, green=165, blue=0, white=0)
        white = dict(red=0, green=0, blue=0, white=255)
        self._light_colors = {
            "O": white,
            "P": orange,
            None: white,
            "O or P": white,
        }

    def _run_setup(self):
        self.stop_event.clear()
        self.drives.start()
        self.neopixel.on()

    def _run_loop(self):
        while not self.stop_event.is_set():
            self._update_neopixel()
            if not self.is_moving:
                self.toggle_position()

            if self.interaction_event.is_set():
                self._interact()
            self.sleep_min()

    def _update_neopixel(self):
        state, brightness = self.drives.value
        color = self._light_colors[state]
        config = dict(
            brightness = brightness,
            **color,
            )
        self.neopixel.configure(**config)

    def _run_setdown(self):
        self.drives.stop()
        self.neopixel.off()

    def _interact(self):
        iterations = 5
        self.turn_to_origin_position()
        self.turn_on_speaker()
        sleep(0.5)
        self.turn_off_speaker()
        for i in range(iterations):
            if self.stop_event.is_set():
                break
            print(f"{self.name} interacting... ({(i+1)/iterations:.0%})")
            self._update_neopixel()
            sleep(1)
        self.interaction_event.clear()