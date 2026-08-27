# The next PCB

**What the board that replaces the one in the rack should do.** Written
while the dirty rework was being planned, so that the rework is a
prototype of this rather than a detour — every pin it moves, this keeps.

Two decisions are now taken, and everything below follows from them:

1. **Absorb Thomas's filter board and analyser array onto the main PCB.**
   One board, no daughterboards, no patch wires. More work to lay out,
   and much less to assemble and much less to go wrong in a gallery three
   months from now.
2. **The amplifier moves to the body.** The board sends line level down
   the harness and the amplifier sits next to its loudspeaker. This was
   section 3's open question in the previous draft; it is answered below,
   and it is the change with the widest reach — it is why the body
   connectors are redrawn.

Read `as built` for what exists and `dirty rework` for what is being
proved before this is committed to.

---

## 1. Keep the pinout exactly

The rework's pinout is not a compromise to be tidied up later — it is the
only one the silicon allows, and it is the one Thomas's own firmware
already uses. Copy it.

**The acceptance test for the pinout is that one sketch runs on both
boards.** Firmware 3 should run unmodified on the reworked board and on
this one, so that swapping the board is swapping the board and nothing
else. That is a better reason to keep the NeoPixel pins where the rework
put them than tidiness is to move them — see the note at the end of this
section.

| Signal | Pin | Why it cannot move |
|---|---|---|
| female1 tone, 160 Hz | **D11** | `OC1A`, the only pin timer 1 can toggle |
| female2 tone, 400 Hz | **D5** | `OC3A` |
| female3 tone, 1 kHz | **D6** | `OC4A` |
| male1 tone, 2.5 kHz | **D46** | `OC5A` |
| male2 tone, 6.25 kHz | **D10** | `OC2A` |
| amplifier shutdown | **D2** | new, and free; see section 4 |
| analyser RESET | **D3** | free choice, but keep it |
| analyser STROBE | **D4** | free choice, but keep it |
| analyser modules 0–4 | **A0–A4** | body order, and the reason module N is body N |
| female light sensors | **A5–A7** | unchanged |
| male light sensors | **A8–A15** | unchanged |
| NeoPixels ×7 | **D7, D8, D9, D14, D15, D16, D17** | any pins; these are the ones the rework used |

**D2, D3 and D4 are now the audio control block** — mute, reset, strobe,
three pins in a row, none of them fixed by silicon and all three worth
keeping together so the silkscreen can say so in one place.

Three pins have a claim on them that is easy to miss:

- **D0 and D1** are the USB link to the driver. Nothing else, ever.
- **D13** is the Mega's own LED, blinked by the bootloader at every reset.
  Do not put audio, or anything else that minds a pulse train at power-on,
  on it. The current board put female3's amplifier there; no audio pin on
  this board is D13, so that fault is designed out rather than avoided.
- **D20 and D21** are the same silicon pins as the dedicated SCL and SDA
  pads. Using one as GPIO drives the other net too. Either drop one pair
  or accept it deliberately.

**Do not tidy the NeoPixels.** Seven bit-banged lines could go anywhere,
and a contiguous run would make the sketch's pin block read as one thing
— but it would also mean the reworked board and this one need different
firmware, during exactly the weeks when both exist and either might be in
the rack. The tidying is worth less than the interchangeability.

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

**The microphone rows stop being break points.** On the current board the
analyser goes *into* the gap at `J11`, because there was no analyser when
`J11` was drawn (`as built` section 2). Here the analyser is between the
connector and the ADC by design: body microphone in, module in, `A0–A4`
out, nothing to fit across and nothing to pull out.

### The dividers

**They move to the body with the amplifier** — see section 3. The board
keeps one **build-out resistor** per channel in series with the line out
instead: 100 R, or a link if it turns out not to be wanted. It costs
nothing, it limits the current if a body cable shorts the filter output
to ground, and it damps whatever the cable capacitance does.

---

## 3. The amplifier lives at the body

**Decided.** This is Thomas's advice — *mount the amplifier close to its
loudspeaker and keep the speaker wires short* — and the reason is that a
class-D output is differential PWM at about 250 kHz with sharp edges,
high currents and real EMI, which on the current board travels the whole
length of a DSUB cable alongside a Dynamixel data line and a NeoPixel
line.

**What the harness carries instead.** A filtered sine at roughly 2.5 Vpp
— the fundamental of a 5 V square wave, through the low-pass, at the
corner. That is hot line level, and deliberately so: it is the largest
signal available, which is what makes it survive a cable full of NeoPixel
switching edges.

**Which is why the divider goes at the body and not on the board.** The
22K/3K3 divider drops that to about 0.33 Vpp for the amplifier input with
the module's volume at maximum. Put it at the board and the harness
carries a third of a volt past a Dynamixel line for several metres; put
it at the amplifier and the harness carries the full 2.5 V and the
attenuation happens where nothing can be injected after it. Same two
resistors, eight times the noise margin.

