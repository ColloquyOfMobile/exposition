# The next PCB — bill of materials

**Generated. Do not edit.** Run `py next_pcb.py` from the repo root after changing `colloquy/hardware/electronics/next_pcb.py`.

## Decided

| Kind | Value | Qty | References |
|---|---|---|---|
| analyser | **MSGEQ7** | 5 | U1, U2, U3, U4, U5 |
| board | **Arduino Mega 2560** | 1 | A1 |
| board | **U2D2** | 1 | M1 |
| capacitor | **100nF** | 1 | C2 |
| capacitor | **10nF** | 2 | C501, C502 |
| capacitor | **150nF** | 2 | C301, C302 |
| capacitor | **220nF** | 2 | C201, C202 |
| capacitor | **470nF** | 2 | C101, C102 |
| capacitor | **470uF** | 1 | C1 |
| capacitor | **47nF** | 2 | C401, C402 |
| connector | **1x1 pad** | 1 | Extra3 |
| connector | **1x6 header** | 2 | Extra1, Extra2 |
| connector | **DC jack** | 1 | J2 |
| connector | **DSUB-15** | 4 | A-J3, B-J4, J1, J5 |
| connector | **JST EH 3** | 1 | J7 |
| connector | **screw bridge** | 1 | J6 |
| link | **0R** | 6 | JP1, JP2, JP3, JP4, JP5, JP6 |
| resistor | **100R** | 5 | R103, R203, R303, R403, R503 |
| resistor | **10K** | 1 | RS1 |
| resistor | **1K2** | 2 | R301, R302 |
| resistor | **1K8** | 2 | R401, R402 |
| resistor | **2K** | 2 | R201, R202 |
| resistor | **2K2** | 4 | R101, R102, R501, R502 |
| resistor | **330R** | 9 | RA1, RA2, RN1, RN2, RN3, RN4, RN5, RN6, RN7 |
| test point | **test pad** | 17 | TP1, TP11, TP12, TP13, TP14, TP15, TP2, TP20, TP21, TP3, TP30, TP31, TP32, TP33, TP34, TP4, TP5 |

---

## Not decided here — confirm before ordering

Neither group below is recorded in this repository, and neither is
the generator's to invent. They are kept apart rather than mixed in
above, because a plausible-looking number passing for a known one is
exactly how a board comes back wrong.

- **The MSGEQ7 support network.** The analyser array is five
  ready-made modules today (`HARDWARE_SETUP.md` section 4) and
  nobody here has drawn the chip. The values below are its
  datasheet's typical application, carried so the schematic has
  something to place. Read them off the datasheet before ordering,
  and take the pin numbering from it too — this netlist names the
  chip's terminals rather than numbering them, on purpose.
- **The light-sensor dividers.** `as built` records that the KiCad
  files do not say whether what sits across `J11`/`J12` is a shunt
  or a resistor, and that the light sensors work, so it is
  something. Measure one and put the number here.

| Kind | Value | Qty | References |
|---|---|---|---|
| capacitor | **100nF** | 5 | C115, C215, C315, C415, C515 |
| capacitor | **10nF** | 5 | C112, C212, C312, C412, C512 |
| capacitor | **33pF** | 5 | C114, C214, C314, C414, C514 |
| resistor | **200K** | 5 | R113, R213, R313, R413, R513 |
| resistor | **22K** | 5 | R111, R211, R311, R411, R511 |
| resistor | **TBC** | 11 | RP1, RP10, RP11, RP2, RP3, RP4, RP5, RP6, RP7, RP8, RP9 |
