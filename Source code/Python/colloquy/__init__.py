from pathlib import Path

#
from colloquy.base_thread import BaseThread
from .code_documentation import CodeDocumentation
from .events import Events
from .tests import Tests

from .drivers import Drivers
from .exposition import Exposition
from .params import Params
from .params_browser import ParamsNode
from .repository import Repository
from .ui import tree
from .virtual_drivers import VirtualDrivers
from .logs import Logs


class Colloquy(BaseThread):
    # The whole evening, and the encounters inside it. These four sit
    # here and not on a body because no single thing starts them: they
    # happen when a wandering bar and a turning female line up, so the
    # only thing whose start() brings them about is the piece itself.
    # One of them, an answer in sound, is a scenario for behaviour that
    # is designed and wired and not built - see CODE_DOCUMENTATION 9.
    scenario_names = (
        "switching-on",
        "a-male-calls-a-female",
        "two-males-call-at-once",
        "the-satisfaction-moment",
        "an-answer-in-sound",
    )

    def __init__(self):
        super().__init__(owner=None)

        self._params = Params.load(Path("local/params.json"))
        self._params_view = ParamsNode(owner=self, key="params", params_dict=self._params)

        self._is_opened = False
        self._virtual_drivers = None

        self._drivers = Drivers(owner=self)
        self._tests = Tests(owner=self)
        self._exposition = Exposition(owner=self)
        self._logs = Logs(owner=self)
        self._code_documentation = CodeDocumentation(owner=self)
        self._repository = Repository(owner=self)

        self["drivers"] = self._drivers
        self["params"] = self._params_view
        self["logs"] = self._logs
        self["repository"] = self._repository

        self._events = Events(shutdown=BaseThread._shutdown)

    @property
    def light_patterns(self):
        # During search the male blinks.
        # The blink pattern define 2 things:
        # - the male identity: 1 or 2
        # - which kind of interation the male is look for (drive state): "O" or "P" or both
        # Extracted from TJ's arduino code "logic35_system.ino, line 87."
        #
        # The `tuple()` entry is TJ's com_pattern_I_R / com_pattern_II_R - "R"
        # for reinforcement, a separate message, not "no drive". His firmware
        # neither transmits nor decodes it (in the inert state a male sends no
        # light at all, MALE_setSearchLight()); it is kept here only because
        # which_is_frustated() can still return an empty tuple if both drives
        # are satisfied while a male is blinking. Females must not compare
        # against it - see readable_light_patterns.
        return {
            "male1": {
                tuple(): (1, 1, 0, 0, 1, 1, 0, 0, 0, 1),
                ("O",): (1, 1, 0, 0, 0, 0, 0, 1, 1, 1),
                ("P",): (1, 1, 0, 0, 0, 0, 1, 1, 1, 0),
                ("O", "P"): (1, 1, 0, 0, 0, 1, 0, 1, 0, 1),
            },
            "male2": {
                tuple(): (1, 1, 0, 0, 1, 1, 1, 0, 0, 0),
                ("O",): (1, 1, 0, 0, 0, 1, 1, 1, 0, 0),
                ("P",): (1, 1, 0, 0, 1, 0, 0, 0, 1, 1),
                ("O", "P"): (1, 1, 0, 0, 1, 0, 1, 0, 1, 0),
            },
        }

    @property
    def readable_light_patterns(self):
        """The patterns a female compares her sensor against: the six a male
        can actually send (each male x O, P, both).

        Deliberately narrower than light_patterns, and matching TJ's own
        receiver, which only ever tests those six (sense_light_pattern.ino).
        Including the two "R" entries breaks identity decoding outright:
        male1's R sequence is male2's O sequence rotated, and since the
        matcher tries every rotation the two cannot be told apart - male2
        asking for O then always decodes as male1, whatever the sensor saw.
        """
        return {
            male: {
                drive: pattern for drive, pattern in patterns.items() if drive
            }
            for male, patterns in self.light_patterns.items()
        }

    @property
    def tests(self):
        return self._tests

    @property
    def colloquy(self):
        return self

    @property
    def name(self):
        return "colloquy"

    @property
    def drivers(self):
        return self._drivers

    @property
    def events(self):
        return self._events

    @property
    def params(self):
        return self._params

    @property
    def exposition(self):
        return self._exposition

    @property
    def logs(self):
        return self._logs

    @property
    def repository(self):
        return self._repository

    @property
    def is_started(self):
        return not self.events.shutdown.is_set()

    @property
    def virtual_drivers(self):
        if self._virtual_drivers is None:
            self._virtual_drivers = VirtualDrivers(owner=self)
        return self._virtual_drivers

    def open(self):
        self._is_opened = True

    def close(self):
        # Base's own close, spelled out because this used to raise: the
        # root carries a "close" in every snapshot (Base._snapshot_base_
        # states), the page draws it as the "<" link at the top of /app,
        # and clicking it raised NotImplementedError - which Server2.wsgi
        # takes for a crash and turns into an emergency stop.
        self._is_opened = False

    def run(
        self,
    ):
        return self.server()

    @property
    def snapshot_children(self):
        children = {
            "drivers": self._drivers,
            "exposition": self._exposition,
            "tests": self._tests,
            "params": self._params_view,
            "logs": self._logs,
            # Not gated by is_simulated, unlike the code documentation
            # below. The two computers this repo is worked on from are
            # the installation's laptop and a dev machine, so the one
            # that most needs telling that origin has moved is the one
            # standing in the gallery with a fortnight-old checkout.
            "repository": self._repository,
        }
        if self.is_simulated:
            # Only when there is a simulation to look at - and only then is
            # it built at all, since the property below constructs it on
            # first access.
            children[self.virtual_drivers.name] = self.virtual_drivers

            # Same test, a different reason: this is the source's own
            # documentation, and the machine that runs the exhibition is
            # the one place nobody reads it. Off that machine it is the
            # first thing on the page, which is where it was asked for -
            # it used to be three clicks deep under "tests", filed by
            # where it happened to be written rather than by what it is.
            children[self._code_documentation.name] = self._code_documentation
        return self._with_scenarios(children)

    def get_states(self, *args):
        """What the page is looking at, having first done what it clicked.

        The walk itself is `colloquy/ui/tree.py` and knows nothing about
        this class: it asks nodes for snapshot_children and snapshot().
        Kept as a method here because that is what the server calls, and
        because a root is a perfectly good thing to ask.
        """
        return tree.get_states(self, *args)

    def shutdown_neopixels(self):
        neopixels = self._drivers.neopixels
        assert neopixels
        for neopixel in neopixels:
            neopixel.off()
        # raise NotImplementedError

    def move_to_origin(self):
        self._drivers.bodies.turn_all_bodies_origin()
        self._drivers.bar.turn_to_origin()
        self._drivers.wait_until_everything_is_still()

    def disable_torque(self):
        self._drivers.disable_torque()

    def emergency_stop(self):
        """Immediately halt all motion: no homing, no coordinated move
        (unlike shutdown()'s move_to_origin - commanding more movement is
        the opposite of what an emergency stop should do). Disable torque
        first since that's the actual physical halt, then signal every
        thread to stop.

        Deliberately does not wait/join: once torque is off, a stale
        goal_position no longer converges, so DXL.is_moving can read True
        forever - a thread stuck in wait_for_servo() won't notice torque
        was cut and will keep polling until its own timeout (60s, long
        enough for the bar to cross its full travel). The
        request handling this must return immediately regardless, since
        the single-threaded dev server can't serve anything else (including
        another emergency-stop click) while blocked in a request.
        """
        self._drivers.disable_torque()
        self.shutdown()
