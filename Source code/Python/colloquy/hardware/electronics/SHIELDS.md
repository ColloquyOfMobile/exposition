# Shields: one backplane, the solutions plugged into it

**A main PCB that carries no solution of its own.** It becomes a
**backplane**: the harness connectors, the power entry, the passives every
solution shares, and **slots**. What differs between solutions is a
**shield** in a slot: the **U2D2** (already one), a **computing shield**
(the Mega 2560 itself, or a Teensy 4.1 on an adapter in the Mega's
footprint), the **MSGEQ7 analyser shield** (the Mega's ear), and five
**voice cards**, the output filters, one per body. **The Teensy needs no
analyser: the microphones reach it straight from the backplane.** Trying
another solution is changing a shield.

Written 2026-10-03; **simplified 2026-10-04**; **direct microphones
2026-10-05**. The people building it are qualified, so this says what to
build, in what order, and how to tell the pieces apart, and leaves out
what a competent hand does anyway. **There is no shield identification in
hardware: the silkscreen does that job** (section 6). It is the sixth
solution, beside `next pcb`, `one board per body`, `opencm and pro
minis`, `ad9833 dual mode` and `thomas or teensy`; the backplane is the
v2 project (`CAD/KiCad/electronic box v2/colloquy-control-v2/`) with its
audio parts moved into shields.

> **The brief, 2026-10-03.** One main PCB that only routes signals and
> power; the solutions are shields. The computing shield comes as a Mega
> and as a Teensy 4.1. The analyser is MSGEQ7s for the Mega; for the
> Teensy the microphones go to it directly and their sound is **analysed
> on the computer**. The output filters are shields too, so a frequency
> can be changed quickly: **fixed** for the Mega, **changeable** for the
> Teensy, made by **a timer and a filter**, not a DAC. **SMD** for every
> simple part.

**Sources.** The backplane's pins and every value moved into a shield are
v2's `circuit.json`; the Teensy facts are PJRC's own code (`pwm.c`,
`analog.c`, `clockspeed.c`, `usb.c`, `usb_desc.h`, read 2026-10-03); the
microphone's output is the MAX9814 datasheet's (Maxim, electrical
characteristics) and this repository's own measurement of it
(`scope > diagnosing a microphone`, and `test goertzel ear` sampling it
straight into a Mega's `A0`); the part choices were checked against their
datasheets when the boards were drawn (`CAD/KiCad/shields/REVIEW.md`).
Every filter figure, frequency and voltage here is computed by
`colloquy/hardware/electronics/shields.py`, and
`pytest_tests/hardware/test_shields.py` holds the tables to it, to
`circuit.json` and to the sketch. What is still unmeasured is in
section 12.

---

## 0. Priorities

| Step | Build | What it gives | Why |
|---|---|---|---|
| **1** | backplane, five Thomas cards, MSGEQ7 shield; the Mega plugs in | **the v2 board**, electrically; firmware 4 unmodified | **the exhibition depends on this step alone** |
| 2 | Teensy adapter in the Mega's place; the analyser slot emptied | the same voices on the Teensy, and the microphones on the laptop | proves the port, and hears at any pitch |
| 3 | five active cards: 1414, 4000, 8000, 250, 500 | cleaner voices at today's pitches | the first step away from Thomas's sound |
| later | other card corners; the continuous sample stream | any pitch; hearing while the piece runs | |

**Each step changes as little as it can**, and its test is the previous
step's test passing again (section 10). Order step 1 first and on its own
if need be; nothing else is needed to open the exhibition.

---

## 1. At a glance

**Drawn: what swaps and what stays.** Hatched is fixed — the same in
every solution: the laptop, the backplane's own parts, the U2D2, the
harness and everything in the bodies. A dashed slot takes a shield,
changed powered down; each voice slot is changed on its own. The dotted
band is what changes with no shield moving at all. One body stands for
all five.

<div style="overflow-x: auto; margin: 1rem 0;">
<svg viewBox="0 0 1300 890" role="img" aria-label="Block diagram of what swaps and what stays in the shield solution. Fixed, the same in every solution: the laptop with its two USB leads; the backplane with its DSUB-15s, power entry, servo bus header, build-out, NeoPixel and photosensor resistors, pull-downs, a 4.7 K and 1 M on each direct microphone, eight LEDs, test pins and ground bonds; the U2D2; the DSUB harness with its four harness boards; and in each of the five bodies the divider, amplifier and speaker, the NeoPixels and photosensors, the MAX9814 microphone and the Dynamixel servo. Swappable, powered down, one of two shields per slot: the computing slot, which is the Mega footprint, takes the Mega 2560 on firmware 4 at 5 V or the Teensy 4.1 adapter on firmware 5 at 3.3 V behind translators; each of the five voice slots takes, on its own, a Thomas card, passive with one fixed pitch, in five variants one per body, or an active card, fourth order with the pitch free within its octave, in thirteen variants with corners from 177 Hz to 11.3 kHz; the analyser slot takes five MSGEQ7s, the Mega's ear, and is left empty with the Teensy. Signals: USB from the laptop to the computing slot and to the U2D2; five 5 V tones from the computing slot to the voice slots; five line outs through the harness to the bodies; NeoPixels and photosensors between the computing slot and the bodies; five microphones from the bodies, each to the analyser slot, whose band outputs return to the computing slot, and also straight to the computing slot through 4.7 K, where the Teensy reads them on A0 to A4; the Dynamixel bus from the U2D2 to the servos. Set in software, with no shield moving: the pitch within the fitted card's octave on the Teensy, the firmware that follows the computing shield, what each body sings, and the hearing, analysed on the laptop.">
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
<rect x="560" y="360" width="405" height="110" rx="5"></rect>
</g>
<g font-family="'IBM Plex Mono', monospace" font-size="10" font-weight="600" fill="currentColor" opacity="0.7">
<text x="207" y="105">COMPUTING SLOT &#183; the Mega footprint</text>
<text x="207" y="380">U2D2 SLOT</text>
<text x="572" y="105">VOICE SLOTS JV1&#8211;JV5 &#183; each swapped on its own</text>
<text x="572" y="380">ANALYSER SLOT JA1 &#183; MEGA ONLY</text>
</g>
<!-- shields -->
<g fill="none" stroke="currentColor" stroke-width="1.7">
<rect x="213" y="120" width="264" height="68" rx="3"></rect>
<rect x="213" y="228" width="264" height="68" rx="3"></rect>
<rect x="578" y="120" width="369" height="68" rx="3"></rect>
<rect x="578" y="228" width="369" height="68" rx="3"></rect>
<rect x="578" y="392" width="369" height="60" rx="3"></rect>
</g>
<rect x="213" y="392" width="264" height="60" rx="3" fill="url(#sw-hatch)" stroke="currentColor" stroke-width="1.7"></rect>
<g font-family="Chivo, sans-serif" font-size="13.5" font-weight="600" fill="currentColor" text-anchor="middle">
<text x="345" y="148">Mega 2560</text>
<text x="345" y="256">Teensy 4.1 adapter</text>
<text x="345" y="418">U2D2</text>
<text x="762" y="144">Thomas card</text>
<text x="762" y="252">Active card</text>
<text x="762" y="417">5 &#215; MSGEQ7</text>
</g>
<g font-family="'IBM Plex Mono', monospace" font-size="10" fill="currentColor" text-anchor="middle" opacity="0.72">
<text x="345" y="169">firmware 4, unmodified &#183; 5 V</text>
<text x="345" y="277">firmware 5 &#183; 3.3 V, translated</text>
<text x="345" y="438">the same in every setup</text>
<text x="762" y="162">passive, Thomas&#8217;s values &#183; one fixed pitch</text>
<text x="762" y="178">5 variants, one per body</text>
<text x="762" y="270">4th order &#183; pitch free within its octave</text>
<text x="762" y="286">13 variants: corners 177 Hz &#8211; 11.3 kHz</text>
<text x="762" y="437">the Mega&#8217;s ear &#183; leave the slot empty with the Teensy</text>
</g>
<g font-family="'IBM Plex Mono', monospace" font-size="11" font-weight="700" fill="currentColor" text-anchor="middle" opacity="0.9">
<text x="345" y="213">&#8645; either one</text>
<text x="762" y="213">&#8645; either one, in each slot</text>
</g>
<!-- fixed on the backplane -->
<rect x="195" y="500" width="300" height="170" rx="5" fill="url(#sw-hatch)" stroke="currentColor" stroke-width="1.6"></rect>
<text x="207" y="522" font-family="'IBM Plex Mono', monospace" font-size="10" font-weight="600" fill="currentColor" opacity="0.8">FIXED ON THE BACKPLANE</text>
<g font-family="'IBM Plex Mono', monospace" font-size="10" fill="currentColor" opacity="0.85">
<text x="207" y="546">4 &#215; DSUB-15 &#183; power entry &#183; servo bus J7</text>
<text x="207" y="566">100 R build-outs &#183; 330 R NeoPixel resistors</text>
<text x="207" y="586">10 K photosensor loads &#183; pull-downs</text>
<text x="207" y="606">4.7 K + 1 M on each direct microphone</text>
<text x="207" y="632">8 LEDs &#183; test pins &#183; ground bonds</text>
</g>
<!-- body -->
<g fill="url(#sw-hatch)" stroke="currentColor" stroke-width="1.6">
<rect x="1110" y="160" width="160" height="60" rx="3"></rect>
<rect x="1110" y="315" width="160" height="40" rx="3"></rect>
<rect x="1110" y="395" width="160" height="40" rx="3"></rect>
<rect x="1110" y="600" width="160" height="40" rx="3"></rect>
</g>
<g font-family="Chivo, sans-serif" font-size="11.5" fill="currentColor" text-anchor="middle">
<text x="1190" y="186">divider &#183; amplifier</text>
<text x="1190" y="204">speaker</text>
<text x="1190" y="339">NeoPixels &#183; photosensors</text>
<text x="1190" y="419">MAX9814 microphone</text>
<text x="1190" y="624">Dynamixel servo</text>
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
<path d="M 1108 415 H 967" stroke-width="2.4" marker-end="url(#sw-ax)"></path>
<path d="M 1005 415 V 490 H 525 V 265 H 497" stroke-width="2.4" marker-end="url(#sw-ax)"></path>
<path d="M 558 422 H 545 V 240 H 497" stroke-width="2.4" marker-end="url(#sw-ax)"></path>
<path d="M 477 440 H 505 V 620 H 1108" stroke-width="1.4" marker-end="url(#sw-ax)"></path>
</g>
<circle cx="1005" cy="415" r="4" fill="currentColor"></circle>
<g font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.85">
<text x="164" y="198">USB</text>
<text x="165" y="415">USB</text>
<text x="499" y="162">tone &#215; 5</text>
<text x="499" y="183">5 V</text>
<text x="972" y="182">line out</text>
<text x="640" y="329">NeoPixels &#183; photosensors</text>
<text x="970" y="406">mic</text>
<text x="499" y="233">bands</text>
<text x="499" y="258">mics</text>
<text x="600" y="484">microphones direct, through 4.7 K &#8594; Teensy A0&#8211;A4</text>
<text x="640" y="614">Dynamixel bus &#183; J7</text>
</g>
<!-- software -->
<rect x="20" y="715" width="1265" height="118" rx="6" fill="none" stroke="currentColor" stroke-width="1.6" stroke-dasharray="1.5 4" stroke-linecap="round"></rect>
<text x="36" y="738" font-family="'IBM Plex Mono', monospace" font-size="10.5" font-weight="600" fill="currentColor" opacity="0.75">SET IN SOFTWARE &#183; NO SHIELD MOVES</text>
<g font-family="Chivo, sans-serif" font-size="12.5" font-weight="600" fill="currentColor">
<text x="36" y="766">Pitch, within the fitted card&#8217;s octave</text>
<text x="352" y="766">Firmware follows the computing shield</text>
<text x="668" y="766">What each body sings</text>
<text x="984" y="766">Hearing, on the laptop</text>
</g>
<g font-family="'IBM Plex Mono', monospace" font-size="10" fill="currentColor" opacity="0.72">
<text x="36" y="788">Teensy only; a Mega plays its timers&#8217; five</text>
<text x="36" y="804">a new octave is another active card</text>
<text x="352" y="788">4 on the Mega, 5 on the Teensy</text>
<text x="352" y="804">flashed from the page</text>
<text x="668" y="788">tone on or off, from the page</text>
<text x="668" y="804">which body sings what pattern</text>
<text x="984" y="788">Goertzel bins at any pitch</text>
<text x="984" y="804">microphones straight to the Teensy</text>
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

| Slot | With the Mega | With the Teensy |
|---|---|---|
| computing | **the Mega 2560 itself**, firmware 4 | **Teensy 4.1 adapter**, firmware 5 |
| analyser | **5 × MSGEQ7**, Thomas's network | **empty**: the microphones go straight to the Teensy |
| voice × 5 | **Thomas card**: passive, one pitch | **active card**: 4th order, an octave of pitch |
| U2D2 | the U2D2, the same in both | |

**Two rules:**

1. **Nothing reaches a Teensy pin above 3.3 V.** Its outputs are
   translated up to 5 V; the photosensors are divided down; the
   microphones never exceed 2.45 V by their own output stage and arrive
   through 4.7 K; the MSGEQ7's outputs are not connected to it at all.
   Section 4c checks every analogue signal against both processors.
2. **The rack supply and the computing shield's USB go on and off
   together.** With one off and the other on, series resistors limit the
   current into the unpowered side to a fraction of a milliamp per line:
   safe for the minute it takes to bring the other up, not a way to leave
   the piece. It is printed on the board (section 6).

---

## 2. The backplane

**Every connection to the harness is the v2 board's**, pin for pin: same
outline, the four DSUB-15s, `J2`, `J6`, `J7` and the spare-conductor
headers in the same places (tables in `thomas or teensy` section 2, held
to `circuit.json` by its own test). The harness boards do not change.

### 2a. Parts

| | What | v2 references |
|---|---|---|
| **kept** | four DSUB-15s, `J2`, `J6`, `J7`, `Extra1`–`Extra3`, U2D2 mount `M1`, the Mega footprint `A1` (on the back) | as v2 |
| **kept** | NeoPixel series 330 R; photosensor loads 10 K provisional; line-out build-outs 100 R; amp-shutdown pull-up 10 K | `RN1`–`RN7`, `RP1`–`RP11`, `R103`–`R503`, `RS1` |
| **kept** | one AGND–GND bond, one bond per body audio return; 470 µF bulk; test pads; mounting holes | `JP1`–`JP6` |
| **moved** to Thomas cards | the five passive filters | `R101`–`C502` |
| **moved** to the MSGEQ7 shield | the five MSGEQ7s and their networks | `U1`–`U5` and theirs |
| **added** | analyser slot `JA1`: 2 × 11 header, 2.54 mm, last pin removed as key | THT |
| **added** | voice slots `JV1`–`JV5`: 2 × 3 header, 2.54 mm, last pin removed as key | THT |
| **added** | M3 standoffs: one per card, two for the analyser shield | |
| **added** | per microphone: 4.7 K from the conductor to its footprint pin, 1 M from that pin to AGND (section 4a) | 0603 |
| **added** | 100 K to GND on each of the seven `…/neopixel/driven` nets | 0603 |
| **added** | 100 K to AGND on each of the five `…/filter out` nets | 0603 |
| **added** | eight LEDs and their resistors (section 6a) | 0603 |
| **added** | 26 test pins, single 1 × 1 headers (section 6b) | THT |

**The pull-downs** keep every NeoPixel strip off a floating data line —
while a processor boots, while one is unpowered, with the slot empty —
which v2 lacks too, and leave an empty voice slot's body at 0 V instead
of an open amplifier input.

### 2b. The computing slot: the Mega footprint, unchanged

Every pin v2 connects keeps v2's net, so the Mega plugs in as it is and
firmware 4 runs unmodified. Held to `circuit.json` by the test.

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

**Five footprint pins are added**, all unconnected on v2 and untouched by
firmware 4: the microphones, direct.

| Added pin | Net | |
|---|---|---|
| `D26` | `female1/mic direct` | through 4.7 K from `female1/microphone` |
| `D27` | `female2/mic direct` | through 4.7 K from `female2/microphone` |
| `D28` | `female3/mic direct` | through 4.7 K from `female3/microphone` |
| `D29` | `male1/mic direct` | through 4.7 K from `male1/microphone` |
| `D30` | `male2/mic direct` | through 4.7 K from `male2/microphone` |

On a Mega these are unused digital inputs, and firmware 4 never looks at
them. The footprint's 5 V pins stay `MEGA_5V`, as v2: the computing
shield's own USB 5 V, feeding `RS1` and the MSGEQ7 shield.

### 2c. The analyser slot `JA1`

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
| 19 | `MEGA_5V` |
| 20 | `GND` |
| 21 | `GND` |
| 22 | key, no pin |

Each microphone sits between two `AGND` pins, so no digital line runs
beside one in the connector.

### 2d. The voice slots `JV1`–`JV5`

One pinout for all five:

| JV pin | Signal |
|---|---|
| 1 | the slot's `<body>/tone`: a 5 V square |
| 2 | `GND` |
| 3 | the slot's `<body>/filter out`: line level, to v2's build-out |
| 4 | `AGND` |
| 5 | `+5V` |
| 6 | key, no pin |

| Voice slot | Body | Pin 1 | Pin 3 | Silkscreen beside it |
|---|---|---|---|---|
| `JV1` | female1 | `female1/tone` | `female1/filter out` | `JV1 · FEMALE1 · MEGA D6 · TEENSY 2` |
| `JV2` | female2 | `female2/tone` | `female2/filter out` | `JV2 · FEMALE2 · MEGA D46 · TEENSY 4` |
| `JV3` | female3 | `female3/tone` | `female3/filter out` | `JV3 · FEMALE3 · MEGA D10 · TEENSY 5` |
| `JV4` | male1 | `male1/tone` | `male1/filter out` | `JV4 · MALE1 · MEGA D11 · TEENSY 6` |
| `JV5` | male2 | `male2/tone` | `male2/filter out` | `JV5 · MALE2 · MEGA D5 · TEENSY 28` |

**Slot N is body N**, in body order, which is module order: one number
identifies a body all the way round, as on every board so far. With
Thomas cards fitted, the copper from tone pin to DSUB is v2's with two
connector contacts in it.

---

## 3. The computing shields

### 3a. The Mega 2560

**The Mega is its own shield**: it plugs into the footprint exactly as
into the v2 board, carried on the back, on its own USB lead. Firmware 4
runs unmodified with the MSGEQ7 shield and Thomas cards: step 1.

### 3b. The Teensy 4.1 adapter

**A board in the Mega's footprint with a Teensy on it**: female headers
where a Mega has them (the ICSP is not needed), the Mega's four mounting
holes, the Teensy in two 1×24 sockets on the far side with its USB at the
end where the Mega's USB-B is. Still two USB leads in the rack.

- **Power: the Teensy's own USB, as a Mega.** It takes 5 V from `VIN`
  and never feeds it; a Schottky from `VIN` gives the footprint's 5 V
  pins (`MEGA_5V`).
- **Its pins are not 5 V tolerant**, so everything leaving for the
  bodies and the cards — seven NeoPixel lines, five tones, two aux lines,
  amp shutdown — goes through four **SN74LV4T125** translators powered
  from `VIN`, which makes them 5 V exactly as from a Mega. A card's level
  does not depend on which processor is fitted.
- **The microphones come in direct** on the five added footprint pins,
  each with 1 nF at the Teensy pin (section 4a).
- **The photosensors are divided** (100 K / 150 K): they are 3-pin
  modules on the body's 5 V and can reach it.
- **The analyser's pins are not connected** — `A0`–`A4`, strobe and
  reset — since with the Teensy the slot is empty.

**The photosensors keep their Mega `A`-numbers, and the microphones take
`A0`–`A4`**, where a Mega reads their bands. Read out of PJRC's core; the
test checks every row against `shields.py`.

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
| 12 | `D17` | `male2/bar neopixel/driven` | translator; firmware's male1 up ring |
| 29 | `D16` | `male1/bar neopixel/driven` | translator; firmware's male2 up ring |
| 30 | `D24` | `male1/aux driven` | translator |
| 31 | `D25` | `male2/aux driven` | translator |
| 32 | `D2` | `amp shutdown` | translator |
| 14 | `D26` | `female1/mic direct` | direct, 1 nF; A0 |
| 15 | `D27` | `female2/mic direct` | direct, 1 nF; A1 |
| 16 | `D28` | `female3/mic direct` | direct, 1 nF; A2 |
| 17 | `D29` | `male1/mic direct` | direct, 1 nF; A3 |
| 18 | `D30` | `male2/mic direct` | direct, 1 nF; A4 |
| 19 | `A5` | `female1/photosensor` | divider; A5 |
| 20 | `A6` | `female2/photosensor` | divider; A6 |
| 21 | `A7` | `female3/photosensor` | divider; A7 |
| 22 | `A8` | `male1/photosensor/A` | divider; A8 |
| 23 | `A9` | `male1/photosensor/B` | divider; A9 |
| 24 | `A10` | `male1/photosensor/C` | divider; A10 |
| 25 | `A11` | `male1/photosensor/D` | divider; A11 |
| 26 | `A12` | `male2/photosensor/A` | divider; A12 |
| 27 | `A13` | `male2/photosensor/B` | divider; A13 |
| 38 | `A14` | `male2/photosensor/C` | divider; A14 |
| 39 | `A15` | `male2/photosensor/D` | divider; A15 |

**Why these pins**: the five tones are on **five different timer units**
(`analogWriteFrequency()` sets a whole unit, so two voices on one would
play one pitch); the microphones are on 14–18, which **both converters
reach**, so they can be sampled in pairs; nothing is on 13, the LED the
bootloader blinks. **Spare**: 0, 1, 3, 33, 34, 35, 36, 37, 40, 41, each to
a labelled pad.

| Part | Value | Package | Note |
|---|---|---|---|
| Teensy 4.1 | | module | two 1×24 female headers |
| Mega-pattern headers | female: five 1×8, one 1×10, one 2×18 | THT | |
| translators ×4 | SN74LV4T125 | TSSOP-14 | `VCC` from `VIN`; `OE` to GND; spare input to GND; partial-power-down outputs (TI) |
| translator input pull-downs ×15 | 100 K | 0603 | low while the Teensy boots or is absent |
| microphone reservoirs ×5 | 1 nF C0G, Teensy pin to GND | 0603 | section 4a |
| photosensor dividers ×11 | 100 K series, 150 K to GND, 10 nF C0G at the pin | 0603 | 5.25 V becomes 3.15 V |
| `VIN` to `MEGA_5V` | Schottky, 1N5819HW | SOD-123 | |
| decoupling | 100 nF per IC; 10 µF on `VIN` and on 3.3 V | 0603, 0805 | |
| test pins ×3 | 1 × 1 header | THT | `VIN`, `3V3`, `GND` (6b) |

---

## 4. The microphones and the analyser

### 4a. The microphones, direct

**`test goertzel ear` already proved it**: a MAX9814 module wired straight
to a Mega's `A0`, nothing in between, sampled at 19.2 kSPS, heard every
tone it was played. The Teensy gets the same signal the same way. Each
microphone conductor branches on the backplane — to `JA1` for the MSGEQ7
shield, and through **4.7 K** to its footprint pin — with **1 M to AGND**
on the pin side, and the adapter adds **1 nF** at the Teensy pin.

**What the microphone puts out** (MAX9814 datasheet, characterised at a
3.3 V supply):

| | Datasheet | Measured here, on the body's 5 V |
|---|---|---|
| output bias | 1.23 V (1.14–1.32 V) | 1.21 V (248 counts of 1023 at 5 V) |
| swing, AGC regulating | 1.40 Vpp (1.26–1.54 Vpp) | about 1.44 Vpp in a quiet room (294 counts) |
| swing, most it will give | 2.0 Vpp at 1 % THD | |
| highest output | 2.45 V | |
| output impedance; minimum load; capacitive load | 50 Ω; 5 kΩ; 200 pF | |

So **the signal lives between about 0.2 and 2.3 V and cannot pass
2.45 V**: inside the Teensy's 0–3.3 V with 0.85 V to spare, and the
measured module agrees with the datasheet on both bias and swing.

**The three parts, and what each is for:**

- **4.7 K series**: the protection a Teensy needs and a Mega did not.
  The datasheet's 2.45 V is at a 3.3 V supply and the modules run on 5 V,
  and a harness conductor shorted to 5 V is a fault worth surviving: it
  would push at most 0.3 mA into the pin's clamp. It also keeps the
  backplane's copper off the MAX9814's 200 pF budget, which the cable has
  already spent, and is a negligible load against its 5 kΩ minimum.
- **1 M to AGND**: a microphone that is unplugged reads a flat **0 V**,
  not a ghost of its neighbour (an open ADC pin reads 95 % of the channel
  converted before it, measured on `microphone_sampler`). It takes 0.5 %
  off the signal. So the bias is a reading: **0 V** nothing plugged in,
  **about 1.23 V** a live MAX9814, **about 0.75 V** the dead module of
  `diagnosing a microphone` (its bias 475 mV low).
- **1 nF at the Teensy pin**: the converter's sampling kick lands on it
  rather than on the cable. With the 4.7 K it is a 34 kHz first-order
  low-pass: a fraction of a decibel at the highest pitch any card
  carries, and all the anti-aliasing the Mega's 19.2 kSPS test shows is
  needed at the Teensy's 44 kSPS.

**No gain, no offset, no buffer.** The signal uses 61 % of the Teensy's
range, about 2480 of its 4096 counts, against the 294 counts of 1023 the
Mega's test worked with. The third that is left is headroom for the moment before
the AGC reacts to a sudden sound (1.1 ms in the datasheet, with its own
timing capacitor).

### 4b. The MSGEQ7 shield: the Mega's ear

**v2's analyser array** in SMD, supplied from `MEGA_5V` exactly as on v2.
150 × 55 mm. Per channel, five times; held to `circuit.json` by the test:

| MSGEQ7 part | Value | Package | v2 (female1's) | Note |
|---|---|---|---|---|
| microphone series | 47K | 0603, 1 % | `R311` | |
| microphone shunt | 6K8 | 0603, 1 % | `R316` | to AGND |
| input coupling | 100nF | 0603 X7R | `C312` | |
| oscillator resistor | 200K 1% | 0603, 1 % | `R313` | to `MEGA_5V` |
| oscillator capacitor | 33pF C0G | 0603 | `C314` | close to pin 8 |
| reference bypass | 100nF | 0603 | `C316` | pin 6 is a reference, **never grounded** |
| attenuator bypass | ATTEN BYPASS (OPEN) | solder jumper | `JS3` | bridged only after measuring |
| supply bypass | 100 nF, `MEGA_5V` to AGND | 0603 | | |
| analyser | `MSGEQ7N` | SOIC-8 | `U3` | buy six from an authorised distributor |

**With the Teensy the slot is empty.** Left in by mistake it does no
harm: its outputs reach footprint pins the adapter does not connect.

### 4c. Voltages and references, checked

**The Teensy's reference is fixed at its own 3.3 V** (`analogReference()`
does nothing on a Teensy 4), so the best use of it is to bring every
signal inside 0–3.3 V with no more margin than safety needs. **The Mega
reads against `AVcc`, its own USB 5 V**, which is also the MSGEQ7's
supply.

| Signal | Read on | Reference | Range at the pin | Span used |
|---|---|---|---|---|
| microphone, direct | Teensy A0–A4 | 3.3 V | 0.23–2.23 V; 2.45 V highest | 61 % |
| photosensor, divided | Teensy A5–A15 | 3.3 V | 0–3.15 V | 95 % |
| photosensor | Mega A5–A15 | 5 V | 0–5.25 V | 100 % |
| MSGEQ7 band | Mega A0–A4 | 5 V | 0 V to its own 5 V supply | ratiometric |
| microphone, direct | Mega D26–D30 | not read | 0.23–2.23 V | |

- **The microphones** are not scaled up on the Teensy: section 4a's
  headroom is worth more than the extra counts.
- **The photosensors** on the Teensy are divided by 0.6, so 5.25 V — the
  top of a USB-class 5 V rail — arrives as 3.15 V: 95 % of the range,
  under it by 0.15 V. On the Mega they read as v2 does; a sensor on the
  jack's 5 V above the USB's 5 V reads 1023, as it always has.
- **The MSGEQ7** runs from the same rail the Mega reads against, so its
  bands are ratiometric and use the whole range.
- **The Mega's internal 2.56 V reference** would suit a microphone on a
  Mega's own `A`-pin, as in `test goertzel ear`, but the photosensors need
  the full 5 V on the same converter, so the piece stays on `AVcc`. The
  test worked on `AVcc` anyway.
- **Digital lines**: everything a Teensy drives toward a body or a card
  is translated to 5 V; nothing at 5 V is driven toward a Teensy.

---

## 5. The voice cards

**A card per slot**, so one body's pitch changes without touching the
others. Each kind is one PCB, 30 × 42 mm, SMD on one side, a 2×3 socket
beneath and one M3 screw; a variant is a BOM. Every card has a pad on its
tone input and two 1-pin headers, `LINE` and `AGND`, 2.54 mm apart, so a
powered speaker or a scope plugs straight on at the bench.

### 5a. The Thomas card: passive, one pitch

**Thomas's channel moved off the main board**: two RC sections, `R1 = R2`
and `C1 = C2`, from tone to line, exactly v2's, plus 100 K from tone to
GND so an undriven slot idles at 0 V. Five variants:

| Thomas card | Body | Plays (Mega) | `R1 = R2` | `C1 = C2` | v2 |
|---|---|---|---|---|---|
| 1 kHz | female1 | 1012 Hz | 1K2 | 150nF | `R301`/`R302`, `C301`/`C302` |
| 2.5 kHz | female2 | 2531 Hz | 1K8 | 47nF | `R401`/`R402`, `C401`/`C402` |
| 6.25 kHz | female3 | 6329 Hz | 2K2 | 10nF | `R501`/`R502`, `C501`/`C502` |
| 160 Hz | male1 | 162 Hz | 2K2 | 470nF | `R101`/`R102`, `C101`/`C102` |
| 400 Hz | male2 | 405 Hz | 2K | 220nF | `R201`/`R202`, `C201`/`C202` |

**Three capacitor lands in parallel per position**, so every value is made
from stocked parts — 470 nF is 220 nF PPS + 220 nF PPS + 30 nF C0G — and
unused lands are left empty. C0G or PPS film only, never X7R: each corner
sits at its own tone and these carry DC.

### 5b. The active card: any pitch in an octave

One quad op-amp (MCP6024, SOIC-14) on `+5V`:

1. **Input**: 15 K from the tone, 10 K to a 2.5 V reference, then a
   buffer. The 5 V square becomes 2.0 Vpp, and its fundamental is
   (4/π) × 2.0 = **2.55 Vpp**: the line level the body divider was sized
   for.
2. **Stage 1**: unity-gain Sallen–Key, two equal resistors `Ra`, 12 nF in
   feedback, 10 nF to AGND — **Q 0.548**.
3. **Stage 2**: the same with `Rb`, 22 nF and 3.3 nF — **Q 1.291**.
   Together a fourth-order Butterworth.
4. **Reference**: 10 K / 10 K across `+5V`, 10 µF, a follower.
5. **Output**: 1 µF X7R and 100 K to AGND, the line centred on 0 V.

**The four capacitors never change; the four resistors (two values) are
the variant.** Where a pitch may sit on a card, computed for the cards
as built:

| Window | Pitch / corner | Fundamental loses | 3rd harmonic | 5th harmonic | Used for |
|---|---|---|---|---|---|
| sweet | 0.60 – 0.85 | at most 1.1 dB | at least 29.7 dB down | at least 51.9 dB down | **choosing** a card |
| allowed | 0.50 – 1.00 | at most 3.1 dB | at least 23.6 dB down | at least 45.6 dB down | what the firmware may play on it |

So **a card carries an octave of pitch in software**, and even at its
edges it is cleaner than Thomas's channels are at their own pitch (21–23
dB). The corners are half an octave apart, so every pitch from 106 Hz to
9.6 kHz has a card. **Build the five of step 3 first**; the rest when a
pitch needs them.

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

**Against Thomas's channel, at the pitches the Mega plays** (same 5 V
square in, so this is the filter alone):

