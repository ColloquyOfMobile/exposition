from .male_female_driver import FemaleMaleDriver
from .mirror_driver import MirrorDriver
from time import sleep

class FemaleDriver(FemaleMaleDriver):

    def __init__(self, **kwargs):
        # print(kwargs)
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



    def run(self, **kwargs):
        print(f"Running {self.name}...")
        self.stop_event.clear()

        self.turn_on_neopixel()

        while not self.stop_event.is_set():
            if not self.is_moving:
                self.toggle_position()

            if self.interaction_event.is_set():
                self._interact()
            sleep(0.01)

        self.turn_off_neopixel()

    def _interact(self):
        iterations = 20
        for i in range(iterations):
            if self.stop_event.is_set():
                break
            print(f"{self.name} interacting... ({(i+1)/iterations:.0%})")
            sleep(1)
        self.interaction_event.clear()