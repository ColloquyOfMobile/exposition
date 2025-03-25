from .male_female_driver import FemaleMaleDriver
from .mirror_driver import MirrorDriver
from time import sleep

class FemaleDriver(FemaleMaleDriver):

    def __init__(self, **kwargs):
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


    # def run(self, **kwargs):
        # print(f"Running {self.name}...")
        # try:
            # self._run_setup()
            # self._run_loop()
            # self._run_setdown()
        # except Exception:
            # msg = traceback.format_exc()
            # self.log(msg)
            # self._run_setdown()
            # raise


    def _run_setup(self):
        self.stop_event.clear()
        self.drives.start()
        self.turn_on_neopixel()

    def _run_loop(self):
        while not self.stop_event.is_set():

            if not self.is_moving:
                self.toggle_position()

            if self.interaction_event.is_set():
                self._interact()
            self.sleep_min()

    def _run_setdown(self):
        self.drives.stop()
        self.turn_off_neopixel()


    def _interact(self):
        iterations = 10
        self.turn_to_origin_position()
        self.turn_on_speaker()
        sleep(0.5)
        self.turn_off_speaker()
        for i in range(iterations):
            if self.stop_event.is_set():
                break
            print(f"{self.name} interacting... ({(i+1)/iterations:.0%})")
            sleep(1)
        self.interaction_event.clear()