| Pitch | Body | Thomas: fundamental | Thomas: 3rd | Thomas: line | Card | Card: fundamental | Card: 3rd | Card: line |
|---|---|---|---|---|---|---|---|---|
| 1012 | female1 | -10.8 dB | -22.3 dB | 1.85 Vpp | 1414 | -0.2 dB | -35.9 dB | 2.49 Vpp |
| 2531 | female2 | -12.3 dB | -23.1 dB | 1.55 Vpp | 4000 | -0.1 dB | -31.6 dB | 2.51 Vpp |
| 6329 | female3 | -8.4 dB | -21.0 dB | 2.42 Vpp | 8000 | -0.6 dB | -38.8 dB | 2.37 Vpp |
| 162 | male1 | -10.0 dB | -21.9 dB | 2.02 Vpp | 250 | -0.0 dB | -32.5 dB | 2.53 Vpp |
| 405 | male2 | -10.5 dB | -22.2 dB | 1.89 Vpp | 500 | -0.8 dB | -39.8 dB | 2.32 Vpp |

| Part | Value | Package |
|---|---|---|
| op-amp | MCP6024 | SOIC-14 |
| input divider | 15 K, 10 K | 0603, 1 % |
| stage 1 | `Ra` ×2; 12 nF, 10 nF | 0603 1 %; C0G 5 % |
| stage 2 | `Rb` ×2; 22 nF, 3.3 nF | 0603 1 %; C0G 5 % |
| reference | 10 K ×2, 10 µF X7R | 0603, 0805 |
| output | 1 µF X7R, 100 K | 0805, 0603 |
| decoupling | 100 nF + 10 µF | 0603, 0805 |

