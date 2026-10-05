# The microphone board

**One small PCB per body that carries the microphone and screws onto the
body's aluminium extrusion.** It replaces Thomas's purple MAX9814
breakout on its hand-wired carrier (`HARDWARE_SETUP.md`, figure 5) with
one assembled board: the same chip, the same straps, the same 3-pin JST
in the same order, so it plugs into `female base` `J3` and `male static`
`J3` with nothing else changed — and into the shield backplane's direct
path to the Teensy, which reads its output as it is.

Written 2026-10-05, for builders who are qualified: what to build, how it
fixes, how to tell it apart. **Sources**: the circuit is the MAX9814
datasheet's own typical application (Maxim, "Typical Application
Circuit" and "Applications Information"); the connector order is read
out of the harness boards' copper; the extrusion is read off the
artwork's videos (`local/videos/`) and the harness boards' own mounting
holes. Every figure here is computed by
`colloquy/hardware/electronics/microphone_board.py`, and
`pytest_tests/hardware/test_microphone_board.py` holds the document to
it and to the copper.

---

## 0. What to build

| Step | Do | Check |
|---|---|---|
| **1** | six boards (five and a spare), straps at Thomas's bench setting | the `5V` LED lights; `OUT` reads about 1.23 V |
| 2 | fit one to a body with a nylon spacer under each hole | the backplane's `MIC DIRECT` pin reads the same 1.23 V |
| 3 | servos moving, every speaker silent, record with `scope` | the noise floor is no higher than with the servos still; if it is, swap the nylon spacers for rubber |
| 4 | fit the other four | `test audio loop` or `test goertzel ear`, every tone heard |

---

## 1. The extrusion, and how the board fixes to it

**No drawing of the frame is in this repository**, so its dimensions
were read off what is there:

- **The videos show T-slot profiles.** On a female, a vertical spine
  carries the speaker housing, the mirror and the NeoPixel shades, with
  two arms near the top. Each arm's cut end shows **two slots stacked**:
  a **20 × 40** profile. The spine has the same face width, about a
  quarter of the speaker housing beside it. So the bodies are the
  **20 mm series: 20 mm faces, 6 mm slots, M5 screws**. The bar and the
  ceiling frame are visibly larger.
- **The harness boards already screw on along one slot.** Each has 8 mm
  holes on its long centreline, nowhere else: `female base` two, 43 mm
  apart; `female static` two, 50 mm; `male static` one and a slot,
  50 mm; `center` two, 70 mm. One line of holes, at whatever spacing,
  is a board held by T-nuts in a single slot.

**Measure one profile of each body with a caliper before ordering
fixings**: the face width and the slot opening. 20 mm and 6 mm is what
the videos say.

**The board is made so the answer changes only the nut.** It takes **M5
screws**, and M5 T-nuts are made for 6, 8 and 10 mm slots, so the same
board goes on a 20-, 30- or 40-series profile with the T-nut for that
slot. Its two holes are on one line, so their spacing along the slot is
whatever the board needs.

| Per hole, from the top | Part |
|---|---|
| screw | M5 × 12 button head, ISO 7380, stainless |
| washer | M5, ISO 7089 (10 mm across) |
| board | 1.6 mm |
| spacer | nylon, 5 mm long, 10 mm across, 5.3 mm bore |
| nut | M5 T-nut for the profile's slot: a 6 mm slot on the 20 mm series |

The screw leaves **4.4 mm** below the spacer for the nut: a full bite on
a 4 mm T-nut, without reaching the floor of the slot.

**The holes are non-plated with no copper near them**, so a screw never
touches the board's ground. The extrusions are one metal frame through
every body, and a body's ground arriving at the frame as well as down its
harness would make a loop round the installation for hum to ride on.

**The spacer does two jobs**: it holds the bottom of the board and its
through-hole leads off the aluminium, and it is the break between the
frame and the microphone. Electret capsules hear vibration, and the frame
carries the servos'. Nylon first; rubber (EPDM) if step 3 hears the
servos.

---

## 2. The board

| | |
|---|---|
| outline | **20 × 62 mm**, the width of a 20-series face; 2 mm corner radius |
| stack | 1.6 mm FR-4, two layers |
| holes | two, **5.5 mm** (M5 clearance), non-plated, on the long centreline, **50 mm apart**, 6 mm from each end |
| keep-out | 12 mm round each hole, both sides: no copper, no parts, room for the washer and the spacer |
| top | every part; **the capsule faces away from the profile**, into the room |
| bottom | no parts; ground pour outside the keep-outs |

**Along the board**, from one end: hole; the **capsule**, centred 17 mm
from the end; the **MAX9814** beside it, so the capsule-to-`MICIN` trace
is a few millimetres; its passives; the **two strap headers**; the
**LED** and the **test pins**; the **JST**, opening toward the far end;
hole.

---

## 3. The circuit

The MAX9814 datasheet's typical application, with three additions for a
microphone at the end of a long harness: a supply filter, an output
build-out, and the straps on headers.

