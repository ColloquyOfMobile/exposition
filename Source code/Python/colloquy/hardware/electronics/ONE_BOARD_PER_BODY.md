# One board per body

**A second full solution, specified against the same fixed harness.**
`next pcb` puts everything on one board in the rack and sends analogue
signals down the DSUBs. This one puts a small processor in each body and
sends almost nothing down them. Both are complete; both are buildable;
they are not variations of each other and this document exists so the
choice can be made on the evidence rather than on which was written
first.

**The constraint is identical and it is the whole point.** The four DSUB
connectors and the harness behind them do not change — not their part
numbers, not their pinouts, not the four boards in `harness`. Everything
below is specified against exactly what `center`, `female static`,
`female base` and `male static` already carry.

---

## 0. This is not a new idea — it is the one the piece had

TJ's original firmware is one sketch per **unit**, with `UNIT_ID` set at
compile time and five copies flashed
(`local/Code/Code/Units/logic35_systems/`, `logic35_systems.ino` line 7).
Each unit had, on its own board:

| What | TJ's pin |
|---|---|
| four light sensors | `A3`, `A2`, `A6`, `A7` |
| its NeoPixel line | `A0` |
| its tone | `D9` (PWM) |
| its amplifier enable | `D11` |
| its own MSGEQ7 — signal, strobe, reset | `A4`, `D2`, `A5` |
| drive, body-stop, mirror bits | `D6`, `D7`, `D8`, `D12`, `D13` |

**`A6` and `A7` say which board it was.** They are analogue-input-only
pins that exist on an ATmega328P in its TQFP package — an Arduino Pro
Mini or a Nano — and do not exist on an Uno. So the board is a **Pro
Mini**, and the pin map above is the proof that a body fits on one with
room over.

What the centralised design did was collect all of that onto one Mega so
that one program could see the whole piece at once. This document asks
what it costs to give it back, now that there is a driver, a servo bus
and a hearing side that TJ did not have.

---

## 1. What moves, and what does not

| | `next pcb` | one board per body |
|---|---|---|
| processor | one Mega 2560, in the rack | **five Pro Minis, one in each body**, plus a bridge in the rack |
| low-pass filter | five channels on the main board | **one in each body**, cut for that body's pitch |
| 22K/3K3 divider | on the main board | **in the body**, at its amplifier |
| MSGEQ7 analyser | five on the main board, one commoned strobe | **none** - the body's own processor does it in software (section 4) |
| MAX9814 microphone | in the body | in the body — unchanged |
| amplifier | in the body | in the body — unchanged |
| loudspeaker | in the body | in the body — unchanged |
| U2D2 and servo bus | in the rack | in the rack — unchanged |
| the four harness boards | unchanged | **`center` and `female static` unchanged**; `female base` and `male static` become populated boards |

Nothing about the servos changes. The Dynamixel bus is still one data
line from the U2D2 to every body, tapped where it is used, and the driver
still turns every body itself. **This is a change to the sensing and
sounding side only.**

---

## 2. What the harness carries afterwards

This is the argument, and it is arithmetic rather than opinion. Read the
"now" columns out of `harness`.

### A female — `female static` / `female base`

| Pin | Now | With a board in the body |
|---|---|---|
| 4 | speaker − | *freed* |
| 5 | photo sensor | *freed* |
| 6 | microphone | *freed* |
| 7 | **+12 V** | **+12 V** |
| 8 | **GND** | **GND** |
| 12 | speaker + | *freed* |
| 13 | neopixel | *freed* |
| 14 | **dynamixel data** | **dynamixel data** |
| 15 | **+5 V** | **+5 V** |
| 1, 2, 3, 9, 10, 11 | spare ×6 | **two carry the bus**; four still spare |

Nine conductors become five. **Ten of fifteen are then spare.**

### A male — `center` / `male static`

| Pin | Now | With a board in the body |
|---|---|---|
| 1 | **GND** | **GND** |
| 2 | **+12 V** | **+12 V** |
| 3 | microphone | *freed* |
| 4, 12, 5, 13 | photo a, b, c, d | *freed ×4* |
| 6 | state LED | *freed* |
| 7, 14 | speaker −, + | *freed* |
| 8 | spare | **bus** |
| 9 | **+5 V** | **+5 V** |
| 10 | **dynamixel data** | **dynamixel data** |
| 11 | body neopixel | *freed* — or kept, see §4 |
| 15 | bar neopixel | *freed* — or kept, see §4 |

Fourteen conductors become five or six. A male's connector goes from
**one** spare to ten.

**The pin numbers still differ between the sexes**, because the DSUBs are
wired differently and that is fixed. What becomes the same is the *set*:
GND, +5 V, +12 V, servo data, bus. Five things, on every body, and
nothing else.

**No analogue signal leaves a body on any of them.** That is the sentence
this whole document is for. Today a microphone's output and a speaker's
drive travel several metres of DSUB shared with a NeoPixel line and the
servo bus; here they travel 100 mm inside the body and never meet the
harness at all.

---

## 3. The bus

**RS-485, half duplex, two conductors, one master in the rack.**