**The level is the input divider**: it gives Thomas's 2.5 Vpp. A hotter
card is a divider variant, up to about 4.5 Vpp, and the first remedy if
`next pcb` section 3's harness measurement comes back weak.

---

## 6. LEDs, test pins and silkscreen

### 6a. LEDs: eight, all on the backplane

**Eight LEDs answer the first questions at a rack**: is the rack
powered, is the computing shield powered, is each body's voice being
sent. All are on the backplane's front, each beside its label, and none
on a shield, so changing a shield never takes an indicator with it.
0603 SMD, high-efficiency; the currents assume a 2 V forward drop.

| LED | Lit means | On net | Colour | Resistor | Current |
|---|---|---|---|---|---|
| `+5V` | the rack supply is on | `+5V` | green | 2.2 K | 1.4 mA |
| `+12V` | the servo and body 12 V is on | `+12V` | green | 4.7 K | 2.1 mA |
| `MEGA 5V` | the computing shield's USB is up: a Mega's own, or the Teensy's through its Schottky | `MEGA_5V` | green | 2.2 K | 1.4 mA |
| `TONE 1`–`TONE 5` | that body's voice is being sent: half-bright while a tone plays, dark when silent | each `<body>/tone`, at its slot | yellow | 1.5 K | 2.0 mA high, 1 mA average |

