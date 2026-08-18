from time import sleep, time
from .u2d2 import U2D2, U2D2Error
from .arduino import Arduino
from colloquy.base_thread import BaseThread
from .female import Female
from .male import Male
from .bar import Bar
from .commands import Commands
from .test import Test
from .bodies import Bodies
from .all_neopixels import AllNeopixels


class Hardware(BaseThread):
    def __init__(self, owner):

        super().__init__(owner)

        if self.is_simulated:
            self.log("Warning: The hardware is simulated.")

        self._is_opened = False
        self._commands = Commands(owner=self)

        self._arduino = Arduino(owner=self)
        self._u2d2 = U2D2(owner=self)
        self[self.u2d2.name] = self.u2d2

        self._drives = []
        self._males = (
            Male(owner=self, id_number=1),
            Male(owner=self, id_number=2),
        )
        # Where the speakers will go - see SCENARIOS section 9, and the
        # wiring that is already in the box for them.
        self._speakers = []

        self._females = (
            Female(owner=self, id_number=1),
            Female(owner=self, id_number=2),
            Female(owner=self, id_number=3),
        )
        # Declared empty here since long before there was a Mirror class.
        self._mirrors = [female.mirror for female in self._females]
        self._bodies = Bodies(owner=owner, males=self.males, females=self.females)
        self._neopixels = AllNeopixels(owner=self, bodies=self._bodies)

        self._bar = Bar(owner=self)

        self._test = Test(owner=self)

        self[self.arduino.name] = self.arduino
        self.add(self.test)

        self[self.bar.name] = self.bar

        for female in self._females:
            self[female.name] = female
            self.drives.extend(female.drives)

        for male in self.males:
            self[male.name] = male
            self.drives.extend(male.drives)

    @property
    def params(self):
        return self.owner.params

    @property
    def test(self):
        return self._test

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def opened(self):
        return self._opened

    @property
    def bodies(self):
        return self._bodies

    @opened.setter
    def opened(self, value):
        # Value is None only in a Close(), this is to avoid recursion.
        if value is not None:
            if self._opened is not None:
                self._opened.close()

        self._opened = value

    @property
    def drives(self):
        return self._drives

    @property
    def name(self):
        return "hardware"

    @property
    def arduino(self):
        return self._arduino

    @property
    def u2d2(self):
        return self._u2d2

    @property
    def bar(self):
        return self._bar

    @property
    def mirrors(self):
        return self._mirrors

    @property
    def males(self):
        return self._males

    @property
    def male1(self):
        return self._males[0]

    @property
    def male2(self):
        return self._males[1]

    @property
    def speakers(self):
        return self._speakers

    @property
    def females(self):
        return self._females

    @property
    def female1(self):
        return self._females[0]

    @property
    def female2(self):
        return self._females[1]

    @property
    def female3(self):
        return self._females[2]

    @property
    def neopixels(self):
        return self._neopixels

    def wait_until_everything_is_still(self, timeout=30, dxls=None, should_stop=None):
        """Blocking. Bounded the same way DXL.wait_for_servo() bounds a
        single servo: a jammed/unresponsive body must not hang whatever
        called this (graceful shutdown) forever.

        `dxls` narrows the wait to just those servos - a caller that
        commanded three bodies to move together only cares about those
        three, and waiting on the whole bus would never settle while any
        other body is swaying.

        `should_stop` is polled while waiting - pass a thread's own
        `_stop_event.is_set` and pressing stop no longer appears to hang
        for however long the move takes. The bar crossing its full length
        is tens of seconds, which is a long time for a stop button to do
        nothing.

        Returns True once everything asked for is still, False if the
        timeout ran out or the wait was interrupted - either way, a caller
        that positioned bodies on purpose needs to know its positioning
        didn't actually happen."""
        if dxls is None:
            dxls = self._u2d2.dxl_list
        start = time()
        while any(dxl.is_moving for dxl in dxls):
            if should_stop is not None and should_stop():
                self.log("wait_until_everything_is_still interrupted.")
                return False
            if time() - start > timeout:
                self.log(f"wait_until_everything_is_still timed out after {timeout}s.")
                return False
            sleep(0.05)
        return True

    def disable_torque(self):
        """Cut torque on every servo, and keep going if one won't answer.

        This is the "make it safe" step of both shutdown and emergency
        stop, so it must not stop halfway: now that a servo transaction
        raises after its retries rather than returning None, one dead
        servo would otherwise leave the other eight powered."""
        for dxl in self._u2d2.dxl_list:
            try:
                dxl.torque_enabled.write(value=0)
            except U2D2Error as error:
                self.log(f"Could not disable torque on {dxl.name}: {error}")

    def open(self):
        self._is_opened = True

    def close(self):
        self._is_opened = False

    def loop(self):
        pass

    def setup(self):
        for bodies in self.bodies:
            bodies.start(started_by=self)
        self.bar.start(started_by=self)

    def setdown(self):
        for bodies in self.bodies:
            bodies.stop()

    @property
    def snapshot_children(self):
        children = {}
        children["bodies"] = self.bodies
        for body in self.bodies:
            children[body.name] = body
        children[self.bar.name] = self.bar
        return children

