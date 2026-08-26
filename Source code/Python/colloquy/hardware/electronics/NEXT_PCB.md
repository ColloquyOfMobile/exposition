# The next PCB

**What the board that replaces the one in the rack should do.** Written
while the dirty rework was being planned, so that the rework is a
prototype of this rather than a detour — every pin it moves, this keeps.

The decision already taken: **absorb Thomas's filter board and analyser
array onto the main PCB.** One board, no daughterboards, no patch wires.
More work to lay out, and much less to assemble and much less to go wrong
in a gallery three months from now.

Read `as built` for what exists and `dirty rework` for what is being
proved before this is committed to.

---

## 1. Keep the pinout exactly

The rework's pinout is not a compromise to be tidied up later — it is the
only one the silicon allows, and it is the one Thomas's own firmware
already uses. Copy it.

| Signal | Pin | Why it cannot move |
|---|---|---|
| female1 tone, 160 Hz | **D11** | `OC1A`, the only pin timer 1 can toggle |
| female2 tone, 400 Hz | **D5** | `OC3A` |
| female3 tone, 1 kHz | **D6** | `OC4A` |
| male1 tone, 2.5 kHz | **D46** | `OC5A` |
| male2 tone, 6.25 kHz | **D10** | `OC2A` |
| analyser STROBE | **D4** | free choice, but keep it |
| analyser RESET | **D3** | free choice, but keep it |
| analyser modules 0–4 | **A0–A4** | body order, and the reason module N is body N |
| female light sensors | **A5–A7** | unchanged |
| male light sensors | **A8–A15** | unchanged |
| NeoPixels ×7 | **D7, D8, D9, D14, D15, D16, D17** | any pins; these are the ones the rework used |

Three pins have a claim on them that is easy to miss:

- **D0 and D1** are the USB link to the driver. Nothing else, ever.
- **D13** is the Mega's own LED, blinked by the bootloader at every reset.
  Do not put audio, or anything else that minds a pulse train at power-on,
  on it. The current board put female3's amplifier there.
- **D20 and D21** are the same silicon pins as the dedicated SCL and SDA
  pads. Using one as GPIO drives the other net too. Either drop one pair
  or accept it deliberately.

**Tidying the NeoPixels is the one free choice here.** Seven bit-banged
lines can go anywhere; putting them on a contiguous run (D14–D20, or a
block in the D30s) makes the sketch's pin block read as one thing. Only
do it if the layout wants it — it costs a firmware edit and buys nothing
else.

---

## 2. Absorb the two boards

### The filter board

Five identical passive second-order low-passes, `R1 = R2` and `C1 = C2`
per stage, which is what makes Thomas's board look as regular as it does:

| Channel | R1 = R2 | C1 = C2 |
|---|---|---|
| 6250 Hz | 2K2 | 10 nF |
| 2500 Hz | 1K8 | 47 nF |
| 1000 Hz | 1K2 | 150 nF |
| 400 Hz | 2K | 220 nF |
| 160 Hz | 2K2 | 470 nF |

Twenty passives, no power, no silicon. Measured result: first harmonic
damped by more than 20 dB, under 10% of the fundamental.

**Silkscreen each channel with its frequency, and put the Mega pin
number next to it.** The one fault this whole design cannot detect is a
tone in the wrong filter channel — a low-pass passes anything below its
corner, so the tone still comes out, still lands in the right analyser
band and still reports "heard"; what is lost is the filtering, and the
symptom appears months later as poor detection in a noisy room. On a
board where the track goes from D11 to the 160 Hz stage and nowhere else,
that fault becomes impossible rather than merely unlikely. **That alone
is worth the layout.**

### The analyser array

Five MSGEQ7s, strobe and reset commoned, one microphone input each, five
outputs to A0–A4. Straightforward, and again: silkscreen module 0 as
`female1`, 1 as `female2`, 2 as `female3`, 3 as `male1`, 4 as `male2`,
because that mapping is the whole reason one number identifies a body
round the entire loop.

### The dividers

Five 22K/3K3 dividers between filter output and amplifier input, sized
for the amplifier's maximum input **with its volume control at maximum**.
Keep them as footprints even if the amplifier ends up being one with its
own attenuator — a clipped amplifier is a square wave again, and the
divider is two resistors.

---

## 3. The one thing to decide before laying it out

**Where does the amplifier live?**

