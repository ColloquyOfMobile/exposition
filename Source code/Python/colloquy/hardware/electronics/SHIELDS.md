# Shields: one backplane, every solution plugged into it

**A specification for a main PCB that carries no solution of its own.**
The main board becomes a **backplane**: the harness connectors, the power
entry, the passives every solution shares, and **slots**. Everything that
differs between the solutions is a **shield** in a slot: the **U2D2** (it
already is one), a **computing shield** (the Mega 2560 itself, or a
Teensy 4.1 on an adapter in the Mega's footprint), an **analyser shield**
(five MSGEQ7s, or five anti-alias buffers that hand the microphones
straight to the Teensy), and five **voice cards**, one per body, which
are the output filters. Trying another solution is changing a shield,
and the backplane has no silicon on it to be the thing that is wrong.

Written 2026-10-03. It is the sixth solution, beside `next pcb`, `one
board per body`, `opencm and pro minis`, `ad9833 dual mode` and `thomas
or teensy`, and it is built on two of them: the backplane is the v2
project (`CAD/KiCad/electronic box v2/colloquy-control-v2/`) with its
audio parts moved into shields, and the Teensy halves reuse `thomas or
teensy` section 4's findings wherever they still apply. Read those for
anything this does not repeat.

> **Decided by the brief, 2026-10-03.** One main PCB that only routes
> signals and power; the solutions are shields. The computing shield
> comes as a Mega and as a Teensy 4.1. The analyser comes as MSGEQ7s for
> the Mega and as a direct route of the microphones to the Teensy, whose
> sound is **analysed on the computer**. The output filters are shields
> too, so a frequency can be changed quickly: **fixed** for the Mega and
> the MSGEQ7s, **changeable** for the Teensy, and made by **a timer
> dividing the clock and a filter rounding it**, not by a DAC, since no
> pitch has to change while the piece is running. **SMD** for every
> simple part, because it is assembled by machine and is the reliable
> choice.

**The answer to the question asked, before the detail.** The Teensy
solution works on all three counts, and section 9 is the check:

- **Voices: yes.** Five pins on five independent timer units play any
  pitch from 18 Hz up, in hardware, to within 0.12 Hz of what was asked
  at every pitch this piece uses. A **voice card** per body rounds the
  square into a near-sine; its corner is set by four SMD resistors, so a
  card variant is a resistor value, and a card carries **any pitch in an
  octave** with no swap at all (section 7).
- **Ears: yes.** Five microphones through anti-alias buffers onto five
  pins that both of the Teensy's converters reach, sampled in pairs at
  about 44 kSPS each and sent to the laptop over 480 Mbit/s USB, where
  `test_goertzel_ear`'s Goertzel already does the analysis (section 9b).
  The one piece of new territory is a hardware-triggered continuous
  stream, and the polled capture that every hardware test needs comes
  first and does not depend on it.
- **The rest of the Mega code: yes**, and mostly unchanged. NeoPixels,
  JSON, light sensors and the MSGEQ7 read port as they stand; the voice
  class is rewritten (its AVR register code becomes two library
  calls); and **four behaviours have to be put back on purpose**, each of
  which would otherwise fail silently: the greeting on port open, the
  reset-to-silence on port open, the light-sensor scale, and the MSGEQ7
  reset pulse width (section 9c).

**What is sourced and what is not.** The backplane's Mega pins and every
value that moves into a shield are read out of the v2 project's
`circuit.json`, and `pytest_tests/hardware/test_shields.py` holds this
document's tables to it, to `colloquy_of_mobiles.ino` and to
`colloquy/hardware/electronics/shields.py`, which computes every filter
figure and frequency here. The Teensy facts were read out of PJRC's own
code on 2026-10-03: the timer map out of `cores/teensy4/pwm.c`, the
converters out of `analog.c` and the ADC library's channel tables, the
150 MHz timer clock out of `clockspeed.c`, the I2C pins out of
`WireIMXRT.cpp`, the USB ids out of `usb_desc.h`, the 134-baud reboot out
of `usb.c`, and Adafruit_NeoPixel's Teensy 4 path out of its own
`show()`. The MSGEQ7's 2.7–5.5 V supply range is its datasheet's, and the
SN74LV4T125's single-supply up-translation is TI's product page.
**Everything else about a part is marked *check***, for `next pcb`
section 5's reason: a figure about a part you intend to buy and a fact
about the part in your hand read identically.

---

## 0. The idea in one paragraph

**The backplane is copper, connectors and passives.** It keeps every
connection the v2 board makes to the harness, pin for pin, and the
passives that belong to the harness rather than to a solution: the
NeoPixel series resistors, the photosensor loads, the line-out
build-outs, the ground bonds. Everything that makes or hears a sound, and
the processor, is in a slot. **The slots speak one language whichever
shield is in them**: the voice lines are 5 V squares, the line outs are
line level, the microphones are raw MAX9814 signals, and the computing
slot is the Mega's own footprint, which is the only reason the Mega needs
no adapter. **The one thing the slots do not fix is the processor's logic
voltage**, and the Arduino R3 footprint already has a pin for that:
`IOREF`, driven by the computing shield, powers every part of every other
shield that a processor pin touches. So any shield works with any other,
electrically, and an experiment is **one shield changed and everything
else held still**.

---

## 1. The shields at a glance

**Drawn: what swaps and what stays.** Hatched is fixed — the same in
every solution: the laptop, the backplane's own parts, the U2D2, the
harness and everything in the bodies. A dashed slot takes either of its
two shields, changed with the rack's supply and the computing shield's
USB unplugged; each voice slot is changed on its own. The dotted band is
what changes with no shield moving at all. One body stands for all five.

<div style="overflow-x: auto; margin: 1rem 0;">
<svg viewBox="0 0 1300 890" role="img" aria-label="Block diagram of what swaps and what stays in the shield solution. Fixed, the same in every solution: the laptop with its two USB leads; the backplane with its DSUB-15s, power entry, servo bus header, build-out, NeoPixel and photosensor resistors, pull-downs, ground bonds, I2C bus and slot id straps; the U2D2; the DSUB harness with its four harness boards; and in each of the five bodies the divider, amplifier and speaker, the NeoPixels and photosensors, the MAX9814 microphone and the Dynamixel servo. Swappable, powered down, one of two shields per slot: the computing slot, which is the Mega footprint, takes the Mega 2560 on firmware 4 with IOREF at 5 V or the Teensy 4.1 adapter on firmware 5 with IOREF at 3.3 V; each of the five voice slots takes, on its own, a Thomas card, passive with one fixed pitch, in five variants one per body, or an active card, fourth order with the pitch free within its octave, in thirteen variants with corners from 177 Hz to 11.3 kHz; the analyser slot takes five MSGEQ7s read by the firmware or five anti-alias buffers whose raw samples go to the laptop. Signals: USB from the laptop to the computing slot and to the U2D2; five 5 V tones from the computing slot to the voice slots; five line outs through the harness to the bodies; NeoPixels and photosensors between the computing slot and the bodies; five microphones from the bodies to the analyser slot, whose outputs return to the computing slot on A0 to A4; the Dynamixel bus from the U2D2 to the servos. Set in software, with no shield moving: the pitch within the fitted card's octave on the Teensy, the firmware that follows the computing shield, how a voice goes quiet, and the shields read back from their id EEPROMs.">
<defs>
<marker id="sw-ax" viewBox="0 0 10 8" refX="9" refY="4" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="8" orient="auto"><polygon points="0,0 10,4 0,8" fill="currentColor"></polygon></marker>
<pattern id="sw-hatch" patternUnits="userSpaceOnUse" width="7" height="7" patternTransform="rotate(45)"><line x1="0" y1="0" x2="0" y2="7" stroke="currentColor" stroke-width="1.4" opacity="0.32"></line></pattern>
</defs>
<text x="20" y="27" font-family="'IBM Plex Mono', monospace" font-size="12.5" font-weight="600" letter-spacing="1.4" fill="currentColor" opacity="0.8">WHAT SWAPS AND WHAT STAYS</text>
<!-- frames -->
<rect x="20" y="300" width="120" height="150" rx="4" fill="url(#sw-hatch)" stroke="currentColor" stroke-width="1.6"></rect>
<rect x="170" y="48" width="820" height="642" rx="6" fill="none" stroke="currentColor" stroke-width="1.8"></rect>
<rect x="1035" y="48" width="40" height="642" rx="3" fill="url(#sw-hatch)" stroke="currentColor" stroke-width="1.4"></rect>
<rect x="1095" y="48" width="190" height="642" rx="6" fill="none" stroke="currentColor" stroke-width="1.4"></rect>
<g font-family="'IBM Plex Mono', monospace" font-size="10.5" font-weight="600" fill="currentColor" opacity="0.75">
<text x="186" y="69">BACKPLANE &#183; FIXED</text>
<text x="1108" y="69">BODY &#215; 5 &#183; FIXED</text>
</g>
<text x="974" y="69" font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.65" text-anchor="end">swap a shield only with the rack supply and the computing USB unplugged</text>
<text x="1059" y="262" font-family="'IBM Plex Mono', monospace" font-size="10" font-weight="600" fill="currentColor" opacity="0.8" text-anchor="middle" transform="rotate(-90 1059 262)">DSUB HARNESS</text>
<text x="1059" y="405" font-family="'IBM Plex Mono', monospace" font-size="10" font-weight="600" fill="currentColor" opacity="0.8" text-anchor="middle" transform="rotate(-90 1059 405)">4 HARNESS BOARDS</text>
<text x="1059" y="640" font-family="'IBM Plex Mono', monospace" font-size="10" font-weight="600" fill="currentColor" opacity="0.8" text-anchor="middle" transform="rotate(-90 1059 640)">FIXED</text>
<!-- slots -->
<g fill="none" stroke="currentColor" stroke-width="1.3" stroke-dasharray="7 4" opacity="0.85">
<rect x="195" y="85" width="300" height="230" rx="5"></rect>
<rect x="195" y="360" width="300" height="110" rx="5"></rect>
<rect x="560" y="85" width="405" height="230" rx="5"></rect>
<rect x="560" y="360" width="405" height="200" rx="5"></rect>
</g>
<g font-family="'IBM Plex Mono', monospace" font-size="10" font-weight="600" fill="currentColor" opacity="0.7">
<text x="207" y="105">COMPUTING SLOT &#183; the Mega footprint</text>
<text x="207" y="380">U2D2 SLOT</text>
<text x="572" y="105">VOICE SLOTS JV1&#8211;JV5 &#183; each swapped on its own</text>
<text x="572" y="380">ANALYSER SLOT JA1</text>
</g>
<!-- shields -->
<g fill="none" stroke="currentColor" stroke-width="1.7">
<rect x="213" y="120" width="264" height="68" rx="3"></rect>
<rect x="213" y="228" width="264" height="68" rx="3"></rect>
<rect x="578" y="120" width="369" height="68" rx="3"></rect>
<rect x="578" y="228" width="369" height="68" rx="3"></rect>
<rect x="578" y="392" width="369" height="60" rx="3"></rect>
<rect x="578" y="490" width="369" height="60" rx="3"></rect>
</g>
<rect x="213" y="392" width="264" height="60" rx="3" fill="url(#sw-hatch)" stroke="currentColor" stroke-width="1.7"></rect>
<g font-family="Chivo, sans-serif" font-size="13.5" font-weight="600" fill="currentColor" text-anchor="middle">
<text x="345" y="148">Mega 2560</text>
<text x="345" y="256">Teensy 4.1 adapter</text>
<text x="345" y="418">U2D2</text>
<text x="762" y="144">Thomas card</text>
<text x="762" y="252">Active card</text>
<text x="762" y="417">5 &#215; MSGEQ7</text>
<text x="762" y="515">5 &#215; anti-alias buffer</text>
</g>
<g font-family="'IBM Plex Mono', monospace" font-size="10" fill="currentColor" text-anchor="middle" opacity="0.72">
<text x="345" y="169">firmware 4, unmodified &#183; IOREF 5 V</text>
<text x="345" y="277">firmware 5 &#183; IOREF 3.3 V</text>
<text x="345" y="438">the same in every setup</text>
<text x="762" y="162">passive, Thomas&#8217;s values &#183; one fixed pitch</text>
<text x="762" y="178">5 variants, one per body</text>
<text x="762" y="270">4th order &#183; pitch free within its octave</text>
<text x="762" y="286">13 variants: corners 177 Hz &#8211; 11.3 kHz</text>
<text x="762" y="437">seven bands per body, read by the firmware</text>
<text x="762" y="535">raw samples to the laptop &#183; Goertzel</text>
</g>
<g font-family="'IBM Plex Mono', monospace" font-size="11" font-weight="700" fill="currentColor" text-anchor="middle" opacity="0.9">
<text x="345" y="213">&#8645; either one</text>
<text x="762" y="213">&#8645; either one, in each slot</text>
<text x="762" y="476">&#8645; either one</text>
</g>
<!-- fixed on the backplane -->
<rect x="195" y="500" width="300" height="170" rx="5" fill="url(#sw-hatch)" stroke="currentColor" stroke-width="1.6"></rect>
<text x="207" y="522" font-family="'IBM Plex Mono', monospace" font-size="10" font-weight="600" fill="currentColor" opacity="0.8">FIXED ON THE BACKPLANE</text>
<g font-family="'IBM Plex Mono', monospace" font-size="10" fill="currentColor" opacity="0.85">
<text x="207" y="546">4 &#215; DSUB-15 &#183; power entry &#183; servo bus J7</text>
<text x="207" y="566">100 R build-outs &#183; 330 R NeoPixel resistors</text>
<text x="207" y="586">10 K photosensor loads &#183; pull-downs</text>
<text x="207" y="606">ground bonds &#183; I2C &#183; slot id straps</text>
<text x="207" y="632">IOREF, set by the computing shield:</text>
<text x="207" y="648">why every combination is safe</text>
</g>
<!-- body -->
<g fill="url(#sw-hatch)" stroke="currentColor" stroke-width="1.6">
<rect x="1110" y="160" width="160" height="60" rx="3"></rect>
<rect x="1110" y="315" width="160" height="40" rx="3"></rect>
<rect x="1110" y="455" width="160" height="40" rx="3"></rect>
<rect x="1110" y="570" width="160" height="40" rx="3"></rect>
</g>
<g font-family="Chivo, sans-serif" font-size="11.5" fill="currentColor" text-anchor="middle">
<text x="1190" y="186">divider &#183; amplifier</text>
<text x="1190" y="204">speaker</text>
<text x="1190" y="339">NeoPixels &#183; photosensors</text>
<text x="1190" y="479">MAX9814 microphone</text>
<text x="1190" y="594">Dynamixel servo</text>
</g>
<text x="80" y="347" font-family="Chivo, sans-serif" font-size="15" font-weight="600" fill="currentColor" text-anchor="middle">Laptop</text>
<g font-family="'IBM Plex Mono', monospace" font-size="10" fill="currentColor" text-anchor="middle" opacity="0.72">
<text x="80" y="367">Python program</text>
<text x="80" y="410">2 USB leads</text>
<text x="80" y="425">in every setup</text>
</g>
<!-- wires -->
<g fill="none" stroke="currentColor">
<path d="M 140 330 H 160 V 205 H 193" stroke-width="1.4" marker-end="url(#sw-ax)"></path>
<path d="M 140 422 H 211" stroke-width="1.4" marker-end="url(#sw-ax)"></path>
<path d="M 495 170 H 558" stroke-width="1.4" marker-end="url(#sw-ax)"></path>
<path d="M 965 190 H 1108" stroke-width="2.4" marker-end="url(#sw-ax)"></path>
<path d="M 495 290 H 512 V 335 H 1108" stroke-width="1.4" marker-end="url(#sw-ax)"></path>
<path d="M 1108 475 H 967" stroke-width="2.4" marker-end="url(#sw-ax)"></path>
<path d="M 558 520 H 545 V 270 H 497" stroke-width="2.4" marker-end="url(#sw-ax)"></path>
<path d="M 477 422 H 530 V 590 H 1108" stroke-width="1.4" marker-end="url(#sw-ax)"></path>
</g>
<g font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.85">
<text x="164" y="198">USB</text>
<text x="165" y="415">USB</text>
<text x="499" y="162">tone &#215; 5</text>
<text x="499" y="183">5 V</text>
<text x="972" y="182">line out</text>
<text x="640" y="329">NeoPixels &#183; photosensors</text>
<text x="974" y="467">mic &#215; 5</text>
<text x="500" y="263">A0&#8211;A4</text>
<text x="640" y="584">Dynamixel bus &#183; J7</text>
</g>
<!-- software -->
<rect x="20" y="715" width="1265" height="118" rx="6" fill="none" stroke="currentColor" stroke-width="1.6" stroke-dasharray="1.5 4" stroke-linecap="round"></rect>
<text x="36" y="738" font-family="'IBM Plex Mono', monospace" font-size="10.5" font-weight="600" fill="currentColor" opacity="0.75">SET IN SOFTWARE &#183; NO SHIELD MOVES</text>
<g font-family="Chivo, sans-serif" font-size="12.5" font-weight="600" fill="currentColor">
<text x="36" y="766">Pitch, within the fitted card&#8217;s octave</text>
<text x="352" y="766">Firmware follows the computing shield</text>
<text x="668" y="766">How a voice goes quiet</text>
<text x="984" y="766">What is fitted, read back</text>
</g>
<g font-family="'IBM Plex Mono', monospace" font-size="10" fill="currentColor" opacity="0.72">
<text x="36" y="788">Teensy only; a Mega plays its timers&#8217; five</text>
<text x="36" y="804">a new octave is another active card</text>
<text x="352" y="788">4 on the Mega, 5 on the Teensy</text>
<text x="352" y="804">flashed from the page</text>
<text x="668" y="788">idle low, as today, or a 1 MHz carrier</text>
<text x="668" y="804">that leaves no thump (Teensy)</text>
<text x="984" y="788">each shield&#8217;s id EEPROM, in the greeting</text>
<text x="984" y="804">a pitch its card can&#8217;t carry is refused</text>
</g>
<!-- legend -->
<g font-family="'IBM Plex Mono', monospace" font-size="10.5" fill="currentColor" opacity="0.8">
<rect x="20" y="856" width="30" height="16" rx="2" fill="url(#sw-hatch)" stroke="currentColor" stroke-width="1.6"></rect>
<text x="58" y="868">fixed: the same in every solution</text>
<rect x="330" y="856" width="30" height="16" rx="2" fill="none" stroke="currentColor" stroke-width="1.3" stroke-dasharray="7 4"></rect>
<text x="368" y="868">a slot: swap its shield, powered down</text>
<rect x="670" y="856" width="30" height="16" rx="2" fill="none" stroke="currentColor" stroke-width="1.7"></rect>
<text x="708" y="868">a shield; &#8645; one of the two is fitted</text>
<rect x="1010" y="856" width="30" height="16" rx="2" fill="none" stroke="currentColor" stroke-width="1.6" stroke-dasharray="1.5 4" stroke-linecap="round"></rect>
<text x="1048" y="868">set in software</text>
</g>
</svg>
</div>

| Slot | Shield for the Mega | Shield for the Teensy | What crosses the slot |
|---|---|---|---|
| computing | **the Mega 2560 itself**, firmware 4 | **Teensy 4.1 adapter**, firmware 5 | everything a processor touches; drives `IOREF` |
| analyser | **5 × MSGEQ7**, Thomas's network | **5 × anti-alias buffer**, raw signal | five microphones in, five outputs to `A0`–`A4` |
| voice × 5 | **Thomas card**: passive, his values, one pitch | **active card**: 4th order, one octave of pitch | a 5 V square in, line level out |
| U2D2 | the U2D2 | the U2D2 | nothing new: its mount and `J7`, as on v2 |

**Any shield works with any other.** The table pairs them the way the
brief does, and that pairing is the target, but no combination can
damage anything and every one of them works, because
each processor-facing part is powered from `IOREF` (section 3d). That is
what makes the backplane an instrument rather than two boards on one
outline:

| Computing | Analyser | Cards | What it is | What it answers |
|---|---|---|---|---|
| Mega | MSGEQ7 | Thomas | **the v2 board**, electrically | the baseline; every existing hardware test |
| Teensy | MSGEQ7 | Thomas | the same chain on another processor | does firmware 5 reproduce firmware 4? |
| Teensy | direct | Thomas | ears on the laptop, voices unchanged | Goertzel against the MSGEQ7, on one pitch set |
| Teensy | direct | active | **the Teensy solution** | the brief's target, at Thomas's pitches first |
| Mega | MSGEQ7 | active | cleaner voices, nothing else changed | what the filter alone buys the room |
| Mega | direct | any | the Mega sampling raw microphones, on a sampling sketch | a diagnosis setup, `microphone_sampler`'s shape |

---

## 2. What does not change: the harness interface

**Every connection to the outside world is the v2 board's**: the same
outline, the four DSUB-15s, `J2`, `J6`, `J7` and the three spare-conductor
headers in the same places with the same nets on the same pins. Those
tables are already restated in `thomas or teensy` section 2 and held to
`circuit.json` by `test_thomas_or_teensy.py`, so they are not copied a
third time here. **None of the four harness boards changes**, and the
body end is `next pcb` section 3's assembly whichever shields are fitted.

---

## 3. The backplane

### 3a. What it keeps from v2

| Kept | v2 references | Why it is the backplane's and not a shield's |
|---|---|---|
| four DSUB-15s, `J2`, `J6`, `J7`, `Extra1`–`Extra3` | as v2 | the harness and the power entry |
| the U2D2 mount | `M1` | the U2D2 slot |
| the Mega footprint, on the back | `A1` | the computing slot (3e) |
| NeoPixel series resistors, 330 R | `RN1`–`RN7` | they protect the cable, whoever drives it |
| photosensor loads, 10 K provisional | `RP1`–`RP11` | they belong to the sensor: a sensor sees the same load whichever processor reads it |
| line-out build-outs, 100 R | `R103`, `R203`, `R303`, `R403`, `R503` | they protect the cable, whichever card feeds it |
| amp shutdown pull-up, 10 K to `MEGA_5V` | `RS1` | the reserved line, as v2 |
| one analogue-to-power ground bond, one per body audio return | `JP1`–`JP6` | grounding is the board's |
| 470 µF bulk, test pads, mounting holes | as v2 | |

### 3b. What leaves v2 for a shield

| Leaves | v2 references | Goes to |
|---|---|---|
| the five passive filters | `R101`/`R102`/`C101`/`C102` … `R501`/`R502`/`C501`/`C502` | five **Thomas cards** (7b) |
| the five MSGEQ7s and their networks | `U1`–`U5`, `R*11`, `R*13`, `R*16`, `C*12`, `C*14`, `C*16`, `JS1`–`JS5` | the **MSGEQ7 analyser shield** (6a) |

### 3c. What it adds

| Added | Value | Package | Why |
|---|---|---|---|
| analyser slot `JA1` | 2 × 12, 2.54 mm, male, pin 24 removed as key | THT | 3f |
| voice slots `JV1`–`JV5` | 2 × 7, 2.54 mm, male, pin 14 removed as key | THT | 3g |
| one M3 standoff per card and two for the analyser shield | | | retention, and a second key: a reversed shield's holes do not line up |
| `IOREF` net | from the footprint's `IORF` pin to both kinds of slot | copper | 3d |
| shield I2C bus, pull-ups | 4K7 × 2 to `IOREF` | 0603 | the shield ids (section 8) |
| slot address straps | to GND or `IOREF`, per slot | copper | which card is in which slot (3g) |
| NeoPixel pull-downs | 100 K to GND on each of the seven `…/neopixel/driven` nets | 0603 | **a strip never sees a floating data line**: not while a processor boots, not while one is unpowered, not with the slot empty |
| line pull-downs | 100 K to AGND on each `…/filter out` net | 0603 | an empty voice slot leaves its body's line at 0 V, not floating into an amplifier |
| `IOREF` bulk | 10 µF X7R to GND | 0805 | |

**The NeoPixel pull-downs are the one change to a net the v2 board
already has**, and they are worth having on any board: with the Mega
unpowered and the rack on, v2's data lines float and a strip may latch
whatever it hears, white included. 100 K costs the Mega nothing.

### 3d. Rails, and who powers what

| Rail | Comes from | Feeds |
|---|---|---|
| `+5V` | `J2`, as v2 | NeoPixels and body supplies, as v2; **the voice cards' op-amps** |
| `+12V` | as v2 | the servo bus and the bodies, as v2 |
| `MEGA_5V` | the footprint's 5 V pins: **the computing shield's own USB 5 V** | `RS1`, a test pad; nothing else |
| `IOREF` | the footprint's `IORF` pin: **the computing shield's logic rail**, 5 V on a Mega, 3.3 V on the Teensy adapter | the processor-facing side of every shield: MSGEQ7s or anti-alias buffers, every id EEPROM, the I2C pull-ups |
| `GND`, `AGND` | as v2, one bond (`JP1`) | as v2 |

**Two rules, and the second is what makes any combination safe.**

1. **Everything a computing shield drives onto the backplane is powered
   by that shield's own USB.** A Mega obeys this by construction — its
   pins are its own — and the Teensy adapter is built to (5b). So "laptop
   off, rack on" and "rack off, laptop on" both leave every line either
   driven or pulled down, never half-powering a processor through its
   pins.
2. **Every part that drives a processor pin runs from `IOREF`.** An
   MSGEQ7 on `IOREF` cannot put more than `IOREF` on `A0`, so the same
   analyser shield is right for a 5 V Mega and a 3.3 V Teensy without a
   jumper and without anybody remembering one. This is what Arduino added
   the pin for: on the R3 header, `IOREF` tells a shield the voltage the
   board's processor runs at, and on a Mega 2560 R3 it is the board's
   5 V (*check* against the board in hand).

### 3e. The computing slot: the Mega's footprint, unchanged

**Every pin the v2 board connects keeps the net v2 gives it**, so the Mega
plugs in as it is and firmware 4 runs unmodified. Read out of
`circuit.json`; the test holds this table to it.

| Mega pin | Net | |
|---|---|---|
| `D2` | `amp shutdown` | reserved, `RS1` |
| `D3` | `analyser/reset` | to `JA1` |
| `D4` | `analyser/strobe` | to `JA1` |
| `D5` | `male2/tone` | to `JV5` |
| `D6` | `female1/tone` | to `JV1` |
| `D7` | `female2/neopixel/driven` | `RN2` |
| `D8` | `female3/neopixel/driven` | `RN3` |
| `D9` | `male1/neopixel/driven` | `RN4` |
| `D10` | `female3/tone` | to `JV3` |
| `D11` | `male1/tone` | to `JV4` |
| `D14` | `female1/neopixel/driven` | `RN1` |
| `D15` | `male2/neopixel/driven` | `RN5` |
| `D16` | `male1/bar neopixel/driven` | `RN6` |
| `D17` | `male2/bar neopixel/driven` | `RN7` |
| `D24` | `male1/aux driven` | |
| `D25` | `male2/aux driven` | |
| `D46` | `female2/tone` | to `JV2` |
| `A0` | `female1/analyser out` | from `JA1` |
| `A1` | `female2/analyser out` | from `JA1` |
| `A2` | `female3/analyser out` | from `JA1` |
| `A3` | `male1/analyser out` | from `JA1` |
| `A4` | `male2/analyser out` | from `JA1` |
| `A5` | `female1/photosensor` | `RP1` |
| `A6` | `female2/photosensor` | `RP2` |
| `A7` | `female3/photosensor` | `RP3` |
| `A8` | `male1/photosensor/A` | `RP4` |
| `A9` | `male1/photosensor/B` | `RP5` |
| `A10` | `male1/photosensor/C` | `RP6` |
| `A11` | `male1/photosensor/D` | `RP7` |
| `A12` | `male2/photosensor/A` | `RP8` |
| `A13` | `male2/photosensor/B` | `RP9` |
| `A14` | `male2/photosensor/C` | `RP10` |
| `A15` | `male2/photosensor/D` | `RP11` |

**Three footprint pins are added**, all unconnected on v2 and untouched by
firmware 4 (no `#define`, no `Wire`); the test checks both:

| Added pin | Net | Why |
|---|---|---|
| `IORF` | `IOREF` | the computing shield's logic rail, out to every other slot |
| `SDA` | `shield/sda` | the R3 header's I2C pair: `D20` on a Mega, Wire2 on the adapter |
| `SCL` | `shield/scl` | `D21` on a Mega |

### 3f. The analyser slot `JA1`

Each microphone sits between two `AGND` pins, so no digital line runs
beside one in the connector.

| JA1 pin | Net |
|---|---|
| 1 | `female1/microphone` |
| 2 | `AGND` |
| 3 | `female2/microphone` |
| 4 | `AGND` |
| 5 | `female3/microphone` |
| 6 | `AGND` |
| 7 | `male1/microphone` |
| 8 | `AGND` |
| 9 | `male2/microphone` |
| 10 | `AGND` |
| 11 | `female1/analyser out` |
| 12 | `female2/analyser out` |
| 13 | `female3/analyser out` |
| 14 | `male1/analyser out` |
| 15 | `male2/analyser out` |
| 16 | `AGND` |
| 17 | `analyser/strobe` |
| 18 | `analyser/reset` |
| 19 | `shield/sda` |
| 20 | `shield/scl` |
| 21 | `IOREF` |
| 22 | `GND` |
| 23 | `+5V` |
| 24 | key, no pin |

### 3g. The voice slots `JV1`–`JV5`

One pinout for all five; the slot decides which body, through which tone
net arrives on pin 1 and which address the straps on pins 11–13 give the
card's id EEPROM.

| JV pin | Signal |
|---|---|
| 1 | the slot's `<body>/tone`: a 5 V square from the computing slot |
| 2 | `GND` |
| 3 | the slot's `<body>/filter out`: line level, to the build-out |
| 4 | `AGND` |
| 5 | `+5V` |
| 6 | `AGND` |
| 7 | `IOREF` |
| 8 | `GND` |
| 9 | `shield/sda` |
| 10 | `shield/scl` |
| 11 | address strap `A0` |
| 12 | address strap `A1` |
| 13 | address strap `A2` |
| 14 | key, no pin |

| Voice slot | Body | Pin 1 | Pin 3 | Straps A2 A1 A0 | Card id at |
|---|---|---|---|---|---|
| `JV1` | female1 | `female1/tone` | `female1/filter out` | GND GND GND | `0x50` |
| `JV2` | female2 | `female2/tone` | `female2/filter out` | GND GND IOREF | `0x51` |
| `JV3` | female3 | `female3/tone` | `female3/filter out` | GND IOREF GND | `0x52` |
| `JV4` | male1 | `male1/tone` | `male1/filter out` | GND IOREF IOREF | `0x53` |
| `JV5` | male2 | `male2/tone` | `male2/filter out` | IOREF GND GND | `0x54` |

**Slot N is body N**, in body order, which is module order, which is
`A0`–`A4`: the same number identifies a body out of the processor,
through its card, into the room and back through the analyser, as on
every board so far. The build-out after pin 3 is v2's own (`R103` … `R503`,
`<body>/filter out` to `<body>/line out`), so with Thomas cards fitted
the copper from tone pin to DSUB is v2's, with two connector contacts in
it.