**A voice LED splits the sound chain in two.** A body that should be
singing with its LED dark: the processor, its translator or the
firmware. LED lit and the room silent: the card, the harness or the
amplifier — go to that slot's `LINE` pin next. Each LED loads its tone
line by 2 mA, which a Mega pin or an SN74LV4T125 drives with a drop of
about 0.1 V: a card's level moves by under 0.2 dB.

**And a ninth that costs nothing**: firmware 5 toggles the processor's
own LED — the Mega's `L` on `D13`, the Teensy's on pin 13, both
unconnected on the backplane — on every command it receives. Flickering
means the program is talking to the board; still means it is not.

### 6b. Test pins: single 1-pin headers

**The test points worth reaching with the board in the rack are single
2.54 mm pin headers (1 × 1, gold)**, so a Dupont female pushes on and
stays, and a meter probe or a scope hook takes them as well. Each has its
label beside it and each row has its own ground pin; rows sit on a
2.54 mm grid, so several Dupont leads fit side by side. Everything else
stays a bare pad.

| Board | Row | Pins | What a pin reads |
|---|---|---|---|
| backplane | power | `+5V`, `+12V`, `MEGA 5V`, `GND` | the three rails; `+12V` with an empty position on each side |
| backplane | voices | `TONE 1`–`TONE 5`, `LINE 1`–`LINE 5`, `AGND` | the 5 V square going into each card; the line level coming out |
| backplane | ears | `MIC DIRECT 1`–`MIC DIRECT 5`, `ANA 1`–`ANA 5`, `AGND` | each microphone as the Teensy sees it (about 1.23 V at rest, 0 V unplugged); each MSGEQ7's bands as the Mega sees them |
| Teensy adapter | power | `VIN`, `3V3`, `GND` | the Teensy's USB 5 V and its 3.3 V |
| every voice card | output | `LINE`, `AGND`, 2.54 mm apart | the card's output: a powered speaker or a scope plugs straight on |