- **Two conductors, and both connectors have them to spare** — a female
  has six spares before anything is freed, a male has one plus ten that
  the change itself frees.
- **Differential**, which is what earns it the right to run several
  metres beside a class-D amplifier's supply and a NeoPixel line's
  switching current.
- **Multi-drop by design.** One master, five devices, addresses on the
  wire. A Pro Mini has one hardware UART and a MAX3485 needs one more pin
  for its driver enable.

**Not the Dynamixel line, and this is deliberate.** It is tempting: it
already reaches every body, it is already half duplex, it already has
addresses, and the U2D2 already masters it. But a body's processor
misbehaving on that wire would stop the piece *moving*, not just stop it
listening — and the failure would look like a servo fault. Motion and
sensing are worth keeping on separate copper for the same reason the
three halves of `open_the_hardware()` are independent.

**One bridge stays in the rack**, and it is worth the part: it speaks the
existing JSON-line protocol to the driver on one USB serial port and
relays to the five nodes. So `colloquy/drivers/arduino/` keeps its shape
— one port, one `send(path, **data)`, one `wait_for_reboot()` — and the
five nodes are addressed by the path they already use (`f1/head`,
`m2/light sensor/a`). Without the bridge, every one of those becomes a
port to open and a firmware version to check.

---

## 4. What each body board becomes

`female base` and `male static` stop being connector breakouts and become
the boards that do the work. Their outlines (50 × 80 and 50 × 90 mm) and
their JST pinouts stay — everything inside the body plugs in exactly as
it does now.

**Added to each:**

| Part | Note |
|---|---|
| Arduino Pro Mini, 5 V / 16 MHz | ATmega328P; TJ's board |
| MAX3485 or equivalent | RS-485 transceiver, with DE/RE on one pin |
| the listening | **in software on the Pro Mini** - a Goertzel bin per pitch, no analyser chip at all. See below; an MSGEQ7 per body is the fallback if it is ever wanted |
| second-order low-pass | **cut for this body's pitch only** — one R/C pair, not five |
| 22K / 3K3 divider | at the amplifier input |
| amplifier module + 470 µF | as `next pcb` section 3, unchanged |
| 120 R bus termination | fitted at the two ends of the chain only |

**A male keeps his two NeoPixel lines on the harness, or does not.** The
up-ring is on the bar rather than in the body, so it may be easier to
drive from the rack even here. Both are possible; the conductors exist
either way. Decide it when the mechanical arrangement of the up-ring is
in front of somebody.

### The MSGEQ7 can go too

**A Pro Mini can do the listening in software, and better.** The chip
under it is an ATmega328P at 16 MHz, and detecting whether one known
frequency is present is what the **Goertzel** algorithm is for: one
multiply-accumulate per sample per frequency, no buffer, no FFT.

The arithmetic, so it is a decision rather than a hope:

| | |
|---|---|
| ADC clock | 16 MHz / 64 = 250 kHz, 13 clocks a conversion |
| sample rate | **19.2 kSPS** - above Nyquist for 6250 Hz with room over |
| resolution | 8 to 9 bits usable, since 250 kHz is over the datasheet's 200 kHz for a full ten |
| cost per bin | ~25 cycles a sample in integer Q15 (the AVR has a hardware `MUL`) |
| five bins | ~2.4 M cycles a second of 16 M - about **15% of the processor** |
| window | 25 ms is 480 samples; bin width 40 Hz, against tones 160 Hz apart at the closest |

**It is better than the MSGEQ7 at this particular job**, which is worth
saying plainly because the MSGEQ7 is the more serious-looking part. Its
seven bands are fixed, octave-spaced and wide-skirted: the five pitches
were *chosen* to land one per band, and two of them still sit in adjacent
bands with the skirts overlapping. A Goertzel bin is centred exactly on
the tone and is as narrow as the window makes it, which rejects the room
far better than a band an octave wide.

**And it deletes a part.** No analyser chip, no commoned strobe, no
reset, no support network - which is one of the only two groups of values
in `next pcb`'s bill of materials that nobody in this repository has been
able to fill in.

Three things it needs, and the third is a real design point:

- the microphone signal biased to mid-rail and AC coupled, which a
  MAX9814 already gives (about 1.25 V);
- comparison between bins rather than absolute level, since the AGC makes
  absolute level meaningless - which is what `test_audio_bringup`'s
  diagnosis already does with its per-band rise;
- **the NeoPixels.** `show()` disables interrupts for roughly 30 us a
  pixel, so a 50-pixel strip is 1.5 ms deaf. Sampling through a write
  loses samples. It is the same collision CODE_DOCUMENTATION 9.13 raised
  about tones, answered there by hardware timers - here the answer is
  cheaper, since the body's own processor decides when it does both and
  can simply not listen while it is writing light.

**The pitch stops being a table.** `drivers/audio.py` exists because five
tones must come out of one chip: a pitch belongs to its timer, Thomas's
OCR values are indexed by timer, and 6250 Hz sits on T2 because T2 is the
8-bit one. With one tone per processor **every body has every timer**, so
any body can have any pitch, and its filter is cut in the same body for
the same pitch. The constraint that moved five bodies across five pins on
2026-08-27 simply does not exist here.