---

## 4. The U2D2 shield

**It already is one**, and nothing about it changes: the padless mount
`M1`, its own USB lead to the laptop, and its real connection the servo
bus header `J7` (GND, +12 V, `dxl_data`), which the DSUBs carry onward as
on v2. `drivers/u2d2/` does not change with any other shield.

---

## 5. The computing shields

### 5a. The Mega 2560

**The Mega is its own shield**: it plugs into the backplane's footprint
exactly as it plugs into the v2 board, carried on the back, on its own
USB lead. `IOREF` is its 5 V. Firmware 4 runs unmodified with the MSGEQ7
shield and Thomas cards, which is the acceptance test of the whole
backplane (section 13). Firmware 5 (9c) adds what a Mega can usefully
learn here, chiefly reading the shield ids on `D20`/`D21`.

### 5b. The Teensy 4.1 adapter

**A board in the Mega's footprint with a Teensy on it.** It carries female
headers where a Mega has them, so it mates the backplane's Mega mating
headers in place of a Mega and mounts on the same four holes. The Teensy
sits in two 1×24 female headers on the far side from the backplane, its
USB connector at the end where a Mega has its USB-B, so the lead leaves
the enclosure where the Mega's did. **Still two USB leads in the rack**:
the computing shield's and the U2D2's.

