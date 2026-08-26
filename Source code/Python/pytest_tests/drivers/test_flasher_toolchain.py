"""Finding arduino-cli, and what it is asked to do.

The part of flashing worth being sure about is which program gets run
with which arguments. None of it needs a board, a serial port or a
running installation, which is the reason it is a module of its own -
same split as `repository/git.py`.

Nothing here actually runs arduino-cli. Two tests below build a command
line and read it; the rest is search order and message quality.
"""
from pathlib import Path

import pytest

from colloquy.drivers.arduino.flasher import toolchain
from colloquy.drivers.arduino.flasher.toolchain import Result, ToolchainError


# --- where it looks, and in what order -----------------------------------


def test_the_params_override_is_tried_before_anything_else():
    """A machine with it somewhere odd says so once, instead of being
    argued with every time."""
    found = toolchain.candidates(override="/somewhere/odd/arduino-cli")

    assert found[0] == Path("/somewhere/odd/arduino-cli")


def test_the_arduino_ide_copy_is_a_candidate():
    """The one that makes this work without asking anybody to install
    anything: the IDE ships arduino-cli, and anybody who has ever flashed
    this board from the IDE already has it, with the AVR core and both
    libraries."""
    found = [str(path) for path in toolchain.candidates()]

    assert any("Arduino IDE" in path or "arduino-ide" in path for path in found)


def test_no_override_means_no_extra_candidate():
    assert len(toolchain.candidates()) == len(toolchain.candidates(override=None))
    assert len(toolchain.candidates(override="x")) > len(toolchain.candidates())


def test_finding_nothing_says_where_it_looked(tmp_path, monkeypatch):
    """The only moment anybody wants the search list is the moment it
    came up empty - so it is in the message rather than in a log."""
    monkeypatch.setattr(toolchain, "candidates", lambda override=None: [tmp_path / "nope"])

    with pytest.raises(ToolchainError) as raised:
        toolchain.find()

    assert "nope" in str(raised.value)
    assert "arduino-cli" in str(raised.value)


def test_find_returns_the_first_one_that_is_actually_there(tmp_path, monkeypatch):
    missing = tmp_path / "missing"
    present = tmp_path / "present"
    present.write_text("", encoding="utf-8")
    monkeypatch.setattr(toolchain, "candidates", lambda override=None: [missing, present])

    assert toolchain.find() == present


# --- the config file -----------------------------------------------------


def test_the_ide_config_is_added_only_when_it_exists(monkeypatch, tmp_path):
    """A properly installed arduino-cli has its own config in its own
    place and must be left to use it. This flag exists for the bundled
    binary, which otherwise reports a correct-sounding 'arduino:avr is not
    installed' about a machine that plainly has it."""
    exe = tmp_path / "arduino-cli"

    monkeypatch.setattr(toolchain, "config_file", lambda: None)
    assert toolchain.base_command(exe) == [str(exe)]

    monkeypatch.setattr(toolchain, "config_file", lambda: tmp_path / "cli.yaml")
    assert toolchain.base_command(exe) == [
        str(exe),
        "--config-file",
        str(tmp_path / "cli.yaml"),
    ]


# --- the command lines ---------------------------------------------------


def test_a_compile_names_the_board_and_the_sketch_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(toolchain, "config_file", lambda: None)
    command = toolchain.compile_command(
        tmp_path / "arduino-cli", tmp_path / "sketch", "arduino:avr:mega"
    )

    assert command[1:] == ["compile", "--fqbn", "arduino:avr:mega", str(tmp_path / "sketch")]


def test_a_compile_alone_never_names_a_port(tmp_path, monkeypatch):
    """The safe half. It touches nothing but a temporary folder, which is
    what makes it worth offering with no refusals at all."""
    monkeypatch.setattr(toolchain, "config_file", lambda: None)
    command = toolchain.compile_command(tmp_path / "cli", tmp_path / "sketch", "fq")

    assert "--port" not in command
    assert "--upload" not in command


def test_an_upload_compiles_and_uploads_in_one_command(tmp_path, monkeypatch):
    """Two commands would leave a window in which the second sends
    whatever the last build happened to leave behind. One command means
    the image that reaches the board was necessarily built from this
    sketch, just now."""
    monkeypatch.setattr(toolchain, "config_file", lambda: None)
    command = toolchain.upload_command(
        tmp_path / "cli", tmp_path / "sketch", "arduino:avr:mega", "COM7"
    )

    assert command[1] == "compile"
    assert "--upload" in command
    assert command[command.index("--port") + 1] == "COM7"


def test_the_default_board_is_the_mega():
    assert toolchain.DEFAULT_FQBN == "arduino:avr:mega"


def test_an_upload_is_given_less_rope_than_a_compile():
    """A compile that is killed early wastes a minute. An upload killed
    early leaves a half-written flash - but it also cannot legitimately
    take five minutes, so it gets its own shorter limit."""
    assert toolchain.UPLOAD_TIMEOUT < toolchain.COMPILE_TIMEOUT
    assert toolchain.UPLOAD_TIMEOUT > 60


# --- reading the output --------------------------------------------------


def test_the_tail_is_the_end_because_that_is_where_the_news_is():
    output = "\n".join(["library path " + str(n) for n in range(40)] + ["Sketch uses 19922 bytes"])

    assert "Sketch uses 19922 bytes" in toolchain.summarise(output)
    assert "library path 0" not in toolchain.summarise(output)


def test_blank_output_says_so_rather_than_rendering_empty():
    assert toolchain.summarise("") == "no output"
    assert toolchain.summarise("\n  \n") == "no output"


@pytest.mark.parametrize(
    "output, expected",
    [
        ("Error: platform arduino:avr is not installed", "Boards Manager"),
        ("fatal error: Adafruit_NeoPixel.h: No such file or directory\nlibrary", "ArduinoJson"),
        ("avrdude: ser_open(): can't open device COM7: Access is denied.", "serial monitor"),
        ("avrdude: stk500v2_ReceiveMessage(): programmer is not responding", "Wrong port"),
    ],
)
def test_the_four_known_failures_become_instructions(output, expected):
    """arduino-cli's own messages are good; these four are worth turning
    into something to do. Everything else is handed on as it stands,
    because guessing at it would be worse than quoting it."""
    assert expected in toolchain.explain(Result(ok=False, output=output))


def test_an_unrecognised_failure_is_quoted_not_guessed_at():
    result = Result(ok=False, output="Error: something nobody has seen before")

    assert toolchain.explain(result) == "Error: something nobody has seen before"
