# Mechanical and assembly decisions

Review basis: the original `electronic box.kicad_pcb`, the generated
`MECHANICAL.md`, and `NEXT_PCB.md`. Coordinates below are millimetres in
the original board frame. These are design decisions for the new board;
enclosure fit and operating current still need physical verification.

## Board and fixed connectors

Retain the 210 × 297 mm outline, x = 44.00–254.00,
y = 52.16–349.16, with 5 mm corner radii. Use a two-layer, 1.6 mm
FR-4 board with nominal 35 µm copper on both sides.

| Reference | Position (x, y) | Rotation |
| --- | --- | --- |
| J5, female1 | 239.160, 322.660 | 90° |
| J1, female2 | 58.000, 303.270 | −90° |
| A-J3, female3/male1 | 97.305, 334.960 | 0° |
| B-J4, male1/male2 | 179.655, 334.960 | 0° |
| J2, DC input | 251.700, 61.170 | −90° |
| A1, Mega shield | 141.160, 53.320 | −90° |
| M1, U2D2 mounting | 49.000, 56.660 | 0° |

The Mega footprint describes the module on the **back** of the PCB.
Its body/connector envelope is approximately x = 140.17–195.49,
y = 46.65–155.25. Its USB connector deliberately overhangs the top
edge. Keep back-side components and standoffs outside this envelope.
Keep the U2D2 envelope, x = 48.75–106.05 and y = 56.41–104.71,
clear of new components on its mounting side.

## Mounting holes and cutouts

Add four 3.2 mm non-plated M3 standoff holes. Reserve an 8 mm diameter
area around each centre for washers, hardware, and copper clearance.
The asymmetric upper positions avoid the U2D2 and DC jack.

| Reference | Centre (x, y) |
| --- | --- |
| H1 | 52.00, 114.00 |
| H2 | 244.00, 82.00 |
| H3 | 52.00, 341.00 |
| H4 | 244.00, 341.00 |

These positions require matching enclosure standoffs; they are not
claims about holes already present in the enclosure. Their hardware
envelopes clear the fixed connector bodies. Recheck against the final
placement before manufacture.

The old board has mounting holes even though its NPTH drill export is
empty: they are circles on `Edge.Cuts` inside footprints. Preserve their
geometry, converting them to ordinary NPTH holes in the local footprints:

- M1: four 4.5 mm holes at (61.00, 59.66), (103.00, 59.66),
  (61.00, 101.66), and (103.00, 101.66).
- J2: one 1.6 mm locating hole at (248.95, 66.02).

No other internal cutouts are required for this revision. The original
Mega footprint has no embedded `Edge.Cuts` holes.

## Footprint and assembly checks

- Vendor the fixed footprints into the new project; their geometry is
  part of the enclosure interface.
- Retain J2's four plated retention slots, 0.8 × 2.0 mm. Enlarge their
  copper pads from 1.0 × 2.2 mm to 1.2 × 2.4 mm to provide a nominal
  0.2 mm annular ring. Confirm that the fabricator accepts plated slots.
- A1 has 92 pads without duplicate numbers or overlapping holes.
  The smallest pad gap is 0.8128 mm: a 0.30 mm track with 0.25 mm
  clearance fits, but has little margin. Prefer routing around headers.
- `5V1`–`5V4` are separate footprint numbers on the same Mega supply;
  similarly `GND1`–`GND6` are Mega ground. Their naming must not create
  unintended separate supplies or a second AGND bond.

## Provisional power envelope

Use at least 2 mm copper for long +5 V/+12 V trunks and a broad power
ground return. A 350 mm, 2 mm wide, 35 µm copper trace has approximately
0.086 Ω resistance at room temperature: about 0.17 V drop at 2 A before
adding the return, connectors, and harness. Track width alone does not
establish a safe installation current.

Use current-limited bring-up, initially no more than 2 A total per rail
and 1 A per powered DSUB branch. These are provisional test ceilings,
not verified connector ratings or guaranteed full-installation capacity.
Measure voltage drop and temperature with the actual harness and loads.
The body amplifier's permitted supply must come from its selected
datasheet; this board's +12 V distribution does not establish that an
existing amplifier can accept +12 V.
