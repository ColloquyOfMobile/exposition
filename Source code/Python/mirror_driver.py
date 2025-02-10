from shared_driver import SharedDriver

class MirrorDriver(SharedDriver):
    
    def __init__(self, **kwargs):
        SharedDriver.__init__(self, **kwargs)
        self.speaker = None
        self.neopixel = None
    
    def turn_to_down_position(self):        
        self.turn_to_max_position()
    
    def turn_to_up_position(self):
        self.turn_to_min_position()