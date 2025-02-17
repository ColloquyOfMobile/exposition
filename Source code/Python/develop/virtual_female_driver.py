from colloquy_driver.female_driver import FemaleDriver

class VirtualFemaleDriver(FemaleDriver):
    pass
    # def __init__(self, **kwargs):
        # # print(kwargs)
        # dxl_manager = kwargs["dynamixel manager"]
        # dxl_id = kwargs["dynamixel id"]
        # origin = kwargs["origin"]
        # FemaleMaleDriver.__init__(
            # self,
            # **kwargs,
            # )

        # mirror_kwargs = kwargs.get("mirror")
        # self.mirror = None
        # if mirror_kwargs:
            # mirror_kwargs["dynamixel manager"] = dxl_manager
            # self.mirror = MirrorDriver(**mirror_kwargs)

        # self.speaker = None
        # self.neopixel = None