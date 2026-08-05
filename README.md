# exposition
Colloquy of Mobiles for exposition in ZKM

## Todo
In KiCad:
- Choose the footprint for power supply capacitor.
- Check dimension of jack barrel.


## Todo: software roadmap

Ordered by priority: get it running reliably first, then make it easy to
retune without code changes, then make faults easy to diagnose, then
polish the day-to-day experience.

### 1. Up and running (do this before anything else)

- **Validate on real hardware.** Everything built and tested this
  refactor ran in simulation (`Base.is_simulated` is only `False` on the
  `Colloquy-Laptop` hostname) - nothing has touched a real Dynamixel or
  Arduino yet. Run `main.py` on the actual machine and confirm servo
  comms, Arduino serial comms, and LED behavior before relying on
  anything else here.
- **Pin `requirements.txt` completely.** It only lists `yattag` and
  `dynamixel_sdk`, but `pyserial` (imported as `serial` in
  `hardware/arduino/`, `hardware/com_port/`, `hardware/u2d2/`) is a hard
  runtime dependency that isn't listed - `pip install -r
  requirements.txt` alone won't actually be enough to run the app on a
  fresh machine.
- **Implement `Colloquy.close()`.** Currently `raise
  NotImplementedError` unconditionally (with dead code after it) - there
  is no clean, non-emergency shutdown path besides the `/shutdown` web
  route. Decide what it should actually do (stop threads, release
  hardware) and implement it.
- **Decide the fate of the male-blink / female-read-pattern behavior.**
  This is the installation's actual interactive concept (see CLAUDE.md:
  each male blinks an identity + requested-drive-state pattern, a female
  is meant to read it and respond) - but `Search.loop()`/`setup()`
  deliberately `raise NotImplementedError("use the turn_back_and_forth
  thread")` right now, so females just turn back and forth instead. Is
  that simplification intentional/permanent for this exhibition, or does
  `ReadPattern` need to be wired up before opening? This is an artistic
  decision as much as a technical one - flag it and decide deliberately
  rather than by default.
- **Confirm the emergency-stop path is enough for unattended operation.**
  `/emergency-stop`, `/shutdown`, `/restart` exist and work, but this is
  a museum installation that will run unattended for stretches - is a
  web route sufficient, or is a physical panic button / auto-restart-on-
  crash needed too?
- **Test USB/serial resilience.** Arduino/U2D2 connections open lazily
  on first use; there's already a "waiting for Arduino to reboot"
  pattern at startup, but reconnect-after-fault (cable unplugged and
  replugged mid-show, Arduino resets on its own) hasn't been exercised.

### 2. Flexible (retune without touching code)

- The new **params tab** (`/app/params`) is the first big step here -
  every value in `local/params.json` is now live-viewable/editable from
  the web UI. Worth a pass during real setup to confirm the values staff
  will actually want to retune on-site (light thresholds, interaction
  origins, per-body drive timing) are all comfortably reachable there.
- **Decide what (if anything) in the `#`-prefixed archive is actually
  planned-but-unfinished work**, vs. permanently retired. CLAUDE.md
  preserves it as reference rather than dead code by convention, and this
  refactor found real orphaned/broken functionality nearby it (a
  `Conversation` concept, a `Mirror` concept, both deleted this pass as
  unreachable) - worth one deliberate pass to confirm nothing there was
  actually meant to ship.
- **Audit which hardcoded constants are likely to need on-site tuning**
  (e.g. the 0.5s blink step, the light-pattern bit sequences) and move
  the ones that do into `params.json` alongside everything else now that
  there's a UI for it.

### 3. Debuggable (diagnose faults quickly when something goes wrong)

- **Fix `ThreadErrors`/`ThreadError`'s stale one-arg `snapshot(path)`
  override** - it shadows the working inherited
  `Base.snapshot(path, focus_path)`, the same crash pattern fixed
  throughout this refactor everywhere else, but explicitly left for
  later since it only matters once a thread actually errors. That's
  exactly the moment you need it to work during a live show, so worth
  fixing before relying on it.
- **Build a live status/health view.** Right now, diagnosing anything
  means clicking through the generic tree browser node by node. A single
  page showing every body's position, torque state, and light-sensor
  reading, plus any `thread_errors`, at a glance would cut diagnosis time
  a lot during setup and rehearsal.
- **Put the chart tooling built this refactor to real use** (the uPlot
  integration, `test_graph_zoom`, `test_sensors`) - wire up light-sensor
  and position logging during rehearsal runs so behavior can be reviewed
  afterward, not only watched live.
- **Stop wiping logs on every restart.** `colloquy/logger.py` clears
  `local/logs/` on process start - if something crashes overnight
  unattended, the log explaining why is gone before anyone looks.
  Archive the previous run's logs instead of deleting them.
- **Coverage sits around 46%** on the new unit test suite - expected and
  fine, since hardware I/O and thread-loop bodies aren't unit-testable by
  design (confirmed this refactor, not a red flag by itself). It does
  mean bugs in `loop()`/`setup()`/`setdown()` bodies can only be caught
  by actually running them, so budget a deliberate rehearsal-testing pass
  on real hardware rather than trusting the test suite's green alone.

### 4. A bit more user-friendly (once the above is solid)

- The web UI is a generic tree browser - functional, but not really
  designed for a non-developer to operate confidently during a show.
  Once the above is stable, a small purpose-built front page (start/
  stop, current status, the handful of common actions) would go a long
  way for staff who don't know the underlying tree structure.
- Two small pre-existing bugs surfaced but left out of scope this
  refactor, worth a quick fix once things are stable: `input/__init__.py`'s
  `commands` property references undefined `Key`/`Space` (crashes if ever
  exercised); `hardware/neopixels/commands/close.py` and
  `tests/test_neopixels/commands/close.py` reference an undefined
  `HTML`/`Action` from an already-commented-out import.
- Once real rehearsal data exists (see "chart tooling" above), invest in
  presenting it well - the vendored uPlot charts already support zoom/
  pan, this is mostly a matter of pointing them at real logged data.