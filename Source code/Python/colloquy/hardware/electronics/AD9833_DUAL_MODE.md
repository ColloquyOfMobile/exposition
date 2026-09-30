# AD9833, dual mode

**One set of boards that runs the piece two ways.** In **central mode**
it is the installation as it runs today: one Mega in the rack, the U2D2
on the servo bus, this repository's program driving everything over one
JSON-line link. In **distributed mode** it is close to TJ's own
arrangement: a Pro Mini in every body doing its own lights, sensors,
voice and ear, and an OpenCM 9.04 in the rack. Going from one to the
other is **plugging modules in or out and moving jumpers**: no board
spin, no soldering, no change to the harness.

Written 2026-09-30, after `sound options` compared five ways to make the
voices and the artist chose the AD9833. It is a fourth solution beside
`next pcb`, `one board per body` and `opencm and pro minis`, and it is
built out of them: central mode is `next pcb` with its filter bank
replaced, and distributed mode is `opencm and pro minis` with the voice
made the same way as in central mode. Read those three for anything this
one does not repeat.

**What is sourced and what is not.** Every conductor, pin and firmware
fact below is read out of this repository (`next pcb` section 5,
`harness`, `colloquy_of_mobiles.ino`, TJ's `logic35_systems`). What is
said about the AD9833, the OpenCM 9.04 and the RS-485 transceivers comes
from general knowledge of those parts and **has not been checked against
their datasheets or measured**. Every such figure is marked *check* where
it matters. `next pcb` section 5 is the reason this matters here: a
supply range copied into a document as a fact destroyed an amplifier on
2026-09-01.

---

## 0. The idea in one paragraph

The AD9833 is what makes two modes cheap. It is a signal generator that
takes a 16-bit command over SPI and then plays a sine, a triangle or a
square by itself at any frequency. Nothing about it cares whether the
processor sending that command is a Mega in the rack or a Pro Mini in a
body. So this design draws **one voice channel** (an AD9833 and a small
buffer) and places it twice: five in the rack for central mode, and one
in each body for distributed mode. Everything after the voice channel
(the divider, the amplifier, the loudspeaker) is the same in both modes,
because both put the same **2.5 Vpp line-level signal** on the same
node at the body.

---

## 1. The two modes at a glance

**Drawn.** The same boards and the same harness in both modes; only what is plugged in, and which way the shunts sit, differs. Solid boxes work in that mode, dashed ones are fitted or socketed and idle. One body board stands for all five.

<div style="overflow-x: auto; margin: 1rem 0;">
<svg viewBox="0 0 1300 895" role="img" aria-label="Block diagram of the AD9833 dual-mode design in its two modes. Central mode: the laptop's Python program talks over USB to the Mega in the rack and to the U2D2. The Mega drives five AD9833 voice channels over SPI; their line-level outputs pass the rack mode jumpers set to C and go down the unchanged DSUB harness to each body board, where the body jumpers set to C send them to the line-level node, the 22K/3K3 divider, the amplifier and the speaker. Each body's MAX9814 microphone goes back up the harness to five MSGEQ7s in the rack, read by the Mega on A0 to A4, and the NeoPixels and photosensors are driven from the Mega directly. The body's Pro Mini socket, voice channel and RS-485 transceiver are idle. Distributed mode: the laptop, optional in step D2, talks over USB to an OpenCM 9.04 in the rack; the Mega, the rack voice channels and the MSGEQ7s are idle. The OpenCM's RS-485 body bus passes the rack jumpers set to D and travels on the same line-out pair to each body, where the jumpers set to D route it to the body's RS-485 transceiver and Pro Mini. The Pro Mini drives its own voice channel into the same line-level node, divider, amplifier and speaker, reads the microphone on A7, and drives the NeoPixels and photosensors. The U2D2 masters the servos in step D1; in step D2 that lead moves to the OpenCM.">
<defs>
<marker id="dm-ax" viewBox="0 0 10 8" refX="9" refY="4" markerUnits="userSpaceOnUse" markerWidth="10" markerHeight="8" orient="auto"><polygon points="0,0 10,4 0,8" fill="currentColor"></polygon></marker>
</defs>
<!-- ================= CENTRAL MODE ================= -->
<g>
<text x="20" y="30" font-family="'IBM Plex Mono', monospace" font-size="12" font-weight="600" letter-spacing="1.4" fill="currentColor" opacity="0.7">CENTRAL MODE &#183; this program, as it runs today</text>
<!-- frames -->
<rect x="20" y="150" width="130" height="110" rx="4" fill="none" stroke="currentColor" stroke-width="1.8"></rect>
<rect x="190" y="50" width="460" height="342" rx="6" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.7"></rect>
<rect x="720" y="50" width="50" height="342" rx="3" fill="none" stroke="currentColor" stroke-width="1.2" stroke-dasharray="4 3" opacity="0.6"></rect>
<rect x="790" y="50" width="490" height="342" rx="6" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.7"></rect>
<g font-family="'IBM Plex Mono', monospace" font-size="10" font-weight="600" letter-spacing="1.2" fill="currentColor" opacity="0.55">
<text x="205" y="72">RACK BOARD</text>
<text x="805" y="72">BODY BOARD &#215; 5</text>
</g>
<g font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">
<text x="745" y="70">DSUB</text><text x="745" y="83">harness</text><text x="745" y="383">fixed</text>
</g>
<!-- wires (drawn before boxes) -->
<g fill="none" stroke="currentColor">
<path d="M150 175 H180 V140 H203" stroke-width="1.4" marker-end="url(#dm-ax)"></path>
<path d="M150 235 H180 V360 H203" stroke-width="1.4" marker-end="url(#dm-ax)"></path>
<path d="M335 120 H393" stroke-width="1.4" marker-end="url(#dm-ax)"></path>
<path d="M565 120 H583" stroke-width="2.4" marker-end="url(#dm-ax)"></path>
<path d="M635 120 H911" stroke-width="2.4"></path>
<path d="M919 120 H933" stroke-width="2.4" marker-end="url(#dm-ax)"></path>
<path d="M1025 120 H1043" stroke-width="2.4" marker-end="url(#dm-ax)"></path>
<path d="M1135 120 H1153" stroke-width="2.4" marker-end="url(#dm-ax)"></path>
<path d="M870 275 H567" stroke-width="2.4" marker-end="url(#dm-ax)"></path>
<path d="M395 275 H300 V192" stroke-width="1.4" marker-end="url(#dm-ax)"></path>
<path d="M870 320 H250 V190" stroke-width="1.4"></path>
<path d="M335 360 H1148" stroke-width="1.4" marker-end="url(#dm-ax)"></path>
<path d="M915 160 V124" stroke-width="1.4" stroke-dasharray="4 3" opacity="0.45"></path>
</g>
<circle cx="915" cy="120" r="4" fill="currentColor"></circle>
<!-- boxes: working -->
<g fill="none" stroke="currentColor" stroke-width="1.6">
<rect x="205" y="90" width="130" height="100" rx="3"></rect>
<rect x="401" y="89" width="170" height="50" rx="3" opacity="0.35"></rect>
<rect x="395" y="95" width="170" height="50" rx="3"></rect>
<rect x="585" y="95" width="50" height="50" rx="2"></rect>
<rect x="401" y="244" width="170" height="50" rx="3" opacity="0.35"></rect>
<rect x="395" y="250" width="170" height="50" rx="3"></rect>
<rect x="205" y="340" width="130" height="40" rx="3"></rect>
<rect x="805" y="95" width="40" height="245" rx="2"></rect>
<rect x="935" y="100" width="90" height="40" rx="3"></rect>
<rect x="1045" y="100" width="90" height="40" rx="3"></rect>
<rect x="1155" y="100" width="90" height="40" rx="3"></rect>
<rect x="870" y="260" width="100" height="30" rx="3"></rect>
<rect x="870" y="305" width="100" height="30" rx="3"></rect>
<rect x="1150" y="345" width="120" height="30" rx="3"></rect>
</g>
<!-- boxes: idle in this mode -->
<g fill="none" stroke="currentColor" stroke-width="1.4" stroke-dasharray="5 4" opacity="0.5">
<rect x="395" y="170" width="170" height="50" rx="3"></rect>
<rect x="880" y="160" width="110" height="40" rx="3"></rect>
<rect x="870" y="215" width="100" height="30" rx="3"></rect>
<rect x="1010" y="160" width="120" height="175" rx="3"></rect>
</g>
<!-- titles -->
<g font-family="Chivo, sans-serif" font-size="13" font-weight="600" fill="currentColor" text-anchor="middle">
<text x="85" y="192" font-size="15">Laptop</text>
<text x="270" y="134">Mega 2560</text>
<text x="480" y="117">5 &#215; voice channel</text>
<text x="610" y="127" font-size="18" font-weight="700">C</text>
<text x="480" y="272">5 &#215; MSGEQ7</text>
<text x="270" y="358">U2D2</text>
<text x="825" y="202" font-size="18" font-weight="700">C</text>
<text x="980" y="117" font-size="12.5">divider</text>
<text x="1090" y="117" font-size="12.5">amplifier</text>
<text x="1200" y="125" font-size="12.5">speaker</text>
<text x="920" y="279" font-size="12">MAX9814 mic</text>
<text x="1210" y="364" font-size="12">Dynamixel servo</text>
</g>
<g font-family="Chivo, sans-serif" font-size="12.5" font-weight="600" fill="currentColor" text-anchor="middle" opacity="0.6">
<text x="480" y="191">OpenCM + RS-485</text>
<text x="935" y="177" font-size="12">voice channel</text>
<text x="1070" y="240">Pro Mini socket</text>
</g>
<!-- small print -->
<g font-family="'IBM Plex Mono', monospace" font-size="10.5" fill="currentColor" opacity="0.62" text-anchor="middle">
<text x="85" y="212">Python program</text>
<text x="85" y="240">2 USB leads</text>
<text x="270" y="152">firmware 5</text>
<text x="270" y="168">JSON over USB</text>
<text x="480" y="134">AD9833 + buffer</text>
<text x="480" y="289">the ear, one band each</text>
<text x="270" y="373">servo bus</text>
<text x="980" y="132">22K / 3K3</text>
<text x="1090" y="132">+ 470 &#181;F</text>
<text x="920" y="324">pixels &#183; photos</text>
</g>
<g font-family="'IBM Plex Mono', monospace" font-size="10" fill="currentColor" opacity="0.5" text-anchor="middle">
<text x="480" y="208">empty in this mode</text>
<text x="935" y="192" font-size="9.5">AD9833 + buffer</text>
<text x="920" y="234">RS-485 &#183; idle</text>
<text x="1070" y="256">empty</text>
</g>
<!-- wire labels -->
<g font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.75" text-anchor="middle">
<text x="165" y="169">USB</text>
<text x="165" y="229">USB</text>
<text x="365" y="113">SPI</text>
<text x="365" y="134">+ 5 CS</text>
<text x="677" y="112">line out</text>
<text x="677" y="136">2.5 Vpp</text>
<text x="610" y="88">mode</text>
<text x="825" y="219">mode</text>
<text x="915" y="108">node</text>
<text x="677" y="268">mic</text>
<text x="345" y="268">A0&#8211;A4</text>
<text x="480" y="313">NeoPixels &#183; photosensors</text>
<text x="480" y="353">Dynamixel data</text>
<text x="870" y="386" text-anchor="start">+5 V &#183; +12 V &#183; GND on every cable</text>
</g>
</g>
<!-- ================= DISTRIBUTED MODE ================= -->
<g transform="translate(0,440)">
<text x="20" y="30" font-family="'IBM Plex Mono', monospace" font-size="12" font-weight="600" letter-spacing="1.4" fill="currentColor" opacity="0.7">DISTRIBUTED MODE &#183; a Pro Mini in every body, close to TJ's</text>
<rect x="20" y="150" width="130" height="110" rx="4" fill="none" stroke="currentColor" stroke-width="1.8"></rect>
<rect x="190" y="50" width="460" height="342" rx="6" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.7"></rect>
<rect x="720" y="50" width="50" height="342" rx="3" fill="none" stroke="currentColor" stroke-width="1.2" stroke-dasharray="4 3" opacity="0.6"></rect>
<rect x="790" y="50" width="490" height="342" rx="6" fill="none" stroke="currentColor" stroke-width="1.4" opacity="0.7"></rect>
<g font-family="'IBM Plex Mono', monospace" font-size="10" font-weight="600" letter-spacing="1.2" fill="currentColor" opacity="0.55">
<text x="205" y="72">RACK BOARD</text>
<text x="805" y="72">BODY BOARD &#215; 5</text>
</g>
<g font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.62" text-anchor="middle">
<text x="745" y="70">DSUB</text><text x="745" y="83">harness</text><text x="745" y="383">fixed</text>
</g>
<g fill="none" stroke="currentColor">
<path d="M150 205 H393" stroke-width="1.4" marker-end="url(#dm-ax)"></path>
<path d="M150 240 H180 V360 H203" stroke-width="1.4" marker-end="url(#dm-ax)"></path>
<path d="M565 195 H575 V120 H583" stroke-width="1.8" marker-end="url(#dm-ax)"></path>
<path d="M635 120 H812 V230 H868" stroke-width="1.8" marker-end="url(#dm-ax)"></path>
<path d="M970 230 H1010" stroke-width="1.8"></path>
<path d="M970 275 H1008" stroke-width="2.4" marker-end="url(#dm-ax)"></path>
<path d="M970 320 H1010" stroke-width="1.4"></path>
<path d="M1010 180 H992" stroke-width="1.4" marker-end="url(#dm-ax)"></path>
<path d="M915 160 V126" stroke-width="2.4" marker-end="url(#dm-ax)"></path>
<path d="M919 120 H933" stroke-width="2.4" marker-end="url(#dm-ax)"></path>
<path d="M1025 120 H1043" stroke-width="2.4" marker-end="url(#dm-ax)"></path>
<path d="M1135 120 H1153" stroke-width="2.4" marker-end="url(#dm-ax)"></path>
<path d="M335 360 H1148" stroke-width="1.4" marker-end="url(#dm-ax)"></path>
</g>
<circle cx="915" cy="120" r="4" fill="currentColor"></circle>
<g fill="none" stroke="currentColor" stroke-width="1.6">
<rect x="395" y="170" width="170" height="50" rx="3"></rect>
<rect x="585" y="95" width="50" height="50" rx="2"></rect>
<rect x="205" y="340" width="130" height="40" rx="3"></rect>
<rect x="805" y="95" width="40" height="245" rx="2"></rect>
<rect x="880" y="160" width="110" height="40" rx="3"></rect>
<rect x="870" y="215" width="100" height="30" rx="3"></rect>
<rect x="1010" y="160" width="120" height="175" rx="3"></rect>
<rect x="935" y="100" width="90" height="40" rx="3"></rect>
<rect x="1045" y="100" width="90" height="40" rx="3"></rect>
<rect x="1155" y="100" width="90" height="40" rx="3"></rect>
<rect x="870" y="260" width="100" height="30" rx="3"></rect>
<rect x="870" y="305" width="100" height="30" rx="3"></rect>
<rect x="1150" y="345" width="120" height="30" rx="3"></rect>
</g>
<g fill="none" stroke="currentColor" stroke-width="1.4" stroke-dasharray="5 4" opacity="0.5">
<rect x="205" y="90" width="130" height="100" rx="3"></rect>
<rect x="395" y="95" width="170" height="50" rx="3"></rect>
<rect x="395" y="250" width="170" height="50" rx="3"></rect>
</g>
<g font-family="Chivo, sans-serif" font-size="13" font-weight="600" fill="currentColor" text-anchor="middle">
<text x="85" y="192" font-size="15">Laptop</text>
<text x="480" y="192">OpenCM 9.04</text>
<text x="610" y="127" font-size="18" font-weight="700">D</text>
<text x="270" y="358">U2D2</text>
<text x="831" y="190" font-size="18" font-weight="700">D</text>
<text x="935" y="177" font-size="12">voice channel</text>
<text x="920" y="234" font-size="12">RS-485</text>
<text x="1070" y="206" font-size="14">Pro Mini</text>
<text x="980" y="117" font-size="12.5">divider</text>
<text x="1090" y="117" font-size="12.5">amplifier</text>
<text x="1200" y="125" font-size="12.5">speaker</text>
<text x="920" y="279" font-size="12">MAX9814 mic</text>
<text x="1210" y="364" font-size="12">Dynamixel servo</text>
</g>
<g font-family="Chivo, sans-serif" font-size="12.5" font-weight="600" fill="currentColor" text-anchor="middle" opacity="0.6">
<text x="270" y="134">Mega 2560</text>
<text x="480" y="117">5 &#215; voice channel</text>
<text x="480" y="272">5 &#215; MSGEQ7</text>
</g>
<g font-family="'IBM Plex Mono', monospace" font-size="10.5" fill="currentColor" opacity="0.62" text-anchor="middle">
<text x="85" y="212">Python program</text>
<text x="85" y="240">optional in D2</text>
<text x="480" y="209">+ RS-485 &#183; body bus</text>
<text x="270" y="373">D1 only</text>
<text x="935" y="192" font-size="9.5">AD9833 + buffer</text>
<text x="1070" y="224" font-size="9.5">one sketch, UNIT_ID</text>
<text x="1070" y="252" font-size="9.5">Goertzel ear on A7</text>
<text x="1070" y="268" font-size="9.5">optional MSGEQ7</text>
<text x="1070" y="296" font-size="9.5">lights, sensors,</text>
<text x="1070" y="310" font-size="9.5">voice, ear</text>
<text x="980" y="132">22K / 3K3</text>
<text x="1090" y="132">+ 470 &#181;F</text>
<text x="920" y="324">pixels &#183; photos</text>
</g>
<g font-family="'IBM Plex Mono', monospace" font-size="10" fill="currentColor" opacity="0.5" text-anchor="middle">
<text x="270" y="152">unplugged</text>
<text x="480" y="134">unused</text>
<text x="480" y="289">unused</text>
</g>
<g font-family="'IBM Plex Mono', monospace" font-size="9.5" fill="currentColor" opacity="0.75" text-anchor="middle">
<text x="165" y="198">USB</text>
<text x="165" y="234">USB</text>
<text x="677" y="112">RS-485</text>
<text x="677" y="136">same pair</text>
<text x="610" y="88">mode</text>
<text x="831" y="206">mode</text>
<text x="915" y="108">node</text>
<text x="1001" y="173">SPI</text>
<text x="480" y="353">Dynamixel data</text>
<text x="480" y="386">D2: this lead moves to the OpenCM</text>
<text x="870" y="386" text-anchor="start">+5 V &#183; +12 V &#183; GND on every cable</text>
</g>
</g>
<!-- ================= LEGEND ================= -->
<g font-family="'IBM Plex Mono', monospace" font-size="10.5" fill="currentColor" opacity="0.75">
<rect x="20" y="862" width="28" height="16" rx="2" fill="none" stroke="currentColor" stroke-width="1.6"></rect>
<text x="56" y="874">working in this mode</text>
<rect x="250" y="862" width="28" height="16" rx="2" fill="none" stroke="currentColor" stroke-width="1.4" stroke-dasharray="5 4" opacity="0.6"></rect>
<text x="286" y="874">fitted or socketed, idle in this mode</text>
<line x1="580" y1="870" x2="620" y2="870" stroke="currentColor" stroke-width="2.4"></line>
<text x="628" y="874">audio</text>
<line x1="700" y1="870" x2="740" y2="870" stroke="currentColor" stroke-width="1.8"></line>
<text x="748" y="874">RS-485 body bus</text>
<line x1="890" y1="870" x2="930" y2="870" stroke="currentColor" stroke-width="1.4"></line>
<text x="938" y="874">digital, sensors, servo data</text>
</g>
</svg>
</div>

| | Central mode | Distributed mode |
|---|---|---|
| program | this repository, unchanged in shape | Pro Mini sketch per body, OpenCM sketch in the rack |
| rack processor | Mega 2560 (plugged in) | OpenCM 9.04 (plugged in); Mega unplugged |
| servo bus master | U2D2 | U2D2 (step D1) or OpenCM (step D2) |
| voice | 5 rack voice channels, line level down the harness | the body's own voice channel |
| ear | 5 MSGEQ7s in the rack, as today | on the body's Pro Mini: Goertzel, or an optional MSGEQ7 |
| lights and sensors | driven from the rack, as today | driven by the body's Pro Mini |
| the line-out pair | carries audio | carries RS-485 |
| harness | unchanged | unchanged |
| distance from TJ (0 to 5) | 2 | about 1 |

**Distributed mode comes in two steps**, and the first is worth having
on its own:

- **D1: bodies distributed, servos unchanged.** The OpenCM only bridges
  the RS-485 body bus to USB; the U2D2 still masters the servos and
  `drivers/u2d2/` does not change. This is `one board per body` with the
  OpenCM as its bridge.
- **D2: the OpenCM masters the servos too.** The U2D2 comes out, one USB
  lead leaves the rack, and a stop that does not need the PC becomes
  possible. This is `opencm and pro minis`.

---

## 2. The voice channel

Drawn once, placed ten times: five in the rack, and one in each body. It turns an SPI command into the 2.5 Vpp line level that
`next pcb` section 3 already sends down the harness, so nothing
downstream has to change.

| Part | Value | Note |
|---|---|---|
| AD9833 module | breakout with its own 25 MHz oscillator | *check* the oscillator frequency on the module actually bought; every frequency word depends on it |
| coupling capacitor | 1 µF film | the module output sits on a DC offset of roughly 0.3 V (*check*) |
| buffer | one op-amp section, non-inverting, gain about 4, biased at mid-rail | rail-to-rail input and output on a single 5 V supply, MCP6002/MCP6004 class |
| reconstruction low-pass | second order, corner about 20 kHz, in the buffer's feedback | smooths the DAC's steps; far above every pitch, so it shapes nothing audible |
| build-out resistor | 100 R in series with the output | as `next pcb` section 2: limits the current into a shorted cable and damps its capacitance |

**Why a gain of 4.** The module gives roughly 0.6 Vpp (*check*), and the
harness signal, the body divider (22K/3K3) and the amplifier setting are
all already specified for 2.5 Vpp. Matching that level keeps the whole
body end of `next pcb` valid in both modes. It is also the largest
signal a 5 V buffer can put on a cable full of NeoPixel edges, which is
why `next pcb` chose it.

**Frequency.** A 28-bit word against a 25 MHz clock gives steps of about
0.09 Hz (*check*). Any pitch in the audible range is available, set per
channel, and changing it is one SPI write.

**Silence.** The chip's `RESET` bit holds the output at mid-scale, which
is silence without a click. The sleep bits stop the clock or power down
the DAC. Firmware uses `RESET` for "off"; it is also what
`speakers/off` sends to all five at once.

**Waveform, and TJ's buzz.** The AD9833 can put out a sine, a triangle,
or a square taken from the top bit of its phase (*check* the square's
amplitude: it is at logic level, not 0.6 Vpp). A square through this
buffer clips at the rails: that is TJ's sound, a buzz rather than a
note. **Sine is the default in both modes; square is a setting**, so the
choice `one board per body` section 4 hands to the artist stays a
setting and never becomes a soldering job.

**The chip is write-only.** It cannot report what frequency it is
playing. Two consequences, both cheap: the firmware writes the whole
frequency word again every time a tone starts rather than trusting it
from last time, and a new `test_*` that listens for the pitch it asked
for is the only way to confirm it (the existing loop tests already do
this per band).

---

## 3. The rack board

Start from the v2 KiCad project
(`CAD/KiCad/electronic box v2/colloquy-control-v2/`, not yet committed on
2026-09-30), which is `next pcb` drawn out in full. Three changes.

### 3a. Five voice channels replace the five filters

The passive two-stage filters and the Mega tone pins that fed them go.
In their place, five voice channels:

| Signal | Mega pin | Note |
|---|---|---|
| SCLK, all five | **D52** | hardware SPI; free in firmware 4 |
| SDATA, all five | **D51** | hardware SPI; free in firmware 4 |
| FSYNC, male1 | **D11** | was male1's 160 Hz tone |
| FSYNC, male2 | **D5** | was male2's 400 Hz tone |
| FSYNC, female1 | **D6** | was female1's 1 kHz tone |
| FSYNC, female2 | **D46** | was female2's 2.5 kHz tone |
| FSYNC, female3 | **D10** | was female3's 6.25 kHz tone |
| (keep as an output) | **D53** | the Mega's SS pin must be an output or its SPI drops out of master mode |

**Each body keeps its pin.** The five tone pins become the five chip
selects in the same order, so the body-to-pin row of `drivers/audio.py`
survives and only the pitch column stops being fixed. Nothing about the
NeoPixel pins that moved to D14 to D17 is reopened.

**What stays.** The five MSGEQ7s, their support network (now complete in
the v2 project's `CIRCUIT_NOTES.md`), the commoned strobe and reset,
`A0` to `A4`, the photosensor dividers, the Mega and U2D2 mounts, both
power rails kept separate, and every connector position.

### 3b. The OpenCM and the body bus

For distributed mode the rack board also carries, unpopulated in central
mode or simply unused:

| Part | Note |
|---|---|
| OpenCM 9.04 mount | on headers, so it plugs in and out like the Mega; *check* which variant carries the Dynamixel TTL connectors |
| RS-485 transceiver, 3.3 V class (MAX3485 type) | on one of the OpenCM's spare serial ports, with one GPIO for driver enable |
| fail-safe bias | pull-up on A, pull-down on B, about 680 R each, so an idle bus reads as a defined state |
| no termination | see section 5 for why a star of short cables does not need it |

### 3c. The mode jumpers

One block of 2.54 mm shunt headers at the rack, silkscreened **C** and
**D**, one row per body:

| Row | C position | D position |
|---|---|---|
| `<body>/line out` | voice channel output | RS-485 **A** |
| `<body>/audio return` | AGND | RS-485 **B** |

**Jumpers rather than a switch chip, on purpose.** A shunt is visible
from across the room, cannot be set wrong by software, and cannot fail
half-way. A mode is changed a few times a year, by hand, at the rack.

**The servo lead is a cable swap, not a jumper.** `J7` (GND / 12 V /
Dynamixel data) goes to the U2D2 in central mode and D1, and to the
OpenCM's Dynamixel port in D2. **Check before the first D2 power-up**:
an OpenCM's Dynamixel ports are tied to its own supply input, and `J7`
carries 12 V. A lead with only GND and data, or the OpenCM's own
supply rating confirmed against 12 V, before anything is plugged in.

---

## 4. The body board

Replaces the `female base` and `male static` breakouts, on their
outlines (50 x 80 and 50 x 90 mm) and **with their JST pinouts
unchanged**, so everything inside a body plugs in exactly as now. In
central mode it is `next pcb` section 3's body assembly; in distributed
mode it is `one board per body` section 4's.

| Part | Central mode | Distributed mode |
|---|---|---|
| amplifier module + 470 µF | fitted | fitted |
| 22K / 3K3 divider at the amplifier input | fitted | fitted |
| MAX9814 microphone | fitted | fitted |
| Pro Mini, 5 V / 16 MHz, on sockets | **empty** | fitted |
| voice channel (AD9833 + buffer) | may be fitted, unused | used |
| RS-485 transceiver, 5 V class (MAX485 type) | may be fitted, disabled by jumper | used |
| MSGEQ7 in a DIP-8 socket, with its support network | empty | **optional**, for TJ's own ear |
| anti-alias RC before the microphone ADC pin | fitted | used |

**One node, two sources.** The divider's top end is the body's
line-level node, and a jumper feeds it from either the harness line-out
conductor (C) or the local voice channel (D). Both are 2.5 Vpp, so the
amplifier, its volume setting and its divider are identical in both
modes and are set once at commissioning.

### The body mode jumpers

One 3-pin shunt header per signal, **harness | JST | Pro Mini**. The
shunt joins the JST pin to the harness conductor in C, and to the Pro
Mini pin in D. In D the harness side is left open at both ends.

| Signal | Female | Male |
|---|---|---|
| amplifier input node | harness line out, or local voice | same |
| line-out pair | to the node and AGND, or to the transceiver A/B | same |
| microphone | harness, or `A7` | same |
| photosensor(s) | harness, or `A0` | harness, or `A0` to `A3` (a, b, c, d) |
| body NeoPixel | harness, or `D6` | harness, or `D6` |
| bar NeoPixel (up-ring) | none | harness, or `D7` |
| state LED | none | harness, or `D5` |

### The Pro Mini's pins, in distributed mode

| Pin | Use | Note |
|---|---|---|
| `D0`, `D1` | RS-485 RO, DI | RO through **1 K**, so an FTDI adapter on the programming header overrides it without lifting a part |
| `D2` | RS-485 DE and /RE together | |
| `D4` | amplifier shutdown | the mute `next pcb` section 4 could not deliver to all five bodies; here each body has its own |
| `D5` | state LED | male only |
| `D6` | body NeoPixel | |
| `D7` | bar NeoPixel | male only |
| `D8`, `D9`, `A6` | MSGEQ7 strobe, reset, output | only if the optional MSGEQ7 is fitted |
| `D10`, `D11`, `D13` | AD9833 FSYNC, SDATA, SCLK | hardware SPI |
| `A0` to `A3` | photosensors | a female uses `A0` |
| `A7` | microphone | analogue-only pin, as TJ used `A6`/`A7` |
| `D3`, `D12`, `A4`, `A5` | spare | `A4`/`A5` are I2C if ever wanted |

**The FTDI header goes somewhere a hand can reach** without taking the
body apart. That is a mechanical question per body and it is the one
that decides how painful five firmwares are (`one board per body`
section 8).

---

## 5. What the harness carries in each mode

No conductor is added or moved. The conductor numbers are `next pcb`
section 5's, read out of the netlist.

| Body | Line out | Audio return | Microphone | Central mode | Distributed mode |
|---|---|---|---|---|---|
| female1 | `J5` 12 | `J5` 4 | `J5` 6 | as `next pcb` | RS-485 on 12/4; mic, photo, pixel conductors open |
| female2 | `J1` 12 | `J1` 4 | `J1` 6 | as `next pcb` | RS-485 on 12/4 |
| female3 | `A-J3` 12 | `A-J3` 5 | `A-J3` 3 | as `next pcb` | RS-485 on 12/5 |
| male1 | `B-J4` 9 | `B-J4` 2 | `A-J3` 13 | as `next pcb` | RS-485 on 9/2 |
| male2 | `B-J4` 6 | `B-J4` 14 | `B-J4` 10 | as `next pcb` | RS-485 on 6/14 |

**Every body already has exactly one pair that carries nothing but its
voice**, and a pair is what RS-485 needs. So distributed mode puts the
body bus on the one conductor pair central mode uses for audio, and
never needs a spare. That matters most for female3 and male1, which have
none.

**In distributed mode each body needs five things**: GND, +5 V, +12 V,
servo data, and the pair. Everything else on its cable is left open at
both ends by the jumpers.

**A star, not a bus, and at this speed it does not matter.** RS-485 is
normally one cable daisy-chained past every node and terminated at both
ends; here each body has its own cable back to the rack. At 115200 baud
a bit lasts about 8.7 µs, while a few metres of cable is tens of
nanoseconds of travel, so reflections have died long before the receiver
samples. Hence bias resistors and no termination. **This is the one
number to measure before trusting it**: scope an edge at the farthest
body, with its NeoPixels running.

**Power is unchanged, and still the thing to measure.** female3, male1
and male2 still share `A-J3` pin 9 for +5 V (`next pcb` section 5). A
Pro Mini, a transceiver and an AD9833 add a few tens of milliamps a body,
which is small beside a NeoPixel strip, but it lands on the conductor
that is already the tightest.

---

## 6. Hearing, and what "any pitch" means in each mode

**Central mode frees the pitch within its band, not across the whole
spectrum.** The ear is still five MSGEQ7s, and the loop tests decide who
spoke by which band rose. So each body may take any pitch **inside its
own analyser band**, and `drivers/audio.py` should refuse one that
leaves it. That is still a real gain: the filters that fixed each pitch
to one frequency are gone, glides and small changes are free, and a sine
puts no harmonics into a neighbour's band.

**Distributed mode frees it completely.** The body's Pro Mini listens
with Goertzel bins (`one board per body` section 4), and a bin can be
centred on any frequency. That is the arrangement where "any pitch,
chosen freely" is fully true, with one rule kept from section 4 there:
**choose the five so that no pitch's harmonics land on another's bin**
(160 Hz x 3 = 480 Hz next to 400 Hz is the example it walks through).

**The optional MSGEQ7 on the body board is TJ's ear given back**, for
anybody who wants the distributed mode to be his arrangement rather than
an improvement on it. It is a socket and a handful of passives, and the
circuit is the one the v2 project already drew.

**Still to measure in distributed mode**, and named in
`opencm and pro minis` section 2: whether a Pro Mini can sample its
microphone while it writes a NeoPixel strip. The body's own processor
can simply not listen while it writes light; whether that loses too much
is a measurement on `Source code/Arduino/goertzel_ear/` with a strip on
the same board.

---

## 7. Software in each mode

### Central mode: the program as it is

- **Firmware 5** on the Mega: an AD9833 driver in the sketch (SPI at a
  modest clock, the five chip selects above), `<body>/speaker` taking
  `{"on": 0|1, "hz": ...}`, and `speakers/off` resetting all five. The
  hardware timers retire. A version bump, because a driver judging a
  firmware-4 board by firmware-5 rules gets every verdict wrong while a
  tone still comes out.
- **`drivers/audio.py`**: the pitch column becomes a default per body
  plus a `params.json` setting, validated against the body's band. The
  body, pin and module columns stay.
- **Everything else unchanged**: `sing`, `hearing`, `reinforcement`, the
  audio tests, `flash firmware`, the page. The U2D2 and `drivers/u2d2/`
  are untouched.

### D1: bodies distributed, servos unchanged

- **A Pro Mini sketch**, one source with `UNIT_ID` set at compile time
  as TJ's was, answering the same paths the Mega answers today (`f1/head`,
  `m2/light sensor/a`, `<body>/speaker`) over RS-485.
- **An OpenCM sketch** that bridges USB JSON lines to the body bus,
  keeping the driver's `send(path, **data)` and its greeting. So
  `drivers/arduino/` keeps its shape and points at a different port.
- **The program itself does not change** as long as those paths are
  answered. This is the point of D1: the Python behaviour drives the
  distributed hardware before anything is moved down into it.
- **Flashing**: six boards instead of one. The flasher's shape
  (`flasher/base.py`) already takes any sketch on any lead; a Pro Mini
  needs an FTDI adapter per flash until a bus bootloader exists.

### D2: the OpenCM masters the servos

- The OpenCM sketch adds the Dynamixel bus (`Dynamixel2Arduino`, as TJ's
  six OpenCM sketches did), and `drivers/u2d2/` is replaced by commands
  over the same JSON link. **This is the largest piece of new software in
  the whole design**, and D1 can run for as long as it takes.
- It is also where TJ's autonomy can come back: the bar's wander rule
  was his (`opencm and pro minis` section 4), and a controller holding a
  deadman can cut torque when the PC stops answering.

---

## 8. How close distributed mode gets to TJ

| TJ's original | Distributed mode here |
|---|---|
| a Pro Mini in each body, one sketch with `UNIT_ID` | the same |
| `tone()` square on `D9` | AD9833, sine or square, any pitch |
| amplifier enable on `D11` | amplifier shutdown on `D4` |
| an MSGEQ7 in each body, band 4 only | Goertzel, or the optional MSGEQ7 |
| four light sensors on the unit | the body's photosensors, as wired today |
| six OpenCMs, one bus each | one OpenCM, one bus (D2), because this harness has one servo line |
| Pro Mini to OpenCM over a few GPIO lines | over the RS-485 pair |
| runs with no PC | possible in D2, not required |

**Distance: about 1 on the scale `sound options` uses.** The body is
his, down to the processor and the pin that is analogue-only. What
differs is where the servos are mastered, how the processors talk, and
a cleaner voice than his by default, with his buzz one setting away.

---

## 9. Changing mode

**Central to distributed:**

1. Stop the piece from the page, `hardware > motors > unplug the motors`
   if the servo lead will move (D2), and power down.
2. At the rack: unplug the Mega (and the U2D2 for D2), plug in the
   OpenCM, move every row of the rack mode block to **D**, move the `J7`
   lead if going to D2.
3. At each body: fit the Pro Mini, move every shunt to **D**.
4. Power up with a current-limited supply, and check each body answers
   on the bus before powering the servos.

**Distributed to central** is the same list backwards. Nothing is
soldered in either direction.

**What a mismatch does.** A body left in C while the rack is in D puts
the RS-485 signal (a few volts of square wave at 115200 baud) into the
divider and out of the speaker as a loud buzz; the reverse puts line
audio into a transceiver that reads it as garbage. **Neither should
damage anything at these levels (*check* against the transceiver's
common-mode range), and both are obvious within a second.** A body with
some shunts in C and some in D is the one that would be hard to find,
which is why every body has one block of shunts in one place, all in one
column when correct.

---

## 10. Trying it on today's box first

The first question, whether an AD9833 sounds right in the room, needs
none of the above. On the installation as it stands:

1. Wire one AD9833 module to the Mega: `D52` SCLK, `D51` SDATA, one tone
   pin as FSYNC (disconnect that pin from Thomas's filter input).
2. Take its output through a 1 µF capacitor into that channel's 22K/3K3
   divider, **bypassing the filter**. At 0.6 Vpp without the buffer it
   will be quieter than a 2.5 Vpp line; that is the gain stage's job on
   the real board.
3. A throwaway sketch that sets a frequency and toggles `RESET`, or a
   firmware 5 branch.

One channel is enough to hear the difference a sine makes, and to check
the module's clock frequency and output level before six more are
bought.

---

## 11. Cost, rough

Hobby-retail figures for 2026, to be checked before ordering.

| | Per unit | Total |
|---|---|---|
| rack: 5 voice channels (modules, op-amps, passives) | about 5 to 10 EUR | 25 to 50 EUR |
| rack: OpenCM 9.04 + transceiver + bias | about 25 to 35 EUR | 25 to 35 EUR |
| body board parts (Pro Mini, voice channel, transceiver, sockets, headers) | about 15 to 25 EUR | 75 to 125 EUR |
| optional MSGEQ7 per body | about 5 to 10 EUR | 25 to 50 EUR |
| amplifiers, microphones, speakers | as `next pcb` | as `next pcb` |

**Central mode alone costs the rack voice channels and nothing else**;
the body boards can be built with their Pro Mini sockets empty and the
distributed parts bought later.

---

## 12. What is open

- **The part checks** marked *check* above: the AD9833 module's clock,
  output level and square amplitude; the OpenCM variant, its supply range
  and what its Dynamixel ports do with 12 V; the transceivers'
  common-mode range.
- **The RS-485 star at 115200 baud**, measured at the farthest body with
  its NeoPixels running (section 5).
- **The line level down a full-length cable**, the measurement
  `next pcb` section 3 has always asked for. Central mode still depends
  on it; distributed mode does not.
- **Sampling while writing NeoPixels** on a Pro Mini (section 6).
- **The amplifier module and its rail**, still open as in `next pcb`
  section 5. The body board carries whatever is chosen; nothing here
  depends on the rail.
- **The body-bus protocol**: addressing, a reply, a timeout, what the
  OpenCM does when a body does not answer (`one board per body`
  section 8).
- **Where the FTDI header goes** in each body.
- **Which pitches**, now that neither the timers nor the filters fix
  them: within their bands in central mode, and chosen against each
  other's harmonics in distributed mode.
