"""Tests for the bench test that drives Thomas's audio subsystem.

The board is a Mega 2560 on a USB lead and there is not one here, so what
is covered is everything that does not need one: the text going out, the
tables coming back, and the judgement made of them. That judgement is the
whole point of the test - it is what a person at a bench reads instead of
the numbers - so it is worth pinning from every side.

The virtual board is exercised too, through the same protocol functions
the real one is read with. That is deliberate: if the two ever disagree
about what a dump looks like, a simulated run goes green while the bench
sits silent.
"""
import io
from types import SimpleNamespace

import pytest

from colloquy.tests.bench_board import BenchBoardLink
from colloquy.tests.test_audio_subsystem import AudioComPort, protocol
# Aliased: pytest tries to collect any imported name starting "Test".
from colloquy.tests.test_audio_subsystem import (
    TestAudioSubsystem as AudioSubsystemTest,
)
from colloquy.virtual_drivers.virtual_audio_serial_port import (
    NOISE_FLOOR,
    TONE_LEVEL,
    VirtualAudioSerialPort,
)


# --- what the board is told ----------------------------------------------


def test_the_timer_numbers_are_the_menus_and_not_the_pitch_order():
    # The trap in this board: "E2" is the 6.25 kHz tone, not the second
    # one up. The menu counts timers, and timer 2 is the 8-bit one.
    assert protocol.TIMERS[2]["hz"] == 6250
    assert protocol.TIMERS[1]["hz"] == 160
    assert protocol.TIMERS_BY_PITCH == (1, 3, 4, 5, 2)
    by_pitch = [protocol.TIMERS[t]["hz"] for t in protocol.TIMERS_BY_PITCH]
    assert by_pitch == sorted(by_pitch)


def test_each_tone_lands_in_its_own_band():
    # The whole point of those five frequencies: five bodies, five voices,
    # no two competing for one of the analyser's seven bands.
    bands = [protocol.expected_band(t) for t in protocol.TIMERS]
    assert sorted(bands) == [1, 2, 3, 4, 5]
    # 63 Hz and 16 kHz are left unused.
    assert 0 not in bands and 6 not in bands


def test_the_pins_match_the_firmware_header():
    # AudioAnalyzer.h, and the board's own "I" table.
    assert protocol.TIMERS[1]["pin"] == "D11"
    assert protocol.TIMERS[3]["pin"] == "D5"
    assert protocol.TIMERS[4]["pin"] == "D6"
    assert protocol.TIMERS[5]["pin"] == "D46"
    assert protocol.TIMERS[2]["pin"] == "D10"


def test_the_commands_are_the_letters_the_menu_takes():
    assert protocol.enable(3) == "E3"
    assert protocol.enable("a") == "Ea"
    assert protocol.disable("a") == "Da"
    assert protocol.dump() == "Aa"
    assert protocol.dump(2) == "A2"
    assert protocol.ABORT == "X"


# --- what comes back ------------------------------------------------------


DUMP = (
    "\x1b[2J\x1b[HModule\t63 Hz\t160 Hz\t400 Hz\t1k Hz\t2.5k Hz\t6.25kHz\t16k Hz\r\n"
    "---------------------------------------------------------------\r\n"
    "   0\t 41\t 615\t 38\t 44\t 39\t 40\t 35\r\n"
    "---------------------------------------------------------------\r\n"
    "   1\t 38\t 620\t 44\t 35\t 42\t 33\t 47\r\n"
    "---------------------------------------------------------------\r\n"
)


def test_a_dump_reads_as_one_row_per_module():
    readings = protocol.parse_tables(DUMP)

    assert [module for module, _ in readings] == [0, 1]
    assert readings[0][1] == (41, 615, 38, 44, 39, 40, 35)


def test_the_header_and_the_rules_are_not_mistaken_for_readings():
    # "63" and "160" in the header line are numbers too, and the dashed
    # rule is a line of its own. Neither is a module.
    assert len(protocol.parse_tables(DUMP)) == 2


def test_a_row_torn_in_half_by_a_read_boundary_is_dropped():
    # Better a missing reading than half a number read as a whole one.
    torn = DUMP[: DUMP.index("   1") + 12]

    readings = protocol.parse_tables(torn)

    assert [module for module, _ in readings] == [0]


def test_the_escape_codes_the_firmware_clears_the_screen_with_come_out():
    assert "\x1b" not in protocol.strip_ansi(DUMP)
    assert "Module" in protocol.strip_ansi(DUMP)


