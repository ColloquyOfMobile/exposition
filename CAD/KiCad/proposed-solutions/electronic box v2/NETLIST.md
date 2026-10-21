# The next PCB — netlist

**Generated. Do not edit.** Run `py next_pcb.py` from the repo root after changing `colloquy/hardware/electronics/next_pcb.py`.

Why it is generated: which body speaks at which pitch, out of which
timer pin and into which analyser module is one table, and the
firmware and four Python nodes already read it
(`colloquy/drivers/audio.py`). This reads the same one, so a channel
cannot be laid out against a pin the sketch does not drive.

`NEXT_PCB.md` is the specification and the reasoning; this is the
wiring. `AS_BUILT.md` is the board that exists today.

---

## 1. Every Mega pin

| Pin | Net |
|---|---|
| **D2** | `amp shutdown` |
| **D3** | `analyser/reset` |
| **D4** | `analyser/strobe` |
| **D5** | `male2/tone` |
| **D6** | `female1/tone` |
| **D7** | `female2/neopixel/driven` |
| **D8** | `female3/neopixel/driven` |
| **D9** | `male1/neopixel/driven` |
| **D10** | `female3/tone` |
| **D11** | `male1/tone` |
| **D14** | `female1/neopixel/driven` |
| **D15** | `male2/neopixel/driven` |
| **D16** | `male1/bar neopixel/driven` |
| **D17** | `male2/bar neopixel/driven` |
| **D24** | `male1/aux driven` |
| **D25** | `male2/aux driven` |
| **D46** | `female2/tone` |
| **A0** | `female1/analyser out` |
| **A1** | `female2/analyser out` |
| **A2** | `female3/analyser out` |
| **A3** | `male1/analyser out` |
| **A4** | `male2/analyser out` |
| **A5** | `female1/photosensor` |
| **A6** | `female2/photosensor` |
| **A7** | `female3/photosensor` |
| **A8** | `male1/photosensor/A` |
| **A9** | `male1/photosensor/B` |
| **A10** | `male1/photosensor/C` |
| **A11** | `male1/photosensor/D` |
| **A12** | `male2/photosensor/A` |
| **A13** | `male2/photosensor/B` |
| **A14** | `male2/photosensor/C` |
| **A15** | `male2/photosensor/D` |

Reserved, and deliberately on nothing:

| Pin | Why |
|---|---|
| **D0** | USB serial to the driver |
| **D1** | USB serial to the driver |
| **D13** | the Mega's own LED - the bootloader blinks it at every reset |
| **D20** | shares silicon with the SDA pad |
| **D21** | shares silicon with the SCL pad |

---

## 2. The five voices

Each tone pin feeds the filter channel of its own frequency and no
other. This is the one fault the whole design cannot detect: a
low-pass passes anything below its corner, so a tone in the wrong
channel still comes out, still lands in its own band and still
reports "heard". What is lost is the filtering, and the symptom is
poor detection in a noisy room months later. Silkscreen every stage
with its frequency and its pin.

| Body | Pitch | Timer | Pin | Filter R | Filter C | Build-out | Test pad |
|---|---|---|---|---|---|---|---|
| **male1** | 160 Hz | T1 | `D11` | R101 = R102 = 2K2 | C101 = C102 = 470nF | R103 = 100R | TP1 |
| **male2** | 400 Hz | T3 | `D5` | R201 = R202 = 2K | C201 = C202 = 220nF | R203 = 100R | TP2 |
| **female1** | 1000 Hz | T4 | `D6` | R301 = R302 = 1K2 | C301 = C302 = 150nF | R303 = 100R | TP3 |
| **female2** | 2500 Hz | T5 | `D46` | R401 = R402 = 1K8 | C401 = C402 = 47nF | R403 = 100R | TP4 |
| **female3** | 6250 Hz | T2 | `D10` | R501 = R502 = 2K2 | C501 = C502 = 10nF | R503 = 100R | TP5 |

---

## 3. The five ears

