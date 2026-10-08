"""Refresh the corrected carrier while preserving scene edits and transforms."""
from pathlib import Path
import bpy
import json
import hashlib
from mathutils import Matrix,Vector

ROOT=Path(__file__).resolve().parent
manifest=json.loads((ROOT/'mega-assembly.json').read_text())
carrier=json.loads((ROOT/'exports/analyser-carrier.json').read_text())['footprints']
module=json.loads((ROOT/'exports/dfrobot-module.json').read_text())['footprints']
errors=[]
for i,entry in enumerate(b for b in manifest['boards'] if b['source']=='dfrobot-module'):
    m=Matrix(entry['matrix_mm'])
    receiving=[Vector((x+25,-y-215)) for x,y in carrier[f'M{i+1}']['pads'].values()]
    for ref in ('J2J3','J4'):
        for x,y in module[ref]['pads'].values():
            point=(m @ Vector((x,-y,0))).xy
            errors.append(min((point-q).length for q in receiving))
assert len(errors)==40 and max(errors)<.015,errors
report={'mating_contacts_checked':40,'maximum_xy_error_mm':max(errors),'files':{}}
for filename in ('mega-configuration.blend','shield-configurations.blend'):
    path=ROOT/filename
    bpy.ops.wm.open_mainfile(filepath=str(path))
    roots=[o for o in bpy.data.objects if o.get('source_board')=='analyser-carrier']
    assert len(roots)==1
    root=roots[0];matrix=root.matrix_basis.copy()
    before=set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(ROOT/'exports/analyser-carrier.glb'))
    imported=set(bpy.data.objects)-before
    collection=root.users_collection[0]
    for old in list(root.children_recursive):bpy.data.objects.remove(old,do_unlink=True)
    for obj in imported:
        for old in list(obj.users_collection):old.objects.unlink(obj)
        collection.objects.link(obj)
        if obj.parent not in imported:obj.parent=root
        obj.name=root.name+' / updated '+obj.name
    assert root.matrix_basis==matrix
    for obj in bpy.data.objects:
        if obj.get('source_board')=='dfrobot-module':
            obj['carrier_fit_note']='Control sockets aligned with corrected J4; physical fit not verified.'
    for scene in bpy.data.scenes:
        scene['dfrobot_fit_note']='22 x 34 mm reference; carrier sockets aligned with J4. Mounting holes intersect side edges.'
    for mesh in list(bpy.data.meshes):
        if mesh.users==0:bpy.data.meshes.remove(mesh)
    bpy.ops.wm.save_as_mainfile(filepath=str(path),compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(path))
    assert next(o for o in bpy.data.objects if o.get('source_board')=='analyser-carrier').matrix_basis==matrix
    report['files'][filename]={'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'reopened':True,'placement_preserved':True}
    if filename=='mega-configuration.blend':
        bpy.context.scene.render.filepath=str(ROOT/'mega-preview.png')
        bpy.ops.render.render(write_still=True)
for check in manifest['alignment_checks']:
    if 'DFRobot analyser' in check['name']:
        check.update(maximum_xy_error_mm=max(errors),aligned=True,note='Carrier sockets corrected to match J4.')
(ROOT/'mega-assembly.json').write_text(json.dumps(manifest,indent=2)+'\n')
for filename in ('validation.json','combined-validation.json','dfrobot-update-validation.json'):
    path=ROOT/filename;data=json.loads(path.read_text())
    data['superseded_by']='carrier-update-validation.json (carrier alignment and affected Blender files)'
    path.write_text(json.dumps(data,indent=2)+'\n')
(ROOT/'carrier-update-validation.json').write_text(json.dumps(report,indent=2)+'\n')
print(report)
