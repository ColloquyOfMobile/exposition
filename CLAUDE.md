# CLAUDE.md

Guidance for Claude Code in this repository. This is the compact version; the long form, with the incident behind each rule, is in git history: `git show 0b8b7b6:CLAUDE.md`.

## What this is

"Colloquy of Mobiles" is a kinetic art installation being prepared for exhibition at ZKM. Three "female" and two "male" mobiles plus a motorized bar, driven by Dynamixel servos (through a U2D2) and an Arduino Mega (NeoPixels, light sensors, voices, microphone analysers). The repo holds the Python control software (`Source code/Python`, where most work happens), Arduino sketches (`Source code/Arduino`), and CAD/electronics (`CAD/`: KiCad, Eagle, FreeCAD, Blender).

## Commands (from the repo root)

- `py main.py` - the installation. Builds `Colloquy`, opens the U2D2 (`COM4`) and the Arduino, blinks every NeoPixel once, starts `Server2` on port 8087 **on every interface** (both URLs printed at startup).
- `py mock_ui.py` - the UI mock on port 8088 (localhost only), against `colloquy/ui/mock.py`; no hardware.
- `py -m pytest "Source code/Python/pytest_tests"` - unit suite, ~2s. **Run it after changing anything under `colloquy/`.**
- `py -m mypy` - scoped type check (see below).
- Generators, rerun after changing their source: `export_gerbers.py` (needs KiCad), `next_pcb.py`, `export_mega_pinout.py`, `export_shields_diagram.py`, `extract_hardware_photos.py` (needs `pymupdf`). Most outputs are held to their source by a pytest test that fails when they go stale.
- `test_process.py` is a dev file-watcher that restarts `main.py` on save - not pytest. `process_csv.py` is a dev helper with hardcoded paths.
- No build step. `requirements.txt` is incomplete (`pyserial`, `watchdog`, ... are imported but unpinned); check imports.

**Startup never dies on hardware.** `open_the_hardware()` reports every failure to `colloquy/startup/` and carries on, because the page that explains a fault and the command that fixes it live in the server. The `startup problems` node appears on the root only when it has something to say. Arduino, servo bus and each servo fail independently. Only the six wired servos (`U2D2.body_dxls`) are initialised - nothing enables torque on a mirror unasked. `Colloquy.servos_were_opened` asks `U2D2.ever_opened`, not just the port name.

If the main PCB is noted as out, the hardware steps are skipped and a standby page is served instead of the tree (see Hardware).

## Machines: simulated vs real

`colloquy/machines.py` names two machines by exact hostname:

