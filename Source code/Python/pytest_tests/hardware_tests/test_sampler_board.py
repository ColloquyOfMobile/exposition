"""The board `test goertzel ear` and `scope` share, and the two presses.

What is pinned here is the part that is easy to get confidently wrong:
the difference between *nobody has asked yet* and *nothing answered*, and
the difference between a firmware older than the one in this repo and one
too old to be any use. Both pairs read alike in a sentence and mean
opposite things - one is a reason to go and find a USB lead, the other is
a reason to carry on.

`sampler_sketch` is read against the real .ino on purpose, the way
`test_firmware.py` reads the installation's: the numbers on the page have
to be the numbers that would be flashed, and a fixture restating them
would agree with itself forever.

Per conftest: nothing is started, no real serial port is opened, and the
hosts here are small duck-typed doubles.
"""
from types import SimpleNamespace

import pytest

from colloquy.tests import sampler_sketch
from colloquy.tests.sampler_board import SamplerBoard, SamplerFlasher

GREETING = "microphone_sampler firmware=2 mic_pin=A0 n=512 fs=19230.8 baud=1000000"
OLD_GREETING = "microphone_sampler firmware=1 mic_pin=A0 n=512 fs=19230.8"


class FakePort:
    """A serial port that hands back a queue of lines once opened."""

    def __init__(self, lines=(), is_open=False):
        self._lines = list(lines)
        self.is_open = is_open
        self.opened = 0
        self.closed = 0

    def open(self):
        self.is_open = True
        self.opened += 1

    def close(self):
        self.is_open = False
        self.closed += 1

    def readline(self):
        if not self._lines:
            return b""
        return self._lines.pop(0)


class Host(SamplerBoard):
    """One test's worth of host: a lead, a refusal and a running flag."""

    # A tenth of a second rather than four: every case here either
    # answers on the first line or was never going to answer at all.
    GREETING_TIMEOUT = 0.1

    def __init__(self, port, refusal=None, started=False, minimum=2):
        self._port = port
        self._refusal = refusal
        self._started = started
        self.MINIMUM_FIRMWARE = minimum
        self.FIRMWARE_NEEDED_FOR = "both channels"
        self._greeting = None
        self._firmware = None

    name = "the host"

    @property
    def port_handler(self):
        return self._port

    @property
    def is_started(self):
        return self._started

    def _why_not_open(self):
        return self._refusal


# --- the sketch, read out of the sketch ----------------------------------


def test_the_numbers_come_out_of_the_ino():
    """Not restated here, for `firmware.py`'s reason: a fixture that
    carries its own copy of the version agrees with itself forever."""
    assert sampler_sketch.firmware_version() == 2
    assert sampler_sketch.baudrate() == 1000000
    assert sampler_sketch.mic_pins() == ("A0", "A1")


def test_the_description_names_both_pins():
    """The second pin is the whole of what firmware 2 added, and the
    whole of what `scope` is for."""
    said = sampler_sketch.describe()

    assert "A0" in said and "A1" in said
    assert "firmware 2" in said


def test_the_firmware_is_read_out_of_a_greeting():
    assert sampler_sketch.firmware_in(GREETING) == 2
    assert sampler_sketch.firmware_in("microphone_sampler mic_pin=A0") is None
    assert sampler_sketch.firmware_in("") is None


# --- the four verdicts ---------------------------------------------------


def test_never_asked_is_not_a_fault():
    """The state the page is in before anybody presses anything. Phrased
    as a thing to do rather than as a finding, because nothing has been
    measured - a board nobody has spoken to is not a broken board."""
    said = sampler_sketch.verdict(None, 2)

    assert "not known yet" in said
    assert "ask the board" in said
    assert "too old" not in said


def test_too_old_says_what_is_lost_and_what_to_do():
    said = sampler_sketch.verdict(1, 2, "both channels")

    assert "firmware 1" in said
    assert "too old" in said
    # What it costs, not just that a number is small. `scope` with one
    # channel is a recording with a flat line in it, which looks like a
    # dead microphone.
    assert "both channels" in said
    assert "firmware 2" in said  # what is here to flash


def test_older_than_this_repo_but_new_enough_is_not_a_fault():
    """The case that matters for `test goertzel ear`: `b` is untouched
    since firmware 1, so a board on 1 works perfectly. Reporting that as
    a failure teaches people to ignore the reading."""
    said = sampler_sketch.verdict(1, 1)

    assert "too old" not in said
    assert "new enough" in said