### What each body gains

Five identical small assemblies, alongside the MAX9814 the rework already
puts there:

| Part | Note |
|---|---|
| amplifier module | class-D, `SHUTDOWN`/`set` **brought out**, not strapped |
| 22K / 3K3 divider | at the amplifier input, sized for volume at maximum |
| 470 µF reservoir | across the amplifier's +5 V and GND, **at the module** |
| loudspeaker | short leads, in the body, as now |
| MAX9814 module | from `dirty rework` section 5 |

The reservoir is not optional. A class-D amplifier at the end of several
metres of thin conductor is a load with real peaks and no local energy
behind it; without a capacitor at the module its supply sags on every
transient and takes the NeoPixels on that cable with it.

**This does not reopen "one board, no daughterboards".** That decision
was about the box — the filter board and the analyser array stop being
separate PCBs in the rack. Modules in a body are the other side of a
cable, and they were always going to be there: the loudspeaker and the
MAX9814 already are.

### What it costs

**The volume controls leave the box.** Five pots on the front of the rack
become five pots inside five bodies, and setting a level means reaching
into the piece. Set them once at commissioning, with the divider chosen
so that "volume at maximum" is a safe place to leave one, and treat the
level as a calibration rather than a control.

### What the rework can still prove, cheaply

The dirty rework runs Thomas's GF1002s next to his own bench speakers,
which is this arrangement with a very short cable. **The one thing it has
not shown is that 2.5 Vpp survives the real harness** — several metres of
DSUB shared with a NeoPixel line and the Dynamixel bus.

That is a measurement, not an argument, and it needs no new hardware:
**run one channel's line level down a full-length body cable, with the
NeoPixels on that cable running, and listen.** Do it before this board is
laid out. If it hums, the answer is a screened pair on the spare
conductors, and the connector tables below already have the spares for it.

---

## 4. The mute line, and why it survives the move

The current amplifiers have `set` strapped permanently high, so nothing
can silence one from software. TJ needed a mute for a reason that is now
void — hardware timers do not tear when NeoPixel writes disable
interrupts (CODE_DOCUMENTATION 9.13) — and with the tone made by a timer,
*stopping the timer already silences the room*: the pin sits low, the
filter output is 0 V, the amplifier has nothing to amplify.

**So the mute line is not for silencing the signal. It is for silencing
the amplifier**, which is a different thing once the amplifier is out of
reach inside a body: its own noise floor, its own turn-on thump, and
whatever a floating input does to it during a reflash.

- **One Mega pin, `D2`, commoned to all five** — one conductor per body
  cable, one net on the board.
- **Pull it up to +5 V on the board with 10 K.** Firmware 3 leaves `D2`
  an input, and the default of a pin nobody drives must be *amplifiers
  enabled*, not five silent bodies and a morning spent looking for why.
  A later firmware drives it low to mute.
- **Confirm the polarity against the module actually chosen.** The
  TPA2005D1's `SHUTDOWN` is active low, which is what the pull-up assumes.
  A module with the opposite sense needs the pull-up to become a
  pull-down, and that is a resistor, not a redesign.

`Colloquy.silence_speakers()` then means what it says.

---

## 5. The body connectors, redrawn

**This is the part the amplifier decision forces**, and it would be worth
doing anyway. Read out of the netlist rather than remembered:

> **`+5V` leaves the current board on exactly three pins** — `J5` 15
> (female1), `J1` 15 (female2) and `A-J3` 9. `+12V` and `dxl_data` leave
> on the same three connectors. **`B-J4` carries no power at all**, only
> GND on its shell — and `B-J4` is the only connector male2 has.

Two things follow, and the second one is urgent:

- **One +5 V conductor already feeds three bodies.** Whatever reaches
  female3, male1 and male2 goes through `A-J3` pin 9 and is distributed
  beyond the board. Three bodies' NeoPixels on one DSUB pin is the
  existing bottleneck; hanging three amplifiers behind it as well is not
  sound.
- **`dirty rework` section 5 says to power each MAX9814 "from the DSUB,
  which already carries +5 V and GND to every body". That is not true of
  male1's or male2's connector.** male1's power arrives on `A-J3` and its
  speaker pair on `B-J4`; male2 has neither. Before wiring a MAX9814 into
  either male, **go and look at where those bodies get their 5 V today** —
  the answer is off this board, and it is not in these files.

### The rule for the new board

**Every body gets its own connector, carrying its own power, its own
signals and its own spares.** No body's supply passes through another
body's cable, and no connector carries two bodies.

**Females keep a DSUB-15; males get a DSUB-25.** Two part numbers rather
than one, for two reasons: a male genuinely needs the pins (four light
sensors, two NeoPixel lines and a state LED fill a 15-way exactly, with
nothing left over), and different shells make it **physically impossible
to plug a female cable into a male port** — which the current
`A-J3`/`B-J4` pair, two identical 15-ways carrying entirely different
things, very much is not.

