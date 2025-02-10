"""Code to Test mecanically the colloquy of Mobiles.
WARNINGS:
- This code is NOT Robust and wasn't designed to be used in exisibition.

TODO:
- Implement a proper error handling.
- Plot interactively the temperature and the current.
"""


import datetime
from dxl_driver_through_ocm import DXLDriverThroughOCM, DXLDriverThroughOCMForBar
import time
from pathlib import Path
import matplotlib.pyplot as plt
import pandas as pd


# Set hier how long the test should take.
TEST_DURATION = datetime.timedelta(hours=0, minutes=5)

# Set these value with trial and error once thank to the mecanical_calibration.py file.
FEMALE1_ORIGIN = 3000
FEMALE2_ORIGIN = 1500
FEMALE3_ORIGIN = 2200
MALE1_ORIGIN = 1300
MALE2_ORIGIN = 2900
BAR_ORIGIN = 3500

# Look in windows device manager.
FEMALE1_COM = "COM15" # Set to None if not plugged
FEMALE2_COM = "COM16" # Set to None if not plugged
FEMALE3_COM = "COM17" # Set to None if not plugged
MALE1_COM = "COM19" # Set to None if not plugged
MALE2_COM = "COM20" # Set to None if not plugged
BAR_COM = "COM21" # Set to None if not plugged



class FemaleMaleDriver:
    """Female and Male driver.

    This object implements the functionnalities to drive a male or female body (not the mirror).

    For calibration:
    - self.move_and_wait
    - self.position

    For test run:
    - self.init
    - self.prepare_for_test_cycle
    - self.move_pos1
    - self.move_pos2
    """

    def __init__(self, dxl_driver, origin):
        """Initialise the instance.

        Parameters:
            dxl_driver: A DXLDriverThroughOCM instance.
            origin: an int indicating the origin position. (Define by trial and error during calibration)

        Attributes define here:
            moving_threshold: Use define if the servo reached his goal.
            __isfrozen: Use to tell __setattr__ that the instance shouldn't be modified.
        """
        self._isfrozen = False
        self.dxl_driver = dxl_driver
        self.origin = origin
        # Use to know if the servo has stopped moving.
        self.moving_threshold = 20
        self._isfrozen = True

    def __setattr__(self, key, value):
        """Use to forbid the creation of new attribute once self._isfrosen = True."""
        if key == "_isfrozen":
            object.__setattr__(self, key, value)
            return
        if self._isfrozen and not hasattr(self, key):
            raise TypeError( "%r is a frozen class" % self )
        object.__setattr__(self, key, value)

    def init(self):
        """Initialise the body's position."""
        self.dxl_driver.torque_enabled = 0
        # Set velocity base profile.
        self.dxl_driver.drive_mode = 0

        # set velocity and acceleration profile.
        self.dxl_driver.profile_velocity = 40
        self.dxl_driver.profile_acceleration = 1

        # Enable torque.
        self.dxl_driver.torque_enabled = 1
        # Move motor to pos1.
        self.move_pos1()

    def prepare_for_test_cycle(self):
        """Prepare the body before a test run.

        To use after self.init() and before run()"""
        self.dxl_driver.torque_enabled = 0
        # Set time base profile.
        self.dxl_driver.drive_mode = 4

        # set velocity and acceleration profile.
        self.dxl_driver.profile_velocity = 5000 #=> 5s to move
        self.dxl_driver.profile_acceleration = 2500 #=> 2.5s to accelerate
        # Enable torque.
        self.dxl_driver.torque_enabled = 1
        # raise NotImplementedError("Reset the drive mode and profile here")

    @property
    def is_moving(self):
        """Tell if the body is still moving."""
        return abs(self.dxl_driver.position-self.dxl_driver.goal_position) > self.moving_threshold

    @property
    def position(self):
        """Get at which position the is."""
        return self.dxl_driver.position

    def wait_for_servo(self):
        """Blocking funtion that waits until the body has reached his goal position."""
        start = time.time()
        while True:
            if not self.is_moving:
                break
            assert time.time() - start < 30, "Moving male or female shouldn't take more than 30s!"


            timelap = time.time() - start

    def move_and_wait(self, position):
        """Blocking function that sets the body's goal position and wait for it to move."""
        # torque should be disabled to set the drive_mode
        self.dxl_driver.torque_enabled = 0
        drive_mode = self.dxl_driver.drive_mode
        profile_velocity = self.dxl_driver.profile_velocity
        profile_acceleration = self.dxl_driver.profile_acceleration

        self.dxl_driver.drive_mode = 0
        self.dxl_driver.profile_velocity = 40
        self.dxl_driver.profile_acceleration = 1
        self.dxl_driver.torque_enabled = 1
        try:
            # print(self.dxl_driver.drive_mode)
            self.dxl_driver.goal_position = position
            self.wait_for_servo()
        finally:
            self.dxl_driver.torque_enabled = 0
            self.dxl_driver.drive_mode = drive_mode
            self.dxl_driver.profile_velocity = profile_velocity
            self.dxl_driver.profile_acceleration = profile_acceleration

    def move_pos1(self):
        """Set body's goal position1. Not blocking!"""
        self.dxl_driver.goal_position = self.origin + 2000/2

    def move_pos2(self):
        """Set body's goal position2. Not blocking!"""
        self.dxl_driver.goal_position = self.origin - 2000/2