def test_several_sweeps_average_per_module():
    readings = [(0, (10, 20, 30, 40, 50, 60, 70)), (0, (20, 40, 60, 80, 100, 120, 140))]

    averages = protocol.average_per_module(readings)

    assert averages[0] == (15, 30, 45, 60, 75, 90, 105)


# --- the judgement --------------------------------------------------------


def silence():
    return (40,) * 7


def with_tone(band, level=620):
    values = [40] * 7
    values[band] = level
    return tuple(values)


def test_the_right_band_rising_is_heard():
    tone = with_tone(protocol.expected_band(4))  # 1 kHz

    assert protocol.verdict(silence(), tone, timer=4, margin=60) == "heard"


def test_nothing_rising_is_silent():
    assert protocol.verdict(silence(), silence(), timer=4, margin=60) == "silent"


def test_a_rise_too_small_to_trust_is_silent():
    # The margin is there to reject drift and room noise, not to measure.
    tone = with_tone(protocol.expected_band(4), level=40 + 59)

    assert protocol.verdict(silence(), tone, timer=4, margin=60) == "silent"


def test_the_wrong_band_rising_is_its_own_answer():
    # Something is sounding, but not where the firmware says it should be:
    # a mis-set timer, or a module on the wrong analog input. Worth
    # telling apart from silence, because it means something different at
    # the bench.
    tone = with_tone(protocol.expected_band(5))  # 2.5 kHz where 1 kHz was asked for

    assert protocol.verdict(silence(), tone, timer=4, margin=60) == "wrong band"


def test_the_expected_band_rising_alongside_a_bigger_neighbour_is_wrong_band():
    values = [40] * 7
    values[protocol.expected_band(4)] = 200
    values[protocol.expected_band(5)] = 600

    assert protocol.verdict(silence(), tuple(values), timer=4, margin=60) == "wrong band"


def test_a_module_that_was_already_noisy_is_measured_against_itself():
    # A module sitting high with nothing playing is not a module hearing
    # something: what counts is the rise, not the level.
    noisy = (300,) * 7

    assert protocol.verdict(noisy, noisy, timer=4, margin=60) == "silent"

    louder = list(noisy)
    louder[protocol.expected_band(4)] = 900
    assert protocol.verdict(noisy, tuple(louder), timer=4, margin=60) == "heard"


# --- the stand-in board ---------------------------------------------------


@pytest.fixture
def board(stub_factory):
    port = VirtualAudioSerialPort(owner=stub_factory())
    port.port = "simulated audio port"
    port.open()
    return port


def drain(port, characters=6000):
    """What the board has to say, ignoring its baud rate.

    Bounded on purpose. A dump never runs out - the board makes another
    sweep whenever the buffer runs low, exactly as the firmware does - so
    "read until empty" is an infinite loop against a streaming command.
    The bound stands in for how long a caller chooses to listen.
    """
    port._budget = characters
    text = port.read(characters).decode("ascii")
    port._budget = 0.0
    return text


def send(port, command):
    port.write((command + protocol.LINE_ENDING).encode("ascii"))


def test_opening_the_port_reads_as_the_board_resetting(board):
    # Which is what the test uses to tell this board from the
    # installation's Arduino on the next USB socket down.
    text = protocol.strip_ansi(drain(board))

    assert protocol.BANNER in text
    assert text.endswith(protocol.PROMPT)


def test_a_dump_with_nothing_playing_sits_at_the_noise_floor(board):
    drain(board)
    send(board, protocol.dump("a"))

    readings = protocol.parse_tables(drain(board))

    assert {module for module, _ in readings} == set(range(protocol.MODULE_COUNT))
    for _module, values in readings:
        assert all(value < NOISE_FLOOR + 20 for value in values)


def test_enabling_a_timer_lifts_that_timers_band_and_no_other(board):
    drain(board)
    send(board, protocol.enable(4))  # 1 kHz
    drain(board)
    send(board, protocol.dump("a"))

    readings = protocol.parse_tables(drain(board))
    expected = protocol.expected_band(4)

    assert readings
    for _module, values in readings:
        assert values[expected] > TONE_LEVEL - 20
        for band, value in enumerate(values):
            if band != expected:
                assert value < NOISE_FLOOR + 20


def test_disabling_all_puts_it_back(board):
    drain(board)
    send(board, protocol.enable("a"))
    drain(board)
    send(board, protocol.disable("a"))
    drain(board)
    send(board, protocol.dump("a"))

    readings = protocol.parse_tables(drain(board))

    assert readings
    for _module, values in readings:
        assert all(value < NOISE_FLOOR + 20 for value in values)


