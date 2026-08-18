"""Web-UI view of the simulated hardware.

The simulator has always held the whole picture - every pixel's colour as
the arduino received it, every servo's position - and never showed any of
it, so the only way to know what the virtual installation was doing was to
read a log or attach a debugger. That gap has cost real time: a run where
the read-pattern test's readout LEDs were being sent plain black looked
identical, on screen, to one where they lit up, and the bug was only found
in a hardware log days later. The simulated state said so all along.

Values are read at render time and nothing here is editable: this is a
window onto the simulation, not another way to drive it.
"""
from colloquy.base import Base

from .dxl_ids import BODY_DXL_IDS
from .virtual_serial_port import REALISTIC_LATENCY
from colloquy.ui import leaves


def _pixel_description(pixel):
    """One pixel group, as the arduino was last told to light it."""
    channels = " ".join(f"{key}{pixel[key]}" for key in ("r", "g", "b", "w"))
    if not any(pixel[key] for key in ("r", "g", "b", "w")):
        # Worth calling out rather than leaving as four zeros to read: a
        # segment commanded to black is indistinguishable from one never
        # commanded at all, and "lit, but at brightness 0" is a mistake
        # this codebase has actually shipped.
        return f"{channels} - dark"
    return channels


class BodyStateNode(Base):
    """One body's simulated pixels and sensors, all shown at once.

    Everything is rendered as plain value leaves in _snapshot_if_opened
    rather than as openable children: there are only a handful of entries
    per body, and the point is to take in a body's whole state at a glance
    instead of clicking into it segment by segment.
    """

    def __init__(self, owner, body_name):
        self._body_name = body_name
        super().__init__(owner=owner)

    @property
    def name(self):
        return self._body_name

    @property
    def snapshot_children(self):
        return {}

    @property
    def _states(self):
        return self.owner.states[self._body_name]

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        for key, value in self._states.items():
            if isinstance(value, dict) and "r" in value:
                description = _pixel_description(value)
            elif isinstance(value, dict):
                # A male's four light sensors, keyed a/b/c/d.
                description = ", ".join(f"{k}: {v}" for k, v in value.items())
            else:
                description = value
            states[key] = leaves.value(path, key, description)
        return states


class FaultsNode(Base):
    """Make the simulated servo bus fail, on purpose.

    U2D2.handle_error() retries every servo transaction five times and then
    raises; none of that had ever run, because the simulated bus always
    succeeded. Turning faults on here exercises the retry loop, the two
    error-reporting calls that used to raise NotImplementedError, and what
    a body does when the bus finally gives up - without unplugging
    anything.

    Rates are per transaction, and there are a lot of transactions: every
    is_moving check reads two registers. 1 in 100 is already a bus in poor
    shape; 1 in 2 is for watching a body fail on purpose.
    """

    _PRESETS = {
        "no faults": (0.0, 0.0),
        "1 in 100 comm errors": (0.01, 0.0),
        "1 in 10 comm errors": (0.1, 0.0),
        "1 in 2 comm errors": (0.5, 0.0),
        "1 in 10 servo errors": (0.0, 0.1),
    }

    @property
    def name(self):
        return "faults"

    @property
    def snapshot_children(self):
        return {}

    @property
    def _packet_handler(self):
        return self.owner.u2d2_packet_handler

    def _make_preset(self, comm, servo):
        def preset(request=None):
            self._packet_handler.set_error_rates(comm=comm, servo=servo)

        return preset

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        handler = self._packet_handler

        for label, (comm, servo) in self._PRESETS.items():
            states[label] = self._make_preset(comm, servo)

        for key, value in (
            ("comm error rate", handler.comm_error_rate),
            ("servo error rate", handler.servo_error_rate),
            ("faults injected", handler.fault_count),
        ):
            states[key] = leaves.value(path, key, value)
        return states


class TimingNode(Base):
    """How fast the simulation pretends to be.

    Both knobs matter for what this codebase actually measures. Servo
    speed decides how long a body faces another, and so how much of a
    blink pattern a female can see. Arduino latency decides how many
    sensor samples she gets per pattern step - ReadPattern bins by wall
    clock, so replying instantly hands her 2-3x more samples than the rig
    ever will.
    """

    _LATENCY_PRESETS = {
        "instant replies (unrealistic)": 0.0,
        "realistic replies (15ms)": REALISTIC_LATENCY,
        "slow replies (50ms)": 0.05,
    }

    @property
    def name(self):
        return "timing"

    @property
    def snapshot_children(self):
        return {}

    def _make_preset(self, latency):
        def preset(request=None):
            self.owner.arduino_serial_port.latency = latency

        return preset

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)

        for label, latency in self._LATENCY_PRESETS.items():
            states[label] = self._make_preset(latency)

        leaf = leaves.into(states, path)

        leaf(
            "arduino round trip",
            f"{self.owner.arduino_serial_port.latency * 1000:.0f}ms",
        )

        # Speed is per servo, but every body is configured identically by
        # DXL.init_hardware(), so one line plus the travel each body has to
        # cover says more than nine identical rows.
        speed = self.owner.dxls[BODY_DXL_IDS["bar"]].speed
        leaf("servo speed", f"{speed:.0f} units/s")
        if speed:
            leaf("body sweep (2000 units)", f"{2000 / speed:.1f}s")
            leaf("bar full travel (10000 units)", f"{10000 / speed:.1f}s")
        return states


class ServosNode(Base):
    """Every simulated dynamixel, by body name rather than by id."""

    @property
    def name(self):
        return "servos"

    @property
    def snapshot_children(self):
        return {}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        dxls = self.owner.dxls
        for body, dxl_id in BODY_DXL_IDS.items():
            dxl = dxls[dxl_id]
            position = dxl.get("position")
            goal = dxl.get("goal position")
            torque = "on" if dxl.get("torque enabled") else "off"
            moving = "" if position == goal else f", moving ({goal - position:+})"
            states[body] = leaves.value(
                path,
                body,
                f"position {position}, goal {goal}, torque {torque}{moving}",
            )
        return states
