# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

"Colloquy of Mobiles" is a kinetic art installation (currently being prepared for exhibition at ZKM). Anthropomorphic "male" and "female" mobiles move along a motorized bar, driven by Dynamixel servos and controlled through an Arduino for LEDs/light sensors. This repo holds the control software (Python), the Arduino firmware, and CAD/electronics design files (KiCad/Eagle/FreeCAD/Blender). Most day-to-day code work happens under `Source code/Python`.

## Running the software

From the repo root:

```
py main.py
```

This calls `colloquy1()` in `main.py`, which:
1. Builds a `Colloquy` object (`Source code/Python/colloquy/__init__.py`)
2. Opens the U2D2 (Dynamixel USB adapter) on `COM4` and the Arduino serial port, and initializes every Dynamixel servo
3. Blinks all NeoPixels once (Arduino reboot can leave LEDs on in a random state)
4. Starts `Server2`, a blocking WSGI server on `http://localhost:8087/`

There is no separate build step (pure Python, no bundler). `requirements.txt` only lists `yattag` (HTML generation) and `dynamixel_sdk`; `pyserial`, `watchdog`, etc. are used but not currently pinned there — check imports if `pip install -r requirements.txt` isn't enough.

`process_csv.py` (dev helper, hardcodes local Windows paths) does majority-vote smoothing over a light-sensor CSV column and writes `<name>_averaged.csv` next to the input.

`test_process.py` is a file-watcher dev loop: it restarts `py -u main.py` on every `.py` change under the watched folder (also strips trailing whitespace on save). It is not a pytest suite despite the name.

**`main.py` currently has `test_process.py`-adjacent debt**: nothing else in the repo runs it as a module; treat it as the entrypoint but expect rough edges (e.g. `Colloquy.close()` raises `NotImplementedError`).

## Simulated vs. real hardware

`Base.is_simulated` (`Source code/Python/colloquy/base.py`) checks `socket.gethostname() == 'Colloquy-Laptop'`. On that exact machine the code drives real Dynamixel servos and a real Arduino over serial; on every other machine (including CI, dev laptops) it transparently runs against `Source code/Python/colloquy/virtual_hardware/` — virtual serial port, virtual packet/port handlers, virtual Dynamixels. This means the whole app (including the web UI) can be exercised without hardware attached. When adding hardware-facing code, keep the real/virtual split intact rather than special-casing simulation inline.

## Architecture: the `Base` object tree

Nearly everything in `colloquy/` is a node in one big tree rooted at the `Colloquy` object, built from two base classes:

- **`Base`** (`colloquy/base.py`): dict-like node (`__getitem__`/`__setitem__`/`__contains__`/`__iter__` over an internal `_dict`) with an `owner` (parent) pointer, a computed `path` (slash-joined name chain to the root), and a `snapshot(path, focus_path)` method that recursively serializes the tree into a dict the web UI renders. Nodes register their children/commands into themselves (`self["some name"] = some_child_or_callable`) rather than using a separate registry.
- **`BaseThread`** (`colloquy/base_thread/__init__.py`), extends `Base`: anything that runs its own background loop (hardware controllers, search behaviors, drives, the whole `Colloquy` object). Subclasses implement `setup()`, `loop()`, `setdown()`; the base class runs them in a `Thread` via `start()`/`stop()`/`join()` with cooperative shutdown (`_stop_event`, class-level `_shutdown` Event shared by all threads) and per-node error capture (`ThreadErrors`) that halts the thread's loop without crashing the process.
- **`BaseHTML`** (`colloquy/base_html.py`): wraps a `Base`/`BaseThread` node to render it as an HTML fragment for the web UI.

Both `Base.__call__`-style dispatch and the web request router work the same way throughout the codebase: a request path is split into `Path(request).parts`, the first part is looked up as a key in `self`, and dispatch recurses (`self[key](request="/".join(leftover))`); an unmatched key raises `NotImplementedError`. This pattern repeats near-verbatim across `Hardware`, `Arduino`, `U2D2`, `Female`, `DXL`, `VirtualHardware`, etc. — when adding a new command/child node, register it in `__init__` via `self[name] = handler_or_child` rather than inventing a new dispatch mechanism.

