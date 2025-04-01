from .body import Body
from .mirror_driver import MirrorDriver
from .neopixel_driver import NeopixelDriver
from threading import Lock
from time import sleep

class FemaleDriver(Body):

    def __init__(self, **kwargs):
        # self._lock = Lock()
        Body.__init__(
            self,
            **kwargs,
            )
        dxl_manager = kwargs["dynamixel manager"]
        dxl_id = kwargs["dynamixel id"]
        origin = kwargs["origin"]

        self.neopixel = NeopixelDriver(owner=self, arduino_manager=self.arduino_manager)

        mirror_kwargs = kwargs.get("mirror")
        self.mirror = None
        if mirror_kwargs:
            mirror_kwargs["dynamixel manager"] = dxl_manager
            self.mirror = MirrorDriver(**mirror_kwargs)

        # self._light_colors = {
            # "O": white,
            # "P": orange,
            # None: white,
            # "O or P": white,
        # }

    def _run_setup(self):
        self.stop_event.clear()
        self.drives.start()
        self.neopixel.on()
        self._update_neopixel()

    def _run_loop(self):
        while not self.stop_event.is_set():
            self._update_neopixel()
            if not self.is_moving:
                self.toggle_position()

            if self.interaction_event.is_set():
                self._interact()
            self.sleep_min()

    def _update_neopixel(self):
        state, brightness, color = self.drives.value
        # color = self._light_colors[state]
        config = dict(
            brightness = brightness,
            **color,
            )
        self.neopixel.configure(**config)

    def _run_setdown(self):
        self.drives.stop()
        self.neopixel.off()

    def _interact(self):
        iterations = 2
        self.turn_to_origin_position()
        self.turn_on_speaker()
        sleep(0.5)
        self.turn_off_speaker()
        for i in range(iterations):
            if self.stop_event.is_set():
                break

            self._update_neopixel()
            sleep(1)
            
            self.drives.o_drive = self.drives.o_drive / 2
            self.drives.p_drive = self.drives.p_drive / 2
        
        self.drives.satisfy()
        
        self.interaction_event.clear()
        print(f"{self.name} finished interaction.")