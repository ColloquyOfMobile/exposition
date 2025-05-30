from colloquy.moving_part import MovingPart
from .search import Search

class Mirror(MovingPart):

    def __init__(self, owner, **kwargs):
        MovingPart.__init__(self, owner, **kwargs)
        self._search = Search(owner=self)
        self._memory = {
            "male1": {
                "O": self.turn_to_up_position,
                "P": self.turn_to_down_position,
            },
            "male2": {
                "O": self.turn_to_up_position,
                "P": self.turn_to_down_position,
            },
        }

    def __enter__(self):
        assert self.dxl_origin is not None, "Calibrate colloquy."
        self.stop_event.clear()


    def __exit__(self, exc_type, exc_value, traceback_obj):
        self.turn_to_origin_position()
        self._search.stop()
        return MovingPart.__exit__(self, exc_type, exc_value, traceback_obj)

    @property
    def is_up(self):
        if self.is_moving:
            return False
        self.log(f"{self.dxl.goal=}")
        self.log(f"{self.dxl_origin - self.motion_range/2=}")
        if self.dxl.goal_position == self.dxl_origin - self.motion_range/2:
            return True
        return False

    @property
    def is_down(self):
        if self.is_moving:
            return False
        self.log(f"{self.dxl.goal=}")
        self.log(f"{self.dxl_origin - self.motion_range/2=}")
        if self.dxl.goal_position == self.dxl_origin - self.motion_range/2:
            return True
        return False

    @property
    def listen_for_confirmation(self):
        return self.owner.listen_for_confirmation

    def turn_to_down_position(self):
        self.turn_to_max_position()

    def turn_to_up_position(self):
        self.turn_to_min_position()

    def memorise_drive(self):
        raise NotImplementedError()

    def _define_position(self):
        male = self.colloquy.interaction.male
        target_drive = self.colloquy.interaction.target_drive
        if len(target_drive) == 1:
            self._move_to_target_position = self._memory[male.name][target_drive[0]]
        elif len(target_drive)==2:
            raise NotImplementedError(f"{target_drive=}")
        else:
            raise NotImplementedError(f"{target_drive=}")

    def _loop(self):
        pass

    def _setup(self):
        self._define_position()
        if self._move_to_target_position is None:
            self._search.start()
            return
        print(f"The {self.name} is moving to target position...")
        self._move_to_target_position()

    def _set_origin(self, origin):
        origin = int(origin[0])
        self.dxl_origin = origin
        self.colloquy.params[self.owner.name][self.name[:-1]]["origin"] = origin
        self.colloquy.save()

    def _add_html_start(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("div"):
            with tag("label", **{"for": f"{self.name}/interacting_with"}):
                text(f"Interacting with:")

            with tag("select", name="male", id=f"{self.name}/interacting_with"):
                with tag("option", value="male1"):
                    text(f"male1")
                with tag("option", value="male2"):
                    text(f"male2")

        with tag("div"):
            with tag("label", **{"for": f"{self.name}/fem_o_drive"}):
                text(f"Fem O drive:")

            with tag("input", type="number", id=f"{self.name}/fem_o_drive", name="fem_o_drive", value=0):
                pass

        with tag("div"):
            with tag("label", **{"for": f"{self.name}/fem_p_drive"}):
                text(f"Fem P drive:")

            with tag("input", type="number", id=f"{self.name}/fem_p_drive", name="fem_p_drive", value=0):
                pass

        with tag("button", name="action", value=f"{self.name}/start"):
            text(f"Start.")
        self.colloquy.actions[f"{self.name}/start"] = self.start

    # def stop(self, **kwargs):
        # raise NotImplementedError
        # if self._is_started:
            # self.stop_event.set()
            # return
        # for element in self.elements:
            # element.stop()