def test_a_dump_streams_until_it_is_aborted(board):
    drain(board)
    send(board, protocol.dump("a"))
    assert len(protocol.parse_tables(drain(board))) > protocol.MODULE_COUNT

    send(board, protocol.ABORT)
    text = protocol.strip_ansi(drain(board))

    # Aborting returns from the firmware's command loop, so main() redraws
    # the whole welcome banner before prompting again - a reader waiting
    # for a bare prompt meets the banner first.
    assert protocol.BANNER in text
    assert text.endswith(protocol.PROMPT)
    assert protocol.parse_tables(drain(board)) == []


def test_a_single_module_dump_prints_only_that_module(board):
    drain(board)
    send(board, protocol.dump(3))

    readings = protocol.parse_tables(drain(board))

    assert {module for module, _ in readings} == {3}


def test_the_firmware_clamp_on_a_nonsense_timer_number(board):
    # enableDisableSingle() clamps anything outside 1-5 to 1. Copied
    # because a test that sends "E9" should see what the board would do,
    # not what would be tidier.
    drain(board)
    send(board, "E9")
    drain(board)
    send(board, protocol.dump("a"))

    readings = protocol.parse_tables(drain(board))
    assert readings
    for _module, values in readings:
        assert values[protocol.expected_band(1)] > TONE_LEVEL - 20


def test_the_board_talks_no_faster_than_its_baud_rate(board):
    # Not decoration: unthrottled, a three-second read collected four
    # thousand sweeps and wrote a 25MB file no bench would ever produce.
    board._budget = 0.0
    board._sent_at = board._sent_at + 0.05  # as if 50ms had not yet passed

    assert board.read(4096) == b""


# --- which machine the board is on ---------------------------------------


def set_hostname(monkeypatch, name):
    monkeypatch.setattr("colloquy.machines.socket.gethostname", lambda: name)


def audio_test_double(chosen):
    """TestAudioSubsystem's port_handler against a double - the real thing
    does filesystem I/O at construction (see conftest).

    `chosen` is the *lead*, which is the whole of the question now: no
    hostname goes into this double at all.
    """
    virtual = SimpleNamespace(port=None, is_open=False, name="the stand-in")
    com_port = SimpleNamespace(
        chosen=chosen,
        stand_in="simulated audio port",
        is_using_the_stand_in=chosen == "simulated audio port",
    )
    return SimpleNamespace(
        _port_handler=None,
        _com_port=com_port,
        baudrate=9600,
        # What BenchBoardLink.stand_in_handler resolves to on the real
        # object; pinned separately below, since a SimpleNamespace does
        # not inherit the mixin's properties.
        stand_in_handler=virtual,
        SERIAL_TIMEOUT=AudioSubsystemTest.SERIAL_TIMEOUT,
    ), virtual


def test_the_stand_in_is_the_virtual_audio_serial_port():
    virtual = SimpleNamespace(port=None)
    double = SimpleNamespace(
        colloquy=SimpleNamespace(
            virtual_drivers=SimpleNamespace(audio_serial_port=virtual)
        )
    )

    assert AudioSubsystemTest.stand_in_handler.fget(double) is virtual


@pytest.fixture
def no_real_serial(monkeypatch):
    """A serial.Serial that records rather than opening anything."""
    opened = []
    monkeypatch.setattr(
        "colloquy.tests.bench_board.serial.Serial",
        lambda **kwargs: SimpleNamespace(port=None, is_open=False, opened=opened.append(kwargs)),
    )
    return opened


def test_a_real_lead_gets_a_real_serial_port(no_real_serial):
    """The bug this pins, in its second form.

    First time round the handler was chosen on `is_simulated`, which sent
    the test at the stand-in while the real Mega sat on the bench beside
    it. The fix was `is_bench`, and it was the same mistake spelled
    differently: the board gets carried to the installation's laptop to be
    run at 12 V beside the piece, and there `is_bench` is False. A board
    is on a lead, not on a hostname.
    """
    double, virtual = audio_test_double(chosen="COM7")

    assert AudioSubsystemTest.port_handler.fget(double) is not virtual


def test_the_stand_in_gets_the_virtual_port():
    double, virtual = audio_test_double(chosen="simulated audio port")

    assert AudioSubsystemTest.port_handler.fget(double) is virtual


def test_a_real_lead_is_opened_even_on_the_installation(monkeypatch, no_real_serial):
    """The machine this was hidden on is the one it is wanted on."""
    set_hostname(monkeypatch, "Colloquy-Laptop")
    double, virtual = audio_test_double(chosen="COM7")

    assert AudioSubsystemTest.port_handler.fget(double) is not virtual