def test_newer_than_this_repo_says_which_way_round():
    said = sampler_sketch.verdict(99, 2)

    assert "newer" in said
    assert "checkout is behind" in said


def test_usable_is_decided_on_the_number_not_the_prose():
    assert sampler_sketch.is_usable(2, 2)
    assert sampler_sketch.is_usable(3, 2)
    assert not sampler_sketch.is_usable(1, 2)
    assert not sampler_sketch.is_usable(None, 2)


# --- the handshake -------------------------------------------------------


def test_asking_opens_the_lead_reads_the_greeting_and_puts_it_back():
    port = FakePort(lines=[GREETING.encode()])
    host = Host(port)

    said = host.handshake()

    assert "firmware 2" in said
    assert host.firmware == 2
    # Put back exactly as found. The other test on the bench may want
    # this lead, and only one of the two can hold it.
    assert port.opened == 1 and port.closed == 1
    assert not port.is_open


def test_a_lead_already_open_has_missed_the_greeting():
    """It greets on reboot and opening the port is what reboots it, so
    there is no asking twice without another reboot - and rebooting the
    board underneath a run that is reading captures off it would lose a
    block to answer nothing new."""
    port = FakePort(lines=[GREETING.encode()], is_open=True)
    host = Host(port)

    said = host.handshake()

    assert "already open" in said
    assert port.opened == 0 and port.closed == 0


def test_nothing_greeting_is_a_finding_rather_than_an_unknown():
    """The difference this pins: the same `None` means "nobody asked" on
    the page and "this lead answered nothing" straight after a press."""
    host = Host(FakePort(lines=[]))

    said = host.handshake()

    assert "nothing greeted" in said
    assert "microphone_sampler" in said
    assert "not known yet" not in said


def test_a_line_from_some_other_sketch_is_not_a_greeting():
    host = Host(FakePort(lines=[b"Hello!\n", b"min:12,max:400\n"]))

    said = host.handshake()

    assert "nothing greeted" in said
    assert host.firmware is None


def test_the_greeting_is_found_among_whatever_else_is_in_the_buffer():
    host = Host(FakePort(lines=[b"\n", b"", GREETING.encode()]))

    assert "firmware 2" in host.handshake()


# --- asking, as a press --------------------------------------------------


def test_a_running_test_is_told_what_is_already_known():
    """No reboot: the loop owns the port, and the greeting is already as
    read as it is going to get."""
    port = FakePort(lines=[GREETING.encode()])
    host = Host(port, started=True)
    host._firmware = 2

    said = host.ask_the_board()

    assert "running" in said
    assert "firmware 2" in said
    assert port.opened == 0


def test_the_press_refuses_for_the_same_reasons_a_run_does():
    host = Host(FakePort(), refusal="no port chosen - pick one under 'com port'")

    said = host.ask_the_board()

    assert said.startswith("refused:")
    assert "com port" in said


def test_a_port_that_will_not_open_is_a_sentence_not_a_traceback():
    import serial

    class Broken(FakePort):
        def open(self):
            raise serial.SerialException("could not open port 'COM9'")

    said = Host(Broken()).ask_the_board()

    assert "could not open the lead" in said
    assert "COM9" in said


# --- the readings --------------------------------------------------------


def readings_of(host):
    found = {}
    host._board_readings(lambda name, value: found.__setitem__(name, value))
    return found


def test_the_page_carries_the_greeting_and_the_judgement_apart():
    """The version is on a line of its own rather than left inside the
    greeting: it is the thing being judged, and a recording with one flat
    line is exactly what an old board looks like from the graph."""
    host = Host(FakePort(lines=[OLD_GREETING.encode()]))
    host.handshake()

    found = readings_of(host)

    assert found["board says"] == OLD_GREETING
    assert "too old" in found["firmware"]


def test_before_anything_is_asked_only_the_verdict_line_is_drawn():
    found = readings_of(Host(FakePort()))

    assert "board says" not in found
    assert "not known yet" in found["firmware"]


# --- the flasher ---------------------------------------------------------


