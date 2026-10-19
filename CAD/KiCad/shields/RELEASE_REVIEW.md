# Release review: shields set, first order

The reviewer's own pass before any board in this folder is ordered. The
designs' own documents (README, REVIEW, VALIDATION, ASSEMBLY,
MANUFACTURING, `SHIELDS.md`) say what was drawn and what was checked by
script. This sheet records what a person checked, what was decided, and
who signed.

| | |
|---|---|
| Reviewer | |
| Reviewed at commit | (fill in when you start: `git rev-parse --short HEAD`) |
| Exhibition opening | (date; every lead time is counted back from it) |
| Fab chosen | PCBWay / JLCPCB |
| Status | in review |

## Where comments go

- **One finding = one row** in the findings table at the bottom: an ID,
  the board, *where* (reference, net, or `x, y` in mm as KiCad shows
  them, and the layer), what is wrong, how serious, what was decided.
- **To draw on something**, plot it to PDF (KiCad: File > Plot > PDF, or
  open the `reports/*.svg`), mark it up, save it as
  `review/<board>-<ID>.pdf` beside this file, and name it in the row.
- **Never write comments into a `.kicad_pcb` or `.kicad_sch`.** Any
  change to a board file changes its digest, marks both Gerber packages
  out of date (`test_pcb_files.py` fails until re-plotted), and the
  generator scripts can rewrite those files. Comments go here; fixes go
  in the board.
- Commit this sheet as you go: it is how the other computer, and the
  next Claude session, see it. "Address the review findings" is enough
  of an instruction to work from the table.

Severity: **blocker** (do not order), **fix** (fix before ordering),
**note** (next revision).

## 0. Checked by script, 2026-10-15 (no hardware connected)

- Both Gerber packages match the current boards: `py export_gerbers.py
  --check` reports all seven current, and each `manufacturing/*.zip`
  records the current `.kicad_pcb` hash.
- pytest: 1796 pass, 259 of them under `hardware/`. VALIDATION.md's note
  that pytest could not collect is out of date.
- Design-rule floors on the backplane and adapter: 0.15 mm track and
  space, 0.3 mm drill, 0.6 mm via. These are within the standard process
  at PCBWay and JLCPCB, so no advanced-process pricing applies.
- Native ERC/DRC 0/0/0 is as recorded on 2026-10-13 (VALIDATION.md). It
  was not re-run today; item 2.1 re-runs it.

Found, and still open:

| # | What | Why it matters |
|---|---|---|
| F1 | **BOMs carry almost no part numbers**: MPN blank on 115 of 116 backplane lines, 66 of 71 adapter, 10 of 12 microphone | an assembly order cannot be quoted or placed |
| F2 | **Two Gerber packages from the same layouts, in different forms.** `CAD/KiCad/production/` (served at `/download/gerbers`) is plotted `--no-x2 --no-netlist`, has paste layers for every board including the voice card and carrier, and has no job file or drill map. `shields/*/manufacturing/*.zip` is Gerber X2 with net attributes, a job file and drill maps, and paste only where the maker places SMD | whoever orders must know which one to send; the voice-card paste layer in `production/` may get a stencil quoted |
| F3 | **Placement files are KiCad's native CSV** (`Ref,Val,Package,PosX,PosY,Rot,Side`) | JLCPCB wants its own column names; rotations of polarised parts must be checked in the maker's placement preview whatever the format |
| F4 | **The documents disagree about release.** `README.md` says "no fabrication release or Gerber order package"; MANUFACTURING.md describes the packages; REVIEW.md is dated 2026-10-08 (basis `79e994b`) and predates the 2026-10-13 changes | the order must rest on one stated basis |
| F5 | **Fit is unproven where it was inferred**: DFRobot socket positions are photo-derived; the clone MAX9814's pin and hole grid and seated height; the Mega's USB-B shell against the 11 mm stack; HM1-HM4 spacers of 4 mm OD at most; every height against the enclosure | a board that does not fit is a re-order; each needs the real part on a 1:1 print |
| F6 | Board-setup minimums are 0 on the analyser carrier (clearance, track) and the voice card (track) | DRC there checks netclass values only, not what the fab can make |
| F7 | **Resolved, 2026-10-19:** carrier contacts 1 and 4 swapped at all five sites (microphone on L, R3 removed and R linked to OUT). Schematic, generators, routed board, silkscreen, mechanical notes, template, both Gerber packages and fit-check pack refreshed | Native ERC/DRC and unconnected counts 0/0/0; independent schematic/PCB and mating checks pass. Physical module fit remains F5. |
| F8 | **Layout corrected, physical fit still blocks the two body boards (2026-10-19).** GF1002 now has nine contacts along the long edge; both H2 clamps moved to the short edge, JA1 moved beside the row, and nearby components moved clear. STEP/VRML, previews, body scenes, Gerbers and 1:1 templates refreshed. Native ERC/DRC/parity and contact-strip clearance checks pass | User authorized documented estimates for this prototype. Measure a real module, verify ROUT pair polarity, cut pin tails flush and dry-fit before ordering. No shield board holds the GF1002, so the shields set is not affected |