- **`Colloquy-Laptop`** - the installation: nine servos, the Arduino. `Base.is_simulated` is False only here. It also auto-pulls and restarts (see Git).
- **`DESKTOP-MRSLS88`** - the bench: Thomas Erforth's audio subsystem (his Mega 2560, filters, amplifiers, microphones, analysers). `Base.is_bench` is True only here; it is also `is_simulated`.
- Anywhere else runs entirely on `colloquy/virtual_drivers/` (virtual serial port, packet/port handlers, Dynamixels, a stand-in for Thomas's board).

Keep the real/virtual split inside the drivers; never special-case simulation inline. **A board is on a lead, not on a machine**: boards get carried between desks, so whether a link is real is decided by the *chosen port*, not the hostname. `Arduino.is_using_the_stand_in` and `BenchComPort.is_using_the_stand_in` (`colloquy/tests/bench_com_port.py`) both mean "the chosen port is the stand-in". Port pickers list real leads wherever `boards.detect()` finds any, plus the stand-in wherever `is_simulated`. `use_port()` swaps the handler when the kind changes. `BenchBoardLink` (`colloquy/tests/bench_board.py`) is the one link for both audio bench tests. Every node that talks to a board shows a `board` reading saying which it is talking to. Pinned by `pytest_tests/drivers/test_arduino_port_choice.py`.

## Architecture: the `Base` tree

Everything in `colloquy/` is a node in one tree rooted at `Colloquy`:

- **`Base`** (`base.py`): dict-like node (`_dict`), `owner` pointer, computed `path`, `snapshot()` serialising the tree for the page.
- **`BaseThread`** (`base_thread/`): `setup()`/`loop()`/`setdown()` in a thread, cooperative stop (`_stop_event`, class-level `_shutdown` shared by all threads), per-node error capture (`ThreadErrors`).
- **`BaseHTML`** (`base_html.py`): renders a node as an HTML fragment.

Dispatch is the same everywhere: split the path, look up the first part in `self`, recurse with the rest; an unknown key raises `NotImplementedError` (= 404). Add a child or command with `self[name] = handler_or_child` in `__init__`; don't invent new dispatch.

- `snapshot_children` is the routing contract: a child drawn but not listed there 404s.
- **A leaf must not share a name with a child** - both go into one dict and the leaf silently replaces the link.
- A `BaseThread`'s bare `start` link is popped wherever it would be an ambiguous or dangerous press (flasher, schedule, `test_audio_at_12v`).

## The web server (`colloquy/server2/`)

`Server2` serves `WSGI2` (`wsgi2.py`); `Colloquy.get_states` delegates to `ui/tree.py`, which walks the tree, calls a command if the path ends in one, and returns a nested dict rendered with `yattag`. It is a generic tree browser, not a dashboard: **new UI = new nodes/commands, not new routes.**

**Concurrency is two halves; never change one alone.** `ThreadingWSGIServer` gives a thread per connection (so the EMERGENCY STOP stays reachable), and `get_states` holds `_command_lock` around the whole walk (so commands never overlap). Off the lock: `/emergency-stop`, `/shutdown`, `/restart/<app path>`, `/static/`, `/download/`, `/pcb/`, `/pcb-order/`, `/update-status`, `/mount-main-pcb`, `/unmount-main-pcb`, `/virtual-panel/<show|hide>/<app path>` (see `wsgi2._parse`).

- `/shutdown` takes the lock via `Colloquy.hold_commands` (bounded at 10s, then proceeds and says so). `/emergency-stop` waits for nothing.
- **One server per port** (`server2/exclusive_port.py`): `HTTPServer`'s SO_REUSEADDR lets a second Windows process listen on 8087 beside the first (two `main.py` split the page between them, 2026-10-22). The server binds with SO_EXCLUSIVEADDRUSE, and `main.py` claims the port (loading that module by path) before importing `colloquy`, so a second instance exits with who holds it, before wiping logs or touching ports. Restarts are unaffected (listener closed before the exec; measured). `pytest_tests/test_exclusive_port.py`.
- Load-bearing: `httpd.timeout` (wakes the accept loop), `RequestHandler.timeout` = 10s (a sleeping phone must not hang `server_close()`), `daemon_threads=False`/`block_on_close=True`. Responses go out in 64 KiB pieces; a response may be an iterable. `pytest_tests/test_command_lock.py`.
- Long-running commands go off the request thread (pattern: `Repository.pull`, the flasher).
- **No authentication**: anyone who can reach port 8087 can stop, flash or unmount. The network and firewall are the protection. `server2/network.py` must never raise. Tests bind 127.0.0.1 only (binding all interfaces raises a firewall dialog).
- Static files carry `ETag` + `Last-Modified` + `Cache-Control: no-cache` (they change while the server runs).

**Errors.** An exception inside a command becomes a `CommandFailed` page (`ui/tree.get_states`), with a next click from `server2/remedies.py` only when it is *known*. An exception anywhere else - the walk, a render, a parse - still emergency-stops the installation. So **a render must never raise**: read hand-editable params defensively. `NotImplementedError` stays the 404. `pytest_tests/test_command_failed_page.py`.

**Tree commands cannot have a last word**: `ui/tree.update()` discards a command's return value and re-renders its node. Anything that must end on its own page or stop the server (unmounting, mounting, the panel toggle, downloads) is a route.

**`/emergency-stop` never homes; `/shutdown` does** (via `power_down()`); `/restart` re-execs without homing.

### Two web UIs, deliberately independent

- **Installation** (`server2/`): runs the exhibition, keeps its old inline-styled look and the red EMERGENCY STOP. Leave it working.
- **Mock** (`ui/wsgi.py`, `ui/server.py`): a styling-free fork (2026-08-19) where the page is being rebuilt from bare markup with `name="..."` hooks and renderer classes; no stylesheet, no emergency stop.

A page change is made twice, or on the mock alone. They serve their own `static/`. They share the snapshot vocabulary in `ui/leaves.py` - `value`, `html`, `svg`, `image`, `pre`, `editor`, plus `into(states, path)`. Build leaves with those constructors; a kind not in `leaves.KINDS` is not drawn. `pytest_tests/ui/test_leaves.py` renders every kind through both.

- The root gates the `virtual drivers` panel and the `code documentation` node on `is_simulated`. The panel's show/hide is a route (`VirtualDrivers.panel_is_open`, separate from the node's own open state).
- Markdown documents (`colloquy/markdown_document.py`): `MarkdownDocument` = view/`edit`/`save`; `GeneratedDocument` has no `edit` and renders from its generator on every view.
- **Charts: `ui/graph_view.py` only** - no JavaScript, server keeps the data and the view. Page size (samples in the window) vs points (drawn); y range from the whole run; `marks=` as `(seconds, label)` with a `marks` child node; `Columns` is a lazy view, so nothing is copied and only the page is read. Emit as `leaves.image`, never `leaves.svg` (that one gets browser-side zoom). `pytest_tests/ui/test_graph_view.py`.

