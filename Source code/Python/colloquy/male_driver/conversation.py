from colloquy.thread_driver import ThreadDriver
from time import time, sleep

class Conversation(ThreadDriver):

    def __init__(self, owner):
        ThreadDriver.__init__(self, owner=owner, name=f"conversation")
        self._watch_out_for_reflection = WatchOutForReflection(owner=self)

    def __enter__(self):
        print(f"The {self.owner.name} is engaging...")
        self.stop_event.clear()
        self.owner.turn_to_origin_position()
        self.owner.beam.start()
        self.colloquy.bar.search.stop()
        self.colloquy.bar.turn_to_interaction_position() # Implement a proper method here.
        self._watch_out_for_reflection.start()

    def __exit__(self, exc_type, exc_value, traceback_obj):
        if self.owner.beam.is_started:
            self.owner.beam.stop()
        return ThreadDriver.__exit__(self, exc_type, exc_value, traceback_obj)

    def _loop(self):
        pass

class WatchOutForReflection(ThreadDriver):

    def __init__(self, owner):
        ThreadDriver.__init__(self, owner=owner, name=f"watch out for reflection")
        self._timeout_start = None
        self.timeout = 4 # seconds

    def __enter__(self):
        print(f"The {self.owner.owner.name} is waiting for beam...")
        self.stop_event.clear()
        self._timeout_start = time()

    def enter(self):
        print(f"The {self.owner.owner.name} is waiting for reflection...")
        self.stop_event.clear()
        self._timeout_start = time()

    def _loop(self):
        if self.sense():
            self.stop_event.set()

        if time() - self._timeout_start > self.timeout:
            print(f"The male doesn't respond...")
            self.stop_event.set()
            self.colloquy.bar.nearby_interaction.stop()
            self.owner.owner.search.start()

    def sense(self):
        return self.colloquy.nearby_interaction.male.is_beaming