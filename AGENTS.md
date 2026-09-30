# Repository Guidelines

## Project Structure & Module Organization

This repository controls the Colloquy of Mobiles kinetic installation.

- `main.py` starts the Python application and web interface.
- `Source code/Python/colloquy/` contains drivers, behaviors, the `Base` object tree, and UI code; browser assets live in `ui/static/`.
- `Source code/Python/pytest_tests/` holds automated tests. `colloquy/tests/` contains interactive hardware tests exposed through the UI.
- `Source code/Arduino/` holds sketches; `Source code/Thomas/` contains the audio subsystem's C++ sources.
- `CAD/` holds mechanical/electronics designs; `docs/` holds references and recorded results.
- `local/` contains ignored calibration, parameters, and runtime output. Preserve it.

## Build, Test, and Development Commands

Run commands from the repository root; quote paths containing spaces. The Python application has no separate build step.

| Command | Purpose |
| --- | --- |
| `py -m pip install -r requirements.txt -r requirements-dev.txt` | Install listed runtime and development dependencies. |
| `py main.py` | Start the application at `http://localhost:8087/`. |
| `py -m pytest` | Run the configured automated suite. |
| `py -m pytest --cov=colloquy --cov-report=term-missing` | Report coverage and uncovered lines. |
| `py -m ruff check .` | Check Pyflakes and syntax rules. |
| `py -m mypy` | Check explicitly scoped modules; install mypy separately. |

Dependency lists are incomplete: imports also require packages such as `pyserial` and `matplotlib`; the `test_process.py` watcher requires `watchdog`.

## Coding Style & Naming Conventions

Follow existing Python style: four-space indentation, `snake_case` functions/modules, `PascalCase` classes, and `UPPER_CASE` constants. Keep formatting changes local; Ruff currently configures linting, not a formatting policy. Add useful annotations without expanding mypy's scope indiscriminately.

Register tree children and commands with `self["name"] = child_or_callable`. Preserve driver/virtual-driver boundaries. Leave `#`-prefixed archived paths untouched.

## Testing Guidelines

Name pytest files and functions `test_*`; mirror the relevant subsystem directory. Read `pytest_tests/conftest.py`: use small doubles, never start `BaseThread` instances or construct the real hardware object graph. Run the suite after changing `colloquy/`. No minimum coverage threshold is configured. Record hardware validation separately; simulation does not establish physical behavior.

## Commit & Pull Request Guidelines

Use focused commits with imperative, descriptive subjects, as in `Keep a scope run's node between requests, so paging works`. History does not use Conventional Commit prefixes consistently. Check status and preserve unrelated work; consult `CLAUDE.md` for synchronization guidance.

PR descriptions should explain the problem, behavior change, validation commands/results, and hardware impact. Link relevant issues and include screenshots for UI changes.
