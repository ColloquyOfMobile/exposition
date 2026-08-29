# The next PCB

**What the board that replaces the one in the rack should do.** Written
while the dirty rework was being planned, so that the rework is a
prototype of this rather than a detour — every pin it moves, this keeps.

Three decisions are taken, and one constraint is given:

1. **Absorb Thomas's filter board and analyser array onto the main PCB.**
   One board, no daughterboards, no patch wires. More work to lay out,
   and much less to assemble and much less to go wrong in a gallery three
   months from now.
2. **The amplifier moves to the body.** The board sends line level down
   the harness and the amplifier sits next to its loudspeaker. This was
   section 3's open question in the previous draft; it is answered below.
3. **The amplifiers run from +12 V**, and the module is specified by its
   supply range (4.5–15 V) rather than by a rail — so male2, which this
   board cannot feed on either rail, runs the same module from its own
   local supply. Section 5's open question in the previous draft; it is
   answered there.
4. **The DSUB connectors and the harness behind them are fixed** — a
   supplier constraint, not a design choice. Four DSUB-15s, the pinout
   `as built` records, no new conductors. Everything below is specified
   against that. **Section 8 keeps the case for redrawing them**, because
   it is a good case and it should not be lost; it is just not what this
   board can assume.

Read `as built` for what exists and `dirty rework` for what is being
proved before this is committed to.

**The wiring and the envelope are generated, not written here.**
`py next_pcb.py` produces three files into
`CAD/KiCad/electronic box v2/` — `NETLIST.md` (every part, every net,
every terminal), `BOM.md` (what to order) and `MECHANICAL.md` (where the
edges and the connectors have to be). This document is the specification
and the reasoning; those are what a schematic and a layout are drawn
from.

It is generated for one reason. Which body speaks at which pitch, out of
which timer pin, into which analyser module is **one table**, and the
firmware and four Python nodes already read it (`colloquy/drivers/audio.py`).
The board reads the same one, so a channel cannot be laid out against a pin
the sketch does not drive — the same arrangement as
`drivers/arduino/firmware.py` reading the baud rate straight out of the
`.ino` rather than restating it. `pytest_tests/hardware/test_next_pcb.py`
then holds the netlist to what this document says: no Mega pin on two
signals, no net with one end, no tone into a filter cut for another
frequency, nothing on D0, D1 or D13.

Two groups of values are deliberately **not** in it, and sit in their own
section of the BOM rather than among the decided ones: the MSGEQ7's
support network (the analyser array is five ready-made modules today and
nobody here has drawn the chip) and whatever is fitted across `J11`/`J12`
for each light sensor. A plausible-looking number passing for a known one
is how a board comes back wrong.

**Nothing above the copper is waiting on anything.** Every decision this
board needs is taken. What is left is three measurements, and none of
them changes a track: what is fitted across `J11`/`J12` (a value for the
BOM), what male2's local supply is (a module setting — section 5), and
whether 2.5 Vpp survives a full-length body cable with its NeoPixels
running (section 3, and the one to do first, because a bad answer is
found at the two ends rather than in the layout).

---

## 1. Keep the pinout exactly

The rework's pinout is not a compromise to be tidied up later — it is the
only one the silicon allows, and it is the one Thomas's own firmware
already uses. Copy it.

**The acceptance test for the pinout is that one sketch runs on both
boards.** Firmware 4 should run unmodified on the reworked board and on
this one, so that swapping the board is swapping the board and nothing
else. That is a better reason to keep the NeoPixel pins where the rework
put them than tidiness is to move them — see the note at the end of this
section.

| Signal | Pin | Why it cannot move |
|---|---|---|
| male1 tone, 160 Hz | **D11** | `OC1A`, the only pin timer 1 can toggle |
| male2 tone, 400 Hz | **D5** | `OC3A` |
| female1 tone, 1 kHz | **D6** | `OC4A` |
| female2 tone, 2.5 kHz | **D46** | `OC5A` |
| female3 tone, 6.25 kHz | **D10** | `OC2A` |
| amplifier shutdown | **D2** | reserved, not wired out; see section 4 |
| analyser RESET | **D3** | free choice, but keep it |
| analyser STROBE | **D4** | free choice, but keep it |
| analyser modules 0–4 | **A0–A4** | body order, and the reason module N is body N |
| female light sensors | **A5–A7** | unchanged |
| male light sensors | **A8–A15** | unchanged |
| NeoPixels ×7 | **D7, D8, D9, D14, D15, D16, D17** | any pins; these are the ones the rework used |