### Female body connector — DSUB-15, ×3, identical

| Pin | Signal |
|---|---|
| 1, 2 | **+5 V** (both pins, paralleled) |
| 3, 4 | **GND** (both pins, paralleled) |
| 5 | +12 V |
| 6 | `dxl_data` |
| 7 | neopixel |
| 8 | photosensor |
| 9 | microphone — MAX9814 `AOUT` in |
| 10 | **line out** — filter output to the body amplifier |
| 11 | **audio return** |
| 12 | **amplifier shutdown** |
| 13, 14, 15 | spare |
| shell | chassis / cable screen |

### Male body connector — DSUB-25, ×2, identical

| Pin | Signal |
|---|---|
| 1, 2, 3 | **+5 V** (all three, paralleled) |
| 4, 5, 6 | **GND** (all three, paralleled) |
| 7 | +12 V |
| 8 | `dxl_data` |
| 9 | body neopixel |
| 10 | up-ring neopixel |
| 11, 12, 13, 14 | photosensor A, B, C, D |
| 15 | microphone — MAX9814 `AOUT` in |
| 16 | **line out** |
| 17 | **audio return** |
| 18 | **amplifier shutdown** |
| 19 | state LED |
| 20 … 25 | spare |
| shell | chassis / cable screen |

**Paralleled power pins are not padding.** They are the cheapest
available answer to the volt dropped in several metres of thin conductor,
now that the current at the far end includes an amplifier's peaks as well
as a NeoPixel strip's.

**`audio return` is the return for the line out and the microphone, and
for nothing else.** Join it to the analogue ground at the board and to
the divider's bottom end and the MAX9814's ground at the body; the
amplifier's *supply* current goes home on the GND pins. The point is to
keep class-D switching current and NeoPixel current out of the copper the
MSGEQ7 inputs are referenced to.

### Grounding, since it now matters

One analogue ground region under the five filters and the five analysers,
joined to the power ground at **a single point** near the Mega's own GND
pad. The +5 V rail that leaves on the body connectors, and its return,
should not run under the filter stages.

### Current budget

Budget **0.5 A of peak amplifier current per body** at 5 V and confirm it
against the module actually chosen — a TPA2005D1 delivering 1.4 W into
8 Ω is roughly that. That is on top of the NeoPixels, it is peak rather
than average, and the local 470 µF is what keeps it from being seen at
the board at all. Check the DC jack and whatever feeds it against the
total before ordering.

---

## 6. Test points and silkscreen

**Put a pad on each filter output.** With the amplifier at the body, the
filter output *is* the line out — it is the single measurement that says
whether a body's voice is right before it leaves the box, and it is now
also the last point on the board where the signal exists at all.

Test points, all of them plain pads:

| Where | Why |
|---|---|
| filter output ×5 | the voice, before it leaves the board |
| analyser output ×5 (A0–A4) | the ear, before the ADC |
| `STROBE`, `RESET` | the two the bringup test cannot tell apart from silence |
| `SHUTDOWN` | is the mute line where you think it is |
| board +5 V, Mega 5 V, GND, analogue GND | four rails, four pads, no probing on a pin |

Silkscreen, because every one of these is a fault that reads as something
else months later:

- **Each filter stage: its frequency and its Mega pin.** `160 Hz — D11`.
- **Each analyser module: its body name.** `module 0 — female1`.
- **Each body connector: its body name**, next to the shell, in the
  largest type that fits.
- **`MEGA 5V` and `BOARD +5V`, spelled out.** They are separate nets and
  should stay separate — the amplifiers and NeoPixels must not draw
  through the Mega's regulator — and on the current board `J9` 35 looks
  exactly like a convenient 5 V rail.
- **`D2 D3 D4 — AUDIO CONTROL`** over the three-pin block.

---

## 7. Smaller things the current board got wrong or left out

- **The two state LEDs are wired and unused.** D24 and D25 drive them
  through a 10K, a jumper header, a BC557 and a 150R, and no firmware has
  ever written to either. **Drop the driver chain**; keep the pin and the
  conductor (male pin 19), so that writing the firmware later costs a
  transistor at the body rather than a board spin. Four passives per male
  for a feature nobody has asked for is the wrong way round.
- **Spares are no longer a privilege of female1 and female2.** The current
  harness has twelve spare conductors and all twelve go to two bodies;
  the tables above give every body three or six. The next thing that
  needs a wire will not be politely limited to the bodies that have one.
- **`J11` and `J12` stop being unlabelled break points**, for the reason
  in section 2 — the analyser is in that path by design now. Whatever
  survives as a series element gets a footprint, a value and a silkscreen
  label.
- **No audio on D13**, and nothing else that minds a pulse train at
  power-on. See section 1.

---

## 8. What is still open above the board

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
  jumper on the body module** — which is now one of five small assemblies
  that already exist for the amplifier — so the field check is a jumper
  move and not a rework.
