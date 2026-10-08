# Shield assemblies — Blender / STEP reference

Created 2026-10-08 from the current shield PCB files. Open
[shield-configurations.blend](shield-configurations.blend) in Blender (5.2).
Use the **Scene selector at the top right** to switch between **Mega** and
**Teensy**. Repeated geometry is shared; each scene keeps its own objects,
placements, visibility and camera. The file opens on Mega.

The original individual files are also retained:

| File | Fitted configuration |
| --- | --- |
| [mega-configuration.blend](mega-configuration.blend) | Backplane, upside-down Mega 2560, five Thomas voice cards, analyser carrier, five modified DFRobot modules |
| [teensy-configuration.blend](teensy-configuration.blend) | Backplane, Teensy adapter, Teensy 4.1, five Thomas voice cards; analyser slot empty |

Each board has a named collection and a parent Empty for moving the whole board.
Components remain individually selectable. The files are self-contained and use
metric units displayed in millimetres (one Blender unit is one metre).
The saved camera and material viewport show the assembled state.

Six remote microphone board collections (five plus spare) are **hidden by default**.
Enable their monitor icon in the Outliner to inspect them beside the rack.
Their display positions are arbitrary: the specification does not define their
body-mounted locations. This is not a proposed mechanical mounting arrangement.

Previews: [Mega](mega-preview.png), [Teensy](teensy-preview.png).
Individual solid STEP and coloured GLB exports for all eight board types are
in [exports](exports/). STEP files can be opened in FreeCAD. These individual
exports use the PCB editor's absolute origin, with Cartesian Y inverted.

## Reference dimensions and limitations

- Backplane PCB is 210 × 297 mm. Board thickness is nominally 1.6 mm.
- Board-to-board mating gap is **11.04 mm**, based on 8.5 mm female socket
  body plus 2.54 mm male header body. This is a model assumption, not a measured
  spacer requirement. Adapter/carrier/voice PCB undersides are at Z=12.64 mm;
  Teensy/DFRobot undersides at Z=25.28 mm. The inverted Mega's component face
  is at Z=12.64 mm and its reverse face is nominally at Z=14.24 mm.
- Spacers show nominal 4 mm outside diameter / 3.2 mm bore. The computing
  slot requires front spacers no larger than 4 mm OD and screw heads on the rear,
  as documented by the PCB project. Screws, nuts, washers and cables are omitted.
- DFRobot geometry is corrected to the user's **22 × 34 mm** dimensions, with
  20.32 mm mounting-hole spacing retained. These are the modified plug-in modules,
  with replacement downward input/control headers. White output connector
  is now an SMD envelope wholly inside the outline. J4 pin 1 now aligns with
  J2J3 pin 6; the carrier control sockets have moved 1.27 mm to match.
  Retained 3.2 mm mounting holes break
  through the narrower side edges; their copper rings were reduced to 3.6 mm.
  Small component placements and connector shape are approximate. See the
  [module notes](../dfrobot-module/README.md).
- Mega planar geometry comes from the original Arduino Rev3e Eagle PCB;
  component bodies/heights are partly simplified. Its unused reserved POWER
  contact 1 has no matching backplane contact. See the
  [Mega notes](../arduino-mega-reference/README.md).
- Teensy uses the previously imported community model, including an inserted
  microSD card and added standard pin headers. It may represent an older hardware
  revision. See the [Teensy notes](../teensy41-reference/README.md).
- **Amber blocks** on the backplane are estimated J2 DC-jack and J6 screw-bridge
  envelopes. Their exact housing dimensions are unknown. The U2D2 mount is empty;
  no U2D2 body geometry was available in the PCB project.
- Remote microphones have a simple assumed Ø9.7 × 6 mm electret capsule and a
  3 × 3 × 0.8 mm U1 IC body added in Blender. The source U1 STEP model was
  unavailable. These bodies, the amber blocks and spacers are Blender additions;
  they are not included in the individual STEP/GLB board exports.
- Standard 2×3/2×11 connector models visually include the keyed absent pin.
  PCB pad positions remain correct; the standard model is an envelope reference.
- All five voice cards use the same physical geometry. Their collection names
  identify the five frequencies; purchased capacitor/resistor body sizes may differ.

This is an assembly size study, not a certified clash-free enclosure model or
a fabrication release. The source schematics, routing and production PCBs were
not changed for these exports.

## Validation and regeneration

The scripts check XY alignment of the mating contacts before saving. Validation
reopens both saved Blender files, checks board transforms, computing mounting
holes, overall scale, configuration populations and embedded assets. Results and
source PCB hashes are in [validation.json](validation.json). Rendered previews
were visually inspected. Contact alignment does not establish physical connector
engagement, purchased-part tolerances or clearance for cabling.

Run from this directory (adjust installed application paths if necessary):

```powershell
& 'C:/Program Files/KiCad/9.0/bin/python.exe' export_boards.py
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python-exit-code 1 --python build_assemblies.py -- mega
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python-exit-code 1 --python build_assemblies.py -- teensy
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python-exit-code 1 --python verify_assemblies.py
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python-exit-code 1 --python combine_scenes.py
```

`export_boards.py` creates ignored staging copies with added visual connector
bodies and resolves local KiCad model paths. It does not overwrite source PCBs.
Assembly manifests record all instance transforms in millimetres.
`combine_scenes.py` combines both files, shares identical meshes, and reopens
the result to verify scene populations, transforms and cameras. Its original
results are recorded in [combined-validation.json](combined-validation.json).
After the DFRobot comment correction, [dfrobot-update-validation.json](dfrobot-update-validation.json)
supersedes the earlier Blender file hashes and the earlier DFRobot alignment
checks. `update_dfrobot_geometry.py` replaces only module geometry in both Mega
and combined files, preserving user scene/placement edits. Do not rerun
`combine_scenes.py` over a user-edited combined file unless discarding those
scene edits is intended. The subsequent carrier correction is validated in
[carrier-update-validation.json](carrier-update-validation.json), which supersedes
the previous carrier mismatch and affected Blender hashes. Regenerate that
geometry in edited Blender files with `update_carrier_geometry.py`.
Imported Arduino, Teensy and KiCad component geometry retains its original
licensing and attribution; see the linked reference-project notes and their
retained source/license files.