**The males hold the two low voices and the females the three high ones**,
which is why the body names in that table are not the ones the previous
draft had. Nothing about the *board* moved: a pitch belongs to its timer
(Thomas's OCR values are indexed by timer, and 6250 Hz is on T2 because T2
is the 8-bit one and cannot reach 160 Hz at its prescaler), so the pitches
stayed put and the bodies moved across the pins. Every filter channel is
still cut for the pin that feeds it. What changed is which body's line out
each filter output lands on — five nets, and on the reworked board five
re-jumperings.

**D2, D3 and D4 are the audio control block** — mute, reset, strobe,
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
| amplifier module | class-D, rated **4.5–15 V**; +12 V in four bodies and male2's local supply in the fifth — section 5 |
| 22K / 3K3 divider | at the amplifier input, sized for volume at maximum |
| 470 µF reservoir | across the amplifier's supply and GND, **at the module** |
| loudspeaker | short leads, in the body, as now |
| MAX9814 module | from `dirty rework` section 5 |

The reservoir is not optional, and under the fixed harness it is doing
more work than it would otherwise: a class-D amplifier at the end of
several metres of thin conductor is a load with real peaks and no local
energy behind it, and for three of the five bodies that conductor is
shared (section 5). Without a capacitor at the module its supply sags on
every transient and takes the NeoPixels on that cable with it.

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
laid out. With the connectors fixed there is no screened pair to fall
back on, so this one matters more than it did: if it hums, the remedy has
to be found at the two ends — source impedance, the return, the divider's
position — rather than in the cable.

---

## 4. The mute line: reserved on the board, not wired to the bodies

The current amplifiers have `set` strapped permanently high, so nothing
can silence one from software. TJ needed a mute for a reason that is now
void — hardware timers do not tear when NeoPixel writes disable
interrupts (CODE_DOCUMENTATION 9.13) — and with the tone made by a timer,
*stopping the timer already silences the room*: the pin sits low, the
filter output is 0 V, the amplifier has nothing to amplify.

**So a mute line would not be silencing the signal. It would be silencing
the amplifier** — its own noise floor, its own turn-on thump — which is a
different thing once the amplifier is out of reach inside a body.

**The fixed harness cannot deliver it to all five bodies**, and that is
what decides it. female1 and female2 have six spare conductors each;
female3 and male1 have none; male2 shares `B-J4`'s single spare. **A mute
that reaches three bodies out of five is worse than no mute at all** —
`Colloquy.silence_speakers()` would half-work, and a command that
half-works is the kind of thing that costs a morning.

So, for this board:

- **`D2` is reserved, pulled up to +5 V through 10 K, and brought to a
  labelled pad** — not to a connector. The net exists, the polarity is
  decided, and wiring it later is a wire rather than a board spin.
- **The pull-up is the safe default.** Firmware 4 leaves `D2` an input,
  and the default of a pin nobody drives must be *amplifiers enabled*,
  not five silent bodies and a morning spent looking for why.
- **If it is ever wanted, the two dead state-LED conductors are the way
  in.** `B-J4` 1 and 13 are wired to nothing in firmware and have been for
  years (section 7); they reach both males. With female1 and female2 on
  their spares, that is four bodies out of five, and only female3 left to
  solve.
- **Confirm the polarity against the module actually chosen.** The
  TPA2005D1's `SHUTDOWN` is active low, which is what the pull-up assumes.
  A module with the opposite sense needs the pull-up to become a
  pull-down, and that is a resistor, not a redesign.

---

## 5. The body connectors, as they are

**Fixed by the supplier**, so the audio has to land on conductors that
already exist. It does, and neatly: **the speaker pair is exactly the two
conductors that stop carrying a speaker** the moment the amplifier moves
into the body.

### The one substitution, per body

| Was | Becomes |
|---|---|
| `<body>/speaker +/out` | **line out** — filter output to the body amplifier |
| `<body>/speaker −/out` | **audio return** |

No new conductor, no new connector, no change to the pinout, and nothing
to ask the supplier for. The loudspeaker moves from the far end of that
pair to the output of the amplifier, a few centimetres away.

**`audio return` is the return for the line out, and for nothing else.**
Join it to the analogue ground at the board, and at the body to the
divider's bottom end and the amplifier's input ground; the amplifier's
*supply* current goes home on the GND conductor. The point is to keep
class-D switching current and NeoPixel current out of the copper the
MSGEQ7 inputs are referenced to.

### Where every audio conductor lands

Read out of the netlist rather than remembered:

| Body | Connector | Line out | Audio return | Microphone | +5 V | GND | Spares |
|---|---|---|---|---|---|---|---|
| **female1** | `J5` | 12 | 4 | 6 | **15** | 8, shell | 6 (`Extra2`) |
| **female2** | `J1` | 12 | 4 | 6 | **15** | 8, shell | 6 (`Extra1`) |
| **female3** | `A-J3` | 12 | 5 | 3 | 9 *(shared)* | 1, shell | none |
| **male1** | `B-J4` | 9 | 2 | `A-J3` 13 | `A-J3` 9 *(shared)* | `A-J3` 1; `B-J4` shell | none |
| **male2** | `B-J4` | 6 | 14 | 10 | **none** | shell only | `B-J4` 7 *(shared)* |

