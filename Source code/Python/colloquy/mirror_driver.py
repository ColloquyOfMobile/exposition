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
        self.stop_event.clear()

    def _loop(self):
        male = self.colloquy.nearby_interaction.male
        female = self.owner
        target_drive = self.owner.target_drive

        iterations = 5
        for i in range(iterations):
            self.toggle_position()
            if self.stop_event.is_set():
                break

            print(f"Toggle position for {self.dxl.dxl_id=}...")
            print(f"Toggle position for {self.name=}...")
            while self.is_moving:
                print(f"Toggle position for {self.dxl.position=}...")
                if self.stop_event.is_set():
                    break
                self._sleep_min()

            female.drives.decrease(target_drive)
            male.drives.decrease(target_drive)


        self.stop_event.set()
        # raise NotImplementedError(f"Start the mirror thread.")