## The web UI / server (`server2`, `wsgi2.py`)

`Server2` (`colloquy/server2/__init__.py`) runs `wsgiref.simple_server` on port 8087 and hands each request to `WSGI2` (`colloquy/server2/wsgi2.py`), which:
- Parses the URL path into `app/...`, `shutdown`, or `restart`
- Calls `colloquy.get_states(*args)` (defined in `colloquy/__init__.py`) which walks the `Base` tree via `snapshot_children`/`snapshot`, optionally executing an update (calling a command) if the path resolves to a callable leaf
- Renders the resulting nested-dict "state" recursively as clickable HTML (`yattag`) — every node is a link that opens/closes it or calls it; this is effectively a generic tree browser/REPL for the whole hardware+behavior graph, not a purpose-built dashboard
- `/shutdown` stops all threads, homes the bodies/bar, disables torque, and sets a shutdown event; `/restart` re-execs the process (`os.execl`) after shutdown

There is no templating framework beyond `yattag`; new UI is added by adding `snapshot_children` / registering new command names on the relevant `Base` node, not by writing new routes.

**Working on the UI**: `py mock_ui.py` serves the same server and renderer against `colloquy/ui/mock.py` — a handful of nodes covering every kind of leaf and link, with no servos, Arduino, threads or params behind them. It listens on **8088**, not the installation's 8087, so it can run alongside `main.py`. `colloquy.ui.mock.request(path)` drives the same thing from a test with no socket at all (see `pytest_tests/ui/test_mock_app.py`), and `colloquy/ui/tree.py` is the path-walk both roots share — `Colloquy.get_states()` is a one-line delegation to it.

The snapshot dict is the **whole contract** between the tree and the page, and `colloquy/ui/leaves.py` is where its vocabulary is defined — one constructor per kind of thing the page can draw (`value`, `html`, `chart`, `svg`, `pre`, `editor`), plus `into(states, path)` for a node with several readings to show. Build leaves with those rather than hand-writing `{"path": ..., "name": ..., "value": ...}`; a kind that isn't in `leaves.KINDS` is one the renderer will not draw. Two things in a snapshot are *not* leaves: child nodes (from `snapshot_children`) and commands (bare callables, rendered as links that call them through the `call` path segment).

## Hardware domain model (`colloquy/hardware/`)

- `Hardware` (`hardware/__init__.py`) owns: `Arduino`, `U2D2` (Dynamixel bus), 3 `Female` bodies, 2 `Male` bodies, a `Bar` (the rail the mobiles ride on), `AllNeopixels`, `Bodies` (groups males+females for bulk operations like homing).
- `U2D2` wraps `dynamixel_sdk` (`PortHandler`/`PacketHandler`) and owns 9 `DXL` servo objects, mapped by name: `female1/2/3`, `male1/2`, `bar` (see `dxl_ids`/`_dxls` in `hardware/__init__.py` and `u2d2/__init__.py`). Real vs. virtual `PacketHandler`/`PortHandler` is selected via `is_simulated`.
- `DXL` (`hardware/dxl/__init__.py`) models one Dynamixel servo's registers (`position`, `goal_position`, `torque_enabled`, `profile_velocity`, etc.) as individual `RegisterHanlder` children read/written through `U2D2.read_1_byte`/`write_4_bytes`/etc. `handle_error` (in `u2d2/__init__.py`) wraps every raw SDK call with retry + logging on comm/servo errors. Position registers are read **signed** (`signed=True` on the register): every servo runs in extended position mode, where positions either side of the servo's zero are normal, and the SDK reads them back as an unsigned dword.
- **Angles, not servo units** (`hardware/angle/`): nothing outside `hardware/angle/` and `hardware/dxl/` should compute a servo position. Each moving thing owns an `Angle` node — `female1.angle`, `male1.angle`, `bar.angle`, `female1.mirror1.angle` — measured in **degrees of the body itself**, zero at its calibrated origin, signed. `angle/conversion.py` holds the two facts it needs: 4096 units to a servo turn, and the reduction (`REDUCTIONS`: a female and the bar turn **three times slower** than their servo; a male and a mirror turn with theirs). So the same 2000 servo units are 175.8° of male but 58.6° of female — write degrees and that stops mattering. Bodies keep `turn_to_origin()`/`turn_to_max_position()`/`toggle_position()`, now expressed as angles (`Female._sweep`, `Bar._travel`), plus `turn_to(degrees)`.
- `Mirror` (`hardware/mirror/`): one per female (`female1.mirror1`), on the dxl ids the females and males leave free (2, 4, 6). Nothing drives it yet — it exists to be calibrated and jogged. It is a plain `Base`, not a thread, and nothing initialises it at startup, so unwired mirror servos cost nothing.
- `Female`/`Male` (`hardware/female/`, `hardware/male/`) each own their `DXL`, `Drives` (behavioral state — "O drive"/"P drive", see `light_patterns` in `colloquy/__init__.py` for the blink-pattern encoding used during search), `Search` (seeking behavior), `Neopixels`, and a `LightSensor`.
- `Arduino` (`hardware/arduino/__init__.py`) talks over a JSON-line serial protocol (`{"path": ..., ...}\n`, response parsed as JSON) to a single `.ino` sketch (`Source code/Arduino/colloquy_of_mobiles/colloquy_of_mobiles.ino`) that fans out to NeoPixel strips (per-body head/bodyO/bodyP/feet/ring/up-ring segments) and analog light sensors. Each addressable strip segment / sensor is a `NeopixelCommand`/`LightSensorCommand` child registered by `arduino_path` (e.g. `"f1/head"`, `"m1/light sensor/a"`) — when the firmware gains a new pixel group or sensor, add both the `.ino`-side handler and a matching `*Command` entry here.

