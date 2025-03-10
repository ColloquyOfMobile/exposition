from .male_female_driver import FemaleMaleDriver
from time import time, sleep
from threading import Event

# From TJ's arduino code "logic35_system.ino, line 87." 
# const bool com_pattern_I_O[com_pattern_count] = {1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1};
# const bool com_pattern_I_P[com_pattern_count] = {1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0};
# const bool com_pattern_I_OP[com_pattern_count] = {1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1};
# const bool com_pattern_II_O[com_pattern_count] = {1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0};
# const bool com_pattern_II_P[com_pattern_count] = {1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1};
# const bool com_pattern_II_OP[com_pattern_count] = {1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0};
# const bool com_pattern_I_R[com_pattern_count] = {1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1};
# const bool com_pattern_II_R[com_pattern_count] = {1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0};
# const bool com_pattern_E[com_pattern_count] = {1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1};
# const bool com_pattern_rejection[com_pattern_count] = {1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0};

class MaleDriver(FemaleMaleDriver):

    def __init__(self, **kwargs):
        dxl_manager = kwargs["dynamixel manager"]
        FemaleMaleDriver.__init__(
            self,
            **kwargs,
            )
        self._blink_profile = [
            #on
            12,
            #off
            21,
            #on
            22,
            #off
            22.5,
            #on
            23.5,
            #off
            24,
            #on
            25,
            #off
            25.5,
            #on
            56.5,
            #off
            59
            ]

    def run(self, **kwargs):
        print(f"Running {self.name}...")
        self.stop_event.clear()
        blink_profile = list(self._blink_profile)

        neopixel_start = time()
        timestamp = blink_profile.pop(0)

        self.turn_on_neopixel()

        while not self.stop_event.is_set():
            if (time() - neopixel_start) > timestamp:
                self.toggle_neopixel()
                if not blink_profile:
                    blink_profile.extend(self._blink_profile)
                    neopixel_start = time()

                timestamp = blink_profile.pop(0)
                # neopixel_start = time()

            if not self.is_moving:
                self.toggle_position()
            self.sleep_min()

            if self.interaction_event.is_set():
                self._interact()

        self.turn_off_neopixel()

    def _interact(self):
        neopixel_state = self._neopixel_memory
        if not neopixel_state:
            self.turn_on_neopixel()
            
        iterations = 10
        self.turn_to_origin_position()
        for i in range(iterations):
            if self.stop_event.is_set():
                break
            print(f"{self.name} interacting... ({(i+1)/iterations:.0%})")
            sleep(1)
        self.interaction_event.clear()
        
        self.turn_on_speaker()
        sleep(0.5)
        self.turn_off_speaker()
        
        if neopixel_state != self._neopixel_memory:
            self.toggle_neopixel()