**Power: its own USB, and nothing else, as a Mega.** PJRC: power must not
be applied to `VIN` while a USB cable is used unless the pads underneath
are cut, so the adapter takes 5 V **from** `VIN` and never puts anything
onto it (`thomas or teensy` 4a's reading). From `VIN` it powers its
translators and, through a Schottky, the footprint's 5 V pins
(`MEGA_5V`), which is what a Mega's own USB does. Its 3.3 V is `IOREF`.
**Its pins are not 5 V tolerant** (PJRC), which decides the rest of the
adapter.

**What crosses from the Teensy to the backplane, and how:**

- **Every output that leaves the backplane is translated to 5 V**:
  the seven NeoPixel lines, the five tones, the two aux lines and amp
  shutdown — fifteen lines through four SN74LV4T125s powered from `VIN`.
  So a body's NeoPixel sees 5 V logic and a voice card sees a 5 V square,
  exactly as from a Mega, and a card's level does not depend on which
  processor is fitted.
- **What stays inside the backplane at `IOREF` level goes direct**: the
  analyser's strobe and reset (an MSGEQ7 on `IOREF` must not be strobed
  at 5 V) and the I2C pair.
- **Every analogue input arrives already inside 0–3.3 V or is divided**:
  the analyser shield's outputs are bounded by `IOREF` (3d), and the
  photosensors, which are 3-pin modules on the body's 5 V and can reach
  it, each pass a 100 K / 150 K divider.