def flasher_double(chosen="COM7", port_open=False, handshake="firmware 2 - ok"):
    """A SamplerFlasher double. Called unbound, per conftest: it is a
    BaseThread hanging off a real test node and neither is built here."""
    handler = FakePort(is_open=port_open)
    owner = SimpleNamespace(
        com_port=SimpleNamespace(chosen=chosen),
        port_handler=handler,
        handshake=lambda: handshake,
        board_verdict="firmware 2 - the sketch in this repo",
    )
    return SimpleNamespace(owner=owner), handler


def test_it_flashes_the_sampler_sketch():
    assert SamplerFlasher.sketch_folder.fget(None) == sampler_sketch.SKETCH_FOLDER
    assert SamplerFlasher.sketch_says(None) == sampler_sketch.describe()


def test_the_port_is_the_owning_test_s_lead_not_the_installation_s():
    """Read out of the test's own picker on every use. The installation's
    `arduino / communication port` is a different board on a different
    lead, and reaching for it here is how avrdude meets the wrong one."""
    fake, _ = flasher_double(chosen="COM12")

    assert SamplerFlasher.port.fget(fake) == "COM12"


def test_it_lets_go_of_the_lead_before_avrdude_wants_it():
    """avrdude cannot have the port while pyserial holds it, and the
    error it gives for that names neither of them."""
    fake, handler = flasher_double(port_open=True)

    SamplerFlasher._release_the_link(fake)

    assert not handler.is_open
    assert handler.closed == 1


def test_a_shut_lead_is_left_shut():
    fake, handler = flasher_double(port_open=False)

    SamplerFlasher._release_the_link(fake)

    assert handler.closed == 0


def test_the_flash_ends_by_asking_the_board_what_it_now_is():
    """The whole check on what actually reached the flash: an upload
    avrdude called a success that left the wrong image on the board is
    caught here and nowhere else."""
    fake, _ = flasher_double(handshake="firmware 2 - the sketch in this repo")

    said = SamplerFlasher._check_the_board(fake, None)

    assert said.startswith("flashed - ")
    assert "firmware 2" in said


def test_a_board_that_cannot_be_asked_after_a_flash_says_so():
    """Rather than reporting avrdude's success as the board's word for
    it - which is the one thing the check exists to stop."""
    fake, _ = flasher_double()
    fake.owner.handshake = _raise

    said = SamplerFlasher._check_the_board(fake, None)

    assert "could not be asked" in said
    assert "flashed -" not in said


def _raise():
    raise OSError("the lead came out")


# --- what each of the two tests needs of the board -----------------------


def test_the_two_tests_ask_different_things_of_one_board():
    """`b` is untouched since firmware 1 and `d` arrived in 2. A board
    that is fine for one is useless to the other, and the page has to say
    which - the same board, the same lead, two answers."""
    from colloquy.tests.scope import Scope
    from colloquy.tests.test_goertzel_ear import TestGoertzelEar

    assert Scope.MINIMUM_FIRMWARE == 2
    assert TestGoertzelEar.MINIMUM_FIRMWARE == 1

    assert "too old" in sampler_sketch.verdict(1, Scope.MINIMUM_FIRMWARE)
    assert "too old" not in sampler_sketch.verdict(
        1, TestGoertzelEar.MINIMUM_FIRMWARE
    )


def sampler_tests():
    from colloquy.tests.scope import Scope
    from colloquy.tests.test_goertzel_ear import TestGoertzelEar

    return (Scope, TestGoertzelEar)


@pytest.mark.parametrize("cls", sampler_tests())
def test_both_tests_reach_the_board_through_this_one_mixin(cls):
    """Not two copies of how to greet a board. They had the same fifteen
    lines of `_open_if_needed` each, against the same sketch, and the one
    that grew a firmware check grew it alone."""
    assert SamplerBoard in cls.__mro__
    assert "_open_if_needed" not in vars(cls)


@pytest.mark.parametrize("cls", sampler_tests())
def test_both_tests_offer_the_flash_and_the_handshake(cls):
    """Read off `snapshot_children`, which is the tree's whole routing
    contract - a child drawn but not listed there is a link that 404s,
    and one listed but not drawn is a page nobody can reach.

    Built rather than inspected would need the whole hardware graph, so
    this reads the source of the one property. Blunt, and it does catch
    the failure it is for: a press registered in `__init__` and forgotten
    in `snapshot_children`.
    """
    import inspect

    source = inspect.getsource(cls.snapshot_children.fget)

    assert "ask the board" in source
    assert "self._flasher.name" in source