### The supply problem, which the board cannot fix

> **`+5V` leaves the current board on exactly three pins** — `J5` 15
> (female1), `J1` 15 (female2) and `A-J3` 9. `+12V` and `dxl_data` leave
> on the same three connectors. **`B-J4` carries no power at all**, only
> GND on its shell — and `B-J4` is the only connector male2 has.

With the connectors fixed, this is a constraint to design around rather
than a fault to correct:

- **female1 and female2 are fine.** Each has its own +5 V conductor and
  its own return, and six spares besides.
- **female3, male1 and male2 share `A-J3` pin 9.** One conductor already
  feeds three bodies' NeoPixels; three amplifiers now sit behind it too.
  This is the number to check before ordering anything.
- **male1's audio and male1's power arrive on different cables** —
  signal on `B-J4`, supply on `A-J3`. Keep the audio return on `B-J4` 2
  paired with `B-J4`'s shell rather than reaching across to `A-J3` 1, so
  the signal's return stays in the cable the signal is in.
- **male2 has no supply from this board at all**, and its NeoPixels run
  today — so its 5 V comes from somewhere off these files. **Find where
  before hanging an amplifier on it**, and check what headroom is left on
  it. This does **not** block the board: `B-J4` has one spare conductor
  and GND only on its shell, so male2's amplifier is fed locally whatever
  rail this board offers, and the rail is decided without it. See
  *Which rail the amplifier runs from*, below.

The same finding corrects `dirty rework` section 5, which is being worked
from right now: it says to power each MAX9814 "from the DSUB, which
already carries +5 V and GND to every body". True of the three females
and of neither male.

### Which rail the amplifier runs from

**+12 V, and the module is specified by its supply range rather than by a
rail.** This waited on male2's supply in the previous draft. It should
not have: male2 cannot take an amplifier supply from this board on
*either* rail, so its answer decides nothing about the other four.

**Why male2 is not a rail question.** `B-J4` carries **one** spare
conductor — pin 7, `centre/spare1` — and GND only on its shell. An
amplifier needs a supply *and* a return. Spending that single spare on
the supply still leaves the return on a cable screen, which is the last
copper class-D switching current should go home through, and it leaves
male2 with no spare at all for the shutdown line section 4 reserves. So
male2's amplifier is fed **locally**, from whatever already runs its
NeoPixels, whichever rail this board offers. That is a finding, not an
open item: it follows from the connector, and the connector is fixed.

**So the four that can be fed decide it on the merits, and the merits say
+12 V:**

- The same acoustic power costs roughly **40% of the current** (5 V/12 V),
  which is the whole of the volt-drop problem in several metres of thin
  conductor.
- The +12 V conductor carries **no NeoPixel current**. The +5 V one
  carries three strips, and for female3 and male1 it is one shared
  conductor — so on +5 V an amplifier's peaks and a strip's peaks are on
  the same wire.
- **The field has now shown what that sharing costs.** On 2026-08-28 the
  reworked board had its sound side taken from the Mega's own 5 V, and it
  browned out and re-enumerated in the middle of a command
  (`docs/errors/2026-08-28-01.txt`; `dirty rework` section 0). This board
  already designs that exact failure out at the rack, by keeping
  `MEGA_5V` off the `+5V` rail — but the same mistake is available one
  level down, at the far end of a body cable, and putting the amplifiers
  on the rail the lights are not on is that lesson applied at the body
  end.
- The cost, stated plainly: **+12 V also feeds the Dynamixels**, whose
  current steps when a servo starts. That is what the 470 µF at the
  module is for. It is a supply disturbance with local energy behind it,
  which is a far easier thing than a shared conductor sagging.

**One part number, kept by specifying a range.** Choose a class-D module
rated across the whole span — **nominally 4.5 V to 15 V** — so the same
assembly runs from +12 V in four bodies and from male2's local supply in
the fifth. The consequence is worth knowing before it is heard: acoustic
power goes as the square of the supply, so **male2 on 5 V is markedly
quieter than the other four**. Two ways out, neither of which blocks this
board: bring +12 V to male2 whenever the harness is next rebuilt
(section 8), or raise male2's local supply. Until one of them happens,
male2's level is a commissioning problem rather than a design one.

**What is still to be measured, and it is not a rail:** what male2's
local supply actually is — its voltage and what headroom is left on it
once an amplifier is added. That is answered by looking at the piece, not
at the CAD, and it decides male2's module setting rather than this
board's copper.