class BarDriver:

    def __init__(self, dxl_driver, origin):
        """Initialise the instance.

        Parameters:
            dxl_driver: A DXLDriverThroughOCM instance.
            origin: an int indicating the origin position. (Define by trial and error during calibration)

        Attributes define here:
            moving_threshold: Use define if the servo reached his goal.
            __isfrozen: Use to tell __setattr__ that the instance shouldn't be modified.
        """
        self._isfrozen = False
        self.dxl_driver = dxl_driver
        self.origin = origin
        # Use to know if the servo has stopped moving.
        self.moving_threshold = 20
        self._isfrozen = True

    def __setattr__(self, key, value):
        """Use to forbid the creation of new attribute once self._isfrosen = True."""
        if key == "_isfrozen":
            object.__setattr__(self, key, value)
            return
        if self._isfrozen and not hasattr(self, key):
            raise TypeError( "%r is a frozen class" % self )
        object.__setattr__(self, key, value)


    def init(self):
        """Initialise the body's position."""
        self.dxl_driver.torque_enabled = 0
        # Set velocity base profile.
        self.dxl_driver.drive_mode = 0

        # set velocity and acceleration profile.
        self.dxl_driver.profile_velocity = 16
        self.dxl_driver.profile_acceleration = 1

        # Enable torque.
        self.dxl_driver.torque_enabled = 1
        # Move motor to origin.
        self.dxl_driver.goal_position = self.origin

    def prepare_for_test_cycle(self):    
        """Prepare the body before a test run.

        To use after self.init() and before run()"""
        self.dxl_driver.torque_enabled = 0
        # Set time base profile.
        # WARNINGS: Time base profile make calculation easier 
        self.dxl_driver.drive_mode = 4

        # set velocity and acceleration profile.
        self.dxl_driver.profile_velocity = 21000 #=> 21s to move
        self.dxl_driver.profile_acceleration = 3500 #=> 3.5s to accelerate
        # Enable torque.
        self.dxl_driver.torque_enabled = 1

    @property
    def is_moving(self):
        """Tell if the body is still moving."""
        return abs(self.dxl_driver.position-self.dxl_driver.goal_position) > self.moving_threshold

    @property
    def position(self):
        """Get at which position the is."""
        return self.dxl_driver.position

    def wait_for_servo(self):
        """Blocking funtion that waits until the body has reached his goal position."""
        start = time.time()
        while True:
            if not self.is_moving:
                print(f"Goal achieved in {time.time() - start:.1f}s.")
                break
            assert time.time() - start < 30, "Moving male or female shouldn't take more than 30s!"




    def move_and_wait(self, position):
        """Blocking function that sets the body's goal position and wait for it to move."""
        # torque should be disabled to set the drive_mode
        self.dxl_driver.torque_enabled = 0
        drive_mode = self.dxl_driver.drive_mode
        profile_velocity = self.dxl_driver.profile_velocity
        profile_acceleration = self.dxl_driver.profile_acceleration

        self.dxl_driver.drive_mode = 0
        print(self.dxl_driver.drive_mode)
        self.dxl_driver.profile_velocity = 30
        print(self.dxl_driver.profile_velocity)
        self.dxl_driver.profile_acceleration = 1
        print(self.dxl_driver.profile_acceleration)
        self.dxl_driver.torque_enabled = 1
        try:
            # print(self.dxl_driver.drive_mode)
            self.dxl_driver.goal_position = position
            self.wait_for_servo()
        finally:
            self.dxl_driver.torque_enabled = 0
            self.dxl_driver.drive_mode = drive_mode
            self.dxl_driver.profile_velocity = profile_velocity
            self.dxl_driver.profile_acceleration = profile_acceleration


    def move_pos1(self):
        """Set body's goal position1. Not blocking!"""
        self.dxl_driver.goal_position = self.origin

    def move_pos2(self):
        """Set body's goal position2. Not blocking!"""
        self.dxl_driver.goal_position = self.origin + 11000