## Male blink pattern / female pattern reading (morse-code identity signal)

Each male sends his ring a 10-bit on/off pattern — a morse-code-like signal encoding (a) which male he is (`male1`/`male2`) and (b) which drive state he currently wants (`O`, `P`, both, or neither) — then holds the ring dark until the next one is due. The 4 reference sequences per male live in `Colloquy.light_patterns` (`colloquy/__init__.py`); the clock they are sent on lives in `colloquy/light_pattern_timing.py`, which carries TJ's numbers and where each one comes from: 0.2s per bit, so a 2s burst, repeating every 4.35s and leaving 2.35s of silence. **The silence is part of the message** — it frames the burst, so a reading that straddles it fails instead of decoding as some rotation of the pattern. Write side: `hardware/male/__init__.py`'s `Male.get_blink_pattern()` picks the sequence for `self.drives.which_is_frustated()`, and `hardware/male/search/blink/__init__.py`'s `Blink.loop()` reads it **once per burst** (a drive state that changes mid-burst takes effect at the next burst, never mid-pattern), writing each bit to `male.ring` as it changes. Read side: `hardware/female/search/read_pattern/__init__.py`'s `ReadPattern` samples the female's light sensor as a boolean, buffers samples, and tries every sub-step sample offset and circular rotation of each candidate against `colloquy.light_patterns` (majority vote per bin, tolerating `max_mismatches` bit errors) to decode which male + requested drive state she's facing.

`hardware/female/search/__init__.py`'s `Search.loop()` sways the female (mirroring `Male.search`'s toggle-position loop) and `setup()` starts `read_pattern` (`started_by=self`, so it stops automatically when `search` stops) — this is what `Female.loop()` triggers whenever a female becomes unsatisfied, so pattern-reading now runs autonomously as part of the live app, not just standalone. `ReadPattern` can still be started/stopped independently via its own web-UI node for isolated testing (see `colloquy/tests/test_read_pattern`). Also note `colloquy/tests/test_light_sensor_values/*` test scenarios do **not** exercise this decode logic — they log/plot raw analog light-sensor values and threshold-crossing pulse durations, a proxy for body-alignment/visibility timing, not pattern-decode accuracy. The exception in kind is `test_for_false_positives`, which runs with **every light off** and plots each female's reading against the angle she was pointing at (average and spread per angle) — it asks whether the room itself can make her read "light", which is the input side of that same threshold (SCENARIOS 5.6, 8.2). `test_with_everything_moving` specifically holds male rings at a **constant steady ON** (not blinking any pattern) — treat its results as "how long is a female facing a lit male," not "can she read his pattern."