## Scenarios

A **scenario** is the artist's term for what the piece visibly does in the room, second by second. Only that: hardware tests are never "scenarios", and `CODE_DOCUMENTATION.md` describes code, not the piece.

- Every `BaseThread` declares `scenario_names`; `_snapshot_if_opened` hangs a `scenarios` child beside `start`/`stop`. Names are behaviours (all females' `search` → `female-looking`). Whole-piece ones sit on `Colloquy`. Hardware tests have them too. Not gated by `is_simulated`.
- Files live in `colloquy/scenarios/`: `<seconds> <description>` per line, a leading `#` title block, `-> other[: label]` to start a child concurrently. `scenario_browser/rendering.py` flattens onto one clock.
- `pytest_tests/test_scenarios.py`: every name has a file, every file is claimed, and `WITHOUT_SCENARIOS` is a ratchet (`Repository`, `ExpositionSchedule`, `Scope`, `read_pattern`, `blink` stay on it on purpose).

## Drivers (`colloquy/drivers/`)

Naming: **`drivers`** is the software layer that drives the piece (`/app/drivers`, sim twin `virtual drivers`); **`drives`** are a body's O/P appetite states (`drivers/drive/`); **`hardware`** is the physical equipment (`/app/hardware`).

- `Drivers` owns `Arduino`, `U2D2`, 3 `Female`, 2 `Male`, `Bar`, `AllNeopixels`, `Bodies`. Each body has its `DXL`, `Drives`, `Search`, `Neopixels`, `LightSensor`.
- `U2D2` wraps `dynamixel_sdk` with nine `DXL`s (`female1-3`, `male1-2`, `bar`, three mirrors on ids 2/4/6). `DXL` registers are `RegisterHanlder` children; `handle_error` retries and logs. All servos run in **extended position mode**; positions read `signed=True`.
- **Angles, never servo units**, outside `drivers/angle/` and `drivers/dxl/`. Each moving thing has an `Angle` in degrees of the body, zero at its calibrated origin. `angle/conversion.py`: 4096 units/turn; bodies and bar turn 3x slower than their servo, mirrors 1:1.
- `Mirror`: plain `Base`, not initialised at startup, jog/calibrate only. Its 81.211° range is TJ's firmware (512 units = 45°); its `dxl origin` must be measured at the rig.
- **Behaviour**: each body starts *and stops* its own search in its own `loop()`. The `Bar` wanders only while some male's `search.is_started` is set. `is_satisfied()` = both appetites down (`not drives.which_is_frustated()`).
- **Arduino**: JSON lines (`{"path": ...}\n`) at 1 Mbaud to `Source code/Arduino/colloquy_of_mobiles/colloquy_of_mobiles.ino`. A new pixel group or sensor needs an `.ino` handler **and** a matching `NeopixelCommand`/`LightSensorCommand` entry. The sketch is the source of truth: `drivers/arduino/firmware.py` reads `SERIAL_BAUDRATE`/`FIRMWARE_VERSION` out of the `.ino`; `params` only copies the baud rate. `wait_for_reboot()` refuses a greeting older than `MINIMUM_FIRMWARE_VERSION`; `_diagnose_silence()` probes old rates then lists USB devices.
- `drivers/arduino/boards.py`: identifies boards by USB bridge VID/PID without opening them (`KNOWN_DEVICES`, which also keeps the U2D2's FTDI lead off the Arduino picker).
- **Flasher** (`drivers/arduino/flasher/`): shells out to the `arduino-cli` bundled with the Arduino IDE, which needs `--config-file ~/.arduinoIDE/arduino-cli.yaml`. One `compile --upload`. A one-job thread (off the lock). Refuses, instantly: unmounted PCB, no/absent/implausible port, anything under `drivers`/`tests` running (filtered by tree path so `Repository` doesn't block it). Ends by reopening the link as the check. `flasher/base.py` is the shared shape; subclasses (`Flasher`, `SamplerFlasher`, `PlotterFlasher`) supply `_check_the_board()` and `_extra_refusals()`.

### Stopping, and the calibration it protects

Extended position mode keeps the turn count in volatile memory and the bar travels 2.4 servo turns, so powering down away from home corrupts the calibration.

- `Colloquy.power_down()` = threads down, lights off, everything home, torque off; returns whether everything arrived. Used by `/shutdown` and unmounting. `HOMING_TIMEOUT` is 90s (a full bar crossing takes ~32s).
- Every step survives hardware that was never opened; "nothing to home" is success, not failure. `shutdown_neopixels`/`silence_speakers` swallow and log.
- `emergency_stop` is `try/finally` around `shutdown()`, and `Server2.wsgi` wraps it the same way: a handler must not fail like what it handles.
- `pytest_tests/test_power_down.py`.

## Hardware (`colloquy/hardware/`, `/app/hardware`)

Belongs here if it would still be true with the software off. Not gated by `is_simulated`.

**`main_pcb/`** - the board carrying both serial links.

- `/unmount-main-pcb` (a route) writes `params["main pcb"]["mounted"] = False` **first**, then `power_down()`, then a goodbye page saying what can be unplugged. Nothing clears the note except a deliberate press.
- **While noted out, the server serves `server2/standby.py` instead of the tree**: `/` is the standby page and every `/app` address 303s to it. That gate (`wsgi2._board_is_out`, asked of the note not the hostname), `main.py` skipping the hardware, and the schedule's refusal are what keep the drivers inactive. The page offers the Gerbers (`/download/gerbers[/<board>]`), the KiCad projects (`/download/kicad`) and `the new PCB is mounted` (`/mount-main-pcb` → `MainPCB.remount()` + restart; nothing starts moving). No EMERGENCY STOP there (it would latch `_shutdown` and end the `Repository` watch). Nothing on it, or in a download, may raise. Installation UI only. `pytest_tests/test_standby.py`.
- Gerbers are plotted on a machine with KiCad and committed (`py export_gerbers.py` → `CAD/KiCad/production/<board>/` + `manifest.json`), refusing any board that fails DRC. The manifest stores line-ending-normalised digests of each `.kicad_pcb`, so a stale plot is detected without KiCad (`pytest_tests/hardware/test_pcb_files.py`). **Re-run after changing any board in its table.** The table is deliberately the shields set plus the two v2 body boards only. `hardware/pcb_files/` is stdlib-only.
- Every LED, diode and electrolytic on those boards has `+` and `-` on the silkscreen beside its pads, so a fitted board can be checked by eye: `mark_polarity.py` (KiCad Python, idempotent; re-run after regenerating a board, then re-export), held by `pytest_tests/hardware/test_polarity_marks.py`.
- **PCB orders** (`pcb_files/orders.py`, `/pcb-order/...`, installation UI only, answered before the board-out gate so it works from standby): each manifest board's card shows its status (`waiting order` / `in the cart` / `ordered` / `error`, notes in `params["pcb orders"]`, so per machine; screenshots in `local/pcb orders/`). `order now` walks every waiting/error board through five JLCPCB steps; each step has next and `something went wrong` (note + optional screenshot → error, then the next board); the cart page marks everything in the cart ordered. `start again from the beginning` sets the cart back to waiting (errors and orders untouched). A cart record keeps digests of its uploads (`uploads`: Gerbers without their time-stamped comments, BOM, CPL); wherever the status is drawn they are compared with the package now, and a board that moved on is offered `again`. Step 4's per-board checks (`CHECKS`) cite their documents, and a test requires an entry for every board. State changes are POST forms; the files each step uploads come out of the checked package (`/pcb/<board>/gerbers|bom|cpl|manual|assembly`).
- `configuration/` records which board is in the rack and what fills its slots (`params["main pcb"]["configuration"]`, kept per board). It drives nothing: consequences are shown, and the two hand-kept records (a body's card vs `audio > wired bodies`) are compared, never reconciled. `configuration/table.py` is the pure half.

**`motors/`** - unplugging the Dynamixel chain. Deliberately does **not** call `power_down()` (that latches the class-level `_shutdown`, after which nothing can start): it stops what drives the piece by tree path, homes, cuts torque, and leaves the process usable. `params["motors"]["plugged in"]` is written first (for the next start); `were_unplugged_this_run` is latched after homing (read by `Colloquy.servos_can_be_commanded`). `pytest_tests/hardware/test_motors.py`.

**`electronics/`** - documents describing what the boards do. The `.md` files sit with their nodes; read the relevant one before touching a design:

- `as built` (current PCB, from the KiCad netlist; `mega-pinout.svg`), `dirty rework` (cuts and jumpers adding Thomas's audio), `next pcb` (replacement, with generated `netlist`/`bill of materials`/`mechanical` under it), `harness` (generated from the four harness boards' `.kicad_pcb`), `cad boards` (index of `CAD/`).
- Alternative architectures: `one board per body`, `opencm and pro minis` (dropped 2026-09-30, the U2D2 stays), `ad9833 dual mode` (chosen for the voices), `sound options`, `thomas or teensy`, `shields` (the backplane + shields design; step 1 - Mega, MSGEQ7 carrier, Thomas cards - is the only one the exhibition depends on), `microphone board`.
- Generated, not written: `next_pcb.py` builds the next board from `drivers/audio.py` (placement and routing deliberately not generated); `shields.py` and `microphone_board.py` compute every figure in their documents. Tests hold each to the spec and to the copper.
- Facts worth knowing before touching the board: `J4`/`J8`/`J10` are a 1:1 breakout of D0-D21 (every cut is one stroke); `J11`/`J12` are break points (body wire on the odd pin, ADC on the even). The shields backplane's former speaker pair is line out/audio return, and its DC jack is centre-positive.
- **Amplifier rail**: the fitted module's rating is a recorded fact (`params["audio"]["amplifier module"]`, `"amplifier max supply volts"` = 5.0), and `test_audio_at_12v` refuses any pass above it. A GF1002 was destroyed on an unsourced "4.5-15 V". **A requirement on a part to buy is not a property of the part in hand; every hard number needs a source** (a `#define`, TJ's firmware, the copper, a datasheet).
- **Importing the `colloquy` package wipes `local/logs`.** Export scripts and scratch scripts load the modules they need by file path.

## Light patterns (male identity signal)

Each male sends a 10-bit pattern on his ring encoding which male he is and which drive he wants (tables in `Colloquy.light_patterns`; `()` is his `R`). Timing in `light_pattern_timing.py` (TJ's numbers): 0.2s/bit, 2s burst, every 4.35s; **the silence frames the message**. `Blink.loop()` reads the pattern once per burst. `ReadPattern` (`drivers/female/search/read_pattern/`) samples the light sensor and matches every offset and rotation with majority vote. A female's `Search` starts `read_pattern` (`started_by=self`).

Light tests (`colloquy/tests/`):

- `test_light_sensor_values/*` log raw values and pulse durations, not pattern decoding. `test_for_false_positives` (all lights off, reading vs angle); `test_seeing_male1_as_the_bar_turns` (reading vs alignment offset, plus a 2-D map); `test_with_everything_moving` (rings steady ON). Results via the shared `results` node.
- `test_read_pattern` stages a pair face to face (failure mode: wrong decode); `test_search` stages nothing (only it can produce a **miss**: two send cycles, `events.MISS_AFTER` = 8.7s). Drives are the tester's to set. One CSV row per episode, not per sample. **No commas in CSV event sentences.**
- `test_reinforcement` stages the find and runs only the exchange; it also logs the real analysers beside the emulated ears.
- **The simulator cannot settle geometry or produce a miss** - it models exactly the rule being tested. Only hardware answers those.

## The sound channel

Every body has a voice (hardware timer tone) and an ear (MSGEQ7 analyser module); firmware 4. **`drivers/audio.py` is the one table**, shared by speaker, microphone, tests and simulator:

| body | pitch | timer | pin | analyser module |
|---|---|---|---|---|
| female1 | 1 kHz | T4 | D6 | 0 (A0) |
| female2 | 2.5 kHz | T5 | D46 | 1 (A1) |
| female3 | 6.25 kHz | T2 | D10 | 2 (A2) |
| male1 | 160 Hz | T1 | D11 | 3 (A3) |
| male2 | 400 Hz | T3 | D5 | 4 (A4) |

- Pitches are Thomas's, one per MSGEQ7 band. A pitch belongs to its timer and a timer to its pin (silicon), so bodies move across pins, never pitches across timers. NeoPixel lines moved to D14-D17 to free tone pins.
- **`audio.BODIES` (body = module = A0-A4 order) ≠ `audio.BODIES_BY_PITCH`.** Iterate the right one.
- Hardware timers, so NeoPixel writes don't tear tones and five voices sound at once.
- `AllAudio` (`all audio`) reads every microphone on one strobe - never read five one at a time to compare them. `silence every speaker` is one firmware command; `Colloquy.silence_speakers()` swallows exceptions.
- `params["audio"]["wired bodies"]`: an unwired analyser input floats and reads garbage. Add a body when its amplifier and analyser are in.
- `drivers/sing/` is `Blink` for a speaker. `drivers/*/reinforcement/` is the exchange (she sings his pattern back; each round takes 20 off the shared appetite; a round is one burst, counted on its rising edge). **`drivers/hearing/` is emulated** (`is_emulated`): no one hears their own voice, no geometry. The male's mirror-light half is knowingly unported.

Audio tests, each answering a different question:

- `test_audio_subsystem` - Thomas's board over his serial menu: are the five boards good. Gated on `is_simulated`.
- `test_audio_loop` - the installation's board: is each body wired to its own channel.
- `test_audio_bringup` - same question, and which link is broken (`diagnosis.py`: most specific finding wins; a voice that peaked anywhere is never sent to a scope; says when it needs a person to listen).
- `test_microphone_signal` - cuts the chain at the analyser input, using the Arduino IDE Serial Plotter with `Source code/Arduino/microphone_plotter/` (routes A/B/C in `MICROPHONE_PLOTTER.md`). Has `flash the plotter sketch` and `flash colloquy firmware back`.
- `test_audio_at_12v` - louder on a higher rail? Two passes with a supply change between (`measure at 5 V`, `measure at 12 V`), each tone judged by `rise` and `share` (the MAX9814 AGC flattens rise). Not gated. `SUPPLY_SETUP.md` hangs off it.
- `test_goertzel_ear` - PC speakers (`sounddevice`) → a Mega running `microphone_sampler` → Goertzel in Python (`goertzel.py`). Heard = a multiple of its own silence (`HEARD_RATIO` 8, `QUIET_FLOOR` 0.01, pinned to a real run). Pitches 750-1500 Hz; 1000/1050 are a deliberate border case (`goertzel.leakage`). A press sounds for `PLAY_SECONDS` = 10. Runs are recorded with marks and saved as CSV under `local/test results/test goertzel ear/`. No stand-in. `Source code/Arduino/goertzel_ear/` is kept for a different question.
- `scope` (not `test_*`: it asks nothing) - records A0 and A1 from `microphone_sampler` firmware 2 (`d` command, `pair` reply; `b`/`block` untouched). Draws the gaps between captures, never end to end. `swing`, `compared`, and `independent` (`trace.coupling_of`, `ghost_of`: a floating pin copies the earlier channel), computed within captures and spread along the run. Old firmware is refused before recording. `DIAGNOSING_A_MICROPHONE.md` hangs off it.

## Exposition schedule (`colloquy/exposition/schedule/`)

`Exposition` is the piece running; `exposition > schedule` starts and stops it by the clock, the only thing that does so with nobody in the room. **Default: no schedule, switched off.**

- A schedule is a run (dates), a week (hours per weekday), exceptionally-running dates and exceptionally-standby dates. `rules.py` (format and params round trip), `solver.py` (one row per date with the rule that gave it; `MAX_DAYS` 800), `rendering.py`, `__init__.py` (node).
- Edited as text through `leaves.editor`; the structure is what's stored in `params["exposition schedule"]`. `parse` names the bad line.
- One switch: `enable`/`disable` (bare start/stop popped). `enable` refuses an unreadable schedule or one with no run; saving never enables. `main.py` calls `start_if_enabled()`.
- It stops only what it started; it refuses to start against the main-PCB or motors notes (never blocks a stop). Naive local time. `CHECK_INTERVAL` 20s. `pytest_tests/exposition/`.

## Parameters (`local/params.json`)

- `colloquy/params.py`'s `Params`: dict that persists on every mutation, nested dicts included. `DEFAULTS` documents the shape.
- Versioned (`PARAMS_VERSION`); `migrate()` backs up to `local/params.json.v<n>.bak` and `_fill_missing` adds new keys recursively. **A new key needs only `DEFAULTS`; a changed meaning needs a version bump and a branch in `migrate()`.** It is the calibration of a physical installation: where a migration can, it leaves a value somebody measured or typed alone (v4, v5).
- Units: `dxl origin` in raw servo units; everything else (`motion range`, `interaction_origins`, thresholds) in degrees of the body, read on every use.
- Notes written by presses and read at startup: `"main pcb"` (`mounted`, `configuration`), `"motors"` (`plugged in`), `"exposition schedule"`. v7 is the one migration that writes one: on `Colloquy-Laptop` only, it notes the board out. **Nothing may ever decide by itself that a board is in.**
- `local/` is git-ignored working state: logs (`local/logs/`, wiped on process start), test results, videos, downloads.

## `#`-prefixed paths

Directories and files starting with `#` (`# app2/`, `colloquy/# threads/`, `colloquy/tests/# test2.py`) are archived implementations, unimportable by construction. Don't import from them, delete them, or partially resurrect them; missing functionality versus them is not-yet-ported, not a bug.

## Git workflow: two computers

The user works from two machines, and the installation's laptop pulls by itself.

- **At the start of a session** (and before each new task in a long one): `git status`, `git fetch`, compare `HEAD` to `origin/<branch>`, and pull first if behind (ask if a conflict would result).
- **Commit after every edit** - small, focused, "why"-style messages matching `git log` - **and push**, unless told otherwise.
- Unexpected local changes at session start may be the other machine's: stash or commit, never discard, and flag them.
- Mixed line endings (`core.autocrlf=true`, no `.gitattributes`): edit with the Edit tool; check `git diff --stat` after any scripted edit.

**`colloquy/repository/`** watches origin: `Repository` (started by `main.py`, not gated) fetches every 5 min and shows the status. Elsewhere, `pull` is a link that appears only when origin has something; it is `--ff-only`, refuses a dirty tree or diverged branch, and runs on the loop thread. A pull doesn't change running code; use `restart`.

**On `Colloquy-Laptop` only** (`Repository.auto_update`), it checks every 60s, pulls (still `--ff-only`) and restarts itself - only when nothing under `drivers`/`tests` is running and never after an EMERGENCY STOP. The server's accept loop asks `restart_is_due`. Progress shows as a banner (`server2/updates.py`, `static/update_watch.js`, `/update-status`). **A commit that fails on import strands the laptop with no server: run the suite before pushing to the branch it tracks.** `pytest_tests/test_automatic_update.py`.

## Type annotations

Annotate where a type is a fact worth stating, and check what you annotate. `py -m mypy` checks only the `files` list in `pyproject.toml` - pure-logic modules (angles, audio table, boards, schedule rules/solver, repository, electronics calculators, ...). **Adding a file to that list is the decision.** The `Base` tree stays off it (dynamic dispatch). `follow_imports = "silent"` is load-bearing; `disallow_untyped_defs` is deliberately unset. Constant-only modules stay unannotated.

## Testing

Two unrelated things are called tests:

- **`Source code/Python/pytest_tests/`** - pure-logic pytest suite. Read `conftest.py` first: never `.start()` a `BaseThread`, never build the real `Colloquy`/`Drivers`, prefer duck-typed doubles or unbound-method calls.
- **`colloquy/tests/`** - interactive **hardware tests**, nodes in the tree run from the page (`BaseThread` + `snapshot_children`). Check for an existing one before writing another. Never call them "scenarios".

Hardware tests are filed by **who does the perceiving** (`colloquy/tests/group.py`, `TestGroup`):

- **`autotests`** reach and record their own answer: `test_light_sensor_values`, `test_read_pattern`, `test_reinforcement`, `test_search`, `test_female_search`, `test_movements`, `test_audio_subsystem`, `test_audio_loop`, `test_audio_bringup`.
- **`manual tests`** need a person's eye, ear or hand: `test_drive_light_values`, `test_male_patterns`, `test_neopixels`, `test_sensors`, `test_microphone_signal`, `test_goertzel_ear`, `test_audio_at_12v`, `scope`.
- The graph demos (`test graph`) sit directly under `tests`, in neither group. `TestGroup` forwards `colloquy`/`drivers`/`params`/`workspace` to its owner and holds the `is_simulated` gate (only `test_audio_subsystem`).

Firmware on test pages (`pytest_tests/hardware_tests/test_colloquy_firmware.py` holds membership):

- The eleven that drive the piece get `flash firmware` + `in sync` from `NeedsColloquyFirmware` (`colloquy/tests/colloquy_firmware.py`), a view on the one shared flasher, hung via `_with_firmware()` in each test's own `snapshot_children`.
- `test_goertzel_ear` and `scope` get a `SamplerFlasher` and `ask the board` (`colloquy/tests/sampler_board.py`), judging the version against what *that* test needs.
- `test_microphone_signal` gets `flash the plotter sketch` (no handshake possible).
- `test_movements`, `test_audio_subsystem`, `test_audio_at_12v` have none (no board, or Thomas's code, which isn't a sketch folder).
