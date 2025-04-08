from .shared_driver import SharedDriver

class MirrorDriver(SharedDriver):

    def __init__(self, owner, **kwargs):
        SharedDriver.__init__(self, owner, **kwargs)

    def turn_to_down_position(self):
        self.turn_to_max_position()

    def turn_to_up_position(self):
        self.turn_to_min_position()

    def run(self):
        raise NotImplementedError

    def open(self):
        pass

    def _run_setup(self):
        self.stop_event.clear()

    def _run_loop(self):
        while not self.stop_event.is_set():
            if not self.is_moving:
                self.owner.drive()
                self.toggle_position()
            self.sleep_min()

    def _run_setdown(self):
        pass