Read out of PJRC's core as described above; the test checks every row
against `shields.py`'s copy of it.

| Teensy pin | Mega pin | Net | How |
|---|---|---|---|
| 2 | `D6` | `female1/tone` | translator; FlexPWM4.2 |
| 4 | `D46` | `female2/tone` | translator; FlexPWM2.0 |
| 5 | `D10` | `female3/tone` | translator; FlexPWM2.1 |
| 6 | `D11` | `male1/tone` | translator; FlexPWM2.2 |
| 28 | `D5` | `male2/tone` | translator; FlexPWM3.1 |
| 7 | `D14` | `female1/neopixel/driven` | translator |
| 8 | `D7` | `female2/neopixel/driven` | translator |
| 9 | `D8` | `female3/neopixel/driven` | translator |
| 10 | `D9` | `male1/neopixel/driven` | translator |
| 11 | `D15` | `male2/neopixel/driven` | translator |
| 12 | `D17` | `male2/bar neopixel/driven` | translator; the strip firmware 4 calls male1's up ring |
| 29 | `D16` | `male1/bar neopixel/driven` | translator; the strip firmware 4 calls male2's up ring |
| 30 | `D24` | `male1/aux driven` | translator |
| 31 | `D25` | `male2/aux driven` | translator |
| 32 | `D2` | `amp shutdown` | translator |
| 34 | `D4` | `analyser/strobe` | direct, 100 R |
| 35 | `D3` | `analyser/reset` | direct, 100 R |
| 24 | `SCL` | `shield/scl` | direct; Wire2 `SCL2` |
| 25 | `SDA` | `shield/sda` | direct; Wire2 `SDA2` |
| 14 | `A0` | `female1/analyser out` | direct; A0 |
| 15 | `A1` | `female2/analyser out` | direct; A1 |
| 16 | `A2` | `female3/analyser out` | direct; A2 |
| 17 | `A3` | `male1/analyser out` | direct; A3 |
| 18 | `A4` | `male2/analyser out` | direct; A4 |
| 19 | `A5` | `female1/photosensor` | divider; A5 |
| 20 | `A6` | `female2/photosensor` | divider; A6 |
| 21 | `A7` | `female3/photosensor` | divider; A7 |
| 22 | `A8` | `male1/photosensor/A` | divider; A8 |
| 23 | `A9` | `male1/photosensor/B` | divider; A9 |
| 26 | `A10` | `male1/photosensor/C` | divider; A12 |
| 27 | `A11` | `male1/photosensor/D` | divider; A13 |
| 38 | `A12` | `male2/photosensor/A` | divider; A14 |
| 39 | `A13` | `male2/photosensor/B` | divider; A15 |
| 40 | `A14` | `male2/photosensor/C` | divider; A16 |
| 41 | `A15` | `male2/photosensor/D` | divider; A17 |

**Why these pins, in the order the constraints bite:**

1. **Five voices on five timer units.** `analogWriteFrequency()` sets a
   whole FlexPWM submodule or QuadTimer channel, so two pins on one unit
   always play one pitch. 2, 4, 5, 6 and 28 are on five different units.
   Their partners (3, 33, 9, 29) are free or used as plain GPIO, which a
   timer does not touch.
2. **The microphones on pins both converters reach, in body order.** Only
   14–23 reach both ADCs; 14–18 are `A0`–`A4`, the same numbers and order
   as on the Mega, so module N is body N on both processors (`thomas or
   teensy` 4a, unchanged).
3. **The I2C pair on Wire2**, pins 24 and 25: the only hardware port not
   on a pin the microphones or the first photosensors want.
4. **The photosensors take the remaining eleven analogue pins.** They are
   slow, so a pin that reaches one converter is enough; the first five
   keep their Mega `A`-numbers.
