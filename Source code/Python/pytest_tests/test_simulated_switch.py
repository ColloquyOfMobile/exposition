"""What decides whether this process drives real hardware, and what that
decision controls in the UI.

Worth pinning precisely: the same switch that hides the virtual-hardware
view is the one that decides whether servos and LEDs are real. If it ever
reads wrong on the installation computer, the view appearing is not a
cosmetic slip - it is the visible symptom of an app that is not driving
anything.
"""
from types import SimpleNamespace

from colloquy import Colloquy
from colloquy.base import Base

INSTALLATION_HOSTNAME = "Colloquy-Laptop"


def set_hostname(monkeypatch, name):
    monkeypatch.setattr("colloquy.base.socket.gethostname", lambda: name)


def test_only_the_installation_computer_runs_real_hardware(monkeypatch, stub_factory):
    node = Base.__new__(Base)

    set_hostname(monkeypatch, INSTALLATION_HOSTNAME)
    assert node.is_simulated is False

    set_hostname(monkeypatch, "some-laptop")
    assert node.is_simulated is True


def test_the_match_is_exact_and_case_sensitive(monkeypatch):
    # Not a recommendation - a warning. socket.gethostname() can answer in
    # a different case than the name was set in, and any mismatch means the
    # installation silently runs against virtual hardware.
    node = Base.__new__(Base)

    for close_but_not_equal in (
        INSTALLATION_HOSTNAME.upper(),
        INSTALLATION_HOSTNAME.lower(),
        INSTALLATION_HOSTNAME + ".local",
        " " + INSTALLATION_HOSTNAME,
    ):
        set_hostname(monkeypatch, close_but_not_equal)
        assert node.is_simulated is True, close_but_not_equal


def _tabs(is_simulated):
    """Colloquy.snapshot_children against a double - the real object does
    filesystem I/O at construction (see conftest)."""
    virtual = SimpleNamespace(name="virtual hardware")
    double = SimpleNamespace(
        _hardware="hardware",
        _exposition="exposition",
        _tests="tests",
        _params_view="params",
        _logs="logs",
        is_simulated=is_simulated,
        virtual_hardware=virtual,
    )
    return Colloquy.snapshot_children.fget(double)


def test_the_virtual_hardware_tab_is_absent_on_the_installation():
    assert "virtual hardware" not in _tabs(is_simulated=False)


def test_the_virtual_hardware_tab_is_present_when_simulated():
    assert "virtual hardware" in _tabs(is_simulated=True)


def test_nothing_builds_the_simulation_when_not_simulated():
    # The tab is what first touches Colloquy.virtual_hardware, and that
    # property constructs the whole simulated stack on access.
    touched = []

    class Double(SimpleNamespace):
        @property
        def virtual_hardware(self):
            touched.append(True)
            return SimpleNamespace(name="virtual hardware")

    double = Double(
        _hardware="hardware",
        _exposition="exposition",
        _tests="tests",
        _params_view="params",
        _logs="logs",
        is_simulated=False,
    )

    Colloquy.snapshot_children.fget(double)

    assert touched == []