### Current budget

Budget **0.25 A of peak amplifier current per body at +12 V**, and
confirm it against the module actually chosen — it is the 0.5 A that a
TPA2005D1 delivering 1.4 W into 8 Ω costs at 5 V, scaled by the rail. It
is peak rather than average, and it is no longer on top of the NeoPixels:
that is the point of choosing this rail.

**male2 keeps the 0.5 A figure**, at 5 V, on its own local supply — which
is the number to check that supply against before hanging an amplifier on
it, since it is already running a NeoPixel strip.

### Grounding, since it now matters

One analogue ground region under the five filters and the five analysers,
joined to the power ground at **a single point** near the Mega's own GND
pad. The +5 V rail that leaves on the body connectors, and its return,
should not run under the filter stages.

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
| `SHUTDOWN` | the reserved mute net, and where it gets wired from |
| board +5 V, Mega 5 V, GND, analogue GND | four rails, four pads, no probing on a pin |

Silkscreen, because every one of these is a fault that reads as something
else months later:

- **Each filter stage: its frequency and its Mega pin.** `160 Hz — D11`.
- **Each analyser module: its body name.** `module 0 — female1`.
- **Each body connector: which bodies it serves**, next to the shell, in
  the largest type that fits. `A-J3` and `B-J4` are two identical 15-ways
  carrying entirely different things and neither says so.
- **On `B-J4`: `NO POWER`.** It is the one fact about that connector that
  nobody expects and everybody needs.
- **The speaker pair, relabelled.** Those two pins no longer carry a
  speaker. `LINE OUT` and `AUDIO RTN`, or somebody will connect one.
- **`MEGA 5V` and `BOARD +5V`, spelled out.** They are separate nets and
  should stay separate — the amplifiers and NeoPixels must not draw
  through the Mega's regulator — and on the current board `J9` 35 looks
  exactly like a convenient 5 V rail.
- **`D2 D3 D4 — AUDIO CONTROL`** over the three-pin block.

---

## 7. Smaller things the current board got wrong or left out

- **The two state LEDs are wired and unused.** D24 and D25 drive them
  through a 10K, a jumper header, a BC557 and a 150R, and no firmware has
  ever written to either. **Drop the driver chain and keep the
  conductors** — `B-J4` 1 and 13 are then two free wires to the two males,
  which is where a mute line would go if one is ever wanted (section 4).
  Four passives per male for a feature nobody has asked for is the wrong
  way round; two spare conductors are not.
- **The spares stay where they are.** Twelve spare conductors, six to
  female1 and six to female2, none to the other three. That is a harness
  fact and this board cannot change it — it is the strongest single
  argument in section 8.
- **`J11` and `J12` stop being unlabelled break points**, for the reason
  in section 2 — the analyser is in that path by design now. Whatever
  survives as a series element gets a footprint, a value and a silkscreen
  label.
- **No audio on D13**, and nothing else that minds a pulse train at
  power-on. See section 1.
- **The board has no mounting holes**, and never had. The exported NPTH
  drill file has a header, an `M30` and not one coordinate between them,
  and there is no `MountingHole` footprint either — an A4 board carrying
  a Mega 2560 as a shield, five DSUB housings and a DC jack, held by
  nothing but those housings' own jackscrews. Four holes and a keep-out
  is a cheap thing to decide on purpose; `MECHANICAL.md` section 3.

---

## 8. Open question: the connectors, if they were ever free

**Kept because it is a good case, not because it is available.** The
supplier constraint is real and this board is specified without it. But
the constraint is a supplier's, and suppliers change — so this is what to
ask for if the question is ever reopened, and it is the shape the harness
should take whenever it is next rebuilt.

**Every body gets its own connector, carrying its own power, its own
signals and its own spares.** No body's supply passes through another
body's cable, and no connector carries two bodies. Three things it fixes,
all of them things sections 4, 5 and 7 have to work around:

- male2 gets a supply of its own, on conductors of its own, and stops
  being the one body whose amplifier this board cannot feed.
- female3, male1 and male2 stop sharing one +5 V conductor.
- every body gets spares, so a mute line — or anything else that next
  needs a wire — is available to all five rather than to two.

**Females keep a DSUB-15; males get a DSUB-25.** Two part numbers rather
than one, for two reasons: a male genuinely needs the pins (four light
sensors, two NeoPixel lines and a state LED fill a 15-way exactly, with
nothing left over), and different shells make it **physically impossible
to plug a female cable into a male port** — which the current
`A-J3`/`B-J4` pair very much is not.

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
| 10 | **line out** |
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

---

## 9. What is still open above the board

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