5. **Everything else on digital-only pins**, avoiding 13 (the LED the
   bootloader blinks — `next pcb` section 1's reason for `D13`).

**Spare**: 0 and 1 (Serial1), 3, 33, 36, 37, each to a test pad. That is
every pin the 4.1 brings to its edge accounted for; there is no room on
this adapter for `thomas or teensy`'s separate bench microphone pin,
which is why the direct analyser shield carries its bench input on
channel 0 instead (6b).

| Part | Value | Package | Note |
|---|---|---|---|
| Teensy 4.1 | | module | in two 1×24 female headers |
| Mega-pattern headers | female: five 1×8, one 1×10, one 2×18 | THT | where a Mega has them; the ICSP 2×3 is not needed |
| translators ×4 | SN74LV4T125 | TSSOP-14 | `VCC` from Teensy `VIN`; all `OE` low; 16 channels, 15 used, one input to GND |
| translator input pull-downs ×15 | 100 K | 0603 | a line is low while the Teensy boots, resets or is absent |
| translator bypass ×4 | 100 nF | 0603 | |
| photosensor dividers ×11 | 100 K series, 150 K to GND, 10 nF C0G at the pin | 0603 | 5.25 V becomes 3.15 V; 0.6 ms |
| analyser control series ×2 | 100 R | 0603 | strobe, reset |
| `VIN` to `MEGA_5V` | Schottky, ≥ 0.5 A | SOD-123 | so nothing ever reaches `VIN` |
| `VIN` bulk | 10 µF X7R | 0805 | |
| `IOREF` | the Teensy's 3.3 V, 10 µF X7R and 100 nF | 0805, 0603 | |
| spare-pin and rail test pads | | pad | 0, 1, 3, 33, 36, 37, `VIN`, 3.3 V |

**The translators' unpowered side is a *check*.** TI sells the
SN74LV4T125 as a single-supply up-translator with 5.5 V-tolerant inputs;
whether its outputs are high-impedance with its own `VCC` at 0 V is the
datasheet's `Ioff` figure, to be read before ordering. It matters one
way only: `VCC` and the Teensy go off together (both from the Teensy's
USB), and the backplane's pull-downs hold every line it drives.

**The photosensor dividers, worked.** A 3-pin photosensor module runs
from the body's 5 V and its output can reach it. 150 / (100 + 150) = 0.6,
so 5.25 V, the top of a USB-class 5 V rail, reaches the pin as 3.15 V.
With the Teensy unpowered and a sensor at 5 V, at most (5 − 0.3) / 100 K
= 47 µA flows into the pin's clamp (*check* against NXP's injection
rating; `thomas or teensy` accepted 70 µA on the same reasoning). The
divider adds 250 K across the 10 K load, so the sensor's operating point
moves by 4 %, and 10 nF at the pin is a reservoir the converter's own
few-picofarad sample capacitor cannot disturb, with a 0.6 ms time
constant against a 200 ms bit.

---

## 6. The analyser shields

Both run every processor-facing part from `IOREF` and carry an id EEPROM
at `0x55` (section 8). Both have the five microphones between `AGND` pins
on the way in.

### 6a. The MSGEQ7 shield: Thomas's analyser, on a card

**Electrically v2's analyser array**, in SMD, with one change: the supply
pin and the oscillator's resistor go to `IOREF` where v2 has `MEGA_5V`.
On a Mega those are the same 5 V, so with a Mega fitted nothing changes
at all. Values are v2's, read out of `circuit.json`; the test holds this
table to it.

