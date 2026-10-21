# PCB assemblies

Open [shield-configurations.blend](shield-configurations.blend) for the combined
assembly. Use Blender's scene selector for Mega, Teensy, female/male bodies and
the left/right/up flex microphone options. Scenes named `ARCHIVE` retain the
older Rev B geometry for reference.

The individual rack files are [mega-configuration.blend](mega-configuration.blend)
and [teensy-configuration.blend](teensy-configuration.blend).

| Folder | Contents |
| --- | --- |
| `previews/` | Rendered assembly and microphone orientation images. |
| `exports/` | Board STEP/GLB exports and their source metadata. |
| `scripts/` | KiCad export, Blender build/update and verification tools. |
| `reports/` | Saved assembly validation reports and placement manifests. |
| `docs/` | Detailed assembly notes, assumptions and regeneration commands. |
| `backups/` | Local Blender autosave backups (ignored by Git). |
| `inputs/`, `logs/` | Local export intermediates and logs (ignored by Git). |

See [the assembly notes](docs/ASSEMBLY_NOTES.md) for how to refresh geometry
while preserving placements and scene edits. Reports record the earlier geometry
checks; moving this folder does not revalidate or modify the geometry.

PCB design sources remain in
[KiCad proposed solutions](../../KiCad/proposed-solutions/), and fabrication
packages remain in [KiCad production](../../KiCad/production/).
