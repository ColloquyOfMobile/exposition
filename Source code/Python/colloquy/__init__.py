from contextlib import contextmanager
from pathlib import Path
from threading import Lock

#
from colloquy.base_thread import BaseThread
from .code_documentation import CodeDocumentation
from .events import Events
from .tests import Tests

from .drivers import Drivers
from .exposition import Exposition
from .hardware import Hardware
from .params import Params
from .params_browser import ParamsNode
from .repository import Repository
from .ui import tree
from .virtual_drivers import VirtualDrivers
from .logs import Logs

# How long /shutdown waits for a command already in flight before homing
# the piece anyway. See Colloquy.hold_commands.
COMMAND_WAIT = 10.0

# How long the orderly shutdown waits for everything to reach its origin.
# A full bar crossing is about 32s at the profile velocity every servo is
# initialised with, so 30 - the previous default - was under the worst
# case rather than over it. See Colloquy.move_to_origin.
HOMING_TIMEOUT = 90.0


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

        # One command at a time, now that the server runs several
        # requests at once. See get_states() for why this has to exist
        # and why it deliberately does not cover the whole request.
        self._command_lock = Lock()

        self._drivers = Drivers(owner=self)
        self._tests = Tests(owner=self)
        self._exposition = Exposition(owner=self)
        self._logs = Logs(owner=self)
        self._hardware = Hardware(owner=self)
        self._code_documentation = CodeDocumentation(owner=self)
        self._repository = Repository(owner=self)

        self["drivers"] = self._drivers
        self["params"] = self._params_view
        self["logs"] = self._logs
        self["hardware"] = self._hardware
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
    def hardware(self):
        return self._hardware

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


    @property
    def snapshot_children(self):
        children = {
            "drivers": self._drivers,
            "exposition": self._exposition,
            "tests": self._tests,
            "params": self._params_view,
            "logs": self._logs,
            # The physical installation, as opposed to the layer that
            # drives it - see colloquy/hardware/. Not gated by
            # is_simulated: the machine with the boards actually in it is
            # the one place this is not hypothetical.
            "hardware": self._hardware,
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

        One at a time, and that lock is load-bearing. Until the server
        grew threads it served strictly serially, which meant nothing
        here could ever run twice at once - an accidental lock around the
        whole application that plenty of this tree quietly relies on. A
        walk both renders and *calls* (tree.get_states runs the command
        the path names, between two snapshots), so two overlapping page
        requests would mean two commands interleaving: bodies driven to
        two different goals, a snapshot read halfway through the command
        changing it. The bus locks under `u2d2` and `arduino` keep single
        transactions safe; they say nothing about a command as a whole.

        So threading buys concurrency exactly where it was wanted and
        nowhere else. Everything that does not go through the tree -
        /emergency-stop, /shutdown, /restart, and every static asset (see
        wsgi2._parse) - is answered without ever reaching this lock, and
        that is the whole point of the exercise: the emergency stop stays
        clickable while a command is busy.
        """
        with self._command_lock:
            return tree.get_states(self, *args)

    @contextmanager
    def hold_commands(self, timeout=COMMAND_WAIT):
        """Wait for the command in flight to finish, then keep the tree to
        yourself for the duration of the block.

        For /shutdown, which homes every body and cuts torque. That used
        to be safe by accident: the server answered one request at a
        time, so a command and the shutdown sequence could not overlap.
        Threaded they can, and the two of them are the worst possible
        pair to interleave - one driving a body somewhere while the other
        drives all of them home and powers them down.

        Bounded, and it proceeds anyway when the wait runs out. A command
        can legitimately sit for a minute (`wait_for_servo`'s own timeout
        is 60s, long enough for the bar to cross its full travel), and a
        shutdown that could be held off indefinitely by a stuck command
        would be worse than one that overlaps it. `held` says which
        happened, so the caller can tell the reader.

        Not used by /emergency-stop, deliberately: that one waits for
        nothing at all, which is the entire difference between the two.
        """
        held = self._command_lock.acquire(timeout=timeout)
        try:
            yield held
        finally:
            if held:
                self._command_lock.release()

    @property
    def servos_were_opened(self):
        """Did this run ever set up the servo bus?

        Asked of the *port name* rather than of `is_open`, and the
        difference matters: `U2D2.__enter__`/`__exit__` open and close the
        port around a transaction that finds it closed, so `is_open`
        flickers during normal running and a shutdown that consulted it
        could decide, on a perfectly healthy installation, that there were
        no servos to bring home.

        The name is set once, by `main.py`'s `open_the_hardware()`, and
        never cleared - and `open_the_hardware()` is skipped entirely when
        the main PCB is noted as unmounted. So an empty name means exactly
        "the links were never opened this run", which is the question.
        """
        return bool(self._drivers.u2d2.port_name)

    def shutdown_neopixels(self):
        """Every light off, and never raising.

        The try is here for the same reason as `silence_speakers`' and it
        was missing: with the main PCB out, or the Arduino simply not
        answering, this raised inside `power_down` before a single body
        had been sent home - and inside `emergency_stop` before a single
        thread had been signalled. Failing to turn a light off must never
        be the thing that stops an installation being stopped.
        """
        try:
            neopixels = self._drivers.neopixels
            assert neopixels
            for neopixel in neopixels:
                neopixel.off()
        except Exception as error:  # noqa: BLE001 - see the docstring
            self.log(f"Could not turn the lights off: {error}")

    def silence_speakers(self):
        """Every tone off, in one command, and never raising.

        Beside the lights rather than folded into them, because they fail
        differently: a strip left lit is visible from the door, and a body
        left humming at 160 Hz in an empty gallery is not something
        anybody notices until the morning. One command, so a link that is
        about to be closed does not have to survive five.

        Swallowing the failure is the point of the try. This is called
        from `emergency_stop`, which cuts torque and *then* signals every
        thread to stop - so anything that raises in between leaves the
        threads running, which is the one outcome an emergency stop must
        not have. A dead Arduino link is exactly when that would happen,
        and a dead link is also a link that is not making any sound.
        """
        try:
            self._drivers.audio.silence()
        except Exception as error:  # noqa: BLE001 - see the docstring
            self.log(f"Could not silence the speakers: {error}")

    def move_to_origin(self):
        """Send every body and the bar home, and say whether they got there.

        This is what protects the calibration across a power cut. Every
        servo runs in extended position mode, where the turn count lives
        in volatile memory: the bar's travel is 293 degrees of bar, which
        is 2.4 turns of its servo, so a bar powered down at the far end
        comes back believing it is somewhere else entirely. Homing first
        leaves it within one turn of its own zero, where a power cycle
        costs nothing.

        The wait used to be the default 30s and its answer was thrown
        away. At `profile_velocity` 20 - 4.58 rev/min at the servo,
        a third of that at the bar - a full crossing takes about 32
        seconds, so the one case where homing matters most (the bar at
        the far end) was also the case most likely to time out, and
        torque was then cut mid-travel without a word. Hence a timeout
        with room in it, and a returned answer that the caller is
        expected to pass on.
        """
        if not self.servos_were_opened:
            # Nothing to bring home, which is not the same as having
            # failed to bring it home - and the difference is the whole
            # meaning of the answer. Returning False here would print the
            # warning about a bar that has lost its turn count, about a
            # bar that was never powered this run.
            self.log(
                "The servo bus was never opened this run, so nothing was "
                "homed. Its calibration is exactly as the last run left it."
            )
            return True

        self._drivers.bodies.turn_all_bodies_origin()
        self._drivers.bar.turn_to_origin()
        return self._drivers.wait_until_everything_is_still(timeout=HOMING_TIMEOUT)

    def power_down(self):
        """The orderly stop, in the order that keeps the calibration.

        Threads first (nothing else should be commanding a body), then
        the lights, then home, and only then torque off - cutting torque
        before the move would leave every body wherever it happened to
        be. Returns whether everything actually got home.

        Shared by /shutdown and by "unmount the main PCB", which is the
        same sequence with a note written first.
        """
        self.shutdown()
        self.join_all()
        self.shutdown_neopixels()
        self.silence_speakers()
        arrived = self.move_to_origin()
        self.disable_torque()
        if not arrived:
            self.log(
                "WARNING: not everything reached its origin before torque was "
                "cut. A servo powered down away from its origin loses its turn "
                "count - check the bar's position before trusting it."
            )
        return arrived

    def disable_torque(self):
        """Cut torque on every servo, if there is a bus to cut it over.

        `Drivers.disable_torque` already keeps going past a servo that
        will not answer, so the bus being absent would be survived - but
        it would be survived nine times, once per servo, each with the
        same paragraph in the log. One fact deserves one line.
        """
        if not self.servos_were_opened:
            self.log("The servo bus was never opened this run - no torque to cut.")
            return
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
        # try/finally, and it is the whole point of this method. Torque
        # off is the physical halt and goes first; signalling the threads
        # is what stops anything commanding a body again. Before this,
        # anything raising in the first left every thread running with no
        # UI left to stop them - which is precisely the outcome the
        # caller (Server2.wsgi, treating any crash as an emergency stop)
        # is reaching for this method to avoid. It arrived as an
        # AssertionError out of U2D2.open on an installation whose main
        # PCB was noted as unmounted.
        try:
            self.disable_torque()
            self.silence_speakers()
        finally:
            self.shutdown()
