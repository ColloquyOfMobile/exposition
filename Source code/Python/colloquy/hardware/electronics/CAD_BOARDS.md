# The boards in `CAD/`

**What each design file in the repository's `CAD/` folder is, where the
board sits in the piece, and which document says more about it.** Six
printed circuit boards are designed there, plus one third-party module
that one of them carries. Every size, part count and connector below was
read out of the design files themselves with KiCad 9.0.7's own `pcbnew`
on 2026-09-30, not remembered. **Pinouts are deliberately not restated
here**: `harness` reads them out of the copper every time it is opened,
and `as built` does the same for the rack board. A second copy of a
pinout is a pinout that can be wrong.

The four harness-board pictures are 3D renders of the design files, not
photographs, made with `kicad-cli pcb render --side top --quality high
--width 900 --height 900`. The DSUB connectors draw as outlines only,
because KiCad has no 3D model for their footprint. After a board changes,
render it again into `server2/static/hardware/board-<name>.jpg`.

## The boards at a glance

| Board | Folder | How many in the piece | Size (mm) | Parts | Status | Pinouts and detail |
|---|---|---|---|---|---|---|
| electronic box | `CAD/KiCad/electronic box/` | 1, in the rack | 210 x 297 (A4) | 46 | in service, reworked by hand | `as built`, `dirty rework` |
| center | `CAD/KiCad/center/` | 1, on the bar | 105 x 135.5 | 6 | in service | `harness` |
| female static | `CAD/KiCad/female static/` | 3, one at each female's joint | 50 x 110 | 3 | in service | `harness` |
| female base | `CAD/KiCad/female base/` | 3, one inside each female | 50 x 80 | 6 | in service | `harness` |
| male static | `CAD/KiCad/male static/` | 2, one inside each male | 50 x 90 | 11 | in service | `harness` |
| colloquy control v2 | `CAD/KiCad/electronic box v2/colloquy-control-v2/` | 1, would replace the electronic box | 210 x 297 (A4) | 132 | **being designed; not committed** | `next pcb`, and the project's own `README.md` |
| TPA2005D1 breakout | `CAD/Eagle/Mono Audio Amp (TPA2005D1) v10/` | 5, plugged onto the electronic box | 20.3 x 20.3 | 25 | third-party (SparkFun), in service | this document |

Every board is **two copper layers on 1.6 mm FR-4**. The five KiCad
boards in service were drawn in KiCad 8 (the three body boards) and
KiCad 9 (`center` and the rack board). None of them fills in its title
block, so a revision letter or a date is never printed on the copper;
**`git log` is the only revision history they have.**

## How they connect

The rack board has four DSUB-15 connectors, and everything else hangs off
them through fixed cables:

```
electronic box ── J5 ──────────────── female static ── female base   (female1)
               ── J1 ──────────────── female static ── female base   (female2)
               ── A-J3 ─┐
               ── B-J4 ─┴─ center ─┬─ female static ── female base   (female3)
                                   ├─ male static                    (male1)
                                   └─ male static                    (male2)
```

**`center` is the only board that splits anything.** It takes the rack's
two shared connectors (`A-J3` and `B-J4`) and hands female3, male1 and
male2 a DSUB-15 each. That is why those three bodies share one +5 V
conductor, `A-J3` pin 9, which `next pcb` section 5 names as the number
to check before hanging any more current on it.

**None of the harness boards has an active component.** They are
connectors and copper: a DSUB on the way in, and either another DSUB on
the way out or one small JST connector per thing in the body. The same
fact is what lets `one board per body` and `ad9833 dual mode` put a
processor on `female base` and `male static` without touching the
harness.

---

## electronic box

The board in the rack, and the only one in service with anything on it
besides connectors. It carries the **Arduino Mega 2560 as a shield**
(`A1`, mounted on the back), the **U2D2** on its own mount (`U1`), **five
SparkFun TPA2005D1 amplifier breakouts** each with a volume pot
(`RV1`-`RV5`), and the four DSUB-15 connectors to the bodies (`J5`
female1, `J1` female2, `A-J3` and `B-J4` shared through `center`).

