from .shared_driver import SharedDriver

class MirrorDriver(SharedDriver):

    def __init__(self, owner, **kwargs):
        SharedDriver.__init__(self, owner, **kwargs)

    def turn_to_down_position(self):
        self.turn_to_max_position()

    def turn_to_up_position(self):
        self.turn_to_min_position()

    def open(self):
        pass

    def __enter__(self):
        assert self.dxl_origin is not None, "Calibrate colloquy."
        self.stop_event.clear()

    def _loop(self):
        male = self.colloquy.nearby_interaction.male
        female = self.owner
        target_drive = self.owner.target_drive

        iterations = 5
        for i in range(iterations):
            if self.stop_event.is_set():
                break
            print(f"Toggle position for {self.name=}...")
            self.toggle_position()

            # print(f"Toggle position for {self.dxl.dxl_id=}...")
            while self.is_moving:
                print(f"{self.position=}")
                dxl = self.colloquy._dxl_manager._dxls[self.dxl.dxl_id]
                print(f"[{dxl._lim_min}, {dxl._lim_max}]")
                if self.stop_event.is_set():
                    break
                self._sleep_min()

            female.drives.decrease(target_drive)
            male.drives.decrease(target_drive)


        self.stop_event.set()
        # raise NotImplementedError(f"Start the mirror thread.")

    def _setup(self, male, fem_o_drive, fem_p_drive, **kwargs):
        male_name = male[0]
        fem_o_drive, fem_p_drive = int(fem_o_drive[0]), int(fem_p_drive[0])

        for interaction in self.colloquy.nearby_interactions.values():
            if interaction.male.name == male_name:
                if interaction.female.name == self.owner.name:
                    self.colloquy.bar.nearby_interaction = interaction
                    break
        self.owner.drives.o_drive = fem_o_drive
        self.owner.drives.p_drive = fem_p_drive

        self.owner._target_drive = self.owner.drives.state

        if kwargs:
            raise NotImplementedError(f"for {self.name}, ({kwargs=})!")

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