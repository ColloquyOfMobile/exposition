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
