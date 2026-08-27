# The next PCB — mechanical envelope

**Generated. Do not edit.** Run `py next_pcb.py` from the repo root after changing `colloquy/hardware/electronics/next_pcb.py`.

Read out of `CAD/KiCad/electronic box/electronic box.kicad_pcb`, not
remembered. The enclosure was cut for that board; a replacement that
is a millimetre out in section 1 does not go in the rack.

---

## 1. The outline, which does not change

|  | Value |
|---|---|
| Size | **210 × 297 mm** (A4) |
| Corner radius | 5 mm, all four |
| Extent, x | 44.00 … 254.00 mm |
| Extent, y | 52.16 … 349.16 mm |

Keep the same origin as well as the same size. Every coordinate
below is in that file's frame, and a new board drawn at 0,0 would
make all of them arithmetic somebody has to redo by hand.

## 2. What the panel has a hole for

These positions are the enclosure's, not the layout's. Everything
else on the board is free.

| Ref | x, y | Rot | Edge | What it is |
|---|---|---|---|---|
| `J5` | 239.16, 322.66 | 90° | right, 14.84 mm in | female1's DSUB - right edge |
| `J1` | 58.00, 303.27 | -90° | left, 14.00 mm in | female2's DSUB - left edge |
| `A-J3` | 97.31, 334.96 | 0° | bottom, 14.20 mm in | female3 and male1's DSUB - bottom edge |
| `B-J4` | 179.66, 334.96 | 0° | bottom, 14.20 mm in | male1's audio and male2's everything - bottom edge |
| `J2` | 251.70, 61.17 | -90° | right, 2.30 mm in | the DC jack - right edge, near the top |
| `A1` | 141.16, 53.32 | -90° | top, 1.16 mm in | the Mega, whose USB socket the driver plugs into |
| `U1` | 49.00, 56.66 | 0° | top, 4.50 mm in | the U2D2's mount, whose USB lead has to reach out too |

Three edges carry connectors — two DSUBs on the bottom, one on the
left, one on the right — and the DC jack is on the right near the
top. The Mega and the U2D2 both sit along the top, because both of
their USB sockets have to be reachable.

## 3. Mounting holes: there are none

The exported NPTH drill file has a header, an `M30`, and not one
coordinate between them, and there is no `MountingHole` footprint on
the board either. An A4 board carrying a Mega 2560 as a shield, five
DSUB housings and a DC jack is held by nothing but those housings'
own jackscrews.

**Decide this on purpose for the next one.** It is four holes and a
keep-out, and the board is large enough to flex against a shield
with forty-odd pins in it.

## 4. The room the amplifiers free

Ten parts leave the board — five TPA2005D1 breakouts and their five
volume pots — because the amplifier moved to the body. They occupied
a band **161 mm wide and 43 mm tall** across the middle of the board:

|  | Value |
|---|---|
| x | 77.22 … 237.80 mm |
| y | 222.34 … 265.78 mm |
| Parts removed | 10 |

That is a bounding box of what was there, not a keep-out and not a
promise — the parts around it have not moved. But the filter stages
and the analyser array have to go somewhere, and this is the room
that appeared, in the half of the board nearest the body connectors.

## 5. What the placement has to respect

Not a layout — that is a person's job in front of a screen — but the
constraints the netlist and `NEXT_PCB.md` between them impose:

- **One analogue ground region** under the five filters and the five
  analysers, bonded to power ground at a single point (`JP1`).
- **The +5 V that leaves on the body connectors, and its return,
  must not run under the filter stages.** That rail now carries an
  amplifier's peaks at the far end of every cable.
- **Each filter channel next to the connector it feeds**, so the
  track from a tone pin to its own stage is short and unambiguous.
  The one fault this design cannot detect is a tone in the wrong
  channel, and a layout where that is obvious to the eye is worth
  more than a note about it.
- **The five analysers together**, since strobe and reset are
  commoned across all five and their outputs land on A0–A4.
- **Test pads reachable with the board in the rack**, or they are
  test pads for a board on a bench, which is not where it fails.
