# Colloquy of Mobiles — Code Documentation

What this software actually does, read off the source and organized by
sub-behavior. For each behavior: the trigger, what follows from it, which
`colloquy/tests/` hardware test (if any) exercises it, and its status.

This is a reference document, not runnable code — it describes what the
code in `colloquy/drivers/` actually does (and doesn't do), to make gaps
and existing coverage visible in one place. File:line references point at
`Source code/Python/colloquy/`.

It is a map of the repository, and it is checked by reading source.
**Scenarios** are the other half of the same installation: the artwork's
behaviour described along the clock, in what is visible in the room, and
checked by standing in front of it with a stopwatch. They live in
`colloquy/scenarios/` as `*.scenario` files and hang off the thing that
starts them — wherever the page offers a start(), it also says what will
happen. Neither document is derivable from the other; an angle quoted in
both went stale in the scenario and not here.

"Scenario" means that and nothing else. The modules under
`colloquy/tests/` were called scenarios for a while and are called
**hardware tests** below: they drive real or simulated bodies over time
and leave a CSV or an SVG for somebody to look at.

## Legend

- ✅ **Covered** — an existing `colloquy/tests/` hardware test exercises this.
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

The `colloquy/tests/` hardware tests (§1-6's "Covered by" column) are
built for a *different* kind of reliability than regression-checking a code
change: they run for tens of seconds to tens of minutes, drive real or
simulated hardware, and produce a CSV/SVG for a human to look at. They're
the right tool for calibrating against actual servos/sensors, not for
quickly confirming "did my change break this."

For that second kind of check — confirming a specific behavior/fix, fast
and repeatably — script it directly against the `Base` tree instead of
going through the web UI or a full hardware test. This is the
same approach used to verify the `Female.Search` fix above:

```python
import sys, time
from pathlib import Path
sys.path.append(str((Path(r"C:\workspace\workspace2\Colloquy\exposition") / "Source code" / "Python").resolve()))
from colloquy import Colloquy

colloquy = Colloquy()
colloquy.drivers.u2d2.com_port.set("COM4")
colloquy.drivers.u2d2.open()
colloquy.drivers.arduino.open()
for dxl in colloquy.drivers.u2d2.dxl_list:
    dxl.init_hardware()

node = colloquy.drivers.female1.search  # whatever you're checking
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
  `virtual_drivers/` automatically — no serial port needed, safe to run
  repeatedly, and fast (no real servo travel time).
- **One fresh `Colloquy()` per check.** A `BaseThread` that has ever
  errored can never `start()` again — `thread_errors` sticks for the
  life of the object (`base_thread/__init__.py:82-83`). Reusing one
  `Colloquy()` across several scripted checks in the same process means
  an earlier failure can make a *later* check fail for the wrong reason.
- **Sleep long enough to cross the relevant tick, not just "a bit."** The
  loop tick itself is ~10ms, but what you're actually watching for is
  usually a sub-thread's own interval (e.g. `ReadPattern` needs a whole
  2s burst buffered before it can match anything, and a male only sends
  one every 4.35s, so budget two cycles; `Drive` increments only every
  2.4s). Sleeping less than that will pass for the wrong reason.
- **Force slow states instead of waiting for them.** Drive values take up
  to ~4 minutes to swing from satisfied to frustrated (§3.1). Don't wait —
  either call the existing forcing setters (`set_o_and_p_to_100()` etc.,
  `drivers/male/drives/__init__.py:122-151`, used the same way by
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
| 1.1 | Male becomes frustrated, starts searching | `Male.loop()`: search not started and `not is_satisfied()` (neither O nor P drive is "freshly satisfied") — `drivers/male/__init__.py:153-160` | `search.start()`: male sways between min/max position every tick it isn't already moving (`search/__init__.py:25-27`), and `search.setup()` starts `blink`, which sets the ring to white and sends the 10-bit pattern for `drives.which_is_frustated()` at 0.2s/bit — a 2s burst, then the ring dark until the next burst, 4.35s after the last one began (`search/blink/__init__.py`, `colloquy/light_pattern_timing.py`) | none directly (see 1.4/1.5 for partial coverage) | ⚠️ Gap |
| 1.2 | Search stops itself when the male goes inert | `Male.loop()` now supervises both ways: it starts his search while he wants something and stops it the moment he wants nothing (`drivers/male/__init__.py`) | **Fixed.** He used to start calling the first time an appetite climbed and then call for the rest of the run, whatever his drives did afterwards - only `Male.setdown()` ever stopped him. TJ's `Logic_male.ino` transmits only while `internal_drive_state` is not the inert one. This is also what lets the bar come to rest (4.1), since the bar follows these flags | `pytest_tests/drivers/test_search_supervision.py`; `test_search` (`tests/test_search/`) runs the whole thing on the bodies | ✅ Fixed |
| 1.3 | Male's drive state changes mid-blink | `Blink.loop()` calls `male.get_blink_pattern()` once, when a burst starts, and not again until the next one (`search/blink/__init__.py`) | **Fixed.** The pattern still follows the drive state — the change simply takes effect at the next burst, as in TJ's firmware, where `MALE_setSearchLight()` is called at the cycle boundary and nowhere else. It used to be re-read every 0.5s step from a per-state deque carrying its own rotation phase, so a switch mid-cycle emitted a few steps belonging to neither pattern — exactly the sort of reading a female decodes as a third one (2.6). This fires ~2.5 minutes into every search, when both drives pass 75 and the male switches to his `("O","P")` pattern for good | `pytest_tests/male/test_blink.py` | ✅ Fixed |
| 1.4 | Manually forcing a drive state and observing the blink pattern | Tester starts `test_male_patterns`, then calls one of the drive setters (`set_o_to_0_p_to_100`, `set_p_to_0_o_to_100`, `set_o_and_p_to_30`, `set_o_and_p_to_100`, `drivers/male/drives/__init__.py:122-151`) | Only the male's `blink` sub-thread runs (no physical sway) — ring blinks the pattern matching the forced state | `test_male_patterns` (`tests/test_male_patterns/__init__.py`) | ✅ Covered (blink only, no sway) |
| 1.5 | Manual sway without drive coupling | Tester starts a male's `turn_back_and_forth` directly from `test_movements` | Male sways min/max on a fixed toggle, ring untouched (no blink) | `test_movements` (`tests/test_movements/__init__.py:173-179`) | ✅ Covered (sway only, no blink) |
| 1.6 | Both drives frustrated simultaneously | `which_is_frustated()` returns `("O","P")` when both `> 75` (frustrated limit), or when `o_drive.value == p_drive.value` in the non-satisfied/non-frustrated middle range (`drivers/male/drives/__init__.py:45-65`) | Male blinks the combined `("O","P")` pattern (e.g. male1: `1,1,0,0,0,1,0,1,0,1`) | `test_read_pattern` forces this via `set_o_and_p_to_100()` (`tests/test_read_pattern/__init__.py:98`) | ✅ Covered |
| 1.7 | Drive tie in the *unsatisfied, non-frustrated* middle range | `o_drive.value == p_drive.value` and neither is satisfied/frustrated | Same `("O","P")` pattern as full frustration (`drivers/male/drives/__init__.py:60-63`) — a partial tie reads identically to "both fully frustrated" | none | ⚠️ Gap |
| 1.8 | Drive value combination outside all handled branches | Should be unreachable given the branch logic, but is a hard crash (`ValueError("Drive Error", ...)`) if ever reached (`drivers/male/drives/__init__.py:64-65`) | Male's `Drives.update()`/blink-pattern selection crashes | none | 🐛 Broken (defensive-only, but untested) |

---

## 2. Female — search, read-pattern, turn-back-and-forth

Females don't blink an identity pattern themselves; they're meant to *read*
a male's blink via their light sensor.

| # | Scenario | Trigger | Behavior | Covered by | Status |
|---|---|---|---|---|---|
| 2.1 | Any female becomes unsatisfied in the live installation | `Female.loop()` calls `search.start()` when unsatisfied (`drivers/female/__init__.py:151-158`), exactly like Male | **Fixed** (was: `Search.setup()`/`loop()` unconditionally raised `NotImplementedError`, crashing the female's whole thread within two loop ticks). Now `search.loop()` sways the female (same toggle-position pattern as Male's search) and `search.setup()` starts `read_pattern` with `started_by=self`, so it starts and stops together with `search` — `drivers/female/search/__init__.py:23-28`. Verified manually: starting `female1.search` no longer raises, `read_pattern.is_started` becomes `True`, and stopping `search` stops `read_pattern` too. | none (manually verified, not yet exercised by an automated test — see suggested next steps) | ✅ Fixed |
| 2.2 | Manual stand-in sway (`turn_back_and_forth`) | Tester starts a female's `turn_back_and_forth` directly | Female sways min/max, no drive/sensor coupling — still useful as an isolated-movement stand-in, though `search` (2.1) is now the real path | `test_movements` (`tests/test_movements/__init__.py:173-179`); used internally by all 4 `test_light_sensor_values` stages (§5) | ✅ Covered |
| 2.3 | Female facing a blinking male, reading his pattern correctly | `ReadPattern.loop()` buffers one burst (2s) of sensor samples, tries 10 sub-step offsets × all 10 circular rotations of the **six** `readable_light_patterns`, accepts first match with ≤1 bit mismatch (`drivers/female/search/read_pattern/__init__.py`) | Records `last_match = (male, drive)` — which expires after two burst cycles (8.7s) if nothing refreshes it, a male being able to refresh it only once every 4.35s — and logs (throttled to once per 2s) `"Pattern detected: {male} drive={drive}"` | `test_read_pattern` (`tests/test_read_pattern/__init__.py`) — forces bar position + both bodies' facing + male drive state, starts `blink` + `read_pattern`, logs expected-vs-detected per second | ✅ Covered (staged manually; see 2.4 for the now-live autonomous path) |
| 2.8 | A female's search ends when she finds a partner | `Search.loop()` compares each decoded match against her own `drives.which_is_frustated()` and stops the search on the first male asking for a drive she is short of, leaving `(male, shared drive)` in `search.partner` (`drivers/female/search/__init__.py`) | **New.** Search used to run forever and a match had no consequence anywhere. She now ignores a male asking for something she doesn't want (as TJ's `Logic_fem.ino` does, switching on her own drive state), and when both want both the shared drive differs per male - `male1` gives O, `male2` gives P, TJ's "pick one" tiebreak | `pytest_tests/female/test_search.py`; `test_female_search` (`tests/test_female_search/__init__.py`) - stages one pairing on the bodies (drive states forced, bar and both bodies moved into position), starts the search and reports how it ended | ✅ Covered |
| 2.9 | What happens after she finds one | `Female.loop()` takes the pair from the search and starts `Reinforcement` (`drivers/female/reinforcement/__init__.py`) | The reinforcement thread raises `NotImplementedError` on its first tick, on purpose: this is the half that would draw the shared drive down (8.6). She then goes quiet rather than spinning - `Female.loop()` refuses to restart a thread that has already errored, so the error stays readable instead of being replaced every tick | `pytest_tests/female/test_female_loop.py` | ⚠️ Placeholder (deliberate) |
| 2.4 | `ReadPattern` running as part of normal `Female` behavior | Now wired: `search.setup()` starts `read_pattern.start(started_by=self)` (2.1) | Once a female becomes unsatisfied, she now both sways *and* attempts to decode any male pattern her sensor sees, autonomously — no test yet drives this end-to-end through `Female.loop()`'s own trigger rather than a manually-started `search` | `test_female_search` covers sway → decode → end for a search started by hand | ⚠️ Gap (narrowed: what is still unexercised is `Female.loop()` starting the search itself, off her own drive state, rather than a test starting it) |
| 2.5 | Female not facing any male / male's ring off while sampling | Sensor reads low/"dark" for that sample window (see §6.1 for the simulated version) | Buffered samples for that window read `0`; if the whole 10-step window is all-dark, `_try_match()` still runs but is unlikely to match any reference pattern (all references start `1,1,...`) | `test_read_pattern` incidentally (whenever bar/male aren't aligned) | ⚠️ Gap (nothing explicitly tests "no match" as the expected outcome) |
| 2.6 | Ambiguous match — the reading is within `max_mismatches=1` of more than one reference | Because every rotation is tried, the closest pair among the six references is only **2 bits apart**, so a single mis-read flash already puts a reading halfway between two answers | `_try_match()` returns the **first** match in iteration order, not the closest — order-dependent, so ambiguity resolves towards `male1` and towards `O` before `P` before `O+P`. Measured over all 1024 possible 10-bit readings: 350 (34%) are accepted as some male; with one flash wrong, only 53% still decode to the pattern actually sent (male1/O 100%, male2/P 20%) | none | ⚠️ Gap (much reduced — before the six-pattern fix a perfectly-read `male2/O` was **impossible** to report, see 2.7) |
| 2.7 | The two "R" patterns are excluded from comparison | `_try_match()` iterates `colloquy.readable_light_patterns` (six entries), not `light_patterns` (eight) — matching TJ's receiver, which only ever tests the same six | **Fixed.** With all eight in the set, `male1`'s R sequence is `male2`'s O sequence rotated, and since every rotation is tried the two are indistinguishable in principle: a perfectly-received `male2/O` decoded as `male1/<no drive>` every time, and the two never-sendable "R" answers absorbed ~15% of the reading space. Now all six decode correctly when read cleanly | none automated (verified exhaustively offline over all 1024 readings) | ✅ Fixed |

---

## 3. Drives (O drive / P drive — satisfaction & frustration)

Shared logic (`drivers/drive/__init__.py`) used identically by males and
females; `Male`/`Female`-specific `Drives` containers layer blink-pattern
selection (male only) and neopixel brightness/color mapping on top.

| # | Scenario | Trigger | Behavior | Covered by | Status |
|---|---|---|---|---|---|
| 3.1 | A drive counts up autonomously | `Drive.loop()` increments by 1 every `_update_interval = 2.4s` (`drivers/drive/__init__.py:113-115`) — ~4 minutes from 0 to 100, no auto-decay once maxed | Value rises monotonically until something external calls `decrease()`/`commit()` | `test_drive_light_values` — starts every drive, waits for **all** of them to hit 100 (`tests/test_drive_light_values/__init__.py:40-44`) | ✅ Covered |
| 3.2 | Drive crosses the satisfaction threshold (`< 12.5`) or frustration threshold (`> 75`) | Natural counting, or a manual setter | `is_satisfied`/`is_frustated` flip; for males this changes `which_is_frustated()` and therefore the blink pattern (§1.6/1.7); for both males and females it changes `Male.is_satisfied()`/`Female.is_satisfied()` and therefore whether `search` is (attempted to be) started | `test_male_patterns` (manual forcing, males only); `test_drive_light_values` (natural rise, both) | ✅ Covered for males; females only get the natural-rise path, not a targeted "just crossed frustration" check |
| 3.3 | Drive is externally satisfied (an interaction "resets" it) | `Drive.decrease()` (`drivers/drive/__init__.py:98-103`, subtracts 20, floor 0) — not called from anywhere in the surveyed loop code, so this only happens via manual/UI invocation today | Drive value drops by 20 | none | ⚠️ Gap — there's no modeled "interaction satisfies the drive" scenario; `decrease()` looks designed for exactly that but nothing calls it automatically |
| 3.4 | `Drive.satisfy()` is called | Not called anywhere in the codebase | `self.o_drive`/`self.p_drive` don't exist on a `Drive` instance (only on the parent `Drives` container) — `AttributeError` | none | 🐛 Broken / dead code (`drivers/drive/__init__.py:123-125`) |
| 3.5 | App starts without `"drive start values"` in `local/params.json` | `Drive.__init__` reads `self.body.params["drive start values"][self.body.name][name]` (`drivers/drive/__init__.py:32`) — this key is **absent from `params.py`'s `DEFAULTS`** | `KeyError` at construction time, before any thread starts | none | 🐛 Broken (config/environment landmine — `DEFAULTS` should probably include this key, or `local/params.json` must always predate a fresh checkout) |
| 3.6 | Drive brightness/color mapping while counting up | `Drives.update()` (male: `drivers/male/drives/__init__.py:112-120`; female: `drivers/female/drives/__init__.py:366-382`) | Male: `up_ring` brightness = `max(o,p)`, `o_drive_level`/`p_drive_level` brightness = raw value. Female: `head` brightness = raw `max(o,p)`, `body_o`/`body_p` brightness = perceptually gamma-compensated value, `feet` color flips orange/puce depending on which drive currently dominates | `test_drive_light_values` | ✅ Covered |

---

## 4. Bar

| # | Scenario | Trigger | Behavior | Covered by | Status |
|---|---|---|---|---|---|
| 4.1 | The bar decides whether the bar wanders | `Bar.loop()` watches the males' search flags and follows them **both ways**: it sets off when any male is calling and stops when the last one goes quiet (`drivers/bar/__init__.py`) | **Fixed.** The starting half was all there was, so the first male to get hungry set the rail going for the rest of the run - sliding back and forth in front of nobody. The rail has no appetite of its own, so what the males are doing is the only thing that can tell it: it exists to carry a calling male past a female, and with nobody calling there is nothing to carry. It reads `search.is_started` rather than `is_satisfied()` deliberately, so it stays in step with a thread that is still winding down. Still full-travel rather than aimed at a particular pair | `pytest_tests/drivers/test_search_supervision.py`; `test_search` | ✅ Fixed |
| 4.2 | Positioning a specific male in front of a specific female | `set_male_in_front_of_female`/`move_male_in_front_of_female_and_wait` using fixed offsets from `params["bar"]["interaction_origins"]` (`drivers/bar/__init__.py:140-151`, `params.py:21-26`) | Bar moves (blocking or non-blocking) to the exact offset for that pair | `test_movements` (jogs every pair), `test_read_pattern`, `test_light_sensor_values` (all use `move_male1_in_front_of_female1_and_wait`) | ✅ Covered |
| 4.3 | Bar's two "linger" sub-behaviors | `turn_back_and_forth` (the full 292.969° travel) vs. `turn_back_and_forth_around_f1` (±43.9° around male1-facing-female1) — `drivers/bar/turn_back_and_forth/__init__.py`, `drivers/bar/turn_back_and_forth_around_f1/__init__.py` | Two different sway scopes; the latter is used by `test_light_sensor_values`'s 3rd stage to simulate "bar drifting near an active pair" without leaving that pair's vicinity | `test_movements` (both, manual); `test_light_sensor_values/test_with_female_male_and_bar_moving` (around-f1 variant, as part of a sequence) | ✅ Covered |
| 4.4 | Accessing `Bar.drives` or `Bar.arduino` | Either property is read (`drivers/bar/__init__.py:53-59`) | `AttributeError` — `self._drives`/`self._arduino` are never assigned in `__init__` (the bar has no drives/arduino segments of its own) | none | 🐛 Broken / dead code — landmine for future test code that assumes every hardware node has these |

---

## 5. Light sensors

| # | Scenario | Trigger | Behavior | Covered by | Status |
|---|---|---|---|---|---|
| 5.1 | Simulated female1 sensor, aligned and lit | (virtual hardware only) female1 near her own origin, bar positioned at the interaction offset for some male in front of female1, and that male's ring is currently in an "on" blink phase (`virtual_drivers/virtual_serial_port.py:140-154`) | Reading ≈ `threashold(300) + noise(100-109)` → `read_as_bool()` is `True` | `test_read_pattern`, `test_light_sensor_values` (indirectly, all stages) | ✅ Covered |
| 5.2 | Simulated female1 sensor, any misalignment (not near origin, no male positioned there, or that male's ring off) | Same code path, else branch | Reading ≈ `threashold(300) - noise(100-109)` → `False` | same as 5.1 (the "off" side is exercised any time the "on" alignment isn't met) | ✅ Covered |
| 5.3 | Simulated male sensors | Always | Flat darkness regardless of any real state — no interaction modelling exists for a male's own sensors in simulation. All three females *are* modelled (they were not always: female2/female3 used to return the same flat value, so nothing involving them could produce a reading to decode) | `test_sensors` (reads the flat value, doesn't validate it against expected state) | ⚠️ Gap — the male sensors have no simulated behaviour capable of exercising a threshold crossing |
| 5.4 | Real hardware sensor polling / manual cover-uncover | Tester starts `test_sensors`, physically covers/uncovers a sensor | Live per-sensor readout in the UI, logged to CSV every 0.5s | `test_sensors` (`tests/test_sensors/__init__.py`) | ✅ Covered (real hardware only — this is not meaningful on simulated hosts beyond 5.1-5.3) |
| 5.5 | Sensor value behavior across a full "everything moving" stress run | 30 males+females+bar all swaying simultaneously for up to 30 min | Per-tick sensor CSV logged for all 3 females | `test_light_sensor_values/test_with_everything_moving` — per `CLAUDE.md`, male rings are held **constant on** here, not blinking a real pattern, so this measures "how long is female facing a lit male," not pattern-decode accuracy | ✅ Covered (with that caveat) |
| 5.6 | **False positives: does a female read light where there is none?** | Tester starts `test_light_sensor_values/test_for_false_positives`, having stopped the installation (it refuses otherwise) | Every light in the installation off, all three females sweeping their own travel, sensor and angle recorded together as fast as the Arduino answers (~9 readings a second each). One graph per female: angle across, sensor value up, with the average reading at each angle and the spread (max − min) there, and the threshold drawn across both. A bump in the average is something bright from that direction; a tall spread is an aim whose reading is not repeatable — either is a false positive waiting to happen. Duration is chosen on the page | `test_light_sensor_values/test_for_false_positives` | ✅ Covered (the answer is a rig measurement — the simulator's "dark" is uniform noise, so it can only prove the plumbing) |

---

## 6. Neopixels

| # | Scenario | Trigger | Behavior | Covered by | Status |
|---|---|---|---|---|---|
| 6.1 | Every segment cycled through red/green/blue/white | Tester starts `test_neopixels` | All 20 segments (3×female's 4 + 2×male's 4) step through colors, 0.8s each, for wiring/visual confirmation | `test_neopixels` (`tests/test_neopixels/__init__.py`) | ✅ Covered |
| 6.2 | Drive-driven brightness/color (male & female) | Drive value changes | See §3.6 | `test_drive_light_values` | ✅ Covered |
| 6.3 | Ring blink during search | See §1.1 | Ring toggles white on/off per pattern bit | `test_male_patterns` (blink only) | ✅ Covered (blink only — not combined with real search-triggered sway, per 1.1) |
| 6.4 | Arduino reboot leaving LEDs on in a random state | App startup (`main.py`'s `colloquy1()`) | All neopixels forced on then off once, to normalize state | none (this is a startup routine, not a hardware test) | ⚠️ Gap — nothing verifies this recovery step actually clears a stuck-on LED |

---

## 7. Cross-body integration scenarios (not exercised by any single test)

These span multiple sub-behaviors and aren't covered end-to-end by any
current hardware test — each piece is tested in isolation (or not at all) but
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
   Half of that missing link is a whole channel rather than a line of code:
   in the original the female answers over sound and the exchange runs from
   there — see §9.
2. **Two males simultaneously frustrated for the same female** — bar can
   only be in front of one male at a time; nothing documents or tests
   the resulting contention/ordering.
3. **A female mid-`turn_back_and_forth` when a male's drive state (and
   therefore blink pattern) changes** — not tested. The garbled boundary
   this used to produce is gone (1.3: the pattern is now picked once per
   burst), so what is left to check is the ordinary case — she is part-way
   through reading when the message she is reading changes to a different
   one between bursts.
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
| 8.3 | Transmission shape | one-shot burst: 40 samples from index 0, then the light goes **off** and the male listens; next burst 87 ticks (4.35s) later | **Ported** (`colloquy/light_pattern_timing.py`): same shape, same 4.35s cycle, minus the listening — there is no sound channel to listen on (8.6), so the male is simply dark for the 2.35s gap | — resolved. Measured on the virtual hardware, male1 facing female1: sending `("O","P")`, 177 of 181 decodes came back `male1/("O","P")`; sending `("P",)`, 173 of 182 came back `male1/("P",)`. Before the gap, a male sending both was read as `P` outright |
| 8.4 | Timing | 50ms per sample, 4 samples per logical bit → 200ms/bit, 2s per full pattern; receive buffer is exactly one pattern long | **Ported**: 200ms/bit, 2s per burst, receive buffer one burst plus a bit. She still samples as fast as the Arduino answers (~30ms on the simulator, 6-7 votes a bit) rather than on TJ's 50ms tick, because the binning is by wall clock and more votes per bin is only ever better | — resolved. A female now needs 2s of clear view instead of 5, which is what makes a decode plausible at all while the bar is sliding past |
| 8.5 | Error budget | ≥34 of 40 samples must agree (6 wrong, 15%); closest pair over all rotations is 8 samples apart, so ≥4 bad samples are needed before a reading sits between two patterns | 1 wrong bin of 10 (10%); closest pair is 2 apart, so **one** bad bin is already halfway to another answer | Same ratio, very different margin: oversampling is what buys TJ's robustness, not the percentage |
| 8.6 | Reply channel | the female answers a light match by transmitting **the same pattern back as sound** (`act_transmit_I_O_sound()`), and the male spends his 2.35s gap listening for it before stopping and entering reinforcement | no sound channel at all | This is the missing closing link of §7.1 — in the original the loop closes over sound, not light. Broken out in full in §9 |
| 8.7 | Who she answers | she filters by her own drive state: looking for O, she accepts only `I_O`, `I_OP`, `II_O`, `II_OP` and ignores a male asking for P (`Logic_fem.ino:110-225`) | **Ported** (2.8): `Search.loop()` applies the same filter, and `which_is_frustated()` moved to `drivers/drive/` so both sexes share one state machine - the female's `Drives` had none at all before, exactly the gap this exposed | — resolved |
| 8.8 | Which pattern wins when two both fit | the six flags are computed independently (`sense_light_pattern.ino` sets all six, and several can be true at once), then resolved by an explicit `if`/`else if` chain **inside her drive-state branch**: looking for P she tries `I_P`, `I_OP`, `II_P`, `II_OP` in that order, and `I_O` is never evaluated at all | `_try_match()` returns the **first** pattern within tolerance while walking `readable_light_patterns` in dict order - male1 `O`, `P`, `both`, then male2 - and the drive filter is applied afterwards, in `Search._shared_drive()` | 8.7 is ported in intent but not in sequencing, and 8.5's thin margin is what makes the difference observable. A burst sitting within tolerance of both `male1/O` and `male1/P`, read by a female who wants P, decodes here as `O` and is then discarded as uninteresting - where TJ never tests `O` in that branch, matches `I_P`, and she finds him. **Fails safe** (a missed find, not a wrong approach) but she takes longer to settle than the original would |
| 8.9 | When a body is inert | `updateInternalDriveState()` (internal.ino) reaches the inert state 1 [Neither] only when **both** appetites are below the interested floor: `(internal_drive_LL > internal_drive_O) && (internal_drive_LL > internal_drive_P)` | **Ported** (2026-08-25). `Male.is_satisfied()` / `Female.is_satisfied()` said `o.is_satisfied or p.is_satisfied`, and now delegate to `which_is_frustated()` - an empty tuple *is* the inert state - so the two cannot drift apart again | — resolved, and it mattered: a body with one appetite full and one empty counted as satisfied and would not search, while `which_is_frustated()` one file over said it wanted the full one. A male in that state blinked a pattern asking for something he had decided not to look for; a female in it ignored every male while advertising a want. It also made half the drive settings unusable for a test - O=100/P=0 is a perfectly ordinary search state and nothing would move |

**Measured, `test read pattern`, 2026-08-21**
(`docs/test_results/test read pattern/2026_08_21_17h_09min_23s.csv`) — male1 to
female1, 129 readings over 128.6s (~30 burst cycles), 117 correct. The wrong
ones are four events, not twelve: consecutive rows share 54% of their sample
buffer (2.2s window, logged every 1.005s), so one bad burst shows as two or
three bad rows.

- 3 rows "nothing seen" at the start — her buffer filling. Expected (8.4).
- 5 rows on the `both`→`P` change, lag 4.02s ≈ one 4.35s cycle. Expected
  (1.3 — the male re-reads his drive state only at a burst boundary), and
  it is the **log** that is wrong here, not the decode: the test's
  `expected drive` column flips instantly where the piece cannot.
- 2 genuine misdecodes (~2 corrupted bursts in 30, ~7%): one `both` read as
  `P`, one `P` read as `O`. Both are 8.8 — distance-2 pairs resolved by dict
  order rather than by her appetite.

So the decode rate itself is unremarkable for a light link; what the run
actually surfaces is 8.8, and it took real bursts to show it because the
simulator is too clean to produce an ambiguous one.

---

## 9. The sound channel (designed and wired, not built)

Sound is the half of the interaction this port has never had, and §8.6 is
only the one-line version of it. This section is the detail, for building
it.

It carries less than you would expect. Who a body is, what it wants, and
whether an exchange is working all travel as **light**. Sound carries
exactly two messages: the female's *answer* — the only message a female
ever sends — and the male's *keep going*
while an exchange is running. Everything below is read off
`local/Code/Code/Units/logic35_systems/`: `act_sound.ino` (send),
`sense_sound.ino` (hear), `sense_sound_pattern.ino` (decode),
`Logic_fem.ino` / `Logic_male.ino` (when and why), constants in
`logic35_systems.ino`, per-body values in `UNIT.ino`.

The `an-answer-in-sound` scenario walks the same exchange in plain
language, end to end, with `the-satisfaction-moment` for what closes it.
Both hang off `Colloquy` on the front page, no single thread having a
start() that brings an encounter about.

**Thomas's audio subsystem answers 9.11, and rewrites 9.10.** ZKM has
built the hearing half, and it changes two of the rows above before
anything is written against them: `Source code/Thomas/` is a Mega 2560 of
its own carrying **five** MSGEQ7 analyser modules — one per body, on
A0–A4, sharing strobe and reset on D4/D3 — and **five** hardware-timer
tone outputs: 160 Hz on D11, 400 Hz on D5, 1 kHz on D6, 2.5 kHz on D46,
6.25 kHz on D10.

Each of those five tones lands in a *different* one of the analyser's
seven bands. TJ's five pitches (1760–2637 Hz, 9.10) all sat inside band
4, so which body was speaking had to come out of the decoded pattern;
here it can come out of which band rose. That is a design change and not
a port, and 9.10's pitch table does not survive it. 9.11's "the box has a
bare microphone pair per body, no analyser chip" is answered outright.

`colloquy/tests/test_audio_subsystem` is the bench test for that board.
It drives Thomas's own tester firmware over its serial menu and reports,
for each of the five tones against each of the five modules, whether the
right band rose — `heard`, `wrong band` or `silent`. It claims nothing
about the rows above: it says whether the five boards work, not that any
of the channel is built.

**Where it stands in this installation** *(rewritten 2026-08-26 — the
hardware half of this section is no longer hypothetical)*:

- **Wired, and now driven.** The electronics box always carried, per
  body, a `<body>/audio` line into a SparkFun TPA2005D1 mono amp,
  `<body>/speaker +/out` and `-/out` to the speaker, and
  `<body>/microphone/1|2` back in. Every net of it is now read out of the
  netlist and written down in **`hardware > electronics > as built`**,
  pin by pin, rather than left as "open the sheet and see".
- **In the firmware.** `colloquy_of_mobiles.ino` at **firmware 4** makes
  five tones on five hardware timers — one per body, on Thomas's own
  pins — and reads all five MSGEQ7 modules through one commoned strobe.
  Paths: `<body>/speaker` with `{"on": 0|1}`, `<body>/microphone`,
  `microphones` for all five at once, `speakers/off`.
- **In the tree.** Every body owns a `speaker` and a `microphone`;
  `Drivers._speakers` is no longer an empty list; `drivers/all audio`
  reads every ear in one sweep and silences every voice in one command;
  `power_down()` and `emergency_stop()` both silence. `drivers/audio.py`
  holds the body/pitch/pin/module table once.
- **Still not built:** the message layer. `Female.Reinforcement` still
  raises on its first tick (2.9), nothing sings a pattern and nothing
  listens for one. 9.1 through 9.9 below are untouched.

**The pin conflict, and what it cost.** Four of Thomas's five tone pins
were NeoPixel lines on this board, and D4 — wanted for the analyser
strobe — was a fifth. A tone pin cannot move (a timer toggles its own
`OCnA` output and no other) and a NeoPixel pin can, so the lights moved
to D14–D17 and the tones did not. The cuts and jumpers that make the
board match are **`hardware > electronics > dirty rework`**; what the
next board should do is **`next pcb`**.

Two of the questions below are answered by that arrangement rather than
by anything written since:

- **9.13 is void.** Sound and NeoPixels no longer fight. The compare
  output toggles its pin in hardware, so `NeoPixel.show()` disabling
  interrupts cannot tear a tone, and nothing has to mute an amplifier
  around every pixel write — which is as well, since `set` is strapped
  high on all five amps and there is no mute line to pull.
- **"One tone at a time" (the second of the three things to settle) is
  void too.** It was a limit of AVR `tone()`, which owns one timer and
  one pin. Five timers means five simultaneous voices, which is what a
  piece with three females and two males needs.

**And one it does not answer.** `test_audio_loop`
(`colloquy/tests/test_audio_loop/`) asks the installation's own board
whether each body's voice reaches each body's ear — twenty-five verdicts,
about twenty-two seconds. It is the only test that can catch a body wired
to another body's filter channel, because it is the only one that knows
which body is which. It still says nothing about whether an MSGEQ7 can
hear anything across a gallery full of visitors.

**The message layer is already here.** This is the part worth knowing
before designing anything: in TJ's firmware *a sound message is the same
message as a light message*. Same ten-bit tables, same 50ms tick, four
ticks a bit, 40 samples end to end — `com_pattern_I_O` is the pattern
whether it is sent as flashes or as tone, and `sense_sound_pattern()` is
`sense_light_pattern()` with the word "light" swapped out. So
`Colloquy.light_patterns`, `colloquy/light_pattern_timing.py` and
`ReadPattern`'s decoder already describe the sound channel too; what is
missing is a way to make a sound and a way to hear one.

Two differences in *which* patterns each channel uses, both deliberate:

- Sound never carries "both". A female answers with one appetite named
  (`act_transmit_I_O_sound` / `_I_P_sound` and the male-II pair), never
  the OP pattern, which is why `Search._shared_drive()` already resolves
  to a single drive.
- Sound is the only channel that carries the two **R** patterns
  (`com_pattern_I_R`, `com_pattern_II_R`) — the male's "keep going".
  Those are the two entries `readable_light_patterns` deliberately
  excludes (2.7): they are not light messages at all, they are sound
  messages that happen to share the table.

| # | Function | TJ's firmware | What it needs here |
|---|---|---|---|
| 9.1 | A female answers a male she recognised | `Logic_fem.ino` switches on her own drive state; on a light match she calls `act_transmit_*_sound()`, `FEMALE_begin_reinforcement()` — which stops her body and starts her mirror wiggling — and sets `internal_reinforcing` | The decision is already ported: `Search.loop()` ends her search with `(male, shared drive)` in `partner` (2.8). What is missing starts one line later — `Reinforcement` has to sing that pair back instead of raising |
| 9.2 | What she sings | **His** pattern, not one of her own: the identity she decoded plus the single appetite they share. 40 samples, 200ms a bit, 2s in all | A `Sing` thread on the female mirroring `drivers/male/search/blink/Blink` — same table, same clock, a tone where `Blink` writes a ring |
| 9.3 | The male's listening window | He listens from `timer_search > com_pattern_count - threshold` (33 ticks, 1.65s into his own 2s burst) until the next burst is due at 87 ticks: about 2.7s, covering the whole gap. `sense_sound_active` is false while he transmits anything | The 2.35s gap this port now sends (8.3) is exactly the room her 2s answer has to fit in. Whatever listens has to be running during the gap and not during the burst |
| 9.4 | Who he accepts | Only his own identity, and only naming an appetite he is still short of (`internal_receptive_to_O/P/OP`, `update_receptiveToDrive()`). A reply meant for the other male, or naming what he no longer wants, is ignored | Mirrors `Search._shared_drive()` on the female side; `which_is_frustated()` already provides the receptivity test for both sexes (8.7) |
| 9.5 | What accepting does | `act_body_stop()`, stop blinking, `act_energy_on()` (ring to steady full white), `internal_reinforcing = true`, stop listening, start counting light on the sensors above and below the ring | A male-side `Reinforcement` to match the female's. Note the male has no such node at all today — only the female's placeholder exists |
| 9.6 | The exchange itself is light, not sound | Every 80 ticks (4s) he tests how many of those ticks his sensors saw light above the room level (`sense_light_reinforce_sum > sense_light_reinforce_TRIGGER`, 20 of 80); her wiggling mirror is what returns his own lamp light to him | The mirror is the physical medium and this port has no mirror driver either (`Drivers._mirrors` is empty). Sound alone does not close the loop — it only agrees to start and keeps confirming |
| 9.7 | The male's "keep going" | On enough collected light he sings `act_transmit_I_R_sound()` / `_II_R_sound()` — the R pattern, 2s — and subtracts `sense_light_reinforce_sum * 10` from the shared drive. Not enough light and he ends the exchange on the spot | The R patterns are already in `Colloquy.light_patterns` under the `tuple()` key, kept precisely for this (see its comment). Scale: his 4800-unit appetite is this port's 0-100, so `sum * 10` is at most ~17 points a round |
| 9.8 | The female's side of the loop | Hearing either R pattern, she subtracts a fixed `FEMALE_reinforcement_decrement` (1200, 600, 1200 for females 1-3) and resets her timer. Ten and a quarter seconds (205 ticks) without hearing it and she gives up and goes back to searching | On the 0-100 scale those are 25, 12.5 and 25 points a round. Don't copy the raw numbers - `Drive` here is 0-100 with the interested floor at 12.5 and the desperate floor at 75 |
| 9.9 | Satisfaction | When the shared drive falls below the interested floor it is **zeroed** and a 6s (120-tick) moment begins, during which neither drive climbs. The male plays a 15-note melody (`act_satisfaction_vals`, note lengths per male in `act_satisfaction_Durations_I/II`, both summing to exactly 120 ticks); the female plays the same rhythm as a brightness ramp in the shared appetite's colour | The only sound in the piece that is not a message. Also the only place anything is ever satisfied - 3.3's missing "interaction satisfies the drive" is this |
| 9.10 | Pitch per body | `act_tone_index = 5 - UNIT_ID` over `act_tone_vals[5] = {1760, 1976, 2093, 2349, 2637}`: female1 2637 Hz, female2 2349, female3 2093, male1 1976, male2 1760. One tone, switched on and off - the pattern is in the on/off, not in the pitch | **Done, and not as a port.** Five pitches, one per body, each in a *different* analyser band, so the pitch itself says who is speaking - which TJ's could not, all five of his sitting in band 4. Same *sense* as his in the end - the males low, the females high - though not for his reason. It ran the other way until 2026-08-27; the artist asked for the males on the low voices, and since a pitch belongs to its timer (Thomas's OCR values are indexed by timer, and 6250 Hz is on the 8-bit T2 which cannot reach 160 Hz) the bodies moved across the pins rather than the pitches across the bodies. Every filter channel untouched; five nets changed. `drivers/audio.py` |
| 9.11 | Hearing | A 7-band MSGEQ7 analyser (strobe/reset/signal on pins 2/A5/A4), read 16 times a tick for sensitivity, looking only at band 4 (~2.5kHz, where the tones sit); a sample counts as a tone when that band exceeds a fixed `sense_sound_thresh = 200` | **Done in hardware.** ~~The box has a bare microphone pair per body, no analyser chip~~ - five MSGEQ7s now, one per body, on A0-A4 with strobe and reset commoned; five MAX9814 modules with AGC replace the bare pairs. What survives: the threshold. It is still absolute, still the weakest part of the light side (8.2), and a microphone in a gallery is still worse |
| 9.12 | Half duplex, per body | Transmitting anything - light or sound - sets `sense_sound_active = false`; `act_transmit_sound_end()` sets it back. Nobody listens to their own voice | Cheap to keep, and the reason a male never decodes his own R pattern as an answer |
| 9.13 | Sound and NeoPixels fight | `act_showlights()` is wrapped in `act_blockSound()`/`act_unblockSound()`, muting the amp for the duration of every pixel write, because `NeoPixel.show()` disables interrupts and the tone tears | **Void.** ~~Whatever generates the tone has to survive that, or be muted around it the same way~~ - the tone is made by a timer's compare output toggling its own pin in hardware, so interrupts being off cannot tear it. As well, since `set` is strapped high on all five amplifiers and there is no mute line to pull |
| 9.14 | Rejection | `com_pattern_rejection` and `act_transmit_rejection_sound()` exist, and the one call site is commented out with `//need a timer for this?` | A female never audibly refuses anyone. Unbuilt in the original too - if it is wanted here, it is a new decision, not a port |

**Three things to settle before writing any of it.**

1. **Where the bit clock lives.** The light channel puts it in Python:
   `Blink` writes one ring command per bit over a ~15ms serial round trip,
   which is comfortable at 200ms a bit. Sound cannot work that way on the
   receive side — TJ samples every 50ms and reads his analyser 16 times
   per sample, which is not something a JSON-line request per sample can
   do. Either the sketch grows the pattern layer (Python says "sing male1
   O" and asks "what have you heard?") or the sampling has to be coarse
   enough to survive the serial link. This is the one decision that
   shapes everything else, and it breaks the symmetry with the light
   channel either way.
2. ~~**One tone at a time.**~~ **Settled.** It was a limit of AVR
   `tone()`, which owns one timer and one pin at a time - and two pairs
   reinforcing at once is normal here, with three females and two males.
   The five voices are on five *separate* hardware timers, so all five
   can sound together and none of them costs anything while it does.
   Timer 0 is left to `millis()`.
3. **Hearing in a gallery.** 9.11, and the one of the three still fully
   open. The original solved "is there a tone" in hardware with a
   band-pass and still needed a fixed threshold; the MSGEQ7s inherit
   exactly that, and the room is full of visitors. The MAX9814's AGC is
   the headroom that makes it survivable, and its two straps are Thomas's
   bench results rather than measurements in this room.

When there is something to run, it should look like the two hardware
tests that already exist for the light side: `test_read_pattern` stages one pair and
logs what was decoded per second, `test_female_search` runs one whole
search and says how it ended. A `test_sound_answer` staging one pair, one
sung reply and one decoded answer is the same shape, and the same shape is
what makes it safe to run on the installation.

---

## 10. Angles, servo units and the reductions

Everything that moves is a Dynamixel commanded in position units, and
three of the four kinds of axis are geared: **a female, a male and the bar
all turn three times slower than their servo; only a mirror turns with
its own**. Which axis is geared is the thing that kept being got wrong —
including here: this section was first written with the male direct, and
everything below that says otherwise has been corrected against the rig.

`drivers/angle/` is the layer that ends it. Each moving thing owns an
`Angle` node measured in **degrees of the body itself**, zero at its
calibrated origin, signed — `female1.angle`, `male1.angle`, `bar.angle`,
`female1.mirror1.angle`. `angle/conversion.py` holds the arithmetic and
the reduction table; nothing outside it and `drivers/dxl/` should compute
a servo position.

`params.json` follows: `"dxl origin"` stays a raw servo reading (it is
one), everything else is degrees, and the file is versioned with a
migration that also fills in keys an older file predates — which is 3.5's
landmine closed.

| # | Subject | Before | Now |
|---|---|---|---|
| 10.1 | What a caller says | `origin + motion_range // 2`, per body, three copies | `angle.turn_to(degrees)`; how far each body travels is a `"motion range"` in params, in degrees (58.594 per female, 58.594 per male, 292.969 for the bar, 87.891 for its sweep around female1, 0 for an unmeasured mirror) — all exactly what the old servo figures worked out to, and editable per body from the params page |
| 10.2 | The bar's meeting points | `interaction_origins` in servo units (0, 2200, 4300, 6200, 8400, 10400) | the same points in degrees of the bar (0, 64.453, 125.977, 181.641, 246.094, 304.688), via `Bar.meeting_angle()` |
| 10.3 | Positions below the servo's zero | **Broken.** Every servo is in extended position mode, where that is normal, and the SDK reads a position back as an unsigned dword. `female1` (origin 100, half-sweep 1000) writes -900 to reach her minimum and read it back as 4294966396, so `is_moving` never saw her arrive and `wait_for_servo` raised after 60s | Position and goal-position registers read signed. Verified on the virtual hardware, which now wraps 4-byte reads to unsigned exactly as the SDK does, so the conversion is exercised here and not only on the rig |
| 10.4 | The mirrors | Three servos built by `U2D2` and mapped to nothing (ids 2, 4, 6) | `Mirror` nodes under each female, angle and calibration only — nothing drives them, nothing initialises them (§9.6 is what will) |

**Three things this made visible. The first two turned out to be the same
mistake, and are fixed; the third stands:**

- ~~**A female's sweep is a third of a male's**~~ — it is not. That
  reading came from this layer carrying the male as direct-drive when he
  is geared 1:3 like everyone else: the identical 2000 servo units are
  58.6° for both of them. Params version 3 divides a stored male angle by
  three on load, so a calibrated installation keeps the sway it had.
- ~~**The simulated "facing forward" window** is ±35.2° for a male
  against ±11.7° for a female~~ — the same error, in the same direction.
  400 servo units is ±11.7° for every body. The threshold stays written
  per kind so one of them can still be narrowed alone.
- **"Arrived" means within 20 servo units** (`DXL.moving_threshold`),
  which is 0.59° for any of the bodies but **1.76° for a mirror**. It is
  why a body asked for +20° reports 19.6° when it stops.

---

## Suggested next steps

Ranked by how much of the above unblocks:

1. ~~Fix or replace `Female.Search` (2.1)~~ — **done**: `search.loop()` now
   sways the female and `search.setup()` starts `read_pattern`.
2. Add a `colloquy/tests/` hardware test that drives the full loop in §7.1
   through the real `Male.loop()`/`Female.loop()` triggers rather than
   staged preconditions, to catch regressions in the autonomous path
   itself. Half of this now exists: `test_female_search` runs a whole
   search on the bodies and says how it ended, but it stages the pairing
   and starts the search itself, so the trigger - a female noticing her
   own drive state - is still the untested step. See "How to test these
   reliably" below for a pattern to build it on.
3. Move the "flash seen" test from an absolute threshold to TJ's
   relative one (8.2) — a sample counted as light only when it exceeds a
   running average of recent samples. This is the highest-value remaining
   decode fix and is independent of everything else in this list.
4. Implement `Female.Reinforcement` (2.9) — the placeholder is in place
   and receives the pair, so what remains is the exchange itself:
   subtract from the shared drive while the partner keeps answering,
   zero it below the interested floor, and hold a satisfaction moment
   with both drives frozen. TJ closes this over the sound channel, now
   broken out function by function in §9, together with what is already
   wired for it and the three decisions that have to be made first. The
   male side (receptivity, his own reinforcement, the mirror that
   actually carries the exchange) is untouched so far.
5. Finish adopting TJ's sampling model (8.5). Burst-then-silence and his
   200ms bit are in (8.3/8.4), and the phase ambiguity went with them;
   what is left is the error margin — comparing 40 samples with a
   tolerance of 6, rather than 10 majority-voted bins with a tolerance of
   1. The oversampling is what buys his robustness, and it is why a
   reading one bin wrong still sits halfway to another answer here.
   Related and far cheaper, independent of the sampling work: 8.8, where
   an ambiguous reading is settled by dict order instead of by what she
   is short of. Either resolve to the *best* match rather than the first,
   or filter the candidate set by her drive state before matching as TJ
   does — the second is what the original actually is.
6. Add `"drive start values"` to `params.py`'s `DEFAULTS` (3.5), or
   document that `local/params.json` must be seeded before first run.
7. ~~Decide whether 1.2/1.7/4.1 (search/wander never stopping itself) is
   intended, and if not, add the missing stop condition.~~ — **done** for
   1.2 and 4.1: a male stops calling when he goes inert, and the bar
   follows the males in both directions, so the piece can now come to
   rest instead of running the rail until the process is killed. 1.7 (a
   drive tie in the middle range reading as "both frustrated") is
   untouched and still a gap.
8. Decide the three figures §10 surfaced: how far a female should
   actually sweep against a male (58.6° vs 175.8° today), how wide the
   simulated "facing forward" window should be for a male (±35.2°), and
   whether `DXL.moving_threshold` should be an angle rather than 20 servo
   units, which means something different on a geared body than on a
   direct one. The first two are fields on the params page; the third is
   one number in `DXL`.
9. Measure how far a mirror can turn before it fouls, and put it in its
   `"motion range"` — it is 0 today, which is why the two "turn to one
   end" commands on a mirror both mean its origin.
10. Build a small **dxl debug tool** under `colloquy/tests/`: ping every id
   on the bus, say which answered and which did not, read back each one's
   id, model and baud rate, and let one servo be jogged on its own. Today
   a servo that will not answer is found out by starting the whole
   installation and reading `startup problems` (`colloquy/startup/`),
   which says *that* `female2` is silent but nothing about why — a lead,
   a duplicated id, a servo at the wrong baud rate and a dead servo all
   look identical from there. It is also the tool wanted when the three
   mirrors are finally wired, since ids 2, 4 and 6 have never been talked
   to in anger. Cheap, and it turns the commonest hardware fault in the
   piece from a guess into a reading.
