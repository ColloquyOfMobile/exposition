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
  usually a sub-thread's own interval (e.g. `ReadPattern` needs a whole
  2s burst buffered before it can match anything, and a male only sends
  one every 4.35s, so budget two cycles; `Drive` increments only every
  2.4s). Sleeping less than that will pass for the wrong reason.
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
| 1.1 | Male becomes frustrated, starts searching | `Male.loop()`: search not started and `not is_satisfied()` (neither O nor P drive is "freshly satisfied") — `hardware/male/__init__.py:153-160` | `search.start()`: male sways between min/max position every tick it isn't already moving (`search/__init__.py:25-27`), and `search.setup()` starts `blink`, which sets the ring to white and sends the 10-bit pattern for `drives.which_is_frustated()` at 0.2s/bit — a 2s burst, then the ring dark until the next burst, 4.35s after the last one began (`search/blink/__init__.py`, `colloquy/light_pattern_timing.py`) | none directly (see 1.4/1.5 for partial coverage) | ⚠️ Gap |
| 1.2 | Search never stops itself when the male becomes satisfied again | `Male.loop()` only *starts* search; nothing in `loop()`, `search.loop()`, or `blink.loop()` re-checks `is_satisfied()` — only `Male.setdown()` calls `search.stop()` (`hardware/male/__init__.py:166-168`) | Once started, a male keeps swaying/blinking indefinitely regardless of drive state, until the whole male thread shuts down | none | ⚠️ Gap (likely unintended — worth confirming with the artist/installer whether this is by design) |
| 1.3 | Male's drive state changes mid-blink | `Blink.loop()` calls `male.get_blink_pattern()` once, when a burst starts, and not again until the next one (`search/blink/__init__.py`) | **Fixed.** The pattern still follows the drive state — the change simply takes effect at the next burst, as in TJ's firmware, where `MALE_setSearchLight()` is called at the cycle boundary and nowhere else. It used to be re-read every 0.5s step from a per-state deque carrying its own rotation phase, so a switch mid-cycle emitted a few steps belonging to neither pattern — exactly the sort of reading a female decodes as a third one (2.6). This fires ~2.5 minutes into every search, when both drives pass 75 and the male switches to his `("O","P")` pattern for good | `pytest_tests/male/test_blink.py` | ✅ Fixed |
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
| 2.3 | Female facing a blinking male, reading his pattern correctly | `ReadPattern.loop()` buffers one burst (2s) of sensor samples, tries 10 sub-step offsets × all 10 circular rotations of the **six** `readable_light_patterns`, accepts first match with ≤1 bit mismatch (`hardware/female/search/read_pattern/__init__.py`) | Records `last_match = (male, drive)` — which expires after two burst cycles (8.7s) if nothing refreshes it, a male being able to refresh it only once every 4.35s — and logs (throttled to once per 2s) `"Pattern detected: {male} drive={drive}"` | `test_read_pattern` (`tests/test_read_pattern/__init__.py`) — forces bar position + both bodies' facing + male drive state, starts `blink` + `read_pattern`, logs expected-vs-detected per second | ✅ Covered (staged manually; see 2.4 for the now-live autonomous path) |
| 2.8 | A female's search ends when she finds a partner | `Search.loop()` compares each decoded match against her own `drives.which_is_frustated()` and stops the search on the first male asking for a drive she is short of, leaving `(male, shared drive)` in `search.partner` (`hardware/female/search/__init__.py`) | **New.** Search used to run forever and a match had no consequence anywhere. She now ignores a male asking for something she doesn't want (as TJ's `Logic_fem.ino` does, switching on her own drive state), and when both want both the shared drive differs per male - `male1` gives O, `male2` gives P, TJ's "pick one" tiebreak | `pytest_tests/female/test_search.py`; `test_female_search` (`tests/test_female_search/__init__.py`) - stages one pairing on the bodies (drive states forced, bar and both bodies moved into position), starts the search and reports how it ended | ✅ Covered |
| 2.9 | What happens after she finds one | `Female.loop()` takes the pair from the search and starts `Reinforcement` (`hardware/female/reinforcement/__init__.py`) | The reinforcement thread raises `NotImplementedError` on its first tick, on purpose: this is the half that would draw the shared drive down (8.6). She then goes quiet rather than spinning - `Female.loop()` refuses to restart a thread that has already errored, so the error stays readable instead of being replaced every tick | `pytest_tests/female/test_female_loop.py` | ⚠️ Placeholder (deliberate) |
| 2.4 | `ReadPattern` running as part of normal `Female` behavior | Now wired: `search.setup()` starts `read_pattern.start(started_by=self)` (2.1) | Once a female becomes unsatisfied, she now both sways *and* attempts to decode any male pattern her sensor sees, autonomously — no test yet drives this end-to-end through `Female.loop()`'s own trigger rather than a manually-started `search` | `test_female_search` covers sway → decode → end for a search started by hand | ⚠️ Gap (narrowed: what is still unexercised is `Female.loop()` starting the search itself, off her own drive state, rather than a scenario starting it) |
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
| 4.1 | Any male starts searching → bar auto-wanders | `Bar.loop()`: if not already searching, and *any* male's `search.is_started`, start the bar's own `search` (plain toggle over its full 292.969° travel) — `hardware/bar/__init__.py` | Bar sways full-range regardless of which male/female pair is actually relevant, and — like male search (1.2) — nothing stops it again automatically | none | ⚠️ Gap (and compounds 2.1: since female search crashes almost immediately, in practice the bar may end up wandering with no female able to read anything) |
| 4.2 | Positioning a specific male in front of a specific female | `set_male_in_front_of_female`/`move_male_in_front_of_female_and_wait` using fixed offsets from `params["bar"]["interaction_origins"]` (`hardware/bar/__init__.py:140-151`, `params.py:21-26`) | Bar moves (blocking or non-blocking) to the exact offset for that pair | `test_movements` (jogs every pair), `test_read_pattern`, `test_light_sensor_values` (all use `move_male1_in_front_of_female1_and_wait`) | ✅ Covered |
| 4.3 | Bar's two "linger" sub-behaviors | `turn_back_and_forth` (the full 292.969° travel) vs. `turn_back_and_forth_around_f1` (±43.9° around male1-facing-female1) — `hardware/bar/turn_back_and_forth/__init__.py`, `hardware/bar/turn_back_and_forth_around_f1/__init__.py` | Two different sway scopes; the latter is used by `test_light_sensor_values`'s 3rd stage to simulate "bar drifting near an active pair" without leaving that pair's vicinity | `test_movements` (both, manual); `test_light_sensor_values/test_with_female_male_and_bar_moving` (around-f1 variant, as part of a sequence) | ✅ Covered |
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
   Half of that missing link is a whole channel rather than a line of code:
   in the original the female answers over sound and the exchange runs from
   there — see §9.
2. **Two males simultaneously frustrated for the same female** — bar can
   only be in front of one male at a time; no scenario documents or tests
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
| 8.7 | Who she answers | she filters by her own drive state: looking for O, she accepts only `I_O`, `I_OP`, `II_O`, `II_OP` and ignores a male asking for P (`Logic_fem.ino:110-225`) | **Ported** (2.8): `Search.loop()` applies the same filter, and `which_is_frustated()` moved to `hardware/drive/` so both sexes share one state machine - the female's `Drives` had none at all before, exactly the gap this exposed | — resolved |

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

`timelines/an-answer-in-sound.timeline` walks the same exchange in plain
language, end to end, with `timelines/the-satisfaction-moment.timeline`
for what closes it.

**Where it stands in this installation.** The wiring exists and nothing
above it does:

- **Wired.** The electronics box carries, per body, a `<body>/audio` line
  into a SparkFun TPA2005D1 mono amp, `<body>/speaker +/out` and
  `-/out` to the speaker, and `<body>/microphone/1|2` back in — all five
  bodies, on the Mega 2560 shield (`CAD/KiCad/electronic box/electronic
  box.kicad_sch`; the amp itself is `CAD/Eagle/Mono Audio Amp (TPA2005D1)
  v10/`). The net labels are in the schematic text but the net-to-pin
  mapping is geometry: open the sheet to read which Mega pin each one
  lands on rather than trusting a guess.
- **Not in the firmware.** `Source code/Arduino/colloquy_of_mobiles/
  colloquy_of_mobiles.ino` handles NeoPixel groups and analog light
  sensors and nothing else — no `tone()`, no microphone read, no amp
  enable line.
- **Not in the tree.** `Hardware._speakers` and `Hardware._mirrors` are
  empty lists (`hardware/__init__.py`), nothing constructs a speaker or
  microphone node, and `Female.Reinforcement` raises on its first tick
  (2.9).

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
| 9.2 | What she sings | **His** pattern, not one of her own: the identity she decoded plus the single appetite they share. 40 samples, 200ms a bit, 2s in all | A `Sing` thread on the female mirroring `hardware/male/search/blink/Blink` — same table, same clock, a tone where `Blink` writes a ring |
| 9.3 | The male's listening window | He listens from `timer_search > com_pattern_count - threshold` (33 ticks, 1.65s into his own 2s burst) until the next burst is due at 87 ticks: about 2.7s, covering the whole gap. `sense_sound_active` is false while he transmits anything | The 2.35s gap this port now sends (8.3) is exactly the room her 2s answer has to fit in. Whatever listens has to be running during the gap and not during the burst |
| 9.4 | Who he accepts | Only his own identity, and only naming an appetite he is still short of (`internal_receptive_to_O/P/OP`, `update_receptiveToDrive()`). A reply meant for the other male, or naming what he no longer wants, is ignored | Mirrors `Search._shared_drive()` on the female side; `which_is_frustated()` already provides the receptivity test for both sexes (8.7) |
| 9.5 | What accepting does | `act_body_stop()`, stop blinking, `act_energy_on()` (ring to steady full white), `internal_reinforcing = true`, stop listening, start counting light on the sensors above and below the ring | A male-side `Reinforcement` to match the female's. Note the male has no such node at all today — only the female's placeholder exists |
| 9.6 | The exchange itself is light, not sound | Every 80 ticks (4s) he tests how many of those ticks his sensors saw light above the room level (`sense_light_reinforce_sum > sense_light_reinforce_TRIGGER`, 20 of 80); her wiggling mirror is what returns his own lamp light to him | The mirror is the physical medium and this port has no mirror driver either (`Hardware._mirrors` is empty). Sound alone does not close the loop — it only agrees to start and keeps confirming |
| 9.7 | The male's "keep going" | On enough collected light he sings `act_transmit_I_R_sound()` / `_II_R_sound()` — the R pattern, 2s — and subtracts `sense_light_reinforce_sum * 10` from the shared drive. Not enough light and he ends the exchange on the spot | The R patterns are already in `Colloquy.light_patterns` under the `tuple()` key, kept precisely for this (see its comment). Scale: his 4800-unit appetite is this port's 0-100, so `sum * 10` is at most ~17 points a round |
| 9.8 | The female's side of the loop | Hearing either R pattern, she subtracts a fixed `FEMALE_reinforcement_decrement` (1200, 600, 1200 for females 1-3) and resets her timer. Ten and a quarter seconds (205 ticks) without hearing it and she gives up and goes back to searching | On the 0-100 scale those are 25, 12.5 and 25 points a round. Don't copy the raw numbers - `Drive` here is 0-100 with the interested floor at 12.5 and the desperate floor at 75 |
| 9.9 | Satisfaction | When the shared drive falls below the interested floor it is **zeroed** and a 6s (120-tick) moment begins, during which neither drive climbs. The male plays a 15-note melody (`act_satisfaction_vals`, note lengths per male in `act_satisfaction_Durations_I/II`, both summing to exactly 120 ticks); the female plays the same rhythm as a brightness ramp in the shared appetite's colour | The only sound in the piece that is not a message. Also the only place anything is ever satisfied - 3.3's missing "interaction satisfies the drive" is this |
| 9.10 | Pitch per body | `act_tone_index = 5 - UNIT_ID` over `act_tone_vals[5] = {1760, 1976, 2093, 2349, 2637}`: female1 2637 Hz, female2 2349, female3 2093, male1 1976, male2 1760. One tone, switched on and off - the pattern is in the on/off, not in the pitch | Gives each body an audible identity on top of the decodable one. Worth keeping: it is also how you tell by ear which body is talking while testing |
| 9.11 | Hearing | A 7-band MSGEQ7 analyser (strobe/reset/signal on pins 2/A5/A4), read 16 times a tick for sensitivity, looking only at band 4 (~2.5kHz, where the tones sit); a sample counts as a tone when that band exceeds a fixed `sense_sound_thresh = 200` | The box has a bare microphone pair per body, no analyser chip. Either band-pass in hardware, or do it in the sketch, or choose tones and thresholds a plain envelope can separate. See 8.2: a fixed absolute threshold is already the weakest part of the light side, and a microphone in a gallery is worse |
| 9.12 | Half duplex, per body | Transmitting anything - light or sound - sets `sense_sound_active = false`; `act_transmit_sound_end()` sets it back. Nobody listens to their own voice | Cheap to keep, and the reason a male never decodes his own R pattern as an answer |
| 9.13 | Sound and NeoPixels fight | `act_showlights()` is wrapped in `act_blockSound()`/`act_unblockSound()`, muting the amp for the duration of every pixel write, because `NeoPixel.show()` disables interrupts and the tone tears | This port writes pixels far more often than TJ did (every ring bit is a serial command). Whatever generates the tone has to survive that, or be muted around it the same way |
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
2. **One tone at a time.** TJ had an Arduino per body. This port has one
   Mega for all five, and AVR `tone()` owns a single timer and a single
   pin at a time. Within one pair the sound is already strictly
   alternating (she sings, then he does), but two pairs reinforcing at
   once is normal in this piece — three females and two males. So either
   the tone generation is multiplexed deliberately, or it moves off
   `tone()` onto per-body hardware.
3. **Hearing in a gallery.** 9.11. The original solved the "is there a
   tone" question in hardware with a band-pass and still needed a fixed
   threshold; whatever replaces the MSGEQ7 here inherits the problem, and
   the room is full of visitors.

When there is something to run, it should look like the two scenarios that
already exist for the light side: `test_read_pattern` stages one pair and
logs what was decoded per second, `test_female_search` runs one whole
search and says how it ended. A `test_sound_answer` staging one pair, one
sung reply and one decoded answer is the same shape, and the same shape is
what makes it safe to run on the installation.

---

## 10. Angles, servo units and the reductions

Everything that moves is a Dynamixel commanded in position units, and two
of the four kinds of axis are geared: **a female and the bar turn three
times slower than their servo; a male and a mirror turn with theirs**. The
same 2000 units written to a male and to a female are therefore two
different movements, which is the thing that kept being got wrong.

`hardware/angle/` is the layer that ends it. Each moving thing owns an
`Angle` node measured in **degrees of the body itself**, zero at its
calibrated origin, signed — `female1.angle`, `male1.angle`, `bar.angle`,
`female1.mirror1.angle`. `angle/conversion.py` holds the arithmetic and
the reduction table; nothing outside it and `hardware/dxl/` should compute
a servo position.

`params.json` follows: `"dxl origin"` stays a raw servo reading (it is
one), everything else is degrees, and the file is versioned with a
migration that also fills in keys an older file predates — which is 3.5's
landmine closed.

| # | Subject | Before | Now |
|---|---|---|---|
| 10.1 | What a caller says | `origin + motion_range // 2`, per body, three copies | `angle.turn_to(degrees)`; the sweeps are declared in degrees (`Female._sweep` 58.594, `Male._sweep` 175.781, `Bar._travel` 292.969, around-f1 87.891) — all exactly what the old servo figures worked out to |
| 10.2 | The bar's meeting points | `interaction_origins` in servo units (0, 2200, 4300, 6200, 8400, 10400) | the same points in degrees of the bar (0, 64.453, 125.977, 181.641, 246.094, 304.688), via `Bar.meeting_angle()` |
| 10.3 | Positions below the servo's zero | **Broken.** Every servo is in extended position mode, where that is normal, and the SDK reads a position back as an unsigned dword. `female1` (origin 100, half-sweep 1000) writes -900 to reach her minimum and read it back as 4294966396, so `is_moving` never saw her arrive and `wait_for_servo` raised after 60s | Position and goal-position registers read signed. Verified on the virtual hardware, which now wraps 4-byte reads to unsigned exactly as the SDK does, so the conversion is exercised here and not only on the rig |
| 10.4 | The mirrors | Three servos built by `U2D2` and mapped to nothing (ids 2, 4, 6) | `Mirror` nodes under each female, angle and calibration only — nothing drives them, nothing initialises them (§9.6 is what will) |

**Three things this made visible, none of them fixed:**

- **A female's sweep is a third of a male's** — 58.6° against 175.8°, from
  the identical 2000 servo units. Nobody chose that; it is what the
  numbers have always meant. Changing it is now one figure in
  `Female.__init__`.
- **The simulated "facing forward" window** was one figure of servo units
  for every body, which is ±11.7° for a female or the bar but **±35.2°
  for a male** — a 70° window in which a male counts as facing his origin,
  and so as visible to a female. Migrated exactly as it was, per kind, so
  the difference is at least written down.
- **"Arrived" means within 20 servo units** (`DXL.moving_threshold`),
  which is 0.59° for a female or the bar but **1.76° for a male or a
  mirror**. It is why a body asked for +20° reports 19.6° when it stops.

---

## Suggested next steps

Ranked by how much of the above unblocks:

1. ~~Fix or replace `Female.Search` (2.1)~~ — **done**: `search.loop()` now
   sways the female and `search.setup()` starts `read_pattern`.
2. Add a `colloquy/tests/` scenario that drives the full loop in §7.1
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
6. Add `"drive start values"` to `params.py`'s `DEFAULTS` (3.5), or
   document that `local/params.json` must be seeded before first run.
7. Decide whether 1.2/1.7/4.1 (search/wander never stopping itself) is
   intended, and if not, add the missing stop condition.
8. Decide the three figures §10 surfaced: how far a female should
   actually sweep against a male (58.6° vs 175.8° today), how wide the
   simulated "facing forward" window should be for a male (±35.2°), and
   whether `DXL.moving_threshold` should be an angle rather than 20 servo
   units, which means something different on a geared body than on a
   direct one. All three are one number each now.
