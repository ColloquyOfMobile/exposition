# Shield assemblies — Blender / STEP reference

Created 2026-10-08 from the current shield PCB files. Open
[shield-configurations.blend](shield-configurations.blend) in Blender (5.2).
Use the **Scene selector at the top right** to switch between **Mega**,
**Teensy**, **Female body** and **Male body**. Repeated rack geometry is shared; each scene keeps its own objects,
placements, visibility and camera. The file opens on Mega.

The 2026-10-15 **Rev C microphone** study adds `Female body - mic left/right`
and `Male body - mic left/right`; the plain body scenes show the upward option.
These use the [32 × 62 mm slotted three-orientation holder](../microphone-flex/README.md).
The 2026-10-20 flex update replaces fixed gain/A/R links with removable JP1/JP2
selectors. Current orientation exports and body scenes include generic shunt
proxies at JP1 2-3 (40dB) and JP2 1-2 (1:500). Earlier Rev B references retain
their fixed links. Header/shunt dimensions and adjustment access require
physical checking.
Exactly one module is fitted in each scene. Select the scene and press Numpad 0
for its camera view. The prior edited body scenes are retained with
`ARCHIVE - ... Rev B reference` in their names. These retain their historical
geometry and must not be used to compare with current KiCad boards. The following original body-study description
still documents their nominal frame assumptions; current microphone views use Rev C and body boards use Rev D.
The [three-position preview](microphone-positions-preview.png) compares the
left, right and upward module choices on the same holder.

The 2026-10-19 revision D updates the six current body scenes: M1 is an 11-pin socket with three male-header groups,
the module sits at an approximately 11 mm underside height, and the two
adjustable insulating supports match it. No hand wires or flush-cut tails
are used. J6 and the analogue parts follow the paired, separated routing.
Rack scenes and retained Rev B references remain unchanged. The nominal
stack, pot height and actual module fit still require measurement.

### Visual parity audit — 2026-10-19

The earlier file-hash check did not establish visual parity. The GLB exporter
substituted an uncoloured STEP compound for KiCad's coloured GF1002 WRL model,
and omitted routed copper layers. All thirteen current board exports now use
KiCad's native VRML visual export, including its model choices, colours, copper,
mask and silkscreen. Engineering STEP exports are retained separately. The PCB
underside remains Z=0 in the assembly exports; no board placement is changed.

All current board instances in the combined, Mega and Teensy Blender files are
refreshed in place. The two historical Rev B body scenes retain their geometry
under explicit `ARCHIVE` names. Use **Female body**, **Male body**, or their
left/right microphone variants for the current revision D boards.
[visual-geometry-validation.json](visual-geometry-validation.json) supersedes
earlier Blender/export hashes. It records a comparison after saving and reopening:
actual vertices, face topology, assigned material colours, board transforms,
scene populations, PCB hashes and individual model dependency hashes. This
checks synchronization with the saved KiCad design, not manufactured fit.

To refresh all current geometry while preserving assembly placements and edits,
run from the repository root:

```powershell
& 'C:/Program Files/KiCad/9.0/bin/python.exe' 'CAD/KiCad/shields/assembly-3d/export_boards.py'
& 'C:/Program Files/KiCad/9.0/bin/python.exe' 'CAD/KiCad/shields/assembly-3d/export_body_boards.py'
& 'C:/Program Files/KiCad/9.0/bin/python.exe' 'CAD/KiCad/shields/microphone-flex/export_variants.py'
& 'C:/Program Files/Blender Foundation/Blender 5.2/blender.exe' --background --python-exit-code 1 --python 'CAD/KiCad/shields/assembly-3d/update_visual_geometry.py' -- --render
```

`visual_exports.py` prepares native visual data and fingerprints its dependencies;
`kicad_vrml.py` converts KiCad's tessellated visual data into coloured GLB.
`update_visual_geometry.py` backs up the original assemblies under ignored
`tmp/model-audit/backups/`, replaces current meshes, and performs the saved-file
comparison. These scripts do not edit source PCB routing or the production plots.

