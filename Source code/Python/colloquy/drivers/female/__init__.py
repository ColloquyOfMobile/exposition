from .neopixels import Neopixels  # Head, BodyO, BodyP, Feet
from .drives import Drives
from colloquy.base_thread import BaseThread
from .light_sensor import LightSensor
from ..angle import Angle
from ..microphone import Microphone
from ..speaker import Speaker
from ..angle.conversion import REDUCTIONS
from ..dxl_origin import DXLOrigin
from ..mirror import Mirror
from .search import Search
from ..sing import Sing
from .reinforcement import Reinforcement
from ..turn_back_and_forth import TurnBackAndForth
from .test import Test


class Female(BaseThread):
    # One female from switch-on, everything she does on her own. All
    # three of them read the same one - they differ in where they stand
    # and in when their appetites start climbing, not in behaviour.
    scenario_names = ("female-body",)

    def __init__(
        self,
        owner,
        id_number,
    ):
        self._name = f"female{id_number}"
        self._id_number = id_number
        super().__init__(owner=owner)
        self._position_memory = None

        self._dxl_origin = DXLOrigin(owner=self)
        self._angle = Angle(owner=self, reduction=REDUCTIONS["female"])

        self._light_sensor = LightSensor(owner=self, name="light sensor")
        self._dxl = owner.u2d2.dxls[self.name]
        self._arduino = owner.arduino

        self._mirror = Mirror(owner=self, id_number=id_number)
        self._drives = Drives(owner=self)
        self._search = Search(owner=self)
        self._sing = Sing(owner=self)
        self._reinforcement = Reinforcement(owner=self)
        self.turn_back_and_forth = TurnBackAndForth(owner=self)

        self._neopixels = Neopixels(owner=self)
        # Her voice and her ear. Nothing drives either yet - see
        # CODE_DOCUMENTATION section 9 - but the hardware under them is
        # real, and a body that owns a speaker can be given a Sing thread
        # in one place instead of five.
        self._speaker = Speaker(owner=self)
        self._microphone = Microphone(owner=self)
        self._test = Test(owner=self)

        self[self.neopixels.name] = self.neopixels
        self[self.drives.name] = self.drives
        self[self.test.name] = self.test
        self[self.search.name] = self.search
        self[self.reinforcement.name] = self.reinforcement
        self[self.dxl_origin.name] = self.dxl_origin
        self[self.angle.name] = self.angle
        self["set current position as dxl origin"] = (
            self.set_current_position_as_dxl_origin
        )
        self[self.light_sensor.name] = self.light_sensor
        self[self.mirror.name] = self.mirror
        self[self.speaker.name] = self.speaker
        self[self.microphone.name] = self.microphone

    @property
    def params(self):
        return self.owner.params

    @property
    def dxl_origin(self):
        return self._dxl_origin

    @property
    def dxl(self):
        return self._dxl

    @property
    def test(self):
        return self._test

    @property
    def search(self):
        return self._search

    @property
    def reinforcement(self):
        return self._reinforcement

    @property
    def sing(self):
        return self._sing

    @property
    def speaker(self):
        return self._speaker

    @property
    def microphone(self):
        return self._microphone

    @property
    def drives(self):
        return self._drives

    @property
    def id_number(self):
        return self._id_number

    @property
    def female(self):
        return self

    @property
    def arduino(self):
        return self._arduino

    @property
    def name(self):
        return self._name

    @property
    def neopixels(self):
        return self._neopixels

    @property
    def is_moving(self):
        return self.dxl.is_moving

    @property
    def light_sensor(self):
        return self._light_sensor

    @property
    def mirror(self):
        """Hers, on its own servo. Nothing drives it yet - see Mirror."""
        return self._mirror

    @property
    def angle(self):
        """Where she is pointing, in degrees from her origin."""
        return self._angle

    @property
    def sweep(self):
        """How far she swings, end to end, in degrees.

        Read from params on every use rather than held, so a range edited
        on the page takes effect on her next sway instead of at the next
        restart. Her 58.594 degrees is what the 2000 servo units she used
        to be given work out to through her 1:3 reduction - the same
        reduction, and so the same sway, as a male."""
        return self.params[self.name]["motion range"]

    @property
    def goal_position(self):
        return self.dxl.goal_position

    @property
    def torque_enabled(self):
        return self.dxl.torque_enabled

    @property
    def read_pattern(self):
        return self.search.read_pattern

    def set_current_position_as_dxl_origin(self, request=None):
        self.dxl_origin.set(self.dxl.position.read())

    def is_satisfied(self):
        """Is she inert - wanting nothing, and so not searching?

        Both appetites, not either. This is TJ's `internal_drive_state ==
        1 [Neither/Inert]`, which `updateInternalDriveState()`
        (internal.ino) reaches only when *both* drives are below the
        interested floor: `(internal_drive_LL > internal_drive_O) &&
        (internal_drive_LL > internal_drive_P)`.

        It said `or` until 2026-08-25, which made a body with one
        appetite full and one empty count as satisfied - so it would not
        search, while `which_is_frustated()` (the same five rules as TJ's,
        one place over) said it wanted the full one and a male in that
        state would blink asking for it. A body advertising a want it had
        decided not to act on.

        Expressed through `which_is_frustated()` rather than spelled out
        again, so the two cannot drift apart a second time: an empty
        tuple *is* the inert state.
        """
        return not self.drives.which_is_frustated()

    def turn_to(self, degrees):
        self.angle.turn_to(degrees)

    def turn_to_max_position(self):
        self.angle.turn_to(self.sweep / 2)
        self._position_memory = "max"

    def turn_to_min_position(self):
        self.angle.turn_to(-self.sweep / 2)
        self._position_memory = "min"

    def toggle_position(self):
        if self._position_memory is None:
            self.turn_to_max_position()
            return

        if self._position_memory == "max":
            self.turn_to_min_position()
            return

        if self._position_memory == "min":
            self.turn_to_max_position()
            return

    def turn_to_origin(self):
        self.angle.turn_to_origin()

    @property
    def is_in_satisfaction_moment(self):
        """Is this body standing in the one moment it has what it wanted?

        Read by its own `Drive`s, which stop climbing while it is true -
        see drive/__init__.py. Guarded on `is_started` as well, because
        `Reinforcement` keeps the flag after the thread has ended and a
        body would otherwise never be hungry again.
        """
        reinforcement = self.reinforcement
        return reinforcement.is_started and reinforcement.is_satisfied_moment

    @property
    def reinforcement_decrement(self):
        """How much one round takes off the appetite this body shares."""
        return self.params["reinforcement decrement"][self.name]

    def loop(self):
        """Her whole life, one tick at a time: get hungry, look, answer.

        Only ever starts one thing, and only when nothing else is running -
        the search and the reinforcement that may follow it own the body
        while they last.
        """
        if self.search.is_started or self.reinforcement.is_started:
            return

        partner = self.search.take_partner()
        if partner is not None:
            # Her search ended because she recognised a male asking for
            # something she wants. Hand the pair over.
            self.reinforcement.partner = partner
            self.reinforcement.start(started_by=self)
            return

        if not self.is_satisfied():
            self.search.start(started_by=self)

    def setup(self):
        self.dxl.init_hardware()
        self.drives.start(started_by=self)

    def setdown(self):
        self.drives.stop()
        self.search.stop()
        self.reinforcement.stop()

    @property
    def snapshot_children(self):
        children = {}
        children["angle"] = self.angle
        children["dxl origin"] = self.dxl_origin
        children[self.dxl.name] = self.dxl
        children["search"] = self.search
        children["reinforcement"] = self.reinforcement
        children["drives"] = self.drives
        children["neopixels"] = self.neopixels
        children["light sensor"] = self.light_sensor
        children[self.mirror.name] = self.mirror
        # Beside the light sensor rather than beside the neopixels, since
        # the pairing that matters is what a body can say and what it can
        # hear - and in this piece those are two channels each.
        children["speaker"] = self.speaker
        children["microphone"] = self.microphone
        return self._with_scenarios(children)