The current board puts all five in the box and sends the amplified output
down a DSUB cable to the body. Thomas's note is the opposite: *mount the
amplifier close to its loudspeaker and keep the speaker wires short*,
because a class-D output is differential PWM at about 250 kHz with sharp
edges, high currents and real EMI — travelling, on this board, alongside
a Dynamixel data line and a NeoPixel line in the same cable.

**The existing harness can already do it the other way.** Every body's
DSUB carries +5 V, +12 V and GND, and each has a `speaker +/out` and a
`speaker −/out` conductor. A remote amplifier at the body needs power
(there), ground (there) and *one* line-level signal — which
`speaker +/out` can carry, leaving `speaker −/out` spare. No new cable,
no new connector, no change to the DSUB pinout: the same wires carrying
something quieter.

Three ways to go, in the order they should be considered:

1. **Amplifier at the body, line level down the harness.** Thomas's
   advice, and the harness already supports it. The box gets quieter and
   the cable stops radiating. Cost: five modules to mount in five bodies,
   and five things to reach when one fails.
2. **Amplifier in the box, as now.** Everything serviceable in one place.
   Cost: the EMI, and it is the arrangement whose author advises against
   it.
3. **Footprints for both, populate one.** Two resistors and a jumper per
   channel. Cheap on a board being laid out from scratch, and it makes
   the question answerable by listening rather than by argument.

**The dirty rework does not settle this**, because it uses Thomas's own
GF1002s next to his own bench speakers — which is arrangement 1 with a
very short cable. Getting the speakers back into the bodies is the step
that asks the question properly, and it should be asked before this board
is laid out.

Also worth deciding at the same time: **a mute line.** The current
amplifiers have `set` strapped permanently high, so nothing can silence
one from software. It is no longer needed for the reason TJ needed it —
hardware timers do not tear when NeoPixel writes disable interrupts
(CODE_DOCUMENTATION 9.13) — but one GPIO commoned to all five shutdown
pins would let an emergency stop actually make the room silent rather
than merely stop asking for tones.

---

## 4. Smaller things the current board got wrong or left out

- **`J11` and `J12` are unlabelled break points.** Each row is two nets
  joined by whatever is fitted across it, and nothing on the board or in
  the files says whether that should be a shunt or a resistor. Silkscreen
  it. Better: if it is a divider resistor, give it a proper footprint and
  a value.
- **The two state LEDs are wired and unused.** D24 and D25 drive them
  through a 10K, a jumper header, a BC557 and a 150R, and no firmware has
  ever written to either. Either use them or leave them off — but do not
  carry four passives per male for a feature nobody has asked for.
- **Only female1 and female2 have spare conductors** (six each, on
  `Extra1` and `Extra2`). female3, male1 and male2 have none. Give every
  body the same two or three spares; the next thing that needs a wire
  will not be politely limited to the two bodies that have one.
- **No test points on the audio path.** Five `<body>/audio` nets, five
  filter outputs, five amplifier inputs, and the speaker pairs are the
  only thing with a test point. Put a pad on each filter output: that is
  the single measurement that tells you whether a body's voice is right
  before it leaves the box.
- **The Mega's 5 V and the board's +5 V are separate nets** and that is
  correct — the amplifiers and NeoPixels should not be drawing through
  the Mega's regulator. Keep it, and mark on the silkscreen which is
  which, because `J9` 35 looks exactly like a convenient 5 V rail.

---

## 5. What is still open above the board

None of this is the sound *channel*, only the hardware it would run on.
CODE_DOCUMENTATION section 9 has the rest, and three of its questions bear
on the layout:

- **Where the bit clock lives.** The light channel puts it in Python:
  `Blink` writes one ring command per bit over a serial round trip, which
  is comfortable at 200 ms a bit. The receive side cannot work that way —
  TJ sampled every 50 ms and read his analyser sixteen times per sample.
  Either the sketch grows the pattern layer, or the sampling gets coarse
  enough to survive the link. **This does not change the board**, which
  is worth knowing: it can be laid out before that is settled.
- **How a tone is sampled.** The MSGEQ7's internal scan catches
  individual points on the waveform of the two lowest tones, so Thomas
  reads four times in quick succession at 160 Hz and twice at 400.
  Firmware, not layout.
- **Hearing in a gallery.** A fixed absolute threshold is already the
  weakest part of the light side, and a microphone in a room full of
  visitors is worse. The MAX9814's AGC is the headroom that makes it
  survivable; its `Gain` and `A/R` straps are Thomas's bench results and
  he says to re-check both in the field. **Bring both straps out to a
  jumper on the module carrier** rather than soldering them, so the field
  check is a jumper move and not a rework.