![The electronic box, front copper](/static/hardware/electronic-box-layout.svg)

| What | Parts |
|---|---|
| power in | DC jack `J2` (PJ-082BH, 10 A), screw bridge `J6`, reservoir `C1` |
| servo bus | JST `J7` (GND, 12 V, Dynamixel data) and the U2D2 mount |
| break-outs of Mega pins | `J4`, `J8`, `J10` (a straight 1:1 breakout of D0-D21), `J9` (2 x 18) |
| microphone and photosensor break points | `J11`, `J12` (2 x 8, each row two separate nets joined only by what is fitted across it) |
| state LED drivers | `Q1`, `Q2` (BC557) with `R1`-`R4` and jumpers `J13`-`J16` |
| spare conductors | `Extra1`, `Extra2` (six each, for female2 and female1) |
| test points | one per speaker, plus `dxl_data` and `center/extra1` |

**The copper is not the whole story.** Thomas's audio subsystem was put
into this board by hand: five track cuts and fourteen wires
(`dirty rework`). The KiCad file shows the board before that. The
two findings that made the rework small, the 1:1 breakout and the break
points, are explained in `as built`.

Files: `electronic box.kicad_pcb`, `.kicad_sch`, `.kicad_pro`.
`schematics.v1.pdf` in `docs/` is the schematic exported from it.

---

## center

On the bar. It is the junction between the rack's two shared connectors
and the three bodies they serve.

![center, top view](/static/hardware/board-center.jpg)

