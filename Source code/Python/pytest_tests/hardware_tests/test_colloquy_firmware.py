"""`flash firmware` on a test's own page, and which tests have one.

Two things are pinned here, and the second is the one that will rot.

**It is a view, not a second flasher.** There is one board and one lead,
so there is one `Flasher`; this node forwards to it and draws what it
says. The moment any refusal is restated here there are eleven copies to
drift, and weaker ones, because only the flasher knows what is on the USB
bus.

**Which tests get one is a decision, not a sweep.** The rule is "does
this test need a sketch this repo can flash" - which is *not* "is this a
hardware test". `test movements` moves servos and touches no board;
Thomas's two drive his own Mega, and his code is `.cpp` files rather than
a sketch folder arduino-cli can compile. A later test that quietly joins
or leaves the set should fail here rather than be noticed at a rack.

Per conftest: nothing is started, no board is opened, and the real
`Colloquy` graph is never built - the classes are read, and the node is
driven against a duck-typed double.
"""
from pathlib import Path
from types import SimpleNamespace

import pytest

from colloquy.drivers.arduino import firmware
from colloquy.tests.colloquy_firmware import ColloquyFirmware, NeedsColloquyFirmware
from colloquy.tests.test_microphone_signal.plotter_flasher import PlotterFlasher


class FakeFlasher:
    def __init__(self, refusal=None, outcome=None, started=False):
        self.refusal = refusal
        self.outcome = outcome
        self.is_started = started
        self.calls = []

    def _why_not_flash(self):
        return self.refusal

    def flash(self):
        self.calls.append("flash")
        return "flashing colloquy_of_mobiles - refresh in a moment"

    def compile_only(self):
        self.calls.append("compile")
        return "compiling colloquy_of_mobiles - refresh in a moment"


def node(flasher=None, greeting=None, problems=()):
    """A ColloquyFirmware on a double of the test it would hang off."""
    flasher = flasher if flasher is not None else FakeFlasher()
    arduino = SimpleNamespace(
        flasher=flasher, greeting=greeting, problems=list(problems)
    )
    owner = SimpleNamespace(
        colloquy=None,
        drivers=SimpleNamespace(arduino=arduino),
        # What `Base.__init__` and `Base.path` walk. A test node is a
        # BaseThread with a real owner chain behind it; this is the least
        # of one that lets the node be built at all.
        owners=[],
        name="the test",
        path=Path("tests/the test"),
    )
    built = ColloquyFirmware(owner=owner)
    return built, flasher


def readings_of(built):
    states = built._snapshot_if_opened(())
    return {
        key: value["value"]
        for key, value in states.items()
        if isinstance(value, dict) and "value" in value
    }


# --- it forwards, it does not decide -------------------------------------


def test_pressing_flash_reaches_the_one_flasher():
    built, flasher = node()

    said = built.flash()

    assert flasher.calls == ["flash"]
    assert "colloquy_of_mobiles" in said


def test_pressing_compile_reaches_the_one_flasher():
    built, flasher = node()

    built.compile_only()

    assert flasher.calls == ["compile"]


def test_a_refusal_is_the_flashers_own_words():
    """Not restated here. Eleven copies of five refusals would drift, and
    only the flasher knows what is on the USB bus."""
    refusal = "COM4 is FTDI FT232R, which is not a board to flash."
    built, _ = node(FakeFlasher(refusal=refusal))

    assert readings_of(built)["can flash"] == f"no - {refusal}"


def test_both_presses_stay_on_the_page_even_when_refused():
    """The opposite rule to the flasher's own page, on purpose: a link
    that vanished exactly when the board was in the state needing it
    would be the wrong way round, and the flasher answers a press it will
    not act on with the reason, in the same request."""
    built, _ = node(FakeFlasher(refusal="the main PCB is noted as unmounted"))

    offered = built.snapshot_children

    assert "flash the board" in offered
    assert "compile only" in offered


# --- what it says --------------------------------------------------------


def test_it_says_what_would_be_flashed_out_of_the_sketch():
    """Read from the .ino rather than restated - `firmware.py`'s
    arrangement, for its reason."""
    built, _ = node()

    said = readings_of(built)["would flash"]

    assert str(firmware.sketch_firmware_version()) in said
    assert str(firmware.sketch_baudrate()) in said


def test_in_sync_is_the_reading_the_node_exists_for():
    """It is what says whether pressing is necessary, and it is what
    somebody about to press start on the test above needs to see."""
    built, _ = node(greeting={"firmware": 2, "baudrate": 1000000})
    assert readings_of(built)["in sync"] == "yes"

    built, _ = node(problems=["the board is running firmware 2"])
    found = readings_of(built)
    assert found["in sync"] == "NO"
    assert "firmware 2" in found["problem 1"]


def test_the_outcome_is_shared_between_every_page_that_draws_one():
    """One board, one answer. A flash started from `test neopixels` shows
    on `test sensors` too, because there is one of it."""
    flasher = FakeFlasher(outcome="flashed - board says firmware 4")
    first, _ = node(flasher)
    second, _ = node(flasher)

    assert readings_of(first)["last flash"] == readings_of(second)["last flash"]


