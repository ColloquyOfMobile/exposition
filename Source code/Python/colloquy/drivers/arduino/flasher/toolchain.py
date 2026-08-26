# -*- coding: utf-8 -*-
# Source code/Python/colloquy/drivers/arduino/flasher/toolchain.py

"""Finding `arduino-cli`, and running it. No node, no thread, no port.

Split out for the same reason `repository/git.py` is: the part worth
being sure about is which program gets run with which arguments, and none
of that needs a board, a serial port or a running installation to test.

**Why `arduino-cli` and not avrdude directly.** avrdude would be fewer
moving parts and it is the wrong trade: it needs a `.hex` that somebody
has already built, which puts the compile somewhere else and makes it
possible to flash a stale binary. Compiling and uploading from the same
`.ino` in one command is the whole point - the sketch in the repo is the
sketch on the board, and `firmware.py` already reads its version out of
that same file.

**Where it looks.** In order, and the order is deliberate:

1. whatever `params["arduino"]["arduino-cli"]` names, if anything - so a
   machine with it somewhere odd can say so once instead of being argued
   with;
2. `arduino-cli` on PATH, for a machine where it was installed properly;
3. **the copy inside the Arduino IDE**, which is the one that is actually
   on the machines here. The IDE ships `arduino-cli` and drives it; it is
   a normal executable in a predictable place, and anybody who has ever
   flashed this board from the IDE already has it, along with the AVR
   core and the two libraries the sketch needs.

That third one is why this can work at all without asking anybody to
install anything, and it comes with a catch worth knowing: the IDE keeps
its cores and libraries under its *own* configuration, not under the
default `arduino-cli` one. Run the bundled binary without pointing it at
`~/.arduinoIDE/arduino-cli.yaml` and it reports a perfectly correct "the
platform arduino:avr is not installed" about a machine that plainly has
it. Hence `config_file()`.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import NamedTuple

# What the board is, in arduino-cli's vocabulary. A Mega 2560 with the
# ATmega2560 on it, which is the default cpu for this fqbn - written
# short because that is what the IDE's own board menu produces, and a
# person comparing the two should see the same string.
DEFAULT_FQBN = "arduino:avr:mega"

# Compiling a sketch with the NeoPixel and JSON libraries from cold takes
# most of a minute on a laptop; uploading 20 KB over a 115200 bootloader
# link takes about ten seconds. Both are generous, because the cost of
# being wrong differs: a compile that is killed early wastes a minute,
# and an *upload* killed early leaves a half-written flash.
COMPILE_TIMEOUT = 300
UPLOAD_TIMEOUT = 180
VERSION_TIMEOUT = 20

# Don't flash a console window on Windows for each subprocess. Zero is
# "no special flags" everywhere else; Popen rejects a non-zero
# creationflags off Windows. Same reasoning as repository/git.py.
_CREATION_FLAGS = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0


class ToolchainError(Exception):
    """arduino-cli could not be found or could not be run.

    Shown on the page as a reading, never raised out of a thread - a
    laptop without the Arduino IDE on it is a normal thing, not a fault in
    the installation.
    """


class Result(NamedTuple):
    """One arduino-cli run, as far as anybody here cares."""

    ok: bool
    output: str

    @property
    def tail(self) -> str:
        """The last few lines, which is where both the good news and the
        bad news are: a successful compile ends with its size report, and
        a failed one ends with the error. The middle is library paths."""
        return summarise(self.output)


def _ide_candidates() -> list[Path]:
    """Where the Arduino IDE keeps its copy, per platform.

    Guesses, and they cost nothing when wrong: each is checked for
    existence before it is offered, and `find()` says what it looked at
    when none of them are there.
    """
    tail = Path("resources/app/lib/backend/resources")
    if sys.platform == "win32":
        roots = [
            Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Arduino IDE",
            Path(os.environ.get("PROGRAMFILES", "")) / "Arduino IDE",
        ]
        return [root / tail / "arduino-cli.exe" for root in roots if str(root) != tail.name]
    if sys.platform == "darwin":
        return [Path("/Applications/Arduino IDE.app/Contents") / tail / "arduino-cli"]
    return [
        Path.home() / ".local/share/arduino-ide" / tail / "arduino-cli",
        Path("/opt/arduino-ide") / tail / "arduino-cli",
    ]


def candidates(override: str | Path | None = None) -> list[Path]:
    """Everywhere this will look, in order, whether or not it is there.

    Returned as a list rather than kept inside `find()` so the page can
    show what was searched when the answer is "nowhere" - which is the
    only moment anybody wants to know.
    """
    found: list[Path] = []
    if override:
        found.append(Path(override))
    on_path = shutil.which("arduino-cli")
    if on_path:
        found.append(Path(on_path))
    found.extend(_ide_candidates())
    return found


def find(override: str | Path | None = None) -> Path:
    """The first candidate that exists. Raises ToolchainError if none do."""
    looked = candidates(override)
    for candidate in looked:
        if candidate.is_file():
            return candidate
    raise ToolchainError(
        "no arduino-cli on this machine. Install the Arduino IDE (which "
        "ships one), or put arduino-cli on PATH, or name it in params "
        'under arduino / "arduino-cli". Looked at: '
        + "; ".join(str(path) for path in looked)
    )


def config_file() -> Path | None:
    """The Arduino IDE's own arduino-cli config, if this machine has one.

    Only ever *added* to a command line, never required: a properly
    installed arduino-cli has its own config in its own place and must be
    left to use it. This exists for the bundled binary, which otherwise
    cannot see the cores and libraries the IDE installed for it.
    """
    path = Path.home() / ".arduinoIDE" / "arduino-cli.yaml"
    return path if path.is_file() else None


def base_command(executable: Path) -> list[str]:
    config = config_file()
    command = [str(executable)]
    if config is not None:
        command += ["--config-file", str(config)]
    return command


def compile_command(executable: Path, sketch: Path, fqbn: str) -> list[str]:
    """Build the sketch, and build it where arduino-cli likes to.

    The sketch *folder* is passed, not the .ino, because that is what
    arduino-cli takes - and it is also the honest unit: the folder is the
    sketch, and a folder whose name does not match its .ino is a thing
    arduino-cli refuses on its own terms with a clear message.
    """
    return base_command(executable) + ["compile", "--fqbn", fqbn, str(sketch)]


def upload_command(executable: Path, sketch: Path, fqbn: str, port: str) -> list[str]:
    """Compile and upload in one go.

    `--upload` on the compile rather than a separate `upload` command, so
    the binary that reaches the board is necessarily the one that was
    just built from this sketch. Two commands would leave a window in
    which the second uploads whatever the last build left behind.
    """
    return base_command(executable) + [
        "compile",
        "--fqbn",
        fqbn,
        "--upload",
        "--port",
        port,
        str(sketch),
    ]


def run(command: list[str], timeout: float) -> Result:
    """One arduino-cli run. Never raises for a non-zero exit.

    stderr is folded into stdout because arduino-cli writes its
    progress to one and its complaints to the other, and reading them
    apart tells a person nothing they want to know.
    """
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=_CREATION_FLAGS,
        )
    except FileNotFoundError as error:
        raise ToolchainError(f"could not run {command[0]}") from error
    except subprocess.TimeoutExpired as error:
        raise ToolchainError(
            f"arduino-cli gave no answer within {timeout:.0f}s"
        ) from error
    except OSError as error:
        raise ToolchainError(f"could not run arduino-cli: {error}") from error

    output = (completed.stdout or "") + (completed.stderr or "")
    return Result(ok=completed.returncode == 0, output=output.strip())


def summarise(output: str, lines: int = 6) -> str:
    """The last few non-empty lines of an arduino-cli run.

    A page reading, not a log: the full output is tens of lines of
    library paths, and the thing worth reading is at the end either way -
    the size report on success, the error on failure.
    """
    kept = [line.strip() for line in output.splitlines() if line.strip()]
    if not kept:
        return "no output"
    return " / ".join(kept[-lines:])


def explain(result: Result) -> str:
    """A failed run, in one sentence, when the failure is one we know.

    arduino-cli's own messages are good, and three of them are worth
    turning into an instruction rather than passing on: the two that mean
    "the IDE has this and you did not point at its config" and the one
    that means somebody else is holding the port. Everything else is
    handed on as it stands, because guessing at it would be worse.
    """
    text = result.output.lower()

    if "platform" in text and "not installed" in text:
        return (
            "the AVR core is not installed for this arduino-cli. In the "
            "Arduino IDE: Boards Manager, 'Arduino AVR Boards'. "
            + result.tail
        )
    if "no such file or directory" in text and "library" in text:
        return (
            "a library the sketch includes is missing - it wants "
            "Adafruit NeoPixel and ArduinoJson. " + result.tail
        )
    if "access is denied" in text or "resource busy" in text or "permission denied" in text:
        return (
            "the port is held by something else. Close the Arduino IDE's "
            "serial monitor, and any other copy of this program. "
            + result.tail
        )
    if "can't open device" in text or "programmer is not responding" in text:
        return (
            "the board did not answer its bootloader. Wrong port, wrong "
            "board type, or a lead that only carries power. " + result.tail
        )
    return result.tail