That is 26 pins on the backplane, 3 on the adapter and 2 on each card.
**Bare pads**: `MIC 1`–`MIC 5` (the conductor, before the 4.7 K), strobe
and reset, the Teensy's spare pins, the MSGEQ7 shield's own outputs, and
each card's tone input.

### 6c. Silkscreen

**The silkscreen is how anybody at the rack knows what is fitted where.**
Text in capitals as given, at least 1 mm high on the backplane and the
adapter, 0.8 mm on cards; `______` is a white box to write in with a
marker. Every LED, pin and pad carries its name.

### Backplane, front

| Where | Text |
|---|---|
| top edge | `COLLOQUY · SHIELD BACKPLANE · REV A` |
| beside the slots, boxed | `POWER RACK AND COMPUTING USB TOGETHER` and below it `CHANGE A SHIELD ONLY WITH BOTH UNPLUGGED` |
| beside each voice slot | the slot's line in 2d, e.g. `JV1 · FEMALE1 · MEGA D6 · TEENSY 2`, and under it `CARD ______  PITCH ______ Hz` |
| along the voice slot row | `SLOT N = BODY N` |
| beside each slot's key | `KEY` with an arrow to the missing pin; `1` at pin 1 |
| beside `JA1` | `JA1 · MSGEQ7 ANALYSER · MEGA ONLY · EMPTY WITH TEENSY` and `MIC ORDER F1 F2 F3 M1 M2 · MODULE N = BODY N` |
| beside the microphone resistors | `MIC DIRECT · 4.7 K · TO TEENSY A0–A4` |
| `M1` and `J7` | `U2D2` and `SERVO BUS · 12 V` |
| rails | `BOARD +5V`, `+12V`, `MEGA 5V (COMPUTING USB)` |
| DSUBs | as v2, with `B-J4 · NO POWER` |
| audio | `LINE OUT` and `AUDIO RTN` at the old speaker pairs; `JP1 · ONLY AGND–GND BOND` |