def test_a_flash_in_progress_says_so():
    built, _ = node(FakeFlasher(started=True))

    assert "in progress" in readings_of(built)["flashing"]


# --- which tests have one ------------------------------------------------

# Every test that reaches the installation's Arduino - a NeoPixel, a
# photosensor, a tone or an ear. Kept as names rather than classes so a
# rename shows up here as a failure rather than an import error.
NEEDS_THE_BOARD = {
    "TestAudioBringup",
    "TestAudioLoop",
    "TestDriveLightValues",
    "TestFemaleSearch",
    "TestLightSensorValues",
    "TestMalePatterns",
    "TestNeopixels",
    "TestReadPattern",
    "TestReinforcement",
    "TestSearch",
    "TestSensors",
}

# And the three that deliberately do not, each for its own reason.
DOES_NOT = {
    # Servos and the bar. No light, no sound, nothing on the Arduino.
    "TestMovements",
    # Thomas's own Mega over his own serial menu, and his code is
    # `Source code/Thomas/*.cpp` - not a sketch folder arduino-cli can
    # be pointed at. Offering a flash would be offering a press that
    # cannot work.
    "TestAudioSubsystem",
    "TestAudioAt12V",
}


def installation_tests():
    from colloquy import tests as tests_module

    found = {}
    for name in NEEDS_THE_BOARD | DOES_NOT:
        found[name] = getattr(tests_module, name)
    return found


def test_every_test_that_drives_the_piece_can_fix_its_board():
    have = {
        name
        for name, cls in installation_tests().items()
        if NeedsColloquyFirmware in cls.__mro__
    }

    assert have == NEEDS_THE_BOARD


def test_the_tests_that_touch_no_sketch_are_left_alone():
    """The rule is "needs a sketch this repo can flash", not "is a
    hardware test" - and the difference is these three."""
    have = {
        name
        for name, cls in installation_tests().items()
        if NeedsColloquyFirmware in cls.__mro__
    }

    assert have & DOES_NOT == set()


@pytest.mark.parametrize("name", sorted(NEEDS_THE_BOARD))
def test_the_node_is_listed_where_the_walk_will_find_it(name):
    """`snapshot_children` is the tree's whole routing contract: a child
    drawn but not listed there is a link that 404s. This is what
    `_with_firmware` exists to guarantee, and reading the source of the
    property is the cheapest way to hold it - building one needs the
    whole hardware graph."""
    import inspect

    cls = installation_tests()[name]
    source = inspect.getsource(cls.snapshot_children.fget)

    assert "_with_firmware" in source


# --- the plotter, which is the one that goes the other way ---------------


def plotter_double(mounted=True, port_open=False):
    arduino = SimpleNamespace(is_open=port_open, closed=[])

    def close():
        arduino.is_open = False
        arduino.closed.append(True)

    arduino.close = close
    return SimpleNamespace(
        owner=SimpleNamespace(drivers=SimpleNamespace(arduino=arduino)),
        colloquy=SimpleNamespace(
            hardware=SimpleNamespace(main_pcb=SimpleNamespace(is_mounted=mounted))
        ),
        params={"arduino": {"communication port": "COM7", "fqbn": "arduino:avr:mega"}},
        arduino=arduino,
    )


def test_the_plotter_flasher_is_named_for_its_direction():
    """Not `flash firmware`, though it is one. This board has two
    sketches that belong on it at different moments, and a link named for
    neither is the one press here somebody could get backwards."""
    assert PlotterFlasher.name.fget(None) == "flash the plotter sketch"


def test_it_uses_the_installations_own_lead_and_board_type():
    """The same board the piece runs on - that is the whole point of the
    two routes, and the whole reason the way back is on this page too."""
    fake = plotter_double()

    assert PlotterFlasher.port.fget(fake) == "COM7"
    assert PlotterFlasher.fqbn.fget(fake) == "arduino:avr:mega"


def test_it_will_not_flash_an_unmounted_board():
    fake = plotter_double(mounted=False)

    assert "unmounted" in PlotterFlasher._extra_refusals(fake)


def test_it_closes_the_drivers_link_before_avrdude_wants_the_port():
    fake = plotter_double(port_open=True)

    was_open = PlotterFlasher._release_the_link(fake)

    assert was_open is True
    assert not fake.arduino.is_open


def test_it_does_not_reopen_the_link_afterwards():
    """The one that would look like tidiness and be a bug.
    `Arduino.open()` waits for a greeting `microphone_plotter` does not
    send and refuses a firmware it was not written for, so a reopen would
    report a failure that is the expected outcome of a successful flash.
    """
    fake = plotter_double(port_open=True)
    fake.arduino.open = _must_not_be_called
    fake.sketch_says = lambda: PlotterFlasher.sketch_says(fake)

    said = PlotterFlasher._check_the_board(fake, True)

    assert "left" in said and "closed" in said
    assert str(firmware.sketch_firmware_version()) in said
    # And it names the way back, because this page is what broke it.
    assert "flash colloquy firmware back" in said


def _must_not_be_called():
    raise AssertionError("the driver's link must not be reopened after this")