| Ref | Part | Value | Package | Why |
|---|---|---|---|---|
| U1 | MAX9814ETD+ | | TDFN-14, 3 × 3 mm | exposed pad to GND; pins 4 and 11 to GND; `SHDN` to VDD, never left open |
| MK1 | electret capsule | 9.7 mm, omnidirectional, −44 dB, 2.2 kΩ load | 2 pins, THT | the size and kind on today's module; *check* the part number in stock |
| R1 | microphone bias | 2.21 kΩ | 0603, 1 % | `MICBIAS` to the capsule |
| C1 | input coupling | 100 nF **C0G** | 0805 | the datasheet asks for a low-voltage-coefficient dielectric here; with `MICIN`'s 100 kΩ, a 16 Hz corner |
| R2, R3 | AGC threshold | 150 kΩ to `MICBIAS`, 100 kΩ to GND | 0603, 1 % | `TH` at 0.8 V: the output is held at 1.6 Vpp |
| C2 | timing, `CT` | 470 nF | 0603 X7R | attack 1.1 ms; release 550 ms at A/R 1:500 |
| C3 | offset, `CG` | 2.2 µF | 0603 X5R | datasheet |
| C4 | bias, `BIAS` | 470 nF | 0603 X7R | datasheet |
| C5, C6 | VDD bypass | 1 µF and 100 nF, at pin 5 | 0603 | datasheet |
| R4, C7 | supply filter | 33 Ω, 22 µF | 0603; 0805 X5R 10 V | the harness 5 V also feeds NeoPixels; a 219 Hz corner for a 0.10 V drop |
| R5 | output build-out | 470 Ω | 0603 | the MAX9814 drives at most 200 pF and a body cable is that much on its own; with 1 nF of cable the corner is 339 kHz |
| JP1 | `GAIN` strap | 1 × 3 header and shunt: GND – `GAIN` – VDD | THT, 2.54 mm | **shunt on VDD: 40 dB**, Thomas's bench setting; GND 50 dB; no shunt 60 dB |
| JP2 | `A/R` strap | 1 × 3 header and shunt: GND – `A/R` – VDD | THT, 2.54 mm | **shunt on GND: 1:500**, Thomas's bench setting; VDD 1:2000; no shunt 1:4000 |
| D1, R6 | power LED | green, 2.2 kΩ | 0603 | on the harness 5 V, before the filter: lit means 5 V is arriving |
| J1 | JST EH 3, B3B-EH-A | | THT, vertical | the harness boards' order, below |
| TP1, TP2 | test pins | 1 × 1 header | THT, 2.54 mm | `OUT` (`MICOUT`, before R5) and `GND`, for a Dupont lead or a scope |

**The output stays DC-coupled.** The datasheet adds an output capacitor
to remove the 1.23 V bias; this board leaves it out on purpose, because
the bias is the reading that tells a live microphone (1.23 V) from an
unplugged one (0 V) and from a dead one, and the shield backplane and
the Teensy read DC.

**What it puts out**: 1.23 V at rest, **held at 1.6 Vpp (0.43–2.03 V)**
by the threshold, and by the datasheet never more than 2.0 Vpp or above
2.45 V. Inside the Teensy's 3.3 V with room to spare, as `shields`
section 4c requires, and close to today's module, measured at 1.44 Vpp.

**The connector, as on the harness boards' microphone sockets** —
`female base` `J3` and `male static` `J3`, read out of their copper:

| J1 pin | Signal |
|---|---|
| 1 | `GND` |
| 2 | `+5V` |
| 3 | `OUT` |

The cable is a 3-way JST EH lead, **pin 1 to pin 1**, its signal wire
twisted with ground.

---

## 4. Where it goes on a body

- **On the body's own profile, capsule facing the room**, never facing
  the profile or a panel.
- **About 10 cm from the body's own speaker**, TJ's spacing in his 2018
  model, on the side of the spine away from it where there is one. Its
  own voice will still be the loudest thing it hears; the program
  ignores a body's own bin, and TJ's males listened between signals.
- **Away from the servo** where the profile allows; step 3 says whether
  it matters.
- **The cable away from the speaker leads and the NeoPixel line**.

---

## 5. Silkscreen

Capitals as given, at least 0.8 mm high; `______` is a white box to
write in.

| Where | Text |
|---|---|
| top | `COLLOQUY · MICROPHONE · REV A` and `BODY ______` |
| by the capsule | `MIC · FACE THE ROOM` |
| by JP1 | `GAIN · VDD 40 dB · GND 50 dB · NONE 60 dB` |
| by JP2 | `A/R · GND 1:500 · VDD 1:2000 · NONE 1:4000` |
| by J1 | `1 GND · 2 5V · 3 OUT` |
| by D1 | `5V` |
| by TP1, TP2 | `OUT · 1.23 V` and `GND` |
| by each hole | `M5` |
| bottom | `NO PARTS · NYLON SPACER 5 mm · M5 T-NUT FOR THE SLOT` |

---

## 6. SMD and through-hole

Every resistor, capacitor, the LED and the MAX9814 are SMD and placed by
the assembler. Through-hole: the capsule, `J1`, the two strap headers and
the two test pins. The MAX9814's TDFN is fine-pitch with an exposed pad:
it is an assembler's part, not a hand-soldering one.

---

## 7. Parts, rough

About **EUR 4–8 a board** in a batch of six, assembled, plus about EUR 1
of fixings per board. The MAX9814 and the capsule are most of it.

---

## 8. What is open

- **The caliper check** on each body's profile, and the T-nut it decides.
- **The capsule's part number**: the 9.7 mm, −44 dB electret on today's
  modules, from a maker still selling it.
- **Step 3**: whether the frame carries servo noise to the microphone,
  and so nylon or rubber.
- **Where a male's profile is**: the videos show the females' clearly
  and the males' less so.
