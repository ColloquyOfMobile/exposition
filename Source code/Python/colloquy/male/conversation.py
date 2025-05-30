from colloquy.thread_element import ThreadElement
from time import time, sleep

class Conversation(ThreadElement):

    def __init__(self, owner):
        ThreadElement.__init__(self, owner=owner, name=f"conversation")
        self._timeout_start = None
        self._timeout = 10 # seconds
        #self._watch_out_for_reflection = WatchOutForReflection(owner=self)

    def __enter__(self):
        print(f"The {self.owner.name} is engaging...")
        self.stop_event.clear()

    def __exit__(self, exc_type, exc_value, traceback_obj):
        if self.owner.beam.is_started:
            self.owner.beam.stop()
        return ThreadElement.__exit__(self, exc_type, exc_value, traceback_obj)

    def _loop(self):
        self._watch_out_for_engagement()

    def _setup(self):
        self.owner.drives.stop()
        self.owner.turn_to_origin_position()
        self.owner.beam.start()
        self.colloquy.bar.search.stop()
        self.colloquy.turn_to_interaction_position()

    def _watch_out_for_engagement(self):
        print(f"Watching out for encouragement...")
        self._timeout_start = time()
        timeout = self._timeout
        target_drive = self.colloquy.interaction.target_drive
        while not self.stop_event.is_set():

            if time() - self._timeout_start > timeout:
                print(f"The female doesn't engage...")
                self.stop_event.set()
                self.colloquy.bar.interaction.stop()
                self.owner.drives.start()
                continue

            for drive in target_drive:
                sensor = self.owner.light_sensors[drive]
                if sensor.engaged:
                    self.owner.drives.decrease(drive=(drive,))
                    self._timeout_start = time()

            if not self.owner.drives.is_satisfied(drive=target_drive):
                # sleep(0.5)
                self.owner.speaker.encourage()
                sleep(4)
                continue

            self.stop_event.set()
            self._climax()
            self.colloquy.bar.interaction.stop()
            self.owner.drives.start()

    def _climax(self):
        print(f"Climax {self.owner.name}...")
        start = time()
        while time()-start < 6:
            self.owner.body_neopixel.ring.on()
            self.owner.speaker.off()
            sleep(0.2)
            self.owner.body_neopixel.ring.off()
            self.owner.speaker.on()
            sleep(0.2)
        self.owner.body_neopixel.ring.off()
        self.owner.speaker.off()






class WatchOutForReflection(ThreadElement):

    def __init__(self, owner):
        ThreadElement.__init__(self, owner=owner, name=f"watch out for reflection")
        self._timeout_start = None
        self.timeout = 4 # seconds

    def __enter__(self):
        print(f"The {self.owner.owner.name} is waiting for reflection...")
        self.stop_event.clear()
        self._timeout_start = time()

    def _loop(self):
        if self.sense():
            self.stop_event.set()

        if time() - self._timeout_start > self.timeout:
            print(f"The male doesn't respond...")
            self.stop_event.set()
            self.colloquy.bar.interaction.stop()
            self.owner.owner.search.start()