### Backplane, back (the computing slot)

`COMPUTING SLOT · MEGA 2560 OR TEENSY ADAPTER`, `USB END` with an arrow,
and the four mounting holes marked `M3`.

### Teensy adapter

| Where | Text |
|---|---|
| top | `TEENSY 4.1 ADAPTER · IN PLACE OF THE MEGA · FIRMWARE 5` |
| across the Teensy sockets | `3.3 V · NOT 5 V TOLERANT` |
| socket outline | `USB ↑` and `PIN 0` / `VIN` at their ends, so the Teensy cannot go in reversed |
| around the translators | `POWERED BY TEENSY USB` |
| by the microphone reservoirs | `MIC A0–A4 · DIRECT` |
| spare pads | their pin numbers: `0 1 3 33 34 35 36 37 40 41` |
| test pins | `VIN`, `3V3`, `GND` |

### MSGEQ7 shield

`MSGEQ7 ANALYSER · MEGA ONLY`; per channel `CH0 F1` … `CH4 M2`; by each
bypass jumper `OPEN UNLESS MEASURED`; by each pin 6 `REF · NEVER GROUND`.
Test pads `ANA 0`–`ANA 4`, `MEGA 5V`, `AGND`.

### Voice cards

**Front of every card**: its kind in large type, `BODY ______` or
`CORNER ______ Hz` to write in, and `LINE` / `AGND` at its two output
pins.
**Back of every card: the whole variant table, with a box to tick**, so
the card says what it is and the resistors can be checked against it.

