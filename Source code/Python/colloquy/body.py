from .shared_driver import SharedDriver
from .speaker_driver import SpeakerDriver
from .drives_handler import DrivesHandler
from pathlib import Path
from threading import Event
from threading import Timer
import traceback


class Body(SharedDriver):

    def __init__(self, owner, **kwargs):
        dxl_manager = kwargs["dynamixel manager"]
        SharedDriver.__init__(self, owner, **kwargs)
        self.arduino_manager = kwargs["arduino manager"]
        self.interaction_event = Event()
        self.drives = DrivesHandler(owner=self)
        self.speaker = SpeakerDriver(owner=self, arduino_manager=self.arduino_manager)

    def open(self):
        SharedDriver.open(self)

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

    def _set_origin(self, origin):
        origin = int(origin[0])
        self.dxl_origin = origin
        self.colloquy.params[self.name]["origin"] = origin
        self.colloquy.save()

    # def add_html(self):
        # doc, tag, text = self.html_doc.tagtext()
        # with tag("h3"):
            # text(f"{self.name.title()}:")

        # with tag("form", method="post"):
            # with tag("label", **{"id": f"{self.name}/origin"}):
                # text(f"Origin:")
                # kwargs = {}
                # if self.dxl_origin is not None:
                    # kwargs = {"value": self.dxl_origin}

            # with tag("input", type="number", id=f"{self.name}/origin", name="origin", **kwargs):
                # pass

            # with tag("button", name="action", value=f"{self.name}/origin/set"):
                # text(f"set.")

            # self.colloquy.actions[f"{self.name}/origin/set"] = self._set_origin