## Female and male body mounting studies — 2026-10-15

The combined file also contains **Female body** and **Male body** scenes.
Select a scene at the top right and use its camera view (Numpad 0) for the
overview. Each contains the current routed v2 body PCB, its directly mounted
GF1002 amplifier with an 11-pin socket and two adjustable insulating supports, and the socketed MAX9814
microphone holder assembly on a separate part of an aluminium profile.
Components and reference hardware remain individually selectable. The
original Mega and Teensy scenes and their object placements are preserved.
Previews: [Female](female-body-preview.png), [Male](male-body-preview.png).

**TJ's installed extrusion has not been identified.** Searches covered the
repository CAD and text, its mechanical-document history, and the local TJ
documentation. The earlier 20-series description was a video-based estimate;
the user identifies the installed profile as an American standard. These
scenes therefore use an explicitly unconfirmed **1 × 2 inch (25.4 × 50.8 mm)**
imperial envelope, with the six-slot arrangement described for
[80/20 1020](https://8020.net/1020.html). This is a comparison reference, not
evidence that TJ used 80/20 or this part number. Slot cavities, lips, corners
and solid internal core are simplified. No manufacturer CAD is reproduced.
The **240 mm length**, board-to-board spacing, orientation on the narrow face,
and body-board **5 mm underside gap** are display assumptions. Body fixing
centres follow the source cutouts: female 43 mm apart, male hole/slot 50 mm
apart. Body spacers are illustrative Ø12/Ø8 × 5 mm insulating supports;
the original artwork's screw and spacer specifications remain unconfirmed.

Microphone mounting follows the documented 50 mm hole spacing and separate
Ø10/Ø5.5 × 5 mm frame spacers; its existing seated-module geometry retains
the provisional 11.04 mm gap. All frame fixings lie on the profile's narrow
face centreline. T-nuts, screws, amplifier hookup wires and microphone leads
are omitted: their selection/routing needs the actual installation. The
microphone's distance from the speaker is not established by this study.
These views do not validate vibration isolation or actual frame/fastener fit.

Regenerate the two current body exports with KiCad Python:

```powershell
& 'C:/Program Files/KiCad/9.0/bin/python.exe' 'CAD/KiCad/shields/assembly-3d/export_body_boards.py'
```

Then run `add_body_scenes.py` with Blender's background Python. On a combined
file already containing these scenes, pass `-- --replace-body-scenes` to
replace only the generated body scenes. This deliberately discards edits to
those two scenes; edits to the rack scenes are retained and checked.
The script saves a backup under `tmp/body-model/`, stages and reopens the
result, verifies the original scenes' object membership, local transforms,
parents, camera and top-level collection visibility, checks frame dimensions
and microphone mounting alignment, then renders both new views.
`body-scenes-validation.json` records these checks and the current combined
file hash, superseding earlier combined-file hashes. Other assembly files
are not changed. PCB sources and amplifier/clamp models are not regenerated.

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
- Remote microphone holders now include the violet MAX9814 module, female
  socket and insulating M2 supports in their STEP/GLB exports. Module planar
  geometry comes from the local reference; socket/spacer heights are nominal.
  No separate capsule or bare-chip proxy is added in Blender. See
  [holder notes](../microphone/README.md) for physical-fit checks.
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
The 2026-10-13 front-SMD adapter update is recorded in
[adapter-update-validation.json](adapter-update-validation.json). Its hashes
supersede earlier hashes of the Teensy and combined Blender files.
`update_adapter_geometry.py` replaces the adapter geometry while preserving
assembly transforms and scene edits; the adapter STEP/GLB exports are refreshed.
Imported Arduino, Teensy and KiCad component geometry retains its original
licensing and attribution; see the linked reference-project notes and their
retained source/license files.