Strobe and reset are commoned across all five, so one cycle through
the seven bands reads every module at once — and reads them at the
same moment, which is the whole reason `read every microphone` is
one command rather than five.

| Body | Ref | Module | ADC | Its own band | Test pad |
|---|---|---|---|---|---|
| **female1** | U3 | module 0 | `A0` | band 3 | TP13 |
| **female2** | U4 | module 1 | `A1` | band 4 | TP14 |
| **female3** | U5 | module 2 | `A2` | band 5 | TP15 |
| **male1** | U1 | module 3 | `A3` | band 1 | TP11 |
| **male2** | U2 | module 4 | `A4` | band 2 | TP12 |

`analyser/strobe` on **D4**, `analyser/reset` on **D3**, both commoned to all five modules.

Module N is body N. Silkscreen the body name beside each module:
that mapping is the whole reason one number identifies a body all
the way round the loop, out of the timer, through the room and back
into the ADC.

---

## 4. The connectors, as the supplier fixes them

One substitution per body against `as built`: `speaker +/out` is now
the line out and `speaker -/out` its return, the amplifier having
moved to the body. Nothing else moves, and nothing is asked of the
supplier. Pin 0 is the shell.

### `J5` — DSUB-15, fixed by the supplier

| Pin | Net |
|---|---|
| shell | `GND` |
| 1 | `female1/spare1` |
| 2 | `female1/spare2` |
| 3 | `female1/spare3` |
| 4 | `female1/audio return` |
| 5 | `female1/photosensor` |
| 6 | `female1/microphone` |
| 7 | `+12V` |
| 8 | `GND` |
| 9 | `female1/spare4` |
| 10 | `female1/spare5` |
| 11 | `female1/spare6` |
| 12 | `female1/line out` |
| 13 | `female1/neopixel` |
| 14 | `dxl_data` |
| 15 | `+5V` |

### `J1` — DSUB-15, fixed by the supplier

| Pin | Net |
|---|---|
| shell | `GND` |
| 1 | `female2/spare1` |
| 2 | `female2/spare2` |
| 3 | `female2/spare3` |
| 4 | `female2/audio return` |
| 5 | `female2/photosensor` |
| 6 | `female2/microphone` |
| 7 | `+12V` |
| 8 | `GND` |
| 9 | `female2/spare4` |
| 10 | `female2/spare5` |
| 11 | `female2/spare6` |
| 12 | `female2/line out` |
| 13 | `female2/neopixel` |
| 14 | `dxl_data` |
| 15 | `+5V` |

### `A-J3` — DSUB-15, fixed by the supplier

| Pin | Net |
|---|---|
| shell | `GND` |
| 1 | `GND` |
| 2 | `+12V` |
| 3 | `female3/microphone` |
| 4 | `female3/photosensor` |
| 5 | `female3/audio return` |
| 6 | `male1/neopixel` |
| 7 | `male1/photosensor/B` |
| 8 | `male1/photosensor/D` |
| 9 | `+5V` |
| 10 | `dxl_data` |
| 11 | `female3/neopixel` |
| 12 | `female3/line out` |
| 13 | `male1/microphone` |
| 14 | `male1/photosensor/A` |
| 15 | `male1/photosensor/C` |

### `B-J4` — DSUB-15, fixed by the supplier - CARRIES NO POWER, silkscreen it

| Pin | Net |
|---|---|
| shell | `GND` |
| 1 | `male1/aux` |
| 2 | `male1/audio return` |
| 3 | `male2/neopixel` |
| 4 | `male2/photosensor/B` |
| 5 | `male2/photosensor/D` |
| 6 | `male2/line out` |
| 7 | `centre/spare1` |
| 8 | `male2/bar neopixel` |
| 9 | `male1/line out` |
| 10 | `male2/microphone` |
| 11 | `male2/photosensor/A` |
| 12 | `male2/photosensor/C` |
| 13 | `male2/aux` |
| 14 | `male2/audio return` |
| 15 | `male1/bar neopixel` |