| Card | Front | Back |
|---|---|---|
| Thomas | `THOMAS VOICE CARD · FIXED PITCH`, `BODY ______` | the five rows of 5a: body, pitch, `R1 = R2`, `C1 = C2`, ☐ |
| active | `ACTIVE VOICE CARD`, `CORNER ______ Hz`, `PLAY 0.5–1 × CORNER · BEST 0.6–0.85 × CORNER` | the thirteen rows of 5b: corner, `Ra`, `Rb`, ☐ |

---

## 7. The Teensy port, checked

### 7a. Voices

**Each voice is a timer toggling a pin in hardware**, as on the Mega: it
costs no processor time and nothing that masks interrupts can tear it.
The timers count a 150 MHz clock with a sixteen-bit divider and a
prescaler up to 128, so the lowest pitch is **17.9 Hz**, and what the core
produces when asked (`shields.teensy_pwm_frequency`) is:

| Asked | Teensy plays | The Mega plays |
|---|---|---|
| 162 | 162.00 Hz | 162 Hz, Thomas's trimmed OCR |
| 405 | 405.00 Hz | 405 Hz |
| 1012 | 1012.01 Hz | 1012 Hz |
| 2531 | 2531.00 Hz | 2531 Hz |
| 6329 | 6329.11 Hz | 6329 Hz |
| 160 | 160.00 Hz | not available |
| 1000 | 1000.00 Hz | not available |
| 6250 | 6250.00 Hz | not available |

So step 2 plays the Mega's pitches exactly. Code:
`analogWriteResolution(8)`, `analogWriteFrequency(pin, hz)`,
`analogWrite(pin, 128)` to sing, `analogWrite(pin, 0)` to stop.

### 7b. Ears

The microphones arrive on pins 14–18, straight from the MAX9814 (4a).
Those pins reach both converters, so a frame is three paired conversions
— about **44 kSPS per microphone** (*check* the conversion time; the
first bench measurement).

1. **Polled capture first.** `microphones/capture` takes a block of 1024
   frames (23 ms) and answers one text line in `microphone_sampler`'s
   `block` format with `ch=5`. Nothing else runs during it, as nothing
   else runs during the Mega's MSGEQ7 sweep today. Every hardware test
   needs only this.
2. **A continuous stream later**, for hearing while the piece runs: a
   second USB serial interface (Dual Serial), hardware-triggered sampling
   with DMA. The one new piece of code in the port, so it is not on the
   path to anything else.

The analysis is already written: `test_goertzel_ear`'s `goertzel.py`.

### 7c. The sketch, part by part

**One sketch, two boards**: `colloquy_of_mobiles.ino` gains a board layer
(`#if defined(__IMXRT1062__)`) and becomes firmware **5** for both.