def test_the_stand_in_is_the_stand_in_even_on_the_bench(monkeypatch):
    set_hostname(monkeypatch, "DESKTOP-MRSLS88")
    double, virtual = audio_test_double(chosen="simulated audio port")

    assert AudioSubsystemTest.port_handler.fget(double) is virtual


def test_the_page_says_which_of_the_two_it_is():
    real, _ = audio_test_double(chosen="COM7")
    stand_in, _ = audio_test_double(chosen="simulated audio port")

    assert AudioSubsystemTest.board_is_real.fget(real) is True
    assert AudioSubsystemTest.board_is_real.fget(stand_in) is False


class LinkUnderTest(BenchBoardLink):
    """The mixin with the two things it wants and nothing else.

    A real object rather than a SimpleNamespace, because `use_port` goes
    back through `port_handler` and a namespace does not inherit the
    mixin's properties - which would make the test pass on plumbing it
    had built itself.
    """

    baudrate = 9600

    def __init__(self, com_port, virtual):
        self._port_handler = None
        self._com_port = com_port
        self._virtual = virtual

    @property
    def stand_in_handler(self):
        return self._virtual


def test_moving_between_the_two_replaces_the_handler(no_real_serial):
    """A name written onto the wrong object opens nothing.

    The stand-in and a `serial.Serial` are different objects, so changing
    the choice cannot be a matter of writing a new port name onto the
    handler already in hand. Straight out of `Arduino.use_port`, and this
    is the path a click on the picker actually takes.
    """
    virtual = SimpleNamespace(port=None, is_open=False)
    com_port = SimpleNamespace(
        chosen="simulated audio port",
        stand_in="simulated audio port",
        is_using_the_stand_in=True,
    )
    link = LinkUnderTest(com_port, virtual)
    assert link.port_handler is virtual

    # As BenchComPort.set does it: params first, then the owner re-points.
    com_port.chosen = "COM7"
    com_port.is_using_the_stand_in = False
    link.use_port("COM7")

    assert link._port_handler is not virtual
    assert link._port_handler.port == "COM7"


def test_moving_back_to_the_stand_in_replaces_it_again(no_real_serial):
    virtual = SimpleNamespace(port=None, is_open=False)
    com_port = SimpleNamespace(
        chosen="COM7", stand_in="simulated audio port", is_using_the_stand_in=False
    )
    link = LinkUnderTest(com_port, virtual)
    assert link.port_handler is not virtual

    com_port.chosen = "simulated audio port"
    com_port.is_using_the_stand_in = True
    link.use_port("simulated audio port")

    assert link._port_handler is virtual


def test_the_installation_is_not_offered_a_bench_test(monkeypatch, stub_factory):
    """It will never have Thomas's boards - they are in an office, and
    offering a run that can only refuse is worse than offering nothing.

    This used to be checked by reading the source of
    Tests.snapshot_children, because building the real thing needs the
    whole hardware graph (see conftest). Since the gate moved down to
    TestGroup - a plain Base with nothing behind it - the behaviour
    itself can be built and asked, which is worth more than a substring.
    """
    from colloquy.tests.group import TestGroup

    bench = stub_factory(name="test audio subsystem", is_started=False)
    ordinary = stub_factory(name="test search", is_started=False)

    group = TestGroup(
        owner=stub_factory(), name="autotests", summary="..."
    ).fill(tests=(ordinary, bench), bench_only=(bench.name,))

    set_hostname(monkeypatch, "Colloquy-Laptop")
    assert list(group.snapshot_children) == ["test search"]

    set_hostname(monkeypatch, "DESKTOP-MRSLS88")
    assert list(group.snapshot_children) == ["test search", "test audio subsystem"]


def fake_leads(monkeypatch, *devices):
    """What `boards.detect()` finds, without a USB bus.

    The picker names a lead by the chip bridging it to USB - see
    boards.py - so a Board, not a bare device name.
    """
    from colloquy.drivers.arduino.boards import Board

    monkeypatch.setattr(
        # The picker moved onto the shared bench base - see
        # colloquy/tests/bench_com_port.py, which both bench boards use.
        "colloquy.tests.bench_com_port.boards.detect",
        lambda: [
            Board(
                device=device,
                name="Arduino Mega 2560 (R3)",
                is_arduino=True,
                vid=0x2341,
                pid=0x0042,
                serial_number=None,
            )
            for device in devices
        ],
    )


def test_the_audio_port_picker_offers_the_stand_in_where_there_is_no_board(
    monkeypatch, stub_factory
):
    set_hostname(monkeypatch, "some-laptop")
    fake_leads(monkeypatch)
    picker = AudioComPort(owner=stub_factory())

    assert picker.ports == ["simulated audio port"]