class ColloquyMecanicalTest:
    def __init__(self):
        """Initialise the instance.

        Attributes define here:
            data_path: file path where to store the Colloquy's data.
            _start: Hold the test start timestamp.
            female1, female2, female3, male1, male2: FemaleMaleDriver instance.
            bar: BarDriver instance.
            _time_duration: Test duration in seconds.
            
        """
        # Handle hardware for serial communication.
        self.data_path = Path("meca_test_data.csv")
        self.data_path.write_text(
                "time,"
                "female1.position,"
                "female1.temperature,"
                "female1.elec_current,"
                "female2.position,"
                "female2.temperature,"
                "female2.elec_current,"
                "female3.position,"
                "female3.temperature,"
                "female3.elec_current,"
                "male1.position,"
                "male1.temperature,"
                "male1.elec_current,"
                "male2.position,"
                "male2.temperature,"
                "male2.elec_current,"
                "bar.position,"
                "bar.temperature,"
                "bar.elec_current\n"
            )
        self._start = None
        self.female1 = FemaleMaleDriver(
            dxl_driver=DXLDriverThroughOCM(
                dynamixel_id=1,
                com_port=FEMALE1_COM,
                ),
            origin = FEMALE1_ORIGIN,
        )
        self.female2 = FemaleMaleDriver(
            dxl_driver=DXLDriverThroughOCM(
                dynamixel_id=1,
                com_port=FEMALE2_COM,
                ),
            origin = FEMALE2_ORIGIN,
        )
        self.female3 = FemaleMaleDriver(
            dxl_driver=DXLDriverThroughOCM(
                dynamixel_id=1,
                com_port=FEMALE3_COM,
                ),
            origin = FEMALE3_ORIGIN,
        )

        self.mirror1 = None
        self.mirror2 = None
        self.mirror3 = None

        self.male1 = FemaleMaleDriver(
            dxl_driver=DXLDriverThroughOCM(
                dynamixel_id=1,
                com_port=MALE1_COM,
                ),
            origin = MALE1_ORIGIN,
        )
        self.male2 = FemaleMaleDriver(
            dxl_driver=DXLDriverThroughOCM(
                dynamixel_id=1,
                com_port=MALE2_COM,
                ),
            origin = MALE2_ORIGIN,
        )

        self.bar = BarDriver(
            DXLDriverThroughOCMForBar(
                dynamixel_id1=1,
                dynamixel_id2=2,
                com_port=BAR_COM,
            ),
            origin = BAR_ORIGIN,
        )
        self._time_duration = TEST_DURATION.total_seconds()

    @property
    def time_left(self):
        """Tell if there is some time left to continue run the test."""
        return time.time() - self._start < self._time_duration

    def run(self):
        """Run the test.
        
        Define here the step of the test."""
        self._start = time.time()
        now = datetime.datetime.now()
        print(f"Test start: {now}")
        print(f"Test duration: {TEST_DURATION}")
        print(f"Test end expected: {now + TEST_DURATION}")

        # Init Colloquy position
        self.init()

        print(f"Running cycles...")
        while(self.time_left):
            self.iterate()

        self.plot_as_svg()

    def iterate(self):
        """Iterate the instruction define here until the time is over."""
        # Init Start cycle
        self.bar.move_pos2()
        self.move_females_and_males_pos2()
        self.gather_data_for(5.25)
        self.move_females_and_males_pos1()
        self.gather_data_for(5.25)
        self.move_females_and_males_pos2()
        self.gather_data_for(5.25)
        self.move_females_and_males_pos1()
        self.gather_data_for(5.25)
        time.sleep(0.25) # Wait 0.25 second before before moving the bar again

        # Go back
        self.bar.move_pos1()
        self.move_females_and_males_pos2()
        self.gather_data_for(5.25)
        self.move_females_and_males_pos1()
        self.gather_data_for(5.25)
        self.move_females_and_males_pos2()
        self.gather_data_for(5.25)
        self.move_females_and_males_pos1()
        self.gather_data_for(5.25)
        time.sleep(0.25) # Wait 0.25 second before before moving the bar again

    def gather_data_for(self, timelap):
        """Blocking function that gather data from the servo and save it into self.data_path.
        
        Parameters:
            timelap: gather data during timelap before saving and returning."""
        data = []
        female1_dxl = self.female1.dxl_driver
        female2_dxl = self.female1.dxl_driver
        female3_dxl = self.female1.dxl_driver
        male1_dxl = self.female1.dxl_driver
        male2_dxl = self.female1.dxl_driver
        bar_dxl = self.female1.dxl_driver

        start = time.time()
        while True:
            data.append(
                (
                    time.time()-self._start,

                    female1_dxl.position,
                    female1_dxl.temperature,
                    female1_dxl.elec_current,

                    female2_dxl.position,
                    female2_dxl.temperature,
                    female2_dxl.elec_current,

                    female3_dxl.position,
                    female3_dxl.temperature,
                    female3_dxl.elec_current,

                    male1_dxl.position,
                    male1_dxl.temperature,
                    male1_dxl.elec_current,

                    male2_dxl.position,
                    male2_dxl.temperature,
                    male2_dxl.elec_current,

                    bar_dxl.position,
                    bar_dxl.temperature,
                    bar_dxl.elec_current,
                )
            )
            if time.time() - start > timelap:
                break

        with self.data_path.open("a") as file:
            for line in data:
                line = ",".join(str(e) for e in line)
                line = f"{line}\n"
                file.write(line)



    def move_females_and_males_pos1(self):
        """Move all the females and male to position1. Not blocking!"""
        self.female1.move_pos1()
        self.female2.move_pos1()
        self.female3.move_pos1()
        self.male1.move_pos1()
        self.male2.move_pos1()

    def move_females_and_males_pos2(self):
        """Move all the females and male to position2. Not blocking!"""
        self.female1.move_pos2()
        self.female2.move_pos2()
        self.female3.move_pos2()
        self.male1.move_pos2()
        self.male2.move_pos2()



    def init(self):
        """Initialise the Colloquy of Mobiles's positions."""
        print(f"Initialising...")
        self.female1.init()
        self.female2.init()
        self.female3.init()
        self.male1.init()
        self.male2.init()
        self.bar.init()

        while True:
            are_still = [
            not self.female1.is_moving,
            not self.female2.is_moving,
            not self.female3.is_moving,
            not self.male1.is_moving,
            not self.male2.is_moving,
            not self.bar.is_moving,
            ]
            start = time.time()
            if all(are_still):
                break

        # Set time base profile.
        self.female1.prepare_for_test_cycle()
        self.female2.prepare_for_test_cycle()
        self.female3.prepare_for_test_cycle()
        self.male1.prepare_for_test_cycle()
        self.male2.prepare_for_test_cycle()
        self.bar.prepare_for_test_cycle()

    def plot_as_svg(self):
        """Plat the current and temperature in a svg file (mecanical_test.svg)."""
        print(f"Saving plot as svg...")
        data = pd.read_csv(self.data_path)
        data['female1.elec_current'] = data['female1.elec_current'].abs()*2.69
        data['female2.elec_current'] = data['female1.elec_current'].abs()*2.69
        data['female3.elec_current'] = data['female1.elec_current'].abs()*2.69
        data['male1.elec_current'] = data['female1.elec_current'].abs()*2.69
        data['male2.elec_current'] = data['female1.elec_current'].abs()*2.69
        data['bar.elec_current'] = data['female1.elec_current'].abs()*2.69


        group_size = len(data) // 100

        data = data.groupby(data.index // group_size).mean()

        x = data["time"] - data["time"][0]
        fig, axes = plt.subplots(6, 1, layout="constrained", figsize=(10, 22))

        fig.suptitle(f'Long duration colloquy mecanical test (Duration: {TEST_DURATION}).')
        for i, title in enumerate(["female1", "female2", "female3", "male1", "male2", "bar"]):
            axe = axes[i]
            axe.set_title(title)
            axe.set_xlabel('time (s)')
            axe.set_ylabel("temperature (°C)")
            axe.set_ylim(0, 60)
            axe.plot(x, data[f"{title}.temperature"], color="red")
            axe = axe.twinx()
            axe.set_ylabel("elec current (mA)")
            axe.set_ylim(0, data[f"{title}.elec_current"].max() + 100)
            axe.plot(x, data[f"{title}.elec_current"], color='blue')

        # plt.tight_layout()
        fig.savefig("mecanical_test.svg")


if __name__ == "__main__":
    ColloquyMecanicalTest().run()