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
            states[key] = {
                "path": path + (key,),
                "name": key,
                "value": description,
            }
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
            states[body] = {
                "path": path + (body,),
                "name": body,
                "value": f"position {position}, goal {goal}, torque {torque}{moving}",
            }
        return states