def test_the_audio_port_picker_offers_real_leads_on_the_bench(monkeypatch, stub_factory):
    set_hostname(monkeypatch, "DESKTOP-MRSLS88")
    fake_leads(monkeypatch, "COM3", "COM7")
    picker = AudioComPort(owner=stub_factory())

    # The stand-in comes last: on a machine with a board plugged into it,
    # the board is the answer. The bench is `is_simulated`, so it is
    # offered - it is what you pick to rehearse the run without the board.
    assert picker.ports == ["COM3", "COM7", "simulated audio port"]


def test_the_audio_port_picker_offers_real_leads_on_the_installation(
    monkeypatch, stub_factory
):
    """The afternoon this whole change is for.

    Thomas's board is carried to the installation's laptop so the 12 V
    pass can be run beside the piece. Asking `is_bench` here listed one
    stand-in and nothing else, and two passes against a simulator differ
    by nothing - which reads exactly like a rail change that bought you
    nothing. There is no stand-in on this machine: `is_simulated` is
    False, so the only thing offered is the board actually plugged in.
    """
    set_hostname(monkeypatch, "Colloquy-Laptop")
    fake_leads(monkeypatch, "COM9")
    picker = AudioComPort(owner=stub_factory())

    assert picker.ports == ["COM9"]


def test_the_picker_draws_the_chip_and_stores_the_com_number(monkeypatch, stub_factory):
    """Which COM number Windows handed out this week is not a fact worth
    carrying in anybody's head; which board it is, is. So the label is
    what the page draws and the device is what gets stored."""
    set_hostname(monkeypatch, "Colloquy-Laptop")
    fake_leads(monkeypatch, "COM9")
    picker = AudioComPort(owner=stub_factory())

    drawn = list(picker.snapshot_children)

    assert drawn == ["COM9 - Arduino Mega 2560 (R3)"]
    assert picker.ports == ["COM9"]


def test_the_stand_in_is_named_by_the_lead_not_the_machine(monkeypatch, stub_factory):
    """`is_using_the_stand_in` is one property and it reads params."""
    set_hostname(monkeypatch, "DESKTOP-MRSLS88")
    owner = stub_factory()
    owner.params = {"audio subsystem": {"communication port": "simulated audio port"}}
    picker = AudioComPort(owner=owner)

    assert picker.is_using_the_stand_in is True

    owner.params["audio subsystem"]["communication port"] = "COM7"
    assert picker.is_using_the_stand_in is False


def test_a_port_remembered_from_another_machine_is_refused(monkeypatch):
    """params outlives the machine that wrote it.

    A laptop that ran this simulated leaves "simulated audio port" in
    params.json. Carried to the bench, that opens nothing and fails with
    a pyserial error naming a port nobody recognises. Found exactly that
    way, on the bench, with the value still in the file.
    """
    refused = []
    double = SimpleNamespace(
        params={"audio subsystem": {"communication port": "simulated audio port"}},
        com_port=SimpleNamespace(ports=["COM3", "COM7"]),
        _refuse=refused.append,
        _start_time=None,
        _verdicts={},
        _silence=None,
        _outcome=None,
        _manual_reply=None,
        _buffer="",
        _file=io.StringIO(),
    )
    double._why_not_open = lambda: AudioSubsystemTest._why_not_open(double)

    AudioSubsystemTest.setup(double)

    assert refused, "a stale port should be refused, not opened"
    assert "simulated audio port" in refused[0]
    assert "COM3" in refused[0]


def test_a_manual_command_refuses_the_same_stale_port(monkeypatch):
    """The traceback this was split out for.

    The check lived only in setup(), so the manual commands - which are
    how somebody at a bench holds one tone while they listen for it -
    went straight at pyserial and raised
    `SerialException: could not open port 'COM5'` out of a request. The
    server read that as a crash worth emergency-stopping the
    installation and left the loop. A stale port name is not that.
    """

    def must_not_be_opened():
        raise AssertionError("opened a port that is not on this machine")

    double = SimpleNamespace(
        params={"audio subsystem": {"communication port": "COM5"}},
        com_port=SimpleNamespace(ports=["COM6"]),
        _port_handler=None,
        _manual_reply=None,
        port_handler=SimpleNamespace(open=must_not_be_opened, is_open=False),
    )
    double._why_not_open = lambda: AudioSubsystemTest._why_not_open(double)

    reply = AudioSubsystemTest._send_manual(double, "e a")

    assert reply.startswith("refused: ")
    assert "COM5" in reply
    assert "COM6" in reply
    assert reply == double._manual_reply
