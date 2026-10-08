# Arduino Mega 2560 Rev3e — mechanical reference

Open `arduino-mega-reference.kicad_pcb` in KiCad and press **Alt+3** for 3D.
`arduino-mega-reference.step` is the assembled reference for mechanical CAD.
All 3D dependencies are included in `3dmodels/`; `preview.png` shows the assembly.

The outline, six 3.2 mm mounting holes, component pad positions and connector
positions are extracted directly from **Arduino's original Rev3e Eagle board**,
not estimated from a photograph. The board outline spans **101.60 × 53.34 mm**
in this source file. Thickness is assumed to be **1.6 mm**.

This is an accurate reference for the manufacturer's planar geometry, with
**approximate component bodies**, not an exact production replica. Most bodies
use KiCad library STEP models. USB-B, reset switch, resonator, crystal, fuse and
USB-interface IC use simplified envelopes; their heights are representative.
The USB-B body footprint follows the original Eagle package outline.
Socket heights and connector housings may differ on the user's particular Mega
or clone. Check those details before relying on tight enclosure clearances.

No routing or schematic was reconstructed for this size/3D task. The original
manufacturer schematic and fully routed Eagle PCB are retained in `source/`.
The KiCad reference is not suitable for fabrication or electrical DRC.
Other installation PCB projects were not changed.

## Sources and attribution

- Arduino S.r.l., Mega 2560 Rev3e, downloaded 2026-10-08 from the
  [official Mega documentation](https://docs.arduino.cc/hardware/mega-2560).
- Original [CAD ZIP](https://docs.arduino.cc/static/00ab83283ad8f7aae17832d0fe1b1d51/A000067-cad-files.zip),
  preserved verbatim in `source/A000067-cad-files.zip`.
- Original hardware license: **CC BY-SA 4.0**, retained in
  `source/A000067-cad-files/License.txt`. This mechanical adaptation is shared
  under that license. Arduino names identify the source hardware, not an
  endorsement of this reconstruction.
- KiCad component library models: CC BY-SA 4.0 with the KiCad library exception.

## Regeneration and checks

Run `build_envelopes.py` with FreeCAD's Python, then `build_reference.py` with
KiCad 9's Python (numpy required). Installed library paths are at the top of the
script. `model-mapping.json` records which bodies are proxies. Its pad-fit error
is a model-alignment diagnostic, not the error of the imported original pads;
the dual-row socket has a numbering-side difference while its physical pin
grid remains aligned.

The STEP export uses Eagle's original origin, corresponding to (50,110) mm in
the translated KiCad board. Native board geometry and model paths were checked,
STEP export completed, and the 3D preview was inspected for connector direction
and placement. No physical sample fit or production validation is claimed.
