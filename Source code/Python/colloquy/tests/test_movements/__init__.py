from colloquy.base_thread import BaseThread
from datetime import datetime
from functools import partial
from time import time


class TestMovements(BaseThread):
    """Exercises every movement primitive in the rig - the bar's full
    travel range plus its per-female interaction positions for each male,
    and each male's/female's local sway range - one axis at a time, in a
    fixed sequence, logging position over time so it's easy to confirm
    each one turns the right way, by the right amount, and stops where
    expected. Especially useful for the bar, since its interaction
    positions are the hardest to eyeball correctness for.

    Deliberately does not use the blocking move_and_wait()/wait_for_servo()
    helpers: each step writes its goal position once and this thread polls
    is_moving on its own loop tick instead, so stop()/emergency_stop() can
    interrupt a step within one tick rather than being stuck in an
    uninterruptible busy-wait.

    Also exposes a curated set of one-click jog commands (min/max/origin
    per body, plus the interaction positions) for manual poking from the
    web UI independent of the automated sequence, and the background
    back-and-forth threads (bar/male/female) as real children so they can
    be started/stopped individually while watching the rig.
    """

    STEP_TIMEOUT = 40  # seconds - a body that hasn't settled by then is treated as stuck, not waited on forever. The bar's full travel range alone measured ~25s in simulation, so this must clear that comfortably.
    SETTLE_PAUSE = 1.0  # seconds to sit at each stop so it's visually obvious where it landed
    LOG_INTERVAL = 0.2  # seconds between position log rows while a step is in flight

    def __init__(self, owner, result_folder):
        super().__init__(owner=owner)

        self._bar = self.hardware.bar
        self._males = list(self.hardware.males)
        self._females = list(self.hardware.females)
        all_bodies = [self._bar] + self._males + self._females

        self._jog_commands = {}
        for body in all_bodies:
            self._jog_commands[f"{body.name} to min"] = body.turn_to_min_position
            self._jog_commands[f"{body.name} to max"] = body.turn_to_max_position
            self._jog_commands[f"{body.name} to origin"] = body.turn_to_origin
        for male in self._males:
            for female in self._females:
                label = f"bar: {male.name} in front of {female.name}"
                self._jog_commands[label] = partial(
                    self._bar.set_male_in_front_of_female, male.name, female.name
                )
        self._jog_commands["home all"] = self._home_all

        self._dir_path = result_folder / self.name
        if not self._dir_path.exists():
            self._dir_path.mkdir()

        self._file = None
        self._start_time = None
        self._last_log_time = 0.0
        self._sequence = None
        self._current_step = None
        self._step_deadline = None
        self._pause_until = None

    @property
    def name(self):
        return "test movements"

    def _home_all(self, request=None):
        for body in [self._bar] + self._males + self._females:
            body.turn_to_origin()

    def run(self):
        now = datetime.now()
        file_path = (
            self._dir_path
            / f"{now.year}_{now.month:02}_{now.day:02}_{now.hour:02}h_{now.minute:02}min_{now.second:02}s.csv"
        )
        run_with = self._file = file_path.open("a")
        super().run(run_with=run_with)

    def setup(self):
        self._start_time = time()
        self._last_log_time = 0.0
        self._file.write("seconds, step, body, position\n")
        self._sequence = list(self._build_sequence())
        self._pause_until = None
        self._advance_step()

    def setdown(self):
        self._start_time = None
        self._current_step = None
        self._file.close()

    def _build_sequence(self):
        all_bodies = [self._bar] + self._males + self._females

        yield ("home all", [(body, body.turn_to_origin) for body in all_bodies])

        yield ("bar to min", [(self._bar, self._bar.turn_to_min_position)])
        yield ("bar to max", [(self._bar, self._bar.turn_to_max_position)])
        yield ("bar to origin", [(self._bar, self._bar.turn_to_origin)])

        for male in self._males:
            for female in self._females:
                label = f"bar: {male.name} in front of {female.name}"
                action = partial(
                    self._bar.set_male_in_front_of_female, male.name, female.name
                )
                yield (label, [(self._bar, action)])
        yield ("bar to origin", [(self._bar, self._bar.turn_to_origin)])

        for body in self._males + self._females:
            yield (f"{body.name} to min", [(body, body.turn_to_min_position)])
            yield (f"{body.name} to max", [(body, body.turn_to_max_position)])
            yield (f"{body.name} to origin", [(body, body.turn_to_origin)])

        yield ("home all", [(body, body.turn_to_origin) for body in all_bodies])

    def _advance_step(self):
        if not self._sequence:
            self._current_step = None
            return

        label, bodies = self._sequence.pop(0)
        for body, action in bodies:
            action()
        self._current_step = (label, bodies)
        self._step_deadline = time() + self.STEP_TIMEOUT

    def loop(self):
        if self._pause_until is not None:
            if time() < self._pause_until:
                return
            self._pause_until = None
            self._advance_step()
            return

        if self._current_step is None:
            self.stop()
            return

        label, bodies = self._current_step
        self._log_positions(label, bodies)

        still_moving = [body for body, _ in bodies if body.is_moving]
        if still_moving and time() < self._step_deadline:
            return

        if still_moving:
            names = ", ".join(body.name for body in still_moving)
            self.log(
                f"Step {label!r} timed out after {self.STEP_TIMEOUT}s waiting on: {names}."
            )

        self._pause_until = time() + self.SETTLE_PAUSE

    def _log_positions(self, label, bodies):
        now = time()
        if (now - self._last_log_time) < self.LOG_INTERVAL:
            return
        self._last_log_time = now

        timestamp = now - self._start_time
        for body, _ in bodies:
            position = body.dxl.position.read()
            self._file.write(f"{timestamp}, {label}, {body.name}, {position}\n")

    @property
    def snapshot_children(self):
        children = {}
        children[self._bar.turn_back_and_forth.name] = self._bar.turn_back_and_forth
        children[self._bar.turn_back_and_forth_around_f1.name] = (
            self._bar.turn_back_and_forth_around_f1
        )
        for body in self._males + self._females:
            children[body.turn_back_and_forth.name] = body.turn_back_and_forth
        return children

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        # Plain commands, injected directly (not via snapshot_children) the
        # same way BaseThread injects "start"/"stop": snapshot_children
        # entries get .snapshot_as_child() called on them when this node is
        # opened, which only real Base objects support - a bare function
        # would crash that walk.
        for key, command in self._jog_commands.items():
            states[key] = command

        if self._current_step is not None:
            label, bodies = self._current_step
            still_moving = ", ".join(
                body.name for body, _ in bodies if body.is_moving
            )
            status = f"moving: {still_moving}" if still_moving else "settled"
            states["current step"] = {
                "path": path + ("current step",),
                "name": "current step",
                "value": f"{label} ({status}, {len(self._sequence)} left)",
            }
        return states
