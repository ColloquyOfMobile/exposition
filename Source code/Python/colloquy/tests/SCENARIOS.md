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

## 1. Male — search & blink (identity signal)

A male's ring blinks a 10-bit pattern that encodes his identity
(`male1`/`male2`) and which drive he wants attention for (see
`colloquy.light_patterns`, `colloquy/__init__.py:44-63`, and
`CLAUDE.md`'s "Male blink pattern" section).

| # | Scenario | Trigger | Behavior | Covered by | Status |
|---|---|---|---|---|---|
| 1.1 | Male becomes frustrated, starts searching | `Male.loop()`: search not started and `not is_satisfied()` (neither O nor P drive is "freshly satisfied") — `hardware/male/__init__.py:153-160` | `search.start()`: male sways between min/max position every tick it isn't already moving (`search/__init__.py:25-27`), and `search.setup()` starts `blink`, which sets the ring to white and begins rotating the 10-bit pattern for `drives.which_is_frustated()` on/off at 0.5s/bit (5s per full cycle) — `search/blink/__init__.py:24-36` | none directly (see 1.4/1.5 for partial coverage) | ⚠️ Gap |
| 1.2 | Search never stops itself when the male becomes satisfied again | `Male.loop()` only *starts* search; nothing in `loop()`, `search.loop()`, or `blink.loop()` re-checks `is_satisfied()` — only `Male.setdown()` calls `search.stop()` (`hardware/male/__init__.py:166-168`) | Once started, a male keeps swaying/blinking indefinitely regardless of drive state, until the whole male thread shuts down | none | ⚠️ Gap (likely unintended — worth confirming with the artist/installer whether this is by design) |
| 1.3 | Male's drive state changes mid-blink | `which_is_frustated()` is re-read once per `get_blink_pattern()` call, which only happens when `blink.setup()` runs (i.e. at search start) — `hardware/male/__init__.py:116-118`, `search/blink/__init__.py` | The pattern deque is fixed for the lifetime of one `blink` run; a drive-state change after search has started does **not** change the blink pattern until search restarts | none | ⚠️ Gap |
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
| 2.1 | **Any female becomes unsatisfied in the live installation** | `Female.loop()` calls `search.start()` when unsatisfied (`hardware/female/__init__.py:151-158`), exactly like Male | `Search.setup()` unconditionally `raise NotImplementedError("use the turn_back_and_forth thread")` (`hardware/female/search/__init__.py:28-31`). First failure is caught and logged into `Search.thread_errors`. On the *next* loop tick, `Female.loop()` calls `search.start()` again, but now `Search.thread_errors` is non-empty, so `start()` itself raises — this time uncaught by `Search`, propagating into **Female's own** thread, which catches it, halts, and stops. **The female's entire thread crashes within two loop ticks of becoming unsatisfied.** | none | 🐛 **Broken** — this is the single highest-impact gap in the whole survey: it means the live installation cannot let a female run un-babysat once her drives fall below the satisfaction threshold, unless something is patched to start `turn_back_and_forth` instead of `search` |
| 2.2 | Manual stand-in sway (`turn_back_and_forth`) | Tester starts a female's `turn_back_and_forth` directly | Female sways min/max, no drive/sensor coupling — this is the only working substitute for "female moving while searching" today | `test_movements` (`tests/test_movements/__init__.py:173-179`); used internally by all 4 `test_light_sensor_values` stages (§5) | ✅ Covered (as a stand-in, not the real `search` path) |
| 2.3 | Female facing a blinking male, reading his pattern correctly | `ReadPattern.loop()` buffers ≥5s of sensor samples, tries 10 sub-step offsets × all 10 circular rotations of every `(male, drive)` reference pattern, accepts first match with ≤1 bit mismatch (`hardware/female/search/read_pattern/__init__.py:80-136`) | Records `last_match = (male, drive)`, logs (throttled to once per 2s) `"Pattern detected: {male} drive={drive}"` | `test_read_pattern` (`tests/test_read_pattern/__init__.py`) — forces bar position + male drive state, starts `blink` + `read_pattern`, logs expected-vs-detected per second | ✅ Covered (but only ever reached through this manual test — see 2.4) |
| 2.4 | `ReadPattern` running as part of normal `Female` behavior | Nothing in `Female.loop()`/`Search.setup()` ever calls `read_pattern.start()` — it's only reachable via `test_read_pattern` | The real installation never decodes a male's pattern; the female-facing-male "identity read" mechanism exists but is dormant | none | ⚠️ Gap (by design per `CLAUDE.md` — "not currently wired into the live app" — but worth re-flagging since the crash in 2.1 means the *replacement* path (`turn_back_and_forth`) isn't wired in either) |
| 2.5 | Female not facing any male / male's ring off while sampling | Sensor reads low/"dark" for that sample window (see §6.1 for the simulated version) | Buffered samples for that window read `0`; if the whole 10-step window is all-dark, `_try_match()` still runs but is unlikely to match any reference pattern (all references start `1,1,...`) | `test_read_pattern` incidentally (whenever bar/male aren't aligned) | ⚠️ Gap (no scenario explicitly tests "no match" as the expected outcome) |
| 2.6 | Ambiguous match — mismatch count ties or is right at the `max_mismatches=1` boundary | Candidate pattern differs from more than one reference by ≤1 bit | `_try_match()` returns the **first** match found in iteration order, not the closest — order-dependent, not "best" match | none | ⚠️ Gap |

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
   → bar auto-wanders (4.1) → a female becomes unsatisfied and *should*
   search, read his pattern (2.3/2.4), and have her drive satisfied
   accordingly. As documented above, this chain breaks immediately at the
   female-search crash (2.1) — nothing currently demonstrates the intended
   full loop working, since `test_read_pattern` stages the preconditions
   manually rather than letting `Female.loop()`/`Male.loop()` drive it.
2. **Two males simultaneously frustrated for the same female** — bar can
   only be in front of one male at a time; no scenario documents or tests
   the resulting contention/ordering.
3. **A female mid-`turn_back_and_forth` when a male's drive state (and
   therefore blink pattern) changes** — not tested; per 1.3, the blink
   pattern itself is also frozen for the run, so this is doubly untested.
4. **Recovering an errored thread** — since an errored `BaseThread` can
   never be `start()`-ed again (see the background note above), there is
   no documented/tested recovery scenario for *any* body once it errors
   once (not just the guaranteed female-search error in 2.1). Worth a
   scenario (and likely a code fix) given 2.1 makes this the normal case,
   not an edge case.

---

## Suggested next steps

Ranked by how much of the above unblocks:

1. Fix or replace `Female.Search` (2.1) — either implement it for real, or
   have `Female.loop()` start `turn_back_and_forth` instead of `search`,
   so a running installation doesn't lose every female thread shortly
   after startup.
2. Add `"drive start values"` to `params.py`'s `DEFAULTS` (3.5), or
   document that `local/params.json` must be seeded before first run.
3. Decide whether 1.2/1.7/4.1 (search/wander never stopping itself) is
   intended, and if not, add the missing stop condition.
4. Once 2.1 is fixed, add a scenario test that drives the full loop in §7.1
   through the real `Male.loop()`/`Female.loop()` triggers rather than
   staged preconditions, to catch regressions in the autonomous path
   itself (today only the manually-staged `test_read_pattern` exercises
   `ReadPattern` at all).
