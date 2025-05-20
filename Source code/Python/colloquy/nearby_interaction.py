from .thread_driver import ThreadDriver

class NearbyInteraction(ThreadDriver):

    def __init__(self, owner, male, female, position):
        ThreadDriver.__init__(self, owner=owner, name=f"interaction {male.name}-{female.name}")
        self._male = male
        self._female = female
        self._position = position

    def __iter__(self):
        yield self.male
        yield self.female

    def __enter__(self):
        self.stop_event.clear()
        self.female.conversation.start()

    def __exit__(self, exc_type, exc_value, traceback_obj):
        if self.female.conversation.is_started:
            self.female.conversation.stop()
        return ThreadDriver.__exit__(self, exc_type, exc_value, traceback_obj)

    @property
    def position(self):
        return self._position

    @property
    def male(self):
        return self._male

    @property
    def female(self):
        return self._female

    def move_to_position_and_wait(self):
        bar = self.colloquy.bar
        position = self.position + bar.dxl_origin
        bar.goal_position = position
        self.female.turn_to_origin_position()
        self.male.turn_to_origin_position()
        self.colloquy.wait_until_everything_is_still()

    def _loop(self):
        pass

    def busy(self):
        return any(
            element.interaction_event.is_set()
            for element
            in self
            )

    def add_html(self):
        pass