| Connector | Label on the board | Kind |
|---|---|---|
| `J3` | to electronic box A | DSUB-15, female |
| `J6` | to electronic box B | DSUB-15, female |
| `J1` | to female static | DSUB-15, male (female3) |
| `J4` | to male 1 | DSUB-15, male |
| `J7` | to male 2 | DSUB-15, male |
| `J2` | dxl center | JST EH, 3 pins (the bar's own servo tap) |

Two 8 mm holes. 189 track segments, 2 vias, no copper pour. The
silkscreen says which gender of connector goes where ("male connector
here", "female connector here"), which is the one thing that is easy to
get wrong at assembly.

---

## female static

At a female's joint, one per female. A pass-through: the cable from the
rack (or from `center`, for female3) comes in on one DSUB, and the cable
down into her body leaves on the other. The one thing it takes off the
cable is the servo line for the female's own body.

![female static, top view](/static/hardware/board-female-static.jpg)

| Connector | Label on the board | Kind |
|---|---|---|
| `J1` | to center/electronic box | DSUB-15, female |
| `J3` | to female base | DSUB-15, male |
| `J2` | dxl female | JST EH, 3 pins |

Two 8 mm holes.

---

## female base

Inside a female, one per female. The end of her cable: every conductor
on it goes to one small connector per thing in her body.

![female base, top view](/static/hardware/board-female-base.jpg)

| Connector | Label on the board | Pins, as printed |
|---|---|---|
| `J7` | (from female static) | DSUB-15, female |
| `J2` | dxl mirror | GND, 12 V, data |
| `J4` | photosensor | GND, 5 V, data |
| `J5` | neopixel | GND, 5 V, data |
| `J3` | microphone | GND, 5 V, data |
| `J6` | speaker | speaker +, speaker - |

Two 8 mm holes. **The servo on this board is the mirror's, not the
body's**: the body servo is tapped off one board up, on `female static`.
50 x 80 mm is the outline `one board per body` and `ad9833 dual mode`
reuse for a populated body board.

---

## male static

Inside a male, one per male. The male's equivalent of `female base`,
with more on it: a male has four light sensors, a state LED and a
second NeoPixel line for the up-ring on the bar.

![male static, top view](/static/hardware/board-male-static.jpg)

| Connector | Label on the board | Kind |
|---|---|---|
| `J7` | (from center) | DSUB-15, female |
| `J1`, `J4`, `J8`, `J9` | photosensor (x 4) | JST EH, 3 pins |
| `J3` | microphone | JST EH, 3 pins |
| `J5` | body neopixel | JST EH, 3 pins |
| `J11` | bar neopixel | JST EH, 3 pins |
| `J10` | state LED | JST EH, 2 pins |
| `J6` | speaker | JST EH, 2 pins |
| `J2` | dxl male | JST EH, 3 pins |

One 8 mm hole and a slot open to the bottom edge. The male has no
static board of his own at a joint: his servo tap is here, on the board
inside him. 50 x 90 mm is the outline the populated body boards reuse.

---

## colloquy control v2

**The replacement for the electronic box, and it is being designed right
now.** It appeared on 2026-09-29 and was still being edited on
2026-09-30 (last write 11:07). **Nothing in this folder is committed**,
so the other computer cannot see it. Its own `README.md` and
`CIRCUIT_NOTES.md` describe it; `MECHANICAL_REVIEW.md` one folder up
holds the mechanical decisions.

As read on 2026-09-30:

| | |
|---|---|
| outline | 210 x 297 mm, the electronic box's own, with 5 mm corners |
| schematic | ten sheets: power, controller, harness, I/O, and one sheet per voice |
| parts | 132 footprints: Mega shield and U2D2 mount as before, the four DSUB-15s in their old positions, five MSGEQ7s in DIP-8 sockets with their full support network, five passive two-stage transmit filters, 11 photosensor shunts (10 K, provisional), test pads, jumpers |
| copper | 1,235 track segments, 59 vias, 8 zones; routing in progress |
| mounting | four new M3 holes (`H1`-`H4`), the U2D2's and the DC jack's holes kept |

**It is built for Thomas's chain, not for the AD9833.** Its five audio
sheets are fixed-pitch filters feeding the body amplifiers.
`ad9833 dual mode` section 3 says what changes: the filters give way to
five AD9833 voice channels, and an RS-485 transceiver on the Mega's
Serial1 and the mode jumpers are added. The U2D2 mount stays as it is. Everything else on it carries over.

The older generated files beside it (`NETLIST.md`, `BOM.md`,
`MECHANICAL.md`, `next_pcb.net`) come from `py next_pcb.py` and describe
the same board at an earlier, incomplete stage. The project's README
says the generator does not regenerate the KiCad project.

---

## TPA2005D1 breakout (Eagle)

**Not ours**: SparkFun's *Mono Audio Amp Breakout*, version 10, drawn by
M. Grusin and released under Creative Commons BY-SA (printed on the
board). It is in the repository because the electronic box carries five
of them, and its footprint is on that board.

| | |
|---|---|
| outline | 20.3 x 20.3 mm (0.8 in square) |
| amplifier | TPA2005D1 in QFN-8 (`U1`), class D, mono |
| gain | set by `R1`/`R2` = 150 K; `R1A`/`R2A` are through-hole positions left unfitted, for changing it |
| headers | `JP1` power (+, -, S), `JP2` in (+, -), `JP3` out (+, -), `JP4` volume (a potentiometer) |
| also on it | decoupling (`C1`-`C4`), a transistor, LED and resistors (`Q1`, `LED1`, `R3`-`R5`), solder jumper `SJ1` |

The **S** pin is the amplifier's shutdown. On the electronic box it is
tied permanently to +5 V, so no amplifier can be muted from software
(`as built` section 4). The TPA2005D1 runs from 2.5 to 5.5 V (its
datasheet, `CAD/KiCad/TPA2005D1_datasheet.pdf`), which is one reason
`next pcb` section 5 treats the amplifier rail as open.

Files: the Eagle `.brd` and `.sch`, and a `.kicad_pro` from a KiCad
import that was started and never finished: there is no KiCad board or
schematic beside it.

---

## Also in `CAD/`, and not boards

- **`CAD/Freecad/`**: five sketches, `<board> edge cut`, one for each
  board in service (`center`, `electronic box`, `female base`,
  `female static`, `male static`). These are the board outlines. The v2
  board has none because it inherits the electronic box's outline.
- **`CAD/KiCad/*.pdf`**: datasheets for parts on the boards: the
  PJ-080BH and PJ-082BH DC jacks, a barrel jack, a backlight LED and the
  TPA2005D1.
- **`CAD/Blender/`**: `scenarios.blend`, `pulse definition.blend`,
  `video analysis.blend`. Not board designs, and not described here.