---

## 5. Every net

A net with one terminal is a mistake, and so is a Mega pin on two
signals. There are none of either here, and
`pytest_tests/hardware/test_next_pcb.py` fails if one appears.

| Net | Terminals | On |
|---|---|---|
| `+12V` | 4 | J7.2, J5.7, J1.7, A-J3.2 |
| `+5V` | 9 | J6.3, C1.1, C2.1, J2.1, J5.15, J1.15, A-J3.9, RS1.2, TP31.1 |
| `AGND` | 33 | JP1.1, C301.2, C302.2, JP4.2, C401.2, C402.2, JP5.2, C501.2, C502.2, JP6.2, C101.2, C102.2, JP2.2, C201.2, C202.2, JP3.2, U3.GND, U4.GND, U5.GND, U1.GND, U2.GND, RP1.2, RP2.2, RP3.2, RP4.2, RP5.2, RP6.2, RP7.2, RP8.2, RP9.2, RP10.2, RP11.2, TP34.1 |
| `GND` | 15 | J6.4, C1.2, C2.2, J2.2, J7.1, A1.GND, JP1.2, J5.0, J5.8, J1.0, J1.8, A-J3.0, A-J3.1, B-J4.0, TP33.1 |
| `MEGA_5V` | 7 | A1.5V, U3.VDD, U4.VDD, U5.VDD, U1.VDD, U2.VDD, TP32.1 |
| `amp shutdown` | 3 | A1.D2, RS1.1, TP30.1 |
| `analyser/reset` | 7 | A1.D3, U3.RESET, U4.RESET, U5.RESET, U1.RESET, U2.RESET, TP21.1 |
| `analyser/strobe` | 7 | A1.D4, U3.STROBE, U4.STROBE, U5.STROBE, U1.STROBE, U2.STROBE, TP20.1 |
| `centre/spare1` | 2 | B-J4.7, Extra3.1 |
| `dxl_data` | 5 | M1.data, J7.3, J5.14, J1.14, A-J3.10 |
| `female1/analyser out` | 3 | U3.OUT, A1.A0, TP13.1 |
| `female1/audio return` | 2 | J5.4, JP4.1 |
| `female1/filter mid` | 3 | R301.2, C301.1, R302.1 |
| `female1/filter out` | 4 | R302.2, C302.1, R303.1, TP3.1 |
| `female1/line out` | 2 | J5.12, R303.2 |
| `female1/microphone` | 2 | J5.6, U3.IN |
| `female1/neopixel` | 2 | J5.13, RN1.2 |
| `female1/neopixel/driven` | 2 | A1.D14, RN1.1 |
| `female1/photosensor` | 3 | J5.5, A1.A5, RP1.1 |
| `female1/spare1` | 2 | J5.1, Extra2.1 |
| `female1/spare2` | 2 | J5.2, Extra2.2 |
| `female1/spare3` | 2 | J5.3, Extra2.3 |
| `female1/spare4` | 2 | J5.9, Extra2.4 |
| `female1/spare5` | 2 | J5.10, Extra2.5 |
| `female1/spare6` | 2 | J5.11, Extra2.6 |
| `female1/tone` | 2 | A1.D6, R301.1 |
| `female2/analyser out` | 3 | U4.OUT, A1.A1, TP14.1 |
| `female2/audio return` | 2 | J1.4, JP5.1 |
| `female2/filter mid` | 3 | R401.2, C401.1, R402.1 |
| `female2/filter out` | 4 | R402.2, C402.1, R403.1, TP4.1 |
| `female2/line out` | 2 | J1.12, R403.2 |
| `female2/microphone` | 2 | J1.6, U4.IN |
| `female2/neopixel` | 2 | J1.13, RN2.2 |
| `female2/neopixel/driven` | 2 | A1.D7, RN2.1 |
| `female2/photosensor` | 3 | J1.5, A1.A6, RP2.1 |
| `female2/spare1` | 2 | J1.1, Extra1.1 |
| `female2/spare2` | 2 | J1.2, Extra1.2 |
| `female2/spare3` | 2 | J1.3, Extra1.3 |
| `female2/spare4` | 2 | J1.9, Extra1.4 |
| `female2/spare5` | 2 | J1.10, Extra1.5 |
| `female2/spare6` | 2 | J1.11, Extra1.6 |
| `female2/tone` | 2 | A1.D46, R401.1 |
| `female3/analyser out` | 3 | U5.OUT, A1.A2, TP15.1 |
| `female3/audio return` | 2 | A-J3.5, JP6.1 |
| `female3/filter mid` | 3 | R501.2, C501.1, R502.1 |
| `female3/filter out` | 4 | R502.2, C502.1, R503.1, TP5.1 |
| `female3/line out` | 2 | A-J3.12, R503.2 |
| `female3/microphone` | 2 | A-J3.3, U5.IN |
| `female3/neopixel` | 2 | A-J3.11, RN3.2 |
| `female3/neopixel/driven` | 2 | A1.D8, RN3.1 |
| `female3/photosensor` | 3 | A-J3.4, A1.A7, RP3.1 |
| `female3/tone` | 2 | A1.D10, R501.1 |
| `male1/analyser out` | 3 | U1.OUT, A1.A3, TP11.1 |
| `male1/audio return` | 2 | B-J4.2, JP2.1 |
| `male1/aux` | 2 | B-J4.1, RA1.2 |
| `male1/aux driven` | 2 | A1.D24, RA1.1 |
| `male1/bar neopixel` | 2 | B-J4.15, RN6.2 |
| `male1/bar neopixel/driven` | 2 | A1.D16, RN6.1 |
| `male1/filter mid` | 3 | R101.2, C101.1, R102.1 |
| `male1/filter out` | 4 | R102.2, C102.1, R103.1, TP1.1 |
| `male1/line out` | 2 | B-J4.9, R103.2 |
| `male1/microphone` | 2 | A-J3.13, U1.IN |
| `male1/neopixel` | 2 | A-J3.6, RN4.2 |
| `male1/neopixel/driven` | 2 | A1.D9, RN4.1 |
| `male1/photosensor/A` | 3 | A-J3.14, A1.A8, RP4.1 |
| `male1/photosensor/B` | 3 | A-J3.7, A1.A9, RP5.1 |
| `male1/photosensor/C` | 3 | A-J3.15, A1.A10, RP6.1 |
| `male1/photosensor/D` | 3 | A-J3.8, A1.A11, RP7.1 |
| `male1/tone` | 2 | A1.D11, R101.1 |
| `male2/analyser out` | 3 | U2.OUT, A1.A4, TP12.1 |
| `male2/audio return` | 2 | B-J4.14, JP3.1 |
| `male2/aux` | 2 | B-J4.13, RA2.2 |
| `male2/aux driven` | 2 | A1.D25, RA2.1 |
| `male2/bar neopixel` | 2 | B-J4.8, RN7.2 |
| `male2/bar neopixel/driven` | 2 | A1.D17, RN7.1 |
| `male2/filter mid` | 3 | R201.2, C201.1, R202.1 |
| `male2/filter out` | 4 | R202.2, C202.1, R203.1, TP2.1 |
| `male2/line out` | 2 | B-J4.6, R203.2 |
| `male2/microphone` | 2 | B-J4.10, U2.IN |
| `male2/neopixel` | 2 | B-J4.3, RN5.2 |
| `male2/neopixel/driven` | 2 | A1.D15, RN5.1 |
| `male2/photosensor/A` | 3 | B-J4.11, A1.A12, RP8.1 |
| `male2/photosensor/B` | 3 | B-J4.4, A1.A13, RP9.1 |
| `male2/photosensor/C` | 3 | B-J4.12, A1.A14, RP10.1 |
| `male2/photosensor/D` | 3 | B-J4.5, A1.A15, RP11.1 |
| `male2/tone` | 2 | A1.D5, R201.1 |
