"""Refresh DFRobot mesh instances without overwriting user scene/placement edits.

Run with Blender --background --python-exit-code 1 --python this_file.py.
"""
from pathlib import Path
import bpy
import hashlib
import json
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
report = {'correction':'22 x 34 mm; SMD J1; J4 pin 1 aligned with J2J3 pin 6',
          'carrier_control_socket_mismatch_mm':1.27,'files':{}}
for filename in ('mega-configuration.blend','shield-configurations.blend'):
    path = ROOT/filename
    bpy.ops.wm.open_mainfile(filepath=str(path))
    roots = [o for o in bpy.data.objects if o.get('source_board') == 'dfrobot-module']
    assert len(roots) == 5, len(roots)
    original = {o.name:[list(r) for r in o.matrix_basis] for o in roots}
    existing = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'exports/dfrobot-module.glb'))
    imported = set(bpy.data.objects)-existing
    # Component J1 envelope must remain wholly within the corrected PCB outline.
    bpy.context.view_layer.update()
    j1 = next(o for o in imported if o.name == 'J1' or o.name.startswith('J1.'))
    # The named assembly parent can contain the actual mesh as a descendant.
    body = [o for o in [j1]+list(j1.children_recursive) if o.type == 'MESH']
    points = [o.matrix_world @ Vector(c) for o in body for c in o.bound_box]
    assert points
    bbox = [[min(p[i] for p in points)*1000,max(p[i] for p in points)*1000] for i in range(3)]
    assert bbox[0][0] >= 53.5 and bbox[0][1] <= 75.5, bbox
    assert bbox[1][0] >= -83 and bbox[1][1] <= -49, bbox
    for root in roots:
        collection = root.users_collection[0]
        for old in list(root.children_recursive):
            bpy.data.objects.remove(old,do_unlink=True)
        copies = {}
        for source in imported:
            copy = source.copy()
            copy.name = root.name+' / corrected '+source.name
            collection.objects.link(copy)
            copies[source] = copy
        for source,copy in copies.items():
            copy.parent = copies.get(source.parent,root)
            copy.matrix_local = source.matrix_local.copy()
        root['mechanical_revision'] = '2026-10-08 User.Comments correction'
        root['carrier_fit_note'] = 'J4 control socket positions differ by 1.27 mm; carrier not changed.'
    for obj in imported:
        bpy.data.objects.remove(obj,do_unlink=True)
    assert original == {o.name:[list(r) for r in o.matrix_basis] for o in roots}
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:bpy.data.meshes.remove(mesh)
    for scene in bpy.data.scenes:
        scene['dfrobot_fit_note'] = 'Corrected 22 x 34 mm reference. J4 carrier sockets still differ by 1.27 mm. Mounting holes break through side edges.'
    bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(path))
    for name,matrix in original.items():
        assert [list(r) for r in bpy.data.objects[name].matrix_basis] == matrix
    report['files'][filename] = {'updated_instances':len(roots),'preserved_root_transforms':True,
                                'j1_bounds_xyz_mm':bbox,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    if filename == 'mega-configuration.blend':
        bpy.context.scene.render.filepath = str(ROOT/'mega-preview.png')
        bpy.ops.render.render(write_still=True)
(ROOT/'dfrobot-update-validation.json').write_text(json.dumps(report,indent=2)+'\n')
manifest_path = ROOT/'mega-assembly.json'
manifest = json.loads(manifest_path.read_text())
for check in manifest['alignment_checks']:
    if 'DFRobot analyser' in check['name']:
        check.update(maximum_xy_error_mm=1.27,aligned=False,
                     note='Module corrected from user comments; carrier control sockets not yet moved.')
manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
for filename in ('validation.json','combined-validation.json'):
    path = ROOT/filename
    historical = json.loads(path.read_text())
    historical['superseded_by'] = 'dfrobot-update-validation.json (DFRobot geometry, fit checks and affected Blender hashes)'
    path.write_text(json.dumps(historical,indent=2)+'\n')
print(json.dumps(report,indent=2))
