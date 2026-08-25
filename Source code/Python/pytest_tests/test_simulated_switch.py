"""What decides whether this process drives real hardware, and what that
decision controls in the UI.

Worth pinning precisely: the same switch that hides the virtual-drivers
view is the one that decides whether servos and LEDs are real. If it ever
reads wrong on the installation computer, the view appearing is not a
cosmetic slip - it is the visible symptom of an app that is not driving
anything.

The switch gates a second thing now - the code documentation on the front
page - and the two want opposite things from a wrong reading. A stray
virtual-drivers panel means the servos are not being driven; a stray
documentation link means nothing at all. They share the test because they
share the question ("is this the installation?"), not because they are
equally serious.

The audio subsystem's hardware setup document is *not* gated, and is not
on the root either: it hangs off the test it describes the bench for.
See pytest_tests/test_documents.py.
"""
from types import SimpleNamespace

from colloquy import Colloquy
from colloquy.base import Base

INSTALLATION_HOSTNAME = "Colloquy-Laptop"


def set_hostname(monkeypatch, name):
    monkeypatch.setattr("colloquy.machines.socket.gethostname", lambda: name)


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
    virtual = SimpleNamespace(name="virtual drivers")
    double = SimpleNamespace(
        # Colloquy's snapshot_children ends by handing its children to
        # BaseThread._with_scenarios; the double stands in for it, since
        # what is under test here is the is_simulated gate.
        _with_scenarios=lambda children: children,
        _drivers="drivers",
        _exposition="exposition",
        _tests="tests",
        _params_view="params",
        _logs="logs",
        _hardware="hardware",
        _repository="repository",
        _code_documentation=SimpleNamespace(name="code documentation"),
        is_simulated=is_simulated,
        virtual_drivers=virtual,
    )
    return Colloquy.snapshot_children.fget(double)


def test_the_virtual_drivers_tab_is_absent_on_the_installation():
    assert "virtual drivers" not in _tabs(is_simulated=False)


def test_the_virtual_drivers_tab_is_present_when_simulated():
    assert "virtual drivers" in _tabs(is_simulated=True)


def test_the_code_documentation_is_on_the_front_page_off_the_installation():
    # It used to be three clicks deep under "tests". It is the source's
    # own documentation, so the front page is where it is wanted - on the
    # machines where the source is being worked on.
    assert "code documentation" in _tabs(is_simulated=True)


def test_the_installation_is_not_offered_the_code_documentation():
    # Nothing breaks if it is drawn there; it is simply not what that
    # machine is for, and the page in the gallery is better without it.
    assert "code documentation" not in _tabs(is_simulated=False)


def test_the_hardware_section_is_on_both_machines():
    # What is physically in the rack, as opposed to the layer that drives
    # it. Not gated: the machine with the boards actually in it is the one
    # place it is not hypothetical.
    assert "hardware" in _tabs(is_simulated=False)
    assert "hardware" in _tabs(is_simulated=True)


def test_the_repository_watch_is_on_both_machines():
    # Deliberately not gated, unlike the code documentation beside it.
    # The repo is worked on from two computers, and the one that most
    # needs telling that origin has moved is the installation's own
    # laptop, sitting in a gallery on a checkout from a fortnight ago.
    assert "repository" in _tabs(is_simulated=False)
    assert "repository" in _tabs(is_simulated=True)


def test_nothing_builds_the_simulation_when_not_simulated():
    # The tab is what first touches Colloquy.virtual_drivers, and that
    # property constructs the whole simulated stack on access.
    touched = []

    class Double(SimpleNamespace):
        @property
        def virtual_drivers(self):
            touched.append(True)
            return SimpleNamespace(name="virtual drivers")

    double = Double(
        _with_scenarios=lambda children: children,
        _drivers="drivers",
        _exposition="exposition",
        _tests="tests",
        _params_view="params",
        _logs="logs",
        _hardware="hardware",
        _repository="repository",
        _code_documentation=SimpleNamespace(name="code documentation"),
        is_simulated=False,
    )

    Colloquy.snapshot_children.fget(double)

    assert touched == []


# --- the bench is a machine of its own ------------------------------------

BENCH_HOSTNAME = "DESKTOP-MRSLS88"


def test_the_bench_has_no_piece_on_it_but_a_real_audio_board(monkeypatch):
    """The case the single is_simulated boolean could not express.

    Thomas's boards are on an office desk. That machine has no servos and
    no Arduino - so the piece is simulated on it - and it has the audio
    subsystem physically attached, so the audio board is not. Reading
    those as one question is what sent the bench test at a stand-in while
    the real board sat on the desk beside it.
    """
    node = Base.__new__(Base)

    set_hostname(monkeypatch, BENCH_HOSTNAME)

    assert node.is_simulated is True
    assert node.is_bench is True


def test_the_installation_has_the_piece_and_no_bench(monkeypatch):
    node = Base.__new__(Base)

    set_hostname(monkeypatch, INSTALLATION_HOSTNAME)

    assert node.is_simulated is False
    assert node.is_bench is False


def test_any_other_machine_has_neither(monkeypatch):
    node = Base.__new__(Base)

    set_hostname(monkeypatch, "some-laptop")

    assert node.is_simulated is True
    assert node.is_bench is False


def test_the_bench_match_is_exact_too(monkeypatch):
    # Same warning as above, and the same cost: a near miss means the test
    # quietly runs against the stand-in, which passes all twenty-five.
    node = Base.__new__(Base)

    for close_but_not_equal in (
        BENCH_HOSTNAME.lower(),
        BENCH_HOSTNAME + ".local",
        " " + BENCH_HOSTNAME,
    ):
        set_hostname(monkeypatch, close_but_not_equal)
        assert node.is_bench is False, close_but_not_equal


def test_the_two_machines_are_not_the_same_machine():
    from colloquy import machines

    assert machines.INSTALLATION != machines.BENCH