| Sketch part | On the Teensy |
|---|---|
| `Adafruit_NeoPixel`, `PixelGroup`, `PixelGroupBeam`, `PixelGroupForFemaleBody` | **unchanged**: the library has a Teensy 4 path |
| `ArduinoJson`, `processCommand()` | **unchanged** |
| `FIRMWARE_VERSION` | 5 |
| `SERIAL_BAUDRATE` | kept at 1000000: USB ignores it, the driver reads it |
| `COMMAND_BUFFER_SIZE`, the receive loop | **unchanged** |
| pin `#define`s | the second set, 3b |
| `LightSensor::read()` | 12-bit read **scaled to Mega counts**, so `params.json` thresholds keep their meaning |
| `Voice` | **rewritten**: the register code becomes the three calls of 7a; `<body>/speaker` gains an optional `hz` |
| `Analyser` | **Mega only**: the Teensy build leaves it out, having no MSGEQ7 |
| `Female`, `Male` | **unchanged** |
| object initialisation | unchanged but for pin names |
| `greeting()` | gains `"board"`: `"mega2560"` or `"teensy41"` |
| `setup()` | unchanged |
| `loop()` | gains the port-open behaviour below |
| the board's own LED (`D13`, Teensy `13`) | **new, on both boards**: toggles on every command received (6a) |
| new paths | `microphones/capture` (the Teensy's), replacing `microphones` (the Mega's bands) |

**Three things the Mega does by accident and the Teensy must do on
purpose**, each of which fails silently otherwise:

- **Greet when the port opens.** Opening a Mega's port reboots it and it
  greets; a Teensy does not reboot. Greet on every rising
  `Serial.dtr()`, and `Arduino.wait_for_reboot()` works unchanged.
- **Go quiet when the port opens or closes.** Return to the boot state —
  pixels off, voices silent — on each DTR edge, so a crashed program
  never leaves a body singing.
- **Scale the light sensors**, above.

And one thing the driver must never do: **134 baud reboots a Teensy into
its bootloader** (`usb.c`), so `firmware.PROBE_BAUDRATES` must never
contain it. The test pins that.

### 7d. Python

- `boards.KNOWN_DEVICES` gains `0x16C0:0x0483` (USB Serial) and
  `0x16C0:0x048B` (Dual Serial), both as plausible Arduinos.
- The flasher's board type follows the computing shield:
  `teensy:avr:teensy41` through PJRC's board package.
- `drivers/audio.py`'s pitch becomes a setting on the Teensy. The corner
  of each fitted active card is noted beside it in `params.json` (the
  card says it in its silkscreen), and the page refuses a pitch outside
  the card's allowed window.
- `drivers/hearing/` stops being emulated on the Teensy, through
  `goertzel.py`.

---

## 8. SMD and through-hole

**Every resistor, capacitor, IC and diode is SMD**: 0603 for signal
parts, 0805 for 10 µF and 1 µF, SOIC or TSSOP for ICs. Through-hole only
for connectors and sockets:

| Through-hole | Where |
|---|---|
| DSUB-15s, `J2`, `J6`, `J7`, Mega mating headers | backplane |
| `JA1`, `JV1`–`JV5` | backplane |
| Mega-pattern female headers, Teensy sockets | Teensy adapter |
| slot sockets | the MSGEQ7 shield and every card |
| test pins, 1 × 1 | backplane, adapter, every card |

**Slot contacts gold on both halves**; the socket's cavity at the key is
plugged.

---

## 9. Placement

- **The backplane keeps v2's outline, fixed connectors, Mega position
  and AGND region**; it is four layers, the adapter four, the cards and
  the MSGEQ7 shield two.
- **Voice slots near the DSUBs' line-out pins; `JA1` and the five 4.7 K
  near the microphone pins**, in the AGND region; `JP1` the only bond.
  The direct microphone traces run over AGND to the footprint, away
  from the tone lines.
- **The tone lines are the backplane's noisiest nets**: short, over
  unbroken ground, away from the microphones.
- **LEDs and test pins where a hand and an eye reach them with the board
  in the rack**: the power row by the power entry, each `TONE` LED with
  its `TONE` / `LINE` pins beside its slot, the ears row beside `JA1`.
- **Heights** — cards in front, the adapter behind — are a dry fit
  against the enclosure before ordering.

---

## 10. Bring-up and changing a shield

1. **Bare backplane**: continuity and isolation as in the v2 README;
   with the rack supply on and no shield, `+5V` and `+12V` lit,
   `MEGA 5V` and every `TONE` dark, every NeoPixel line and `LINE` pin at
   0 V through its pull-down, every `MIC DIRECT` pin at 0 V.
2. **Step 1**: Mega, MSGEQ7 shield, five Thomas cards, firmware 4, then
   `test audio loop` and `test audio bringup` exactly as on v2; each
   `TONE` LED lights with its body. **The backplane's acceptance test.**
3. **Step 2**: the Teensy adapter in the Mega's place, the analyser slot
   empty, firmware 5 at the Mega's pitches. `MEGA 5V` lights from the
   Teensy's USB and its own LED flickers with each command. A meter on
   each `MIC DIRECT` pin first: about 1.23 V. Then polled capture and `goertzel.py`: every
   tone on its own bin, heard by the expected microphones.
4. **Step 3**: the five active cards, still at the Mega's pitches.
5. **Then** free the pitches within each card's window, and
   `next pcb` section 3's harness measurement with both card kinds.

**Changing a shield**: stop the piece from the page, unplug the rack
supply and the computing USB, change the shield, write the card or slot
in its silkscreen box, power both back up together.

---

## 11. Parts, rough

| | Qty | Rough |
|---|---|---|
| backplane | 1 | about v2's board cost |
| Teensy adapter | 1 | EUR 45–60 |
| MSGEQ7 shield | 1 | EUR 20–40 |
| Thomas cards | 5 | EUR 10–20 |
| active cards, assembled | 5 to 13 | EUR 3–6 each |

**The Teensy solution on its own** — adapter and five active cards — is
about **EUR 60–90**.

---

## 12. What is open

- The Teensy's conversion time, and so the sampling rate (7b).
- The continuous stream (7b).
- The MAX9814's highest output on a 5 V supply: the datasheet gives it at
  3.3 V. The 4.7 K makes it harmless either way; the measured swing on 5 V
  matches the 3.3 V figures.
- Heights against the enclosure (9).
- `next pcb` section 3's harness measurement and section 5's amplifier
  rail; nothing here depends on either.
- The photosensor loads, still v2's provisional 10 K.
