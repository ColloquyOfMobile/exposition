"""What decides whether this process drives real hardware, and what that
decision controls in the UI.

Worth pinning precisely: the same switch that hides the virtual-hardware
view is the one that decides whether servos and LEDs are real. If it ever
reads wrong on the installation computer, the view appearing is not a
cosmetic slip - it is the visible symptom of an app that is not driving
anything.

The switch gates a second thing now - the code documentation on the front
page - and the two want opposite things from a wrong reading. A stray
virtual-hardware panel means the servos are not being driven; a stray
documentation link means nothing at all. They share the test because they
share the question ("is this the installation?"), not because they are
equally serious.
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
        # Colloquy's snapshot_children ends by handing its children to
        # BaseThread._with_scenarios; the double stands in for it, since
        # what is under test here is the is_simulated gate.
        _with_scenarios=lambda children: children,
        _hardware="hardware",
        _exposition="exposition",
        _tests="tests",
        _params_view="params",
        _logs="logs",
        _code_documentation=SimpleNamespace(name="code documentation"),
        _hardware_setup=SimpleNamespace(name="hardware setup"),
        is_simulated=is_simulated,
        virtual_hardware=virtual,
    )
    return Colloquy.snapshot_children.fget(double)


def test_the_virtual_hardware_tab_is_absent_on_the_installation():
    assert "virtual hardware" not in _tabs(is_simulated=False)


def test_the_virtual_hardware_tab_is_present_when_simulated():
    assert "virtual hardware" in _tabs(is_simulated=True)


def test_the_code_documentation_is_on_the_front_page_off_the_installation():
    # It used to be three clicks deep under "tests". It is the source's
    # own documentation, so the front page is where it is wanted - on the
    # machines where the source is being worked on.
    assert "code documentation" in _tabs(is_simulated=True)


def test_the_installation_is_not_offered_the_code_documentation():
    # Nothing breaks if it is drawn there; it is simply not what that
    # machine is for, and the page in the gallery is better without it.
    assert "code documentation" not in _tabs(is_simulated=False)


def test_the_hardware_setup_is_offered_on_every_machine():
    # The other half of the same decision, and the opposite way round.
    # The installation'''s own machine is the one wired to the thing being
    # wired, so it is the last place to hide the wiring document - while
    # the code documentation beside it is no use there at all.
    assert "hardware setup" in _tabs(is_simulated=True)
    assert "hardware setup" in _tabs(is_simulated=False)


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
        _with_scenarios=lambda children: children,
        _hardware="hardware",
        _exposition="exposition",
        _tests="tests",
        _params_view="params",
        _logs="logs",
        _code_documentation=SimpleNamespace(name="code documentation"),
        _hardware_setup=SimpleNamespace(name="hardware setup"),
        is_simulated=False,
    )

    Colloquy.snapshot_children.fget(double)

    assert touched == []
