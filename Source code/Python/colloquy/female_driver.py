from .body import Body
from .mirror_driver import MirrorDriver
from .neopixel_driver import NeopixelDriver
from threading import Lock
from time import sleep

class FemaleDriver(Body):

    def __init__(self, owner, **kwargs):
        # self._lock = Lock()
        Body.__init__(
            self,
            owner,
            **kwargs,
            )
        dxl_manager = kwargs["dynamixel manager"]
        dxl_id = kwargs["dynamixel id"]
        origin = kwargs["origin"]

        self.neopixel = NeopixelDriver(owner=self, name="neopixel")

        mirror_kwargs = kwargs.get("mirror")
        self.mirror = None
        if mirror_kwargs:
            mirror_kwargs["dynamixel manager"] = dxl_manager
            self.mirror = MirrorDriver(owner=self, **mirror_kwargs)
        self._target_drive = None

    @property
    def target_drive(self):
        return self._target_drive

    def __enter__(self):
        assert self.dxl_origin is not None, "Calibrate colloquy."
        self.stop_event.clear()
        self.drives.start()
        self.neopixel.on()
        self._update_neopixel()

    def _loop(self):
        self._update_neopixel()
        if not self.is_moving:
            self.toggle_position()

        if self.interaction_event.is_set():
            self._interact()
        # self.sleep_min()

    def _update_neopixel(self):
        state, brightness, color = self.drives.value
        # color = self._light_colors[state]
        config = dict(
            brightness = brightness,
            **color,
            )
        self.neopixel.configure(**config)

    def stop(self):
        self.drives.stop()
        self.neopixel.off()
        Body.stop(self)

    def _interact(self):
        nearby_interaction = self.colloquy.nearby_interaction
        assert nearby_interaction.female is self, f"{nearby_interaction.female.name=},{self.name=}"
        male = self.colloquy.nearby_interaction.male
        print(f"{self.drives.state=}, {male.drives.state=}")
        for state in self.drives.state:
            if state in male.drives.state:
                self._target_drive = state
                male.interaction_event.set()
                self.turn_to_origin_position()
                male.turn_to_origin_position()
                self.turn_on_speaker()
                sleep(0.5)
                self.turn_off_speaker()
                self.drives.stop()
                if self.drives.thread is not None:
                    self.drives.thread.join()
                while self.is_moving or male.is_moving:
                    if self.stop_event.is_set():
                        break
                    self._sleep_min()
                break
        else:
            self.interaction_event.clear()
            return

        self.mirror.start()
        while self.mirror.thread.is_alive():
            self._sleep_min()

        self.drives.start()
        self.interaction_event.clear()
        male.interaction_event.clear()
        print(f"{self.name} finished interaction.")

    def open(self):
        Body.open(self)
        self.neopixel.open()
        self.mirror.open()