## 1. Scope of this order (project manager)

`SHIELDS.md` section 0: **the exhibition depends on step 1 alone**, and
it can be ordered on its own.

| Board | Qty drawn | Step | In this order? | Qty to order |
|---|---|---|---|---|
| backplane, 4 layers, 210 x 297 mm | 1 | 1 | | |
| voice-thomas, 2 layers | 5 | 1 | | (spares, new pitches) |
| analyser-carrier, 2 layers | 1 | 1 | | |
| microphone holder, 2 layers | 6 | (decide) | | |
| teensy-adapter, 4 layers | 1 | 2 | | |
| female-base-v2, male-static-v2 | 3, 2 | not shields; physical fit pending (F8) | | |

- [ ] Decide what goes in this order. The adapter is step 2 and can wait.
      The microphone holders belong to no step yet.
- [ ] `/download/gerbers` offers all seven boards as one set, including
      the two body boards. Make sure the person ordering knows which are
      in.

## 2. Electrical review (engineer)

Order of work: backplane, voice card, analyser carrier, microphone
holder, then the adapter if it is in the order.

### 2.1 Every board

- [ ] Open the `.kicad_pro` in KiCad 9. Run ERC, then DRC with *Test for
      parity between PCB and schematic* ticked: 0 / 0 / 0.
- [ ] Board Setup > Constraints: set the minimums to the chosen fab's
      capability (F6) and re-run DRC.
- [ ] Open **the package you will send** (F2) in the Gerber viewer or
      the maker's online viewer, not the `.kicad_pcb`: every layer is
      there, the 4-layer stack is in order, the outline is closed, the
      drills sit in their pads, and no silkscreen lies on a pad.
- [ ] Check each footprint you are about to buy against its datasheet:
      pad size, pitch, pin 1. No script checks a land pattern against a
      real part.
- [ ] Polarity marks (electrolytic, diodes, LEDs, pin 1) are visible on
      silkscreen and agree with the 3D view.
- [ ] A revision and date are on the silkscreen.

### 2.2 Backplane

- [ ] **The mirrored Mega slot.** Print the front copper and Edge.Cuts at
      1:1, lay a real Mega on it **component side down**, and check every
      header pin and all four holes. This is the costliest possible
      mistake on the set: a wrong mirror swaps every pin.
- [ ] Under the Mega's USB-B and power jack there is nothing but mask.
      The shell is about as tall as the 11 mm stack (SHIELDS.md 2b).
- [ ] Harness: check one DSUB-15 pin for pin against v2 by eye. A test
      holds the positions and pinout to v2's `circuit.json`; this guards
      against both being wrong together.
- [ ] +12 V (servo supply): at least 2 mm wide, outer layers only (a DRC
      rule enforces it). Compare the worst-case servo current with the
      copper weight you will order, and choose 1 oz or 2 oz outer.
- [ ] Inner layers: the GND and +5V pours are broken by signal tracks
      (REVIEW.md). Look for splits under the tone lines and the direct
      microphone traces.
- [ ] AGND: JP1 is the only AGND-GND bond, and the microphone traces
      run over AGND, away from the tone lines.
- [ ] C1, 470 uF 25 V: which rail, voltage margin, polarity.
- [ ] Eight LEDs: polarity and series resistor values.
- [ ] Slot keying (pin 6/22 removed, cavity blocked) agrees between the
      backplane slots and the cards.
- [ ] Test pins and LEDs can be reached and seen with the board in the
      rack.

### 2.3 Voice card (one layout, five populations)

- [ ] Holes: R1/R2 at 7.62 mm pitch, C1/C2 at 5 mm pitch. Check the
      envelope against the **actual** film capacitors you will buy,
      470 nF included (7 x 6.5 mm reserved).
- [ ] The card cannot go into its slot the wrong way round.
- [ ] The five variant BOMs match Thomas's values (`voice-thomas/variants`).
- [ ] The pitch/body write-in box is on the front, the tick table on the
      back.

### 2.4 Analyser carrier

- [ ] Print `analyser-carrier/mounting-template.svg` at 100 %, check the
      50 mm scale bar, and lay **one converted module** on it: all eight
      pins and both holes. Do this before ordering (README there).
- [ ] Module 0 is rotated 180 degrees: the silkscreen shows it.
- [ ] The module conversion (R3 removed, R jumpered to OUT, microphone
      on L) is written where the person fitting it will read it, and the
      carrier's silkscreen says the same (F7).

### 2.5 Microphone holder

- [ ] Measure a real violet module: pin pitch, the 10.033 mm hole
      spacing, the header offset, and the seated height (11.04 mm
      nominal).
- [ ] J1 is GND / +5V / OUT, pin 1 to pin 1 with the existing harness.
- [ ] R1/R2 straps (40 dB gain, AR 1:500) match the modules in use now.
- [ ] M5 holes 50 mm apart on the actual artwork profile.

### 2.6 Teensy adapter (if in this order)

- [ ] CM1-CM5 beside the Teensy socket, clear of its body.
- [ ] Level translation on every 5 V line toward the Teensy.
- [ ] The Teensy stands tallest: check its height against the enclosure.

## 3. Ready to order (project manager)

- [ ] **Freeze**: write the reviewed commit above. If any board changes
      after it, re-plot and review the diff before ordering.
- [ ] **One package** chosen (F2). Recommended: the
      `shields/*/manufacturing/*.zip`, which carry the assembly policy
      (stencil only where the maker places parts).
- [ ] **Fab options** that MANUFACTURING.md leaves open: quantity, outer
      copper weight (2.2), finish, mask colour, the maker's standard
      4-layer stack-up, 1.6 mm.
- [ ] **Quote the backplane first**: 4 layers at 210 x 297 mm drives the
      cost.
- [ ] **Assembly BOM** (F1): an orderable part number for every SMD line
      on the backplane, adapter and microphone holder, checked for stock
      at the maker. The 470 uF electrolytic is the likeliest
      extended-library part.
- [ ] **Placement file** (F3) in the maker's format; check every rotation
      in their preview before paying.
- [ ] **Hand-fit parts bought in parallel**: DSUB-15s, gold headers and
      sockets, test pins, film capacitors, metal-film resistors, M3
      round spacers of 4 mm OD at most, M2 nylon supports, M5 hardware.
      Order spares.
- [ ] **Lead time** counted back from the opening: fab and assembly,
      shipping and customs, hand soldering, bring-up (SHIELDS.md
      section 10).
- [ ] **Each fit check in F5 has an owner and a date.** Who holds the
      DFRobot modules, a spare Mega, a violet module, the enclosure?
- [ ] **Fallback**: the board now in the rack stays until step 1 passes
      its acceptance test (`test audio loop`, then `test audio
      bringup`). Do not note it out before.
- [ ] **One stated basis** (F4): after sign-off, mark README and
      REVIEW "ordered at `<commit>`" and tag that commit.
- [ ] **Archive what was sent**: the exact zip, the maker's order number
      and the date, in the sign-off table.

## 4. Sign-off

| Board | Electrical (2) | Fit (F5) | Order (3) | Ordered: date, maker, order no. |
|---|---|---|---|---|
| backplane | | | | |
| voice-thomas | | | | |
| analyser-carrier | | | | |
| microphone | | | | |
| teensy-adapter | | | | |

## Findings

| ID | Board | Where | Finding | Severity | Decision | Status |
|---|---|---|---|---|---|---|
| R1 | | | | | | open |