## Parameters and persisted state (`local/`)

- `colloquy/params.py`'s `Params` is a `dict` subclass that auto-persists to JSON on every mutation (`local/params.json`), recursively wrapping nested dicts so deep edits also trigger a save. `DEFAULTS` in the same file documents the expected shape (servo origins per body, bar interaction origins per male/female pair, arduino baud rate, sensor thresholds).
- **Units in `params.json`**: `"dxl origin"` is in raw servo units — it is the reading a body gives when it points where it should. *Everything else is in degrees of the body*: `"motion range"` (how far it travels end to end — a body sways half of it either side of its origin, the bar runs from its origin to the far end), the bar's `interaction_origins` and `"motion range around female1"`, and the simulator's `near origin threshold` (per kind, since the reductions differ). Ranges are read from params on every use, so editing one on the params page takes effect on the next sway rather than at the next restart.
- The file is **versioned** (`"params version"`, `PARAMS_VERSION`). `Params.load()` runs `migrate()`, which converts an older file (backing it up as `local/params.json.v<n>.bak` first — it is the calibration of a physical installation) and fills in any key the file predates. Add a new key to `DEFAULTS` and existing installations get it; changing the *meaning* of a key needs a version bump and a branch in `migrate()`.
- `local/` also holds runtime logs (`local/logs/<thread-name>.log`, rotated at ~2000 lines by `colloquy/logger.py`, whose log folder is **wiped on process start**), recorded test data, and video captures — all git-ignored working state, not source.

## Old/inactive code: the `#`-prefixed convention

Several directories and files are prefixed with `#` (e.g. `Source code/Python/# app2/`, `colloquy/# threads/`, `colloquy/tests/# test2.py`). A leading `#` makes the path an invalid Python identifier, so these are inert by construction — they are archived previous implementations kept for reference during the ongoing refactor, not dead code to silently delete or partially resurrect. Don't import from them; if functionality is missing versus a `#`-prefixed sibling, treat it as intentionally not-yet-ported rather than a bug.

## Git workflow: two computers, keep in sync

The user works on this repo from two different computers. Uncommitted or unpushed work from the other machine is easy to accidentally shadow or lose.

- **Before starting any work in a session**, run `git status` and `git fetch` and compare local `HEAD` to `origin/<current-branch>`. If the remote has commits not present locally, pull (merge or rebase, whichever keeps history clean — ask the user if a conflict would result) before making edits, so you're never editing on top of a stale tree.
- **Periodically re-check** (e.g. before starting a new task within a long session), since the other computer may push while this session is running.
- **After every edit you make**, commit it — don't let changes accumulate uncommitted across a session. Use small, focused commits with clear messages describing the "why", following the repo's existing commit style (see `git log`).
- **Push after committing** so the other computer can pick up the change, unless the user says otherwise.
- If `git status` shows unexpected local changes at the start of a session (likely from the other computer's uncommitted work, e.g. synced via a shared drive), do not discard them — stash or commit them first, and flag it to the user.

## Testing

There are two separate things called tests here, and they do not overlap.

**`Source code/Python/pytest_tests/`** is a real pytest suite (~200 pure-logic unit tests, runs in ~2s: `py -m pytest "Source code/Python/pytest_tests"` from the repo root). It never touches hardware, threads or the filesystem — read `pytest_tests/conftest.py` first, it states the rules (never `.start()` a `BaseThread`, never build the real `Colloquy`/`Hardware` object graph, prefer small duck-typed doubles or unbound-method calls). **Run it after changing anything under `colloquy/`** — several of these tests pin behaviour that is easy to break from a distance, e.g. the light-pattern tables and `ReadPattern`'s decode.

**`colloquy/tests/`** is the other kind: interactive behavioral scenarios (`test1`, `test_drive_light_values`, `test_light_sensor_values`, `test_male_patterns`, `test_neopixels`) exposed as nodes in the same `Base` tree and driven through the web UI like any other hardware command — they exercise real or virtual hardware over time (e.g. logging light sensor values while bodies move) rather than asserting pure functions. When asked to "test" something in this codebase, check whether an existing scenario under `colloquy/tests/` already covers it before writing a new one, and follow the same `BaseThread`/`snapshot_children` pattern.
