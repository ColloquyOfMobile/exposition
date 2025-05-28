from colloquy.thread_element import ThreadElement
from time import time, sleep

class Conversation(ThreadElement):

    def __init__(self, owner):
        ThreadElement.__init__(self, owner=owner, name=f"conversation")
        # self._watch_out_for_beam = WatchOutForBeam(owner=self)
        self._timeout_start = None
        self._timeout = 4 # seconds

    def __enter__(self):
        print(f"The {self.owner.name} is engaging...")
        self.stop_event.clear()

    def _watch_out_for_beam(self):
        print(f"Watching out for the beam...")
        self._timeout_start = time()
        timeout = self._timeout
        while not self.stop_event.is_set():
            if self.owner.sensor.beamed():
                self.owner.mirror.start()
                return

            if time() - self._timeout_start > timeout:
                print(f"The male doesn't beam...")
                self.stop_event.set()
                self.colloquy.bar.interaction.stop()
                self.owner.search.start()
            self._sleep_min()

    def _listen_for_encouragement(self):
        print(f"Listening out for encouragement...")
        self._timeout_start = time()
        timeout = self._timeout
        target_drive = self.colloquy.interaction.target_drive
        while not self.stop_event.is_set():
            if time() - self._timeout_start > timeout:
                print(f"The male doesn't encourage...")
                self.stop_event.set()
                self.colloquy.bar.interaction.stop()
                self.owner.drives.start()

            if self.owner.microphone.is_encouraged:
                self.owner.drives.decrease(drive=target_drive)
                self._timeout_start = time()

            if not self.owner.drives.is_satisfied(drive=target_drive):
                sleep(1)
                continue

            self.stop_event.set()
            self._climax()
            self.colloquy.bar.interaction.stop()
            self.owner.drives.start()

    def _climax(self):
        print(f"Climax {self.owner.name}...")
        start = time()
        neopixel = self.owner.neopixel
        orange = self.owner.drives.orange
        puce = self.owner.drives.puce
        neopixel.on()
        while time()-start < 6:
            neopixel.configure(brightness=255, **orange)
            self.owner.speaker.off()
            sleep(0.2)
            neopixel.configure(brightness=255, **puce)
            self.owner.speaker.on()
            sleep(0.2)
        neopixel.off()
        self.owner.speaker.off()

    def _listen(self):
        return self.colloquy.interaction.male.is_encouraging

    def _loop(self):
        self._listen_for_encouragement()

    def _setup(self, **kwargs):
        self.owner.turn_to_origin_position()
        self.owner.notify_male()
        self._watch_out_for_beam()


class WatchOutForBeam(ThreadElement):

    def __init__(self, owner):
        ThreadElement.__init__(self, owner=owner, name=f"watch out for beam")
        self._timeout_start = None
        self.timeout = 4 # seconds

    def __enter__(self):
        print(f"The {self.owner.owner.name} is waiting for beam...")
        self.stop_event.clear()
        self._timeout_start = time()

    def __exit__(self, exc_type, exc_value, traceback_obj):
        return ThreadElement.__exit__(self, exc_type, exc_value, traceback_obj)

    def _loop(self):
        if self.sense():
            self.stop_event.set()
            self.owner.owner.mirror.start()
            return

        if time() - self._timeout_start > self.timeout:
            print(f"The male doesn't respond...")
            self.stop_event.set()
            self.colloquy.bar.interaction.stop()
            self.owner.owner.search.start()

    def sense(self):
        return self.colloquy.interaction.male.is_beaming