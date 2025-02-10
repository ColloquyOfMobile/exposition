from male_female_driver import FemaleMaleDriver

class MaleDriver(FemaleMaleDriver):
    
    def __init__(self, **kwargs):
        dxl_manager = kwargs["dynamixel manager"]
        FemaleMaleDriver.__init__(
            self, 
            **kwargs,
            # dxl_manager, 
            # dxl_id = kwargs["dynamixel id"], 
            # dxl_origin = kwargs["origin"]
            )
        self.speaker = None
        self.neopixel = None