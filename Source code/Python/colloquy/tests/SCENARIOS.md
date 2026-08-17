# Colloquy of Mobiles — Interaction Scenarios

A catalog of the interaction/behavior scenarios this installation can be in,
organized by sub-behavior. For each scenario: the trigger, the resulting
behavior, which `colloquy/tests/` scenario (if any) exercises it, and its
status.

This is a reference document, not runnable code — it describes what the
code in `colloquy/hardware/` actually does (and doesn't do), to make gaps
and existing coverage visible in one place. File:line references point at
`Source code/Python/colloquy/`.

## Legend

- ✅ **Covered** — an existing `colloquy/tests/` scenario exercises this.
- ⚠️ **Gap** — a real scenario the autonomous installation can reach, with
  no test (and in some cases no working code path) exercising it.
- 🐛 **Broken** — a code path that will crash or misbehave if reached, found
  while researching this document.

Background: every behavior below runs as a `BaseThread`
(`base_thread/__init__.py`) — `setup()` once, then `loop()` on a ~10ms tick
until stopped, `setdown()` on exit. Any exception in `setup()`/`loop()` is
caught, logged to that thread's `thread_errors`, and **permanently** stops
the thread — a second `start()` call on an errored thread raises
`NotImplementedError` (`base_thread/__init__.py:82-83`) instead of retrying.
This is why some scenarios below (§2.1) are outright crashes rather than
just "unexercised."

---

## How to test these reliably

The `colloquy/tests/` scenario modules (§1-6's "Covered by" column) are
built for a *different* kind of reliability than regression-checking a code
change: they run for tens of seconds to tens of minutes, drive real or
simulated hardware, and produce a CSV/SVG for a human to look at. They're
the right tool for calibrating against actual servos/sensors, not for
quickly confirming "did my change break this."

For that second kind of check — confirming a specific behavior/fix, fast
and repeatably — script it directly against the `Base` tree instead of
going through the web UI or a full `colloquy/tests/` scenario. This is the
same approach used to verify the `Female.Search` fix above:

```python
import sys, time
from pathlib import Path
sys.path.append(str((Path(r"C:\workspace\workspace2\Colloquy\exposition") / "Source code" / "Python").resolve()))
from colloquy import Colloquy

colloquy = Colloquy()
colloquy.hardware.u2d2.com_port.set("COM4")
colloquy.hardware.u2d2.open()
colloquy.hardware.arduino.open()
for dxl in colloquy.hardware.u2d2.dxl_list:
    dxl.init_hardware()

node = colloquy.hardware.female1.search  # whatever you're checking
node.start(started_by=None)
time.sleep(3)  # a few multiples of the node's own tick / sub-thread interval

assert not node.thread_errors, list(node.thread_errors)
assert node.is_started

node.stop()
node.join()
assert not node.is_started
```

A few things that make this reliable rather than flaky:

- **Run it away from the exhibition laptop.** `Base.is_simulated`
  (`base.py:104-107`) is `True` on any machine whose hostname isn't
  `Colloquy-Laptop`, which routes every hardware call through
  `virtual_hardware/` automatically — no serial port needed, safe to run
  repeatedly, and fast (no real servo travel time).
- **One fresh `Colloquy()` per check.** A `BaseThread` that has ever
  errored can never `start()` again — `thread_errors` sticks for the
  life of the object (`base_thread/__init__.py:82-83`). Reusing one
  `Colloquy()` across several scripted checks in the same process means
  an earlier failure can make a *later* check fail for the wrong reason.
- **Sleep long enough to cross the relevant tick, not just "a bit."** The
  loop tick itself is ~10ms, but what you're actually watching for is
  usually a sub-thread's own interval (e.g. `ReadPattern` needs ≥5s of
  buffered samples before it can match anything, `Drive` increments only
  every 2.4s). Sleeping less than that will pass for the wrong reason.
- **Force slow states instead of waiting for them.** Drive values take up
  to ~4 minutes to swing from satisfied to frustrated (§3.1). Don't wait —
  either call the existing forcing setters (`set_o_and_p_to_100()` etc.,
  `hardware/male/drives/__init__.py:122-151`, used the same way by
  `test_read_pattern`) or set `drive._value`/`_update_interval` directly
  before starting the thread.
- **Always stop/join what you started**, and check for stray processes
  afterward (`tasklist | grep python` / `Get-Process python`) if a script
  didn't exit on its own — `BaseThread`s are non-daemon, so anything left
  running (including a child started via `started_by=`) keeps the process
  alive.
- **Assert on the object, not on rendered HTML.** `thread_errors`,
  `is_started`, `.value`, `.last_match` etc. are all plain attributes on
  the node — cheaper and less brittle than driving the WSGI app and
  scraping its output, which is what the web UI is for (manual
  exploration), not scripted checks.

---

## 1. Male — search & blink (identity signal)

A male's ring blinks a 10-bit pattern that encodes his identity
(`male1`/`male2`) and which drive he wants attention for (see
`colloquy.light_patterns`, `colloquy/__init__.py`, and `CLAUDE.md`'s "Male
blink pattern" section).

The table is transcribed from TJ's firmware (`local/Code/Code/Units/
logic35_systems/logic35_systems.ino`) — see §8 for how faithfully, and
where this implementation diverges. One correction that matters here: the
fourth pattern per male, keyed `tuple()` in Python, is TJ's
`com_pattern_I_R`/`II_R` — **"R" for reinforcement, a separate message,
not "no drive wanted"**. In his inert state a male transmits no light at
all (`MALE_setSearchLight()`), so only three patterns per male are ever
sent, and his receiver only ever compares those six
(`sense_light_pattern.ino`). `Colloquy.readable_light_patterns` is that
six-pattern subset; `light_patterns` remains the full transcription.

| # | Scenario | Trigger | Behavior | Covered by | Status |
|---|---|---|---|---|---|
| 1.1 | Male becomes frustrated, starts searching | `Male.loop()`: search not started and `not is_satisfied()` (neither O nor P drive is "freshly satisfied") — `hardware/male/__init__.py:153-160` | `search.start()`: male sways between min/max position every tick it isn't already moving (`search/__init__.py:25-27`), and `search.setup()` starts `blink`, which sets the ring to white and begins rotating the 10-bit pattern for `drives.which_is_frustated()` on/off at 0.5s/bit (5s per full cycle) — `search/blink/__init__.py:24-36` | none directly (see 1.4/1.5 for partial coverage) | ⚠️ Gap |
| 1.2 | Search never stops itself when the male becomes satisfied again | `Male.loop()` only *starts* search; nothing in `loop()`, `search.loop()`, or `blink.loop()` re-checks `is_satisfied()` — only `Male.setdown()` calls `search.stop()` (`hardware/male/__init__.py:166-168`) | Once started, a male keeps swaying/blinking indefinitely regardless of drive state, until the whole male thread shuts down | none | ⚠️ Gap (likely unintended — worth confirming with the artist/installer whether this is by design) |
| 1.3 | Male's drive state changes mid-blink | `Blink.loop()` calls `male.get_blink_pattern()` on **every** 0.5s step, and that re-reads `which_is_frustated()` each time (`hardware/male/__init__.py:116-118`, `search/blink/__init__.py:24-30`) | The pattern **does** follow the drive state live. But each drive-state has its own deque holding its own rotation phase, so switching mid-cycle emits a garbled boundary — a few steps that are neither the old pattern nor the new one, i.e. exactly the sort of reading a female can decode as a third pattern (2.6). In practice this fires ~2.5 minutes into every search, when both drives pass 75 and the male switches to his `("O","P")` pattern for good | none | ⚠️ Gap (earlier revisions of this file claimed the pattern was frozen for the run — that was wrong) |
| 1.4 | Manually forcing a drive state and observing the blink pattern | Tester starts `test_male_patterns`, then calls one of the drive setters (`set_o_to_0_p_to_100`, `set_p_to_0_o_to_100`, `set_o_and_p_to_30`, `set_o_and_p_to_100`, `hardware/male/drives/__init__.py:122-151`) | Only the male's `blink` sub-thread runs (no physical sway) — ring blinks the pattern matching the forced state | `test_male_patterns` (`tests/test_male_patterns/__init__.py`) | ✅ Covered (blink only, no sway) |
| 1.5 | Manual sway without drive coupling | Tester starts a male's `turn_back_and_forth` directly from `test_movements` | Male sways min/max on a fixed toggle, ring untouched (no blink) | `test_movements` (`tests/test_movements/__init__.py:173-179`) | ✅ Covered (sway only, no blink) |
| 1.6 | Both drives frustrated simultaneously | `which_is_frustated()` returns `("O","P")` when both `> 75` (frustrated limit), or when `o_drive.value == p_drive.value` in the non-satisfied/non-frustrated middle range (`hardware/male/drives/__init__.py:45-65`) | Male blinks the combined `("O","P")` pattern (e.g. male1: `1,1,0,0,0,1,0,1,0,1`) | `test_read_pattern` forces this via `set_o_and_p_to_100()` (`tests/test_read_pattern/__init__.py:98`) | ✅ Covered |
| 1.7 | Drive tie in the *unsatisfied, non-frustrated* middle range | `o_drive.value == p_drive.value` and neither is satisfied/frustrated | Same `("O","P")` pattern as full frustration (`hardware/male/drives/__init__.py:60-63`) — a partial tie reads identically to "both fully frustrated" | none | ⚠️ Gap |
| 1.8 | Drive value combination outside all handled branches | Should be unreachable given the branch logic, but is a hard crash (`ValueError("Drive Error", ...)`) if ever reached (`hardware/male/drives/__init__.py:64-65`) | Male's `Drives.update()`/blink-pattern selection crashes | none | 🐛 Broken (defensive-only, but untested) |

---

## 2. Female — search, read-pattern, turn-back-and-forth

Females don't blink an identity pattern themselves; they're meant to *read*
a male's blink via their light sensor.

| # | Scenario | Trigger | Behavior | Covered by | Status |
|---|---|---|---|---|---|
| 2.1 | Any female becomes unsatisfied in the live installation | `Female.loop()` calls `search.start()` when unsatisfied (`hardware/female/__init__.py:151-158`), exactly like Male | **Fixed** (was: `Search.setup()`/`loop()` unconditionally raised `NotImplementedError`, crashing the female's whole thread within two loop ticks). Now `search.loop()` sways the female (same toggle-position pattern as Male's search) and `search.setup()` starts `read_pattern` with `started_by=self`, so it starts and stops together with `search` — `hardware/female/search/__init__.py:23-28`. Verified manually: starting `female1.search` no longer raises, `read_pattern.is_started` becomes `True`, and stopping `search` stops `read_pattern` too. | none (manually verified, not yet exercised by an automated scenario — see suggested next steps) | ✅ Fixed |
| 2.2 | Manual stand-in sway (`turn_back_and_forth`) | Tester starts a female's `turn_back_and_forth` directly | Female sways min/max, no drive/sensor coupling — still useful as an isolated-movement stand-in, though `search` (2.1) is now the real path | `test_movements` (`tests/test_movements/__init__.py:173-179`); used internally by all 4 `test_light_sensor_values` stages (§5) | ✅ Covered |
| 2.3 | Female facing a blinking male, reading his pattern correctly | `ReadPattern.loop()` buffers ≥5s of sensor samples, tries 10 sub-step offsets × all 10 circular rotations of the **six** `readable_light_patterns`, accepts first match with ≤1 bit mismatch (`hardware/female/search/read_pattern/__init__.py:80-136`) | Records `last_match = (male, drive)` — which expires after 10s if nothing refreshes it — and logs (throttled to once per 2s) `"Pattern detected: {male} drive={drive}"` | `test_read_pattern` (`tests/test_read_pattern/__init__.py`) — forces bar position + both bodies' facing + male drive state, starts `blink` + `read_pattern`, logs expected-vs-detected per second | ✅ Covered (staged manually; see 2.4 for the now-live autonomous path) |
| 2.8 | A female's search ends when she finds a partner | `Search.loop()` compares each decoded match against her own `drives.which_is_frustated()` and stops the search on the first male asking for a drive she is short of, leaving `(male, shared drive)` in `search.partner` (`hardware/female/search/__init__.py`) | **New.** Search used to run forever and a match had no consequence anywhere. She now ignores a male asking for something she doesn't want (as TJ's `Logic_fem.ino` does, switching on her own drive state), and when both want both the shared drive differs per male - `male1` gives O, `male2` gives P, TJ's "pick one" tiebreak | `pytest_tests/female/test_search.py` | ✅ Covered |
| 2.9 | What happens after she finds one | `Female.loop()` takes the pair from the search and starts `Reinforcement` (`hardware/female/reinforcement/__init__.py`) | The reinforcement thread raises `NotImplementedError` on its first tick, on purpose: this is the half that would draw the shared drive down (8.6). She then goes quiet rather than spinning - `Female.loop()` refuses to restart a thread that has already errored, so the error stays readable instead of being replaced every tick | `pytest_tests/female/test_female_loop.py` | ⚠️ Placeholder (deliberate) |
| 2.4 | `ReadPattern` running as part of normal `Female` behavior | Now wired: `search.setup()` starts `read_pattern.start(started_by=self)` (2.1) | Once a female becomes unsatisfied, she now both sways *and* attempts to decode any male pattern her sensor sees, autonomously — no test yet drives this end-to-end through `Female.loop()`'s own trigger rather than a manually-started `search` | none | ⚠️ Gap (fix landed, but no automated scenario exercises the full autonomous trigger → sway → decode chain yet) |
| 2.5 | Female not facing any male / male's ring off while sampling | Sensor reads low/"dark" for that sample window (see §6.1 for the simulated version) | Buffered samples for that window read `0`; if the whole 10-step window is all-dark, `_try_match()` still runs but is unlikely to match any reference pattern (all references start `1,1,...`) | `test_read_pattern` incidentally (whenever bar/male aren't aligned) | ⚠️ Gap (no scenario explicitly tests "no match" as the expected outcome) |
| 2.6 | Ambiguous match — the reading is within `max_mismatches=1` of more than one reference | Because every rotation is tried, the closest pair among the six references is only **2 bits apart**, so a single mis-read flash already puts a reading halfway between two answers | `_try_match()` returns the **first** match in iteration order, not the closest — order-dependent, so ambiguity resolves towards `male1` and towards `O` before `P` before `O+P`. Measured over all 1024 possible 10-bit readings: 350 (34%) are accepted as some male; with one flash wrong, only 53% still decode to the pattern actually sent (male1/O 100%, male2/P 20%) | none | ⚠️ Gap (much reduced — before the six-pattern fix a perfectly-read `male2/O` was **impossible** to report, see 2.7) |
| 2.7 | The two "R" patterns are excluded from comparison | `_try_match()` iterates `colloquy.readable_light_patterns` (six entries), not `light_patterns` (eight) — matching TJ's receiver, which only ever tests the same six | **Fixed.** With all eight in the set, `male1`'s R sequence is `male2`'s O sequence rotated, and since every rotation is tried the two are indistinguishable in principle: a perfectly-received `male2/O` decoded as `male1/<no drive>` every time, and the two never-sendable "R" answers absorbed ~15% of the reading space. Now all six decode correctly when read cleanly | none automated (verified exhaustively offline over all 1024 readings) | ✅ Fixed |

---

## 3. Drives (O drive / P drive — satisfaction & frustration)

Shared logic (`hardware/drive/__init__.py`) used identically by males and
females; `Male`/`Female`-specific `Drives` containers layer blink-pattern
selection (male only) and neopixel brightness/color mapping on top.

| # | Scenario | Trigger | Behavior | Covered by | Status |
|---|---|---|---|---|---|
| 3.1 | A drive counts up autonomously | `Drive.loop()` increments by 1 every `_update_interval = 2.4s` (`hardware/drive/__init__.py:113-115`) — ~4 minutes from 0 to 100, no auto-decay once maxed | Value rises monotonically until something external calls `decrease()`/`commit()` | `test_drive_light_values` — starts every drive, waits for **all** of them to hit 100 (`tests/test_drive_light_values/__init__.py:40-44`) | ✅ Covered |
| 3.2 | Drive crosses the satisfaction threshold (`< 12.5`) or frustration threshold (`> 75`) | Natural counting, or a manual setter | `is_satisfied`/`is_frustated` flip; for males this changes `which_is_frustated()` and therefore the blink pattern (§1.6/1.7); for both males and females it changes `Male.is_satisfied()`/`Female.is_satisfied()` and therefore whether `search` is (attempted to be) started | `test_male_patterns` (manual forcing, males only); `test_drive_light_values` (natural rise, both) | ✅ Covered for males; females only get the natural-rise path, not a targeted "just crossed frustration" check |
| 3.3 | Drive is externally satisfied (an interaction "resets" it) | `Drive.decrease()` (`hardware/drive/__init__.py:98-103`, subtracts 20, floor 0) — not called from anywhere in the surveyed loop code, so this only happens via manual/UI invocation today | Drive value drops by 20 | none | ⚠️ Gap — there's no modeled "interaction satisfies the drive" scenario; `decrease()` looks designed for exactly that but nothing calls it automatically |
| 3.4 | `Drive.satisfy()` is called | Not called anywhere in the codebase | `self.o_drive`/`self.p_drive` don't exist on a `Drive` instance (only on the parent `Drives` container) — `AttributeError` | none | 🐛 Broken / dead code (`hardware/drive/__init__.py:123-125`) |
| 3.5 | App starts without `"drive start values"` in `local/params.json` | `Drive.__init__` reads `self.body.params["drive start values"][self.body.name][name]` (`hardware/drive/__init__.py:32`) — this key is **absent from `params.py`'s `DEFAULTS`** | `KeyError` at construction time, before any thread starts | none | 🐛 Broken (config/environment landmine — `DEFAULTS` should probably include this key, or `local/params.json` must always predate a fresh checkout) |
| 3.6 | Drive brightness/color mapping while counting up | `Drives.update()` (male: `hardware/male/drives/__init__.py:112-120`; female: `hardware/female/drives/__init__.py:366-382`) | Male: `up_ring` brightness = `max(o,p)`, `o_drive_level`/`p_drive_level` brightness = raw value. Female: `head` brightness = raw `max(o,p)`, `body_o`/`body_p` brightness = perceptually gamma-compensated value, `feet` color flips orange/puce depending on which drive currently dominates | `test_drive_light_values` | ✅ Covered |

---

## 4. Bar

| # | Scenario | Trigger | Behavior | Covered by | Status |
|---|---|---|---|---|---|
| 4.1 | Any male starts searching → bar auto-wanders | `Bar.loop()`: if not already searching, and *any* male's `search.is_started`, start the bar's own `search` (plain toggle over its full 10000-unit range) — `hardware/bar/__init__.py:111-118` | Bar sways full-range regardless of which male/female pair is actually relevant, and — like male search (1.2) — nothing stops it again automatically | none | ⚠️ Gap (and compounds 2.1: since female search crashes almost immediately, in practice the bar may end up wandering with no female able to read anything) |
| 4.2 | Positioning a specific male in front of a specific female | `set_male_in_front_of_female`/`move_male_in_front_of_female_and_wait` using fixed offsets from `params["bar"]["interaction_origins"]` (`hardware/bar/__init__.py:140-151`, `params.py:21-26`) | Bar moves (blocking or non-blocking) to the exact offset for that pair | `test_movements` (jogs every pair), `test_read_pattern`, `test_light_sensor_values` (all use `move_male1_in_front_of_female1_and_wait`) | ✅ Covered |
| 4.3 | Bar's two "linger" sub-behaviors | `turn_back_and_forth` (full 10000-range) vs. `turn_back_and_forth_around_f1` (±1500 around male1-facing-female1) — `hardware/bar/turn_back_and_forth/__init__.py`, `hardware/bar/turn_back_and_forth_around_f1/__init__.py` | Two different sway scopes; the latter is used by `test_light_sensor_values`'s 3rd stage to simulate "bar drifting near an active pair" without leaving that pair's vicinity | `test_movements` (both, manual); `test_light_sensor_values/test_with_female_male_and_bar_moving` (around-f1 variant, as part of a sequence) | ✅ Covered |
| 4.4 | Accessing `Bar.drives` or `Bar.arduino` | Either property is read (`hardware/bar/__init__.py:53-59`) | `AttributeError` — `self._drives`/`self._arduino` are never assigned in `__init__` (the bar has no drives/arduino segments of its own) | none | 🐛 Broken / dead code — landmine for future scenario code that assumes every hardware node has these |

---

## 5. Light sensors

| # | Scenario | Trigger | Behavior | Covered by | Status |
|---|---|---|---|---|---|
| 5.1 | Simulated female1 sensor, aligned and lit | (virtual hardware only) female1 near her own origin, bar positioned at the interaction offset for some male in front of female1, and that male's ring is currently in an "on" blink phase (`virtual_hardware/virtual_serial_port.py:140-154`) | Reading ≈ `threashold(300) + noise(100-109)` → `read_as_bool()` is `True` | `test_read_pattern`, `test_light_sensor_values` (indirectly, all stages) | ✅ Covered |
| 5.2 | Simulated female1 sensor, any misalignment (not near origin, no male positioned there, or that male's ring off) | Same code path, else branch | Reading ≈ `threashold(300) - noise(100-109)` → `False` | same as 5.1 (the "off" side is exercised any time the "on" alignment isn't met) | ✅ Covered |
| 5.3 | Simulated female2/female3 and both males' sensors | Always | Flat `10` regardless of any real state — no interaction modeling exists for these in simulation (`virtual_hardware/virtual_serial_port.py:137-138`) | `test_sensors` (reads the flat value, doesn't validate it against expected state) | ⚠️ Gap — female2/female3 and male sensors have no simulated scenario capable of exercising real threshold-crossing behavior; only female1 does |
| 5.4 | Real hardware sensor polling / manual cover-uncover | Tester starts `test_sensors`, physically covers/uncovers a sensor | Live per-sensor readout in the UI, logged to CSV every 0.5s | `test_sensors` (`tests/test_sensors/__init__.py`) | ✅ Covered (real hardware only — this is not meaningful on simulated hosts beyond 5.1-5.3) |
| 5.5 | Sensor value behavior across a full "everything moving" stress run | 30 males+females+bar all swaying simultaneously for up to 30 min | Per-tick sensor CSV logged for all 3 females | `test_light_sensor_values/test_with_everything_moving` — per `CLAUDE.md`, male rings are held **constant on** here, not blinking a real pattern, so this measures "how long is female facing a lit male," not pattern-decode accuracy | ✅ Covered (with that caveat) |

---

## 6. Neopixels

| # | Scenario | Trigger | Behavior | Covered by | Status |
|---|---|---|---|---|---|
| 6.1 | Every segment cycled through red/green/blue/white | Tester starts `test_neopixels` | All 20 segments (3×female's 4 + 2×male's 4) step through colors, 0.8s each, for wiring/visual confirmation | `test_neopixels` (`tests/test_neopixels/__init__.py`) | ✅ Covered |
| 6.2 | Drive-driven brightness/color (male & female) | Drive value changes | See §3.6 | `test_drive_light_values` | ✅ Covered |
| 6.3 | Ring blink during search | See §1.1 | Ring toggles white on/off per pattern bit | `test_male_patterns` (blink only) | ✅ Covered (blink only — not combined with real search-triggered sway, per 1.1) |
| 6.4 | Arduino reboot leaving LEDs on in a random state | App startup (`main.py`'s `colloquy1()`) | All neopixels forced on then off once, to normalize state | none (this is a startup routine, not a `colloquy/tests/` scenario) | ⚠️ Gap — no scenario verifies this recovery step actually clears a stuck-on LED |

---

## 7. Cross-body integration scenarios (not exercised by any single test)

These span multiple sub-behaviors and aren't covered end-to-end by any
current scenario — each piece is tested in isolation (or not at all) but
the full chain never runs together as it would in the real installation:

1. **Full autonomous loop**: a male becomes frustrated → blinks his pattern
   → bar auto-wanders (4.1) → a female becomes unsatisfied and searches,
   reading his pattern (2.3/2.4), and (once something acts on a match —
   see below) has her drive satisfied accordingly. The female-search crash
   (2.1) that used to break this immediately is now fixed, but nothing yet
   demonstrates the *whole* loop end-to-end through `Female.loop()`/
   `Male.loop()`'s own triggers — `test_read_pattern` still stages bar
   position and drive state manually rather than letting the autonomous
   triggers drive it, and nothing currently reacts to `read_pattern.last_match`
   by satisfying the matched drive (that link doesn't exist yet — matches
   are logged/recorded but have no effect on the female's or male's state).
2. **Two males simultaneously frustrated for the same female** — bar can
   only be in front of one male at a time; no scenario documents or tests
   the resulting contention/ordering.
3. **A female mid-`turn_back_and_forth` when a male's drive state (and
   therefore blink pattern) changes** — not tested; per 1.3 the pattern
   switches live and garbles at the boundary, which is exactly the sort of
   reading 2.6 mis-decodes, so this is the most likely source of confident
   wrong answers in the live installation.
4. **Recovering an errored thread** — since an errored `BaseThread` can
   never be `start()`-ed again (see the background note above), there is
   no documented/tested recovery scenario for *any* body once it errors
   once. The failure is at least *visible* now: rendering a failed thread
   used to raise `TypeError` out of `ThreadErrors.snapshot()` and take the
   whole page down, so the one thing that could say what had gone wrong was
   the thing that broke (observed on real hardware, `docs/errors/
   2026-08-17.txt`). It now renders every traceback under that node inline,
   its own first, then any from threads it started. There is still no way
   to *clear* them from the UI. This used to be the guaranteed, near-immediate outcome for every
   female (2.1) — now that's fixed, but the underlying "no recovery path"
   limitation still applies to any other thread that errors.

---

## 8. Divergences from TJ's original firmware (`logic35_systems`)

Read against `local/Code/Code/Units/logic35_systems/` — send in
`act_light.ino` (`act_transmit_light()`), receive in `sense_light.ino`
(sample → bit) and `sense_light_pattern.ino` (bits → match), tables and
constants in `logic35_systems.ino`, decisions in `Logic_male.ino` /
`Logic_fem.ino`. Note the 10-step table Python copied is **commented out**
there; the active one is 40 samples.

What matches: the pattern *values* (verified — the active 40-sample arrays
are exactly the 10-step ones upsampled ×4, all eight of them), and
rotation-tolerant matching (TJ compares one alignment per tick against a
circular buffer, so all 40 alignments are covered over one pattern length —
trying every rotation at once is the same idea, not a shortcut).

| # | Subject | TJ's firmware | This implementation | Consequence |
|---|---|---|---|---|
| 8.1 | Patterns compared | six (I/II × O/P/OP) | six, since the fix (2.7) | — resolved |
| 8.2 | "Flash seen" test | `sample − running_average(last 100 samples ≈ 5s) > 30` — AC-coupled, self-calibrating to ambient light and to the male's distance | `read() > params["photosensor_threashold"]` (300), one fixed absolute level shared by all three females | **Largest remaining divergence.** In a bright room the sensor can sit above the threshold permanently, or a distant ring never reach it; no amount of pattern logic recovers from a bit stream that is all-1 or all-0 |
| 8.3 | Transmission shape | one-shot burst: 40 samples from index 0, then the light goes **off** and the male listens; next burst 87 ticks (4.35s) later | continuous rotation of a deque, no gap, forever | TJ's silence frames the burst, so a wrong alignment mixes in the dark period and fails. A seamless loop makes every rotation equally plausible — the phase ambiguity is self-inflicted |
| 8.4 | Timing | 50ms per sample, 4 samples per logical bit → 200ms/bit, 2s per full pattern; receive buffer is exactly one pattern long | 500ms per bit, 5s per full pattern | A female needs 5s of clear view where the original needs 2 — a large difference while the bar is sliding past |
| 8.5 | Error budget | ≥34 of 40 samples must agree (6 wrong, 15%); closest pair over all rotations is 8 samples apart, so ≥4 bad samples are needed before a reading sits between two patterns | 1 wrong bin of 10 (10%); closest pair is 2 apart, so **one** bad bin is already halfway to another answer | Same ratio, very different margin: oversampling is what buys TJ's robustness, not the percentage |
| 8.6 | Reply channel | the female answers a light match by transmitting **the same pattern back as sound** (`act_transmit_I_O_sound()`), and the male spends his 2.35s gap listening for it before stopping and entering reinforcement | no sound channel at all | This is the missing closing link of §7.1 — in the original the loop closes over sound, not light |
| 8.7 | Who she answers | she filters by her own drive state: looking for O, she accepts only `I_O`, `I_OP`, `II_O`, `II_OP` and ignores a male asking for P (`Logic_fem.ino:110-225`) | **Ported** (2.8): `Search.loop()` applies the same filter, and `which_is_frustated()` moved to `hardware/drive/` so both sexes share one state machine - the female's `Drives` had none at all before, exactly the gap this exposed | — resolved |

---

## Suggested next steps

Ranked by how much of the above unblocks:

1. ~~Fix or replace `Female.Search` (2.1)~~ — **done**: `search.loop()` now
   sways the female and `search.setup()` starts `read_pattern`.
2. Add a `colloquy/tests/` scenario that drives the full loop in §7.1
   through the real `Male.loop()`/`Female.loop()` triggers rather than
   staged preconditions, to catch regressions in the autonomous path
   itself (today only the manually-staged `test_read_pattern` exercises
   `ReadPattern` at all) — see "How to test these reliably" below for a
   pattern to build it on.
3. Move the "flash seen" test from an absolute threshold to TJ's
   relative one (8.2) — a sample counted as light only when it exceeds a
   running average of recent samples. This is the highest-value remaining
   decode fix and is independent of everything else in this list.
4. Implement `Female.Reinforcement` (2.9) — the placeholder is in place
   and receives the pair, so what remains is the exchange itself:
   subtract from the shared drive while the partner keeps answering,
   zero it below the interested floor, and hold a satisfaction moment
   with both drives frozen (8.6). TJ closes this over the sound
   channel, which this port has no equivalent of - decide whether to
   port sound or to close the loop over light instead. The male side
   (receptivity, his own reinforcement) is untouched so far.
5. Consider adopting TJ's sampling model outright (8.3-8.5): burst then
   silence, 50ms samples, 4 per bit, tolerance as a fraction of 40. That
   would replace the phase ambiguity and thin error margin in one move,
   rather than tuning `max_mismatches` against a 2-bit minimum distance.
6. Add `"drive start values"` to `params.py`'s `DEFAULTS` (3.5), or
   document that `local/params.json` must be seeded before first run.
7. Decide whether 1.2/1.7/4.1 (search/wander never stopping itself) is
   intended, and if not, add the missing stop condition.
