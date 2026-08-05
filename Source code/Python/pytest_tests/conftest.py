"""Shared fixtures/doubles for the pure-logic unit test suite.

Rules for every test in this suite:
- Never call .start()/.start_command()/.stop_command() on a BaseThread.
- Never construct real U2D2/Arduino/VirtualHardware/DXL objects, and never
  construct the real Colloquy/Hardware/Female/Male object graph:
  Colloquy() does filesystem I/O at construction (Params.load() reads
  local/params.json), and Female/Male/Drives construction requires a
  working params["drive start values"][<body name>] entry - real
  construction is slow, filesystem/CWD-dependent, and can side-effect-
  spawn a background thread the moment goal_position is written through
  the real virtual DXL chain (VirtualDXL.set() spawns a bare
  threading.Thread when torque is enabled).
- Prefer small hand-built doubles (below) over the real object graph.
- For instance methods on classes that are expensive/impossible to
  construct standalone, call the method **unbound** against a small
  duck-typed double exposing only the attributes the method body
  touches, e.g.:
      fake = SimpleNamespace(
          _dxl_origin=SimpleNamespace(get=lambda: 1000),
          _motion_range=2000,
          dxl=SimpleNamespace(goal_position=SimpleNamespace(write=lambda v: None)),
          _position_memory=None,
      )
      Female.turn_to_max_position(fake)
      assert fake._position_memory == "max"

Gotcha: if you construct a REAL Base/BaseThread subclass with a
stub_factory()-built owner (rather than using the unbound-method
pattern above), Base.__init__ asserts `owner is not self.owners`,
which computes `[self.owner] + self.owner.owners` - so the owner you
pass needs an `.owners` attribute too, or construction raises
AttributeError. stub_factory() defaults `owners=[]` for exactly this
reason; only override it if a test specifically needs a non-empty
ancestor chain.
"""
import contextlib
from types import SimpleNamespace

import pytest


class FakeDrive:
    """Duck-typed stand-in for colloquy.hardware.drive.Drive - exposes only
    what Drives.which_is_frustated() touches (.value/.is_satisfied/
    .is_frustated/.lock)."""

    def __init__(self, value, satisfaction_lim=30, frustrated_lim=180):
        self.value = value
        self._satisfaction_lim = satisfaction_lim
        self._frustrated_lim = frustrated_lim
        self.lock = contextlib.nullcontext()

    @property
    def is_satisfied(self):
        return self.value < self._satisfaction_lim

    @property
    def is_frustated(self):
        return self.value > self._frustrated_lim


@pytest.fixture
def fake_drive():
    return FakeDrive


class FakeArduino:
    """Duck-typed stand-in for Arduino - supports `with arduino:` and
    `.send(path) -> str`, as used by LightSensor.read()."""

    def __init__(self, response="0"):
        self.response = response
        self.sent_paths = []

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def send(self, path):
        self.sent_paths.append(path)
        return self.response


@pytest.fixture
def fake_arduino():
    return FakeArduino


def make_stub(**attrs):
    """Build a throwaway SimpleNamespace exposing exactly the given
    attributes - for duck-typed doubles passed to unbound methods, or as
    the `owner` for a real Base/BaseThread subclass under test (see the
    "Gotcha" note above re: the default `owners=[]`)."""
    attrs.setdefault("owners", [])
    return SimpleNamespace(**attrs)


@pytest.fixture
def stub_factory():
    return make_stub