| MSGEQ7 part | Value | Package | v2 (female1's) | Note |
|---|---|---|---|---|
| microphone series | 47K | 0603, 1 % | `R311` | with the shunt, 0.126 |
| microphone shunt | 6K8 | 0603, 1 % | `R316` | to AGND |
| input coupling | 100nF | 0603 X7R | `C312` | |
| oscillator resistor | 200K 1% | 0603, 1 % | `R313` | to `IOREF` |
| oscillator capacitor | 33pF C0G | 0603 | `C314` | includes stray: keep both against pin 8 |
| reference bypass | 100nF | 0603 | `C316` | pin 6 is a reference, **never grounded** |
| attenuator bypass | ATTEN BYPASS (OPEN) | solder jumper | `JS3` | bridged only after measuring |
| supply bypass | 100 nF, `IOREF` to AGND | 0603 | | against pins 1 and 2 |
| analyser | `MSGEQ7N` | SOIC-8 | `U3` | in the datasheet's ordering table beside the DIP |
| test pads | analyser out ×5, strobe, reset | pad | | as v2 |

**With a Teensy fitted it runs at 3.3 V**, which the MSGEQ7's datasheet
allows (2.7–5.5 V, best at 5 V). The Teensy reads it against its own
3.3 V and the MSGEQ7's outputs scale with its supply, so band counts
should be comparable with the Mega's; whether the oscillator, and so the
band centres, hold at 3.3 V is a measurement, not a claim. It is the
comparison configuration, not the target.

**SOIC rather than v2's socket** is `thomas or teensy` section 3's
argument, and it is weaker here: a bad chip now costs a shield, not the
main board. Buy six from an authorised distributor.

### 6b. The direct shield: the microphones to the Teensy

**Per microphone, `thomas or teensy` 4c's buffer**, with two additions
learned since:

| Part | Value | Package | Note |
|---|---|---|---|
| input bias | 1 M to AGND | 0603 | **an unplugged microphone reads a flat 0 V**, not a ghost of its neighbour |
| input resistors | 10 K, 10 K | 0603, 1 % | Sallen–Key, unity gain; also the fault limit |
| feedback capacitor | 2.2 nF C0G | 0603 | |
| ground capacitor | 1 nF C0G to AGND | 0603 | about 10.7 kHz, Q 0.74 |
| op-amp | rail-to-rail in and out, on `IOREF` | MCP6004 class, SOIC-14, *check* | two quads: five sections used, three tied off as followers to AGND |
| output isolation | 100 R, then 1 nF C0G to AGND | 0603 | the converter's kick lands on 1 nF |
| bench input | JST EH 3: GND, `+5V`, signal | THT | `female base`'s microphone pin order, so a body's MAX9814 plugs in |
| channel 0 source | 1×3 header and shunt: `HARNESS` — channel 0 — `BENCH` | THT | default `HARNESS` |
| supply bypass | 100 nF + 10 µF at each quad | 0603, 0805 | |
| test pads | each output, `IOREF` | pad | |

**Why the 1 M matters.** An unconnected ADC pin does not read silence; it
reads about 95 % of the channel converted before it (`microphone_sampler`,
measured), and the scope once reported a disconnected microphone as
"both are hearing the room". Here the op-amp drives the pin, so the pin
is never open, but the op-amp's own input would be. 1 M to AGND gives a
missing microphone a value no working one has, and makes the bias a
three-way reading: **0 V** nothing plugged in, **about 1.25 V** a live
MAX9814, **about 0.78 V** the dead module of `diagnosing a microphone`
(its bias 475 mV low). DC-coupled throughout, so the Teensy reads it
without a scope.

**Range**: the MAX9814 swings about 2 Vpp around 1.25 V (*check*), so
0.25–2.25 V reaches a pin whose converter spans 0–3.3 V. With a Mega
fitted the same shield runs at 5 V and the Mega can sample it, which is
`microphone_sampler`'s arrangement with five microphones.

---

## 7. The voice cards

### 7a. One card per body, and why not one shield for five

**A pitch set is five independent choices**, and a five-channel shield
would make it one: changing female2's octave would mean another board
with four channels unchanged. With a card per slot, the stock is a few
cards per octave, and a new pitch for one body is one card swapped.
**One PCB design per kind**, and a variant is a BOM: the active card
differs from octave to octave in four resistors and nothing else. Each
card is about 30 × 40 mm, SMD on one side, a 2×7 female header beneath,
one M3 screw.

Every card has the same five test pads — tone in, the filter's input
node, stage 1, line out, AGND — with line out and AGND **2.54 mm apart**,
so a clip lead or a two-pin header takes a powered speaker and a card
can be proved on the bench before any body is connected.

### 7b. The Thomas card: passive, fixed, his values

**Thomas's channel, moved off the main board.** Two RC sections,
`R1 = R2` and `C1 = C2`, from the tone pin to the line, exactly as v2
draws them; the test holds this table to `circuit.json`. One variant per
body.

| Thomas card | Body | Plays (Mega) | `R1 = R2` | `C1 = C2` | v2 |
|---|---|---|---|---|---|
| 1 kHz | female1 | 1012 Hz | 1K2 | 150nF | `R301`/`R302`, `C301`/`C302` |
| 2.5 kHz | female2 | 2531 Hz | 1K8 | 47nF | `R401`/`R402`, `C401`/`C402` |
| 6.25 kHz | female3 | 6329 Hz | 2K2 | 10nF | `R501`/`R502`, `C501`/`C502` |
| 160 Hz | male1 | 162 Hz | 2K2 | 470nF | `R101`/`R102`, `C101`/`C102` |
| 400 Hz | male2 | 405 Hz | 2K | 220nF | `R201`/`R202`, `C201`/`C202` |

Plus a **100 K from tone to GND** on the card, so an undriven slot idles
at 0 V as v2's line does, and the id EEPROM. Capacitors **C0G or PPS
film, never X7R**: each corner sits at its own tone and these carry DC,
`thomas or teensy` section 3's argument in full. The 150, 220 and 470 nF
parts are large in C0G (1210–1812, *check* stock); PPS film at the same
value is the fallback, with its own footprint.

**What the Thomas channel actually does to a square**, computed from
these values at the pitch each plays: its corner sits about **a third** of
the way to the tone, so the fundamental loses 8–12 dB and the third
harmonic lands **21 to 23 dB** below it — Thomas's own measurement said
"more than 20 dB". That is the baseline the active card has to beat.

### 7c. The active card: any pitch in an octave

**The signal path**, one quad op-amp on `+5V`:

1. **Input divider and reference** (section A): 15 K from the tone to a
   node, 10 K from the node to a 2.5 V reference, 470 pF from the node
   to AGND, followed by a buffer. The 5 V square becomes **2.0 Vpp around
   2.5 V**, and its fundamental is (4/π) × 2.0 = **2.55 Vpp**: `next pcb`
   section 3's line level, for which the body's 22K/3K3 divider was
   sized.
2. **Stage 1** (section B): unity-gain Sallen–Key, two equal resistors
   `Ra`, 12 nF in feedback, 10 nF to AGND — **Q 0.548**.
3. **Stage 2** (section C): the same with `Rb`, 22 nF and 3.3 nF —
   **Q 1.291**. Together a fourth-order Butterworth (0.541 and 1.307
   wanted; E12 C0G values move it by nothing that matters).
4. **Reference** (section D): 10 K / 10 K across `+5V`, 10 µF, a
   follower.
5. **Output**: 1 µF X7R and 100 K to AGND, so the line is centred on
   0 V and feeds the 25 K body divider with a 6 Hz corner.

**With equal resistors in each stage, the capacitors set the shape and
the resistors set the corner.** So the four capacitors never change and
the four resistors (two values) *are* the card variant: changing a card's
octave is a BOM line, and on a card in hand it is four 0603 resistors.

**Where a pitch may sit on a card**, as a fraction of its corner, computed
by `shields.py` for the cards as built (E96 resistors, E12 capacitors):

| Window | Pitch / corner | Fundamental loses | 3rd harmonic | 5th harmonic | Used for |
|---|---|---|---|---|---|
| sweet | 0.60 – 0.85 | at most 1.1 dB | at least 29.7 dB down | at least 51.9 dB down | **choosing** a card |
| allowed | 0.50 – 1.00 | at most 3.1 dB | at least 23.6 dB down | at least 45.6 dB down | what firmware plays on a fitted card |

**The allowed window is the whole of "change the frequency without
changing the card"**: one octave, in firmware, and even at its edges the
card is no worse than Thomas's channel is at its own pitch. Beyond it,
the next card. The cards' corners are **half an octave apart**, which is
what makes the sweet windows join up (0.6 × √2 = 0.849): every pitch from
106 Hz to 9.6 kHz has a card that carries it with at most 1.1 dB lost.

| Card | Corner | Sweet window | Allowed window | `Ra` (×2) | `Rb` (×2) |
|---|---|---|---|---|---|
| 177 | 177 Hz | 106–150 Hz | 88–177 Hz | 82K5 | 105K |
| 250 | 250 Hz | 150–212 Hz | 125–250 Hz | 57K6 | 75K |
| 354 | 354 Hz | 212–301 Hz | 177–354 Hz | 41K2 | 52K3 |
| 500 | 500 Hz | 300–425 Hz | 250–500 Hz | 29K4 | 37K4 |
| 707 | 707 Hz | 424–601 Hz | 354–707 Hz | 20K5 | 26K7 |
| 1000 | 1000 Hz | 600–850 Hz | 500–1000 Hz | 14K7 | 18K7 |
| 1414 | 1414 Hz | 849–1202 Hz | 707–1414 Hz | 10K2 | 13K3 |
| 2000 | 2000 Hz | 1200–1700 Hz | 1000–2000 Hz | 7K32 | 9K31 |
| 2828 | 2828 Hz | 1697–2404 Hz | 1414–2828 Hz | 5K11 | 6K65 |
| 4000 | 4000 Hz | 2400–3400 Hz | 2000–4000 Hz | 3K65 | 4K64 |
| 5657 | 5657 Hz | 3394–4808 Hz | 2828–5657 Hz | 2K55 | 3K32 |
| 8000 | 8000 Hz | 4800–6800 Hz | 4000–8000 Hz | 1K82 | 2K32 |
| 11314 | 11314 Hz | 6788–9617 Hz | 5657–11314 Hz | 1K27 | 1K65 |

**Against Thomas's channel, at the pitches the Mega plays.** Same 5 V
square in, so this is the filter alone:

| Pitch | Body | Thomas: fundamental | Thomas: 3rd | Thomas: line | Card | Card: fundamental | Card: 3rd | Card: line |
|---|---|---|---|---|---|---|---|---|
| 1012 | female1 | -10.8 dB | -22.3 dB | 1.85 Vpp | 1414 | -0.2 dB | -35.9 dB | 2.49 Vpp |
| 2531 | female2 | -12.3 dB | -23.1 dB | 1.55 Vpp | 4000 | -0.1 dB | -31.6 dB | 2.51 Vpp |
| 6329 | female3 | -8.4 dB | -21.0 dB | 2.42 Vpp | 8000 | -0.6 dB | -38.8 dB | 2.37 Vpp |
| 162 | male1 | -10.0 dB | -21.9 dB | 2.02 Vpp | 250 | -0.0 dB | -32.5 dB | 2.53 Vpp |
| 405 | male2 | -10.5 dB | -22.2 dB | 1.89 Vpp | 500 | -0.8 dB | -39.8 dB | 2.32 Vpp |

**Two things the active card buys besides freedom**: a voice **8.5 to 18 dB
cleaner** at the same pitch, and five voices **within 0.21 V of each
other in level** where Thomas's channels spread from 1.55 to 2.42 Vpp, because
a passive filter's loss depends on how far its corner happens to sit
below the tone. (Thomas's line levels are unloaded and for a 5.0 V
square; the body divider's 25 K barely loads them.)

**Parts, per active card:**

| Part | Value | Package | Note |
|---|---|---|---|
| op-amp | quad, rail-to-rail in and out, about 10 MHz, 5 V: MCP6024 class | SOIC-14, *check* | A buffer, B stage 1, C stage 2, D reference |
| input divider | 15 K from tone, 10 K to reference | 0603, 1 % | 2.0 Vpp |
| input RC | 470 pF C0G, node to AGND | 0603 | 56 kHz with the divider's 6 K; strips the idle carrier (7e) before any op-amp |
| stage 1 | `Ra` ×2; 12 nF feedback, 10 nF to AGND | 0603 1 %; C0G 5 % | |
| stage 2 | `Rb` ×2; 22 nF feedback, 3.3 nF to AGND | 0603 1 %; C0G 5 % | |
| reference | 10 K / 10 K, 10 µF X7R | 0603, 0805 | |
| output | 1 µF X7R series, 100 K to AGND | 0805, 0603 | |
| supply bypass | 100 nF + 10 µF, `+5V` to AGND | 0603, 0805 | |
| id EEPROM | section 8 | SOIC-8 or TSSOP-8 | |

**Every capacitor is a small C0G part**: 3.3 to 22 nF, 0603 or 0805. That
is deliberate and is the other reason the card is active: Thomas's
passive values need 150–470 nF in C0G, which is a large part or a film
one, where an op-amp lets the impedances rise and the capacitors shrink.
The tolerances move the corner by up to 5 % and the Q by a few per cent,
which the windows above absorb.

**The level is a resistor, deliberately.** The divider gives Thomas's
2.5 Vpp, which is what the body divider was sized for. A hotter card is a
BOM variant of the divider — up to about 4.5 Vpp before the op-amp's
rails — and the first remedy if `next pcb` section 3's harness
measurement comes back weak. It is also the one way a card could
overdrive a body, which is why the default is Thomas's level.

### 7d. Why not a DAC, and why not a filter that follows a clock

**Not a DAC**, because the brief says no pitch changes while the piece
runs, and then a DAC buys a waveform nobody asked for at the price of a
clock tree, three converters and a 3.3 V analogue domain (`thomas or
teensy` 4b is that design, kept as the record). A timer and a filter
also stay in TJ's family: his voices were squares.

**Not a switched-capacitor filter** (MAX7400 or LTC1069 class, a corner
set by a clock at a hundred times it), though it is the obvious next
step: a card whose corner *follows* the pitch would make the octave limit
disappear, and if the tone were divided down from the filter's own clock
by a counter on the card the two could never disagree. It is left out of
the first set for three reasons: the voice line would have to carry the
clock rather than the tone, which is a second meaning for one slot pin;
it adds clock feedthrough at a few tens of kilohertz to a line headed for
a class-D amplifier; and those parts' availability is unchecked. **The
slot allows it later**: a card says what it is in its id (section 8), so
a tracking card is a third kind, not a new backplane.

### 7e. Silence, and the thump

Today a voice idles at 0 V and jumps to a 2.5 V average when its timer
starts, and the amplifier's input capacitor hears the step as a thump —
at every bit edge of a sung pattern (`thomas or teensy` section 1). A Mega
on firmware 4 does exactly this with either card, and that is right for
the first comparisons.

**A Teensy can idle without the step.** Instead of holding the pin low it
can hold it at **a 1 MHz square at exactly 50 %**, whose average is the
tone's own: the card's 470 pF input RC takes 25 dB off it before the
op-amp and the filter takes the rest, so the line sits still, and when
the tone starts the average does not move. 1 MHz rather than lower to
stay clear of class-D switching frequencies. **It is a firmware setting,
`idle`, defaulting to `low`** — Thomas's behaviour, so the first
Teensy run changes one thing — and `carrier` once the room has heard
both. On a Thomas card the same carrier leaves the line at 2.5 V between
tones, which is equally free of steps. A scope on an idle voice line then
shows 1 MHz, which the silkscreen says (section 12).

---

## 8. Shield identity: an id EEPROM on every shield

**Every card and the analyser shield carry a 2 kbit I2C EEPROM** saying
what they are. It exists for this repository's oldest failure: **a board
that answers cheerfully and is wrong**. A Teensy asked for 1000 Hz on a
card cut for 400 Hz sings into a filter that takes 24 dB off it, reports
the voice sounding, and the symptom is a body that is never heard. With
an id, the firmware refuses the pitch and says which card is in the way.
It is the same idea as the Raspberry Pi HAT's id EEPROM, for the same
reason.

| | |
|---|---|
| part | AT24C02D or M24C02 class, **one whose address pins are honoured** — not a 24LC02B, which ignores them (*check* the part chosen) |
| package | SOIC-8 or TSSOP-8 |
| supply | `IOREF`, so the bus is at the processor's level with no translator |
| address | `0x50` + the slot's straps (3g); the analyser shield straps itself to `0x55` |
| write protect | `WP` pulled to `IOREF` by 10 K on the card; a solder jumper to GND allows writing, once, at assembly |
| contents | one line of JSON, at most 256 bytes |

```
{"kind":"voice active","corner":1414,"sweet":[849,1202],"allowed":[707,1414],"rev":1,"serial":"VA-1414-007"}
{"kind":"voice thomas","body":"female1","hz":1012,"rev":1,"serial":"VT-1000-002"}
{"kind":"analyser msgeq7","rev":1,"serial":"AM-001"}
{"kind":"analyser direct","corner":10700,"rev":1,"serial":"AD-001"}
```

**Who reads it.** Firmware 5, on either processor, reads all six at boot
and on a `shields` command, and names them in its greeting. The Teensy
refuses a `hz` outside the fitted card's allowed window, and plays a card
that does not answer only at the compiled-in pitch, named `unknown`.
Firmware 4 never looks, and the backplane works without a single EEPROM
fitted. The Python side shows them under `drivers/arduino` beside `board
says`.

---

## 9. The Teensy solution, checked

### 9a. The voices: timers, not software

**Each voice is a timer toggling a pin in hardware**, which is the Mega's
own arrangement and keeps its two virtues (`colloquy_of_mobiles.ino`'s
`Voice` comment): a sounding tone costs no processor time, and nothing
that disables interrupts — Adafruit_NeoPixel's `show()` does, for 2.0 ms
per female strip — can tear it. Five voices sound at once on five units.

**What the timers can do.** Every FlexPWM submodule and QuadTimer channel
counts the 150 MHz bus clock, with a sixteen-bit divider and a prescaler
up to 128. So the lowest pitch is 150 MHz / 128 / 65535 = **17.9 Hz**, the
step at 10 kHz is under 0.7 Hz, and what the core actually produces when
asked — `shields.teensy_pwm_frequency`, the same arithmetic as
`flexpwmFrequency()` — is:

| Asked | Teensy plays | The Mega plays |
|---|---|---|
| 162 | 162.00 Hz | 162 Hz, Thomas's trimmed OCR |
| 405 | 405.00 Hz | 405 Hz |
| 1012 | 1012.01 Hz | 1012 Hz |
| 2531 | 2531.00 Hz | 2531 Hz |
| 6329 | 6329.11 Hz | 6329 Hz |
| 160 | 160.00 Hz | not available: OCR steps |
| 1000 | 1000.00 Hz | not available |
| 6250 | 6250.00 Hz | not available |

**So the first Teensy run can play the Mega's pitches exactly**, not
Thomas's round names, which is what "change one thing at a time" needs:
same pitch to a hundredth of a hertz, different processor.

**Code.** `analogWriteResolution(8)`, then `analogWriteFrequency(pin, hz)`
and `analogWrite(pin, 128)` to sing, `analogWrite(pin, 0)` (or the 1 MHz
carrier, 7e) to stop. A duty of exactly half is what keeps the even
harmonics out; the cards are designed against odd ones only.

### 9b. The ears: two converters, sampled in pairs

**The front end** is the direct analyser shield (6b): an anti-alias
buffer per microphone, about 10.7 kHz, bounded by `IOREF`. **The
converters**: pins 14–18 all reach both of the Teensy's ADCs, so a frame
is three paired conversions — female1 with female2, female3 with male1,
male2 with a spare — each pair sampled at the same instant and the pairs
a couple of microseconds apart. Five channels at **about 44 kSPS each**
is the design point (`thomas or teensy` 8's number), 22.7 µs a frame, of
which the conversions take a few (*check* the conversion time at 12 bits
without averaging; it is the first thing to measure). That is well past
twice the highest pitch any card carries.

**Two capture modes, and the order matters.**

1. **Polled capture, first.** A `microphones/capture` command takes a
   block — 1024 frames, 23 ms — paced off the Cortex-M7's cycle counter,
   and answers with one line in `microphone_sampler`'s `block` format
   extended with `ch=5` and the measured `fs=`, frames interleaved. Text,
   so the Serial Monitor remains a second opinion: about 25 kB a block,
   a few milliseconds on 480 Mbit/s USB. **Nothing else runs during a
   capture** — commands wait, exactly as they wait for the Mega's 8 ms
   MSGEQ7 sweep today — so no `show()` can interrupt one. It is all
   ordinary code, and every hardware test that hears (`test audio loop`,
   `test audio bringup`, `test reinforcement`'s band columns, `scope`,
   `test goertzel ear`) needs only this.
2. **A continuous stream, for the piece itself.** Hearing while the piece
   runs must not stall the light link: a female bins her photosensor
   against a wall clock every 50 ms, and a 23 ms capture in the middle of
   that moves a sample. So the running piece wants the samples on **a
   second USB serial interface** (Teensy's *Dual Serial* type, product
   id `0x048B`), binary, with a frame counter so the laptop can see any
   loss, sampled by **hardware**: a timer triggering both converters
   through the ADC_ETC block, results moved by DMA. Then neither the
   command loop nor `show()` masking interrupts can move a sample.
   5 × 44.1 kSPS × 2 bytes is 441 kB/s, a small fraction of the link. **This
   is the one piece of new territory in the port** — register-level, and
   nobody here has written it — so it is proved on the bench before the
   piece depends on it, and the fallback is a top-priority timer
   interrupt with a NeoPixel driver that does not mask interrupts
   (OctoWS2811's Teensy 4 support, *check*).

**The analysis is already written.** `test_goertzel_ear`'s `goertzel.py`
bins any block at any pitch, its `HEARD_RATIO` and `QUIET_FLOOR` are
measurements of a real room, and `leakage()` says which two pitches are
too close to tell apart on a given block. Five bodies' bins on five
channels is a 5 × 5 heard matrix — the thirty-five MSGEQ7 numbers'
replacement, with each bin exactly on its body's pitch. **Choosing
pitches gains one rule from the cards**: keep each pitch off another's
third harmonic, which the cards hold 29.7 dB down but not at zero.

### 9c. Porting the Mega sketch, part by part

**One sketch, two boards.** `colloquy_of_mobiles.ino` stays the single
source of truth — `firmware.py` reads its version and baud rate out of
it and the simulator reads its paths out of it — and gains a board layer:
`#if defined(__IMXRT1062__)` around the pin `#define`s, the `Voice`
internals and the hearing. Firmware **5** for both boards, since a
driver judging a Teensy by a Mega's greeting would get the hearing
wrong.

| Sketch part | On the Teensy |
|---|---|
| `Adafruit_NeoPixel`, `PixelGroup`, `PixelGroupBeam`, `PixelGroupForFemaleBody` | **unchanged.** `show()` has a Teensy 4 path (cycle-counted, `__IMXRT1062__`, port set/clear registers); it masks interrupts for a strip's length, 2.0 ms for 50 GRBW pixels, which is harmless to timer voices and to a polled capture |
| `ArduinoJson`, `processCommand()` and its if-chain | **unchanged**; plain C++ |
| `FIRMWARE_VERSION` | 5 |
| `SERIAL_BAUDRATE` | **kept at 1000000.** USB serial ignores it, but `firmware.py` reads it and the greeting carries it, and keeping the number keeps `baudrate_problems()` quiet for the right reason |
| `COMMAND_BUFFER_SIZE`, the receive loop | **unchanged** |
| pin `#define`s | a second set, section 5b |
| `LightSensor::read()` | `analogRead()` at 12 bits, **scaled to the counts a Mega would report** (×3.3 / 4095 / 0.6 × 1023 / 5), so every threshold in `params.json` keeps its meaning |
| `Voice` | **rewritten**: two library calls (9a) replace the register code; gains an optional `hz` in `<body>/speaker`, refused outside the card's window; the reply is unchanged |
| `Analyser` | **unchanged but one line**: the reset pulse needs a deliberate `delayMicroseconds(1)`. The comment's "100 ns min, 28 us measured" was measured on a Mega, where `digitalWrite` itself is that slow; on a Teensy two writes back to back are tens of nanoseconds, under the MSGEQ7's minimum |
| `Female`, `Male` | **unchanged**: they only hold pixel groups and sensors |
| object initialisation | **unchanged** but for pin names: `LightSensor(59)` and its siblings name the Mega's raw pin numbers |
| `strips[]`, `females[]`, `males[]` | arrays of **copies**, as on the Mega: `begin()` runs on a copy that shares the original's pixel buffer. Harmless on both boards; worth knowing before anything stateful relies on them |
| `greeting()` | gains `"board"` (`"mega2560"` or `"teensy41"`) and `"shields"` (section 8) |
| `setup()` | same order — pixels off, voices silent, then the link — plus reading the ids |
| `loop()` | gains the **port-open behaviour**, below |
| new paths | `microphones/capture` (9b), `shields`; `microphones` answers only with the MSGEQ7 shield fitted, and says why otherwise |

**The port-open behaviour is the part that would fail silently**, and it
is two things the Mega does by accident of its hardware:

- **It greets when the port opens.** Opening a Mega's port toggles DTR,
  the 16U2 resets the processor, and the sketch greets from `setup()`;
  `Arduino.wait_for_reboot()` waits for exactly that line. A Teensy's USB
  is the processor's own, so opening the port resets nothing and the
  greeting would have gone out once, at power-on, to nobody. **The sketch
  greets on every rising edge of `Serial.dtr()`**, which pyserial raises
  when it opens a port (*check* that its default holds on Windows); the
  driver's handshake then works unchanged.
- **It resets to silence when the port opens.** A Mega's reboot also
  turns every pixel off and silences every voice, so a crashed program
  never leaves a body singing past the next open. **The sketch returns to
  its boot state on each DTR edge, rising and falling**: a program that
  lets go of the port leaves the room quiet, and one that opens it finds
  the board as a reboot would have left it.

**And one thing the driver must never do.** A host that sets the line to
**134 baud** reboots a Teensy into its bootloader (`usb.c`). The driver's
`_diagnose_silence()` reopens the port at every rate in
`firmware.PROBE_BAUDRATES`; none is 134, and the test now pins that,
since a probe there would turn "the board is quiet" into "the board is in
its bootloader".

### 9d. What the Python side needs

None of it is needed to build the boards; all of it is needed to use the
Teensy.

- **`boards.KNOWN_DEVICES` gains PJRC's ids**: `0x16C0:0x0483` (USB
  Serial) and `0x16C0:0x048B` (Dual Serial), both as plausible Arduinos,
  so the port picker names a Teensy and the flasher's refusals accept
  one. The bootloader is HID and has no COM port.
- **The flasher's board type becomes the computing shield's**:
  `teensy:avr:teensy41`, with `usb=serial2` once the stream exists,
  through PJRC's board package (`package_teensy_index.json`) in the same
  IDE-bundled arduino-cli. Its upload tool is PJRC's; *check* that the
  port comes back under the same name for the closing reopen, which is
  still the check — the board greeting in its own words.
- **`firmware.py`** reads `board` and `shields` out of the greeting, and
  `drivers/arduino` shows both.
- **`drivers/audio.py`'s pitch column becomes a setting** on the Teensy,
  checked against the fitted cards' windows; its `timer` and `pin`
  columns become the board's (they are for showing, never used).
- **`drivers/hearing/` stops being emulated** where the direct shield is
  fitted, through `goertzel.py`.
- **The simulator** learns the new paths from the same if-chain, as now.

### 9e. Verdict

**It ports.** Of the sketch's parts, the NeoPixels, the JSON link, the
command loop and the MSGEQ7 read move unchanged; the voice is rewritten
in a few lines; four behaviours are put back on purpose. The polled ears
are ordinary code. **The risk is concentrated in one place**, the
hardware-triggered stream, and nothing before step 6 of section 13
depends on it. Rough effort, as `sound options` estimated: one to two
weeks for both halves, of which the stream is the uncertain part.

---

## 10. SMD, and what stays through-hole

**Every resistor, capacitor, IC and diode on every board is SMD and
placed by the assembler.** 0603 for signal parts, 0805 for 10 µF and the
build-outs, SOIC or TSSOP for every IC. What stays through-hole is a
short list, and every item on it is a connector, a socket for a module,
or a fixed footprint:

| Through-hole | Where | Why |
|---|---|---|
| four DSUB-15s, `J2`, `J6`, `J7` | backplane | fixed footprints and positions |
| Mega mating headers | backplane, back | v2's: five 1×8, one 1×10, one 2×18 |
| `JA1`, `JV1`–`JV5` | backplane | a slot is plugged and unplugged; a through-hole header takes that, a surface one peels |
| Mega-pattern female headers | Teensy adapter | mate the backplane |
| Teensy sockets | Teensy adapter | two 1×24 |
| slot sockets | every shield and card | the other half of the slot |
| bench microphone, channel-0 header | direct analyser shield | so a body's module plugs in |

**Gold-plated contacts on both halves of every slot**, since a slot
carries line level and microphone signals and will be mated more than a
production connector usually is. Most assemblers fit through-hole parts
at extra cost; all of these are large pads and easy by hand otherwise.

---

## 11. Placement

- **The backplane keeps v2's outline, fixed connectors, Mega position and
  AGND region.** SMD and the move of the filters and analysers into
  shields free most of the area v2's through-hole audio parts took.
- **The voice slots near the DSUBs' line-out pins**, so the line runs
  from card to build-out to DSUB in a few centimetres; **the analyser
  slot near the microphone pins**. Both in v2's AGND region, with `JP1`
  still the only bond.
- **Card height** above the backplane decides the enclosure's front
  clearance: a mated 2×7 header pair is roughly 11 mm (*check* the
  parts chosen), plus the card and its tallest part. A dry-fit question, as `thomas or teensy` 6 left the third
  USB lead — here there is no third lead.
- **The Teensy adapter's height behind the backplane** is the Mega's
  headers plus two Teensy sockets; compare with the Mega's USB-B jack in
  the same enclosure before ordering.
- **The voice lines are the backplane's noisiest new nets** — 5 V edges,
  and with the carrier idle 1 MHz continuously. Keep them short, over
  unbroken ground, and off the microphone side of `JA1`.

---

## 12. Test points and silkscreen

Every v2 test pad stays. Added on the backplane:

| Where | Why |
|---|---|
| each slot's tone and filter-out pins | what goes into a card and what comes out, with or without the card |
| `IOREF` | **5 V says a Mega is fitted, 3.3 V a Teensy**, with a meter |
| `MEGA_5V` | the computing shield's USB is up |
| `shield/sda`, `shield/scl` | a bus that will not answer |

Silkscreen, because each of these is a fault that reads as something else:

- **Each voice slot**: `JV1 — female1 — D6 / Teensy 2`, the same for all
  five, and `SLOT N = BODY N`.
- **`JA1`**: the five microphones in body order and `module N = body N`.
- **`IOREF: MEGA 5 V / TEENSY 3.3 V`** beside its pad.
- **On every active card**: its corner and both windows — `CARD 1414 —
  SWEET 849–1202 — ALLOWED 707–1414` — and `IDLE MAY BE 1 MHz`.
- **On every Thomas card**: `THOMAS — female1 — 1012 Hz`.
- **On the Teensy adapter**: `3.3 V — NOT 5 V TOLERANT` across the
  Teensy, and `POWERED BY TEENSY USB` around the translators.
- Everything `next pcb` section 6 asked for: `B-J4 — NO POWER`, `MEGA 5V`
  and `BOARD +5V` spelled out, `LINE OUT` and `AUDIO RTN`.

---

## 13. Bring-up, one shield at a time

**The shield order is the experiment order.** Each step changes one
shield, and each step's test is the previous step's test passing again.

1. **Bare backplane**: continuity and isolation as in the v2 README;
   `IOREF` isolated from both 5 V rails with no computing shield; every
   NeoPixel line and every filter-out line reading 0 V through its
   pull-down.
2. **The v2 board, rebuilt**: Mega, MSGEQ7 shield, five Thomas cards.
   Firmware 4, then `test audio loop` and `test audio bringup` exactly as
   on the v2 board. **This is the backplane's acceptance test.**
3. **Change the processor**: the Teensy adapter in the Mega's place,
   same shields. Firmware 5 at the Mega's five pitches. The same two
   tests pass, which proves the port before anything else changes.
4. **Change the ears**: the direct shield for the MSGEQ7s. Polled
   capture and `goertzel.py`: every body's tone on its own bin, heard by
   the expected microphones, with the bias reading of each microphone
   on the page.
5. **Change the voices**: active cards 1414, 4000, 8000, 250 and 500 for
   the Thomas cards, still at the Mega's pitches. What the room hears
   changes and nothing else does.
6. **Free the pitches**, within each card's window, and then the
   continuous stream for the running piece.
7. **`next pcb` section 3's harness measurement**, with Thomas cards and
   with active ones. It was always the one to do first.

**Changing a shield**: stop the piece from the page, unplug the rack's
supply **and** the computing shield's USB, change the shield, power back
up. No shield is hot-pluggable: a header meets its pins in no particular
order, and an EEPROM met half-powered on a live bus can be written by a
glitch its write protection never sees.

---

## 14. Parts, rough

Hobby-retail figures for 2026, to be checked before ordering.

| | Qty | Rough total |
|---|---|---|
| backplane: v2 without its audio parts, plus slot headers and pull-downs | 1 | v2's board cost, about the same |
| Teensy adapter: Teensy 4.1, sockets, translators, dividers | 1 | EUR 45–60 |
| MSGEQ7 shield: five `MSGEQ7N` and their networks | 1 | EUR 20–40 |
| direct analyser shield: two quads and their filters | 1 | EUR 5–10 |
| Thomas cards | 5 | EUR 10–20 |
| active cards, small batch, assembled | 10–15 | EUR 3–6 each |
| id EEPROMs | one per shield | EUR 0.3 each |

**The Teensy solution on its own**, the adapter, the direct shield and
five active cards, is **about EUR 65–100**, in line with `thomas or
teensy`'s Teensy mode (EUR 60–85) and with `sound options`. A full stock
of the thirteen cards, so any pitch can be set in an afternoon, adds the
other eight.

---

## 15. Against `thomas or teensy`

Both test both chains on one board; they differ in what changing chains
is.

| | `thomas or teensy` | `shields` |
|---|---|---|
| changing chains | one shunt, three relays | change shields, powered down |
| both chains fitted at once | yes, one idle | no: one of each pair |
| processors | Mega always, Teensy beside it | one or the other, in one footprint |
| USB leads | 3 in Teensy mode | **2 in every setup** |
| Teensy voice | I2S, three DACs: any waveform, level in software | **timer and active card**: a rounded square, any pitch in an octave per card |
| changing one variable at a time | voice and ear move together with the shunt | **any one shield**, any combination (section 1) |
| the main board's silicon | relays, DACs, op-amps, buffers | **none** |
| what a bad part costs | the main board | a shield |
| connector contacts in the audio path | none new | two per voice, two per microphone |

**The case for shields** is the second-to-last row and the one above it:
the board that cannot be quickly replaced carries nothing that can fail
quietly, and everything that can is on a board that can be. **The case
against** is the last row: every voice and every microphone now crosses a
connector twice, which is why the slots are gold, keyed and screwed down,
and why a body that goes quiet sends somebody to its card's test pads
before anywhere else.

---

## 16. What is open

- **The part checks** marked *check*: the SN74LV4T125's unpowered
  outputs, the op-amps (MCP6024 and MCP6004 classes) and their input
  current, the EEPROM's address pins, the i.MX RT's injection rating, the
  Schottky, C0G stock for Thomas's 150–470 nF, the MAX9814's 2 Vpp, the
  Teensy's dimensions, IOREF on the Mega in hand.
- **The Teensy's conversion time** at 12 bits without averaging, and so
  the rate actually achieved for five microphones (9b).
- **The continuous stream** (9b): ADC_ETC and DMA, the one new piece.
- **The MSGEQ7 at 3.3 V**: band centres and counts, for the
  Teensy-with-MSGEQ7 comparison only.
- **pyserial's DTR on open**, on the laptop's Windows, which the greeting
  now depends on (9c).
- **The enclosure**: card height in front, adapter height behind (11).
- **The harness measurement** (`next pcb` section 3), and the amplifier
  module and its rail (`next pcb` section 5); nothing here depends on
  either.
- **The photosensor loads**, still v2's provisional 10 K.
- **A netlist.** This is the specification; drawing it is the v2
  project with its audio sheets moved into four small projects (Teensy
  adapter, two analyser shields, two card kinds) and the slots added.