---

## 5. What the main board becomes

Almost nothing, which is the other half of the argument:

- the four DSUBs, in the panel, unchanged;
- power in, and the +5 V / +12 V distribution;
- the U2D2 on its mount, and the servo bus;
- the bridge processor and one RS-485 transceiver;
- the DC jack, the screw bridge, the JST.

**Gone from it:** five filters (10 R, 10 C), five dividers, five MSGEQ7s
and their support networks, five build-out resistors, the commoned strobe
and reset, and every analogue net. That is roughly **sixty parts off the
board in the rack and twelve onto each of five boards in the bodies.**

---

## 6. Against `next pcb`, honestly

**Where one board per body is better:**

- **No analogue on the harness.** `next pcb` section 3 has one thing it
  admits it has not shown: that 2.5 Vpp survives several metres of DSUB
  with the NeoPixels on that cable running. Here there is nothing to
  show — the signal never gets on the cable.
- **The bit clock stops being an open question.** CODE_DOCUMENTATION
  section 9 and `next pcb` section 9 both name it: the light channel
  sends one ring command per bit over a serial round trip, which is
  comfortable at 200 ms a bit, and the *receive* side cannot work that
  way — TJ sampled every 50 ms and read his analyser sixteen times per
  sample. A processor in the body does exactly what his did, with no link
  in the loop at all. `next pcb` says this "does not change the board".
  For this solution it *is* the board.
- **Conductor pressure disappears.** male2's shared +5 V, the male
  connector with one spare, the whole of section 5 and the case in
  section 8 — all of it is about conductors that this design stops using.
- **A failure is local.** One body deaf is one body deaf. On the
  centralised board, the Mega is the piece.
- **The pitches come free** (§4), and each filter is cut for one channel
  in the body it serves.

**Where `next pcb` is better:**

- **One firmware, one port, one version.** `drivers > arduino` compares
  the sketch in this repo against what the board says it is running and
  refuses a mismatch. Five nodes is five of that, and a node running last
  month's sketch is a body that behaves subtly wrongly.
- **Flashing.** `flash firmware` puts a sketch on the Mega over the USB
  lead the driver already uses. **A Pro Mini has no USB** — it wants an
  FTDI adapter on a six-pin header, and the header is inside a body at
  the end of a harness. Flashing over the bus is possible and is not
  written; see §8.
- **One log, one place to look.** A node that will not answer is behind a
  DSUB, inside a body, up a ladder.
- **Fewer assemblies.** One populated board plus five amplifier modules,
  against six populated boards. More boards is more connectors, and
  connectors are what fail in a gallery.
- **It is nearly specified.** `next_pcb.py` is the board as data, it
  generates a netlist KiCad imports, and every decision in it is taken.
  This document is a specification with no netlist behind it yet.

**The recommendation.** Build `next pcb` for the exhibition: it is
finished, it is one board, and the piece has a date. Keep this one, and
**let section 3's measurement decide whether it is needed** — run one
channel's line level down a full-length body cable with the NeoPixels on
that cable running, and listen. If that is clean, the centralised board
is the cheaper answer and the right one. If it hums, the remedy is not a
better filter at the rack: it is not putting the signal on the cable, and
this document is how.

Two things make that an easy bet rather than a hedge. The measurement
needs no new hardware and can be done this week. And **the harness does
not change either way** — every conductor this design would use is one
the other design already has.

---

## 7. What it costs to keep both open

Very little, and worth saying precisely:

- `harness` is shared, unchanged, and already generated.
- The bodies' JST pinouts are shared: a speaker, a microphone, a light
  sensor and a NeoPixel line plug into the same connectors either way.
- The amplifier, the MAX9814, the divider and the 470 µF are the same
  parts in the same place in both.
- Only the **filters and the analysers** sit in a different place, and
  only the **processor count** differs.

So the parts to buy for the bodies are the same parts in both solutions,
and the decision is reversible for as long as the main board is
unbuilt.

---

## 8. What is open in this one

- **Flashing five nodes.** A bootloader that takes a sketch over RS-485
  is the obvious answer and is not written. Failing that, an FTDI header
  brought out to somewhere reachable — which is a mechanical question
  about each body, not an electrical one.
- **The bus protocol.** The bridge can keep the driver's JSON-line
  protocol facing the PC, but what it speaks to the nodes is unwritten.
  Addressing, a status return, a timeout, and what happens when a node
  does not answer.
- **Where the pattern layer lives.** With a processor in the body it
  *can* live there, which is what makes the bit clock tractable — but
  then a female's decode happens where the driver cannot watch it. The
  read-pattern tests under `colloquy/tests/` all assume the driver can
  see the samples. That is a real cost and it is not a wire.
- **Which pitches**, now that they are free. They should still land in
  five different MSGEQ7 bands, since that is what makes the pitch say who
  is speaking — but the assignment is no longer forced by which timer is
  eight bits wide.
- **The up-ring**, per §4.
