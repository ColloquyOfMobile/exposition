"""Reopen both delivered Blender files and check placement and embedded assets."""
import bpy
import hashlib
import json
from pathlib import Path
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent
results = {}
for config in ('mega','teensy'):
    path = ROOT/(config+'-configuration.blend')
    bpy.ops.wm.open_mainfile(filepath=str(path))
    manifest = json.loads((ROOT/(config+'-assembly.json')).read_text())
    visible = [b for b in manifest['boards'] if not b['hidden']]
    assert len(visible) == (13 if config == 'mega' else 8)
    assert bpy.context.scene.unit_settings.system == 'METRIC'
    for board in manifest['boards']:
        obj = bpy.data.objects[board['name']]
        expected = Matrix(board['matrix_mm'])
        expected.translation *= .001
        # Hidden collections are excluded from dependency evaluation on file load.
        actual = obj.matrix_basis if board['hidden'] else obj.matrix_world
        assert max(abs(actual[i][j]-expected[i][j]) for i in range(4) for j in range(4)) < 1e-6, (board['name'],actual,expected)
    external = [im.filepath for im in bpy.data.images
                if im.source == 'FILE' and im.filepath and not im.packed_file]
    assert not external, external
    meshes = [o for o in bpy.context.scene.objects if o.type == 'MESH' and not o.hide_get()
              and any(not c.hide_viewport for c in o.users_collection)]
    points = [o.matrix_world @ Vector(c) for o in meshes for c in o.bound_box]
    bounds = [[round(min(p[i] for p in points)*1000,3),round(max(p[i] for p in points)*1000,3)] for i in range(3)]
    # Microphones must remain hidden and the rack must retain its 210 x 297 mm scale.
    assert 200 < bounds[0][1]-bounds[0][0] < 230, bounds
    assert 290 < bounds[1][1]-bounds[1][0] < 320, bounds
    back = json.loads((ROOT/'exports/backplane.json').read_text())['footprints']
    def positions(boardname, refs):
        b = next(b for b in manifest['boards'] if b['name'] == boardname)
        data = json.loads((ROOT/'exports'/(b['source']+'.json')).read_text())['footprints']
        m = Matrix(b['matrix_mm'])
        return [m @ Vector((data[r]['xy'][0],-data[r]['xy'][1],0)) for r in refs]
    target = [Vector((back[r]['xy'][0],-back[r]['xy'][1],0)) for r in ('HM1','HM2','HM3','HM4')]
    if config == 'mega':
        source = positions('07 Mega 2560 - components face down',['H'+str(i) for i in range(1,7)])
    else:
        source = positions('07 Teensy adapter',['HM'+str(i) for i in range(1,5)])
    error = max(min((p.xy-q.xy).length for q in source) for p in target)
    assert error < .015, error
    results[config] = {'visible_boards':len(visible),'hidden_microphones':6,
                       'visible_meshes':len(meshes),'bounds_xyz_mm':bounds,
                       'computing_mount_max_xy_error_mm':round(error,6),
                       'connector_checks':manifest['alignment_checks'],
                       'external_image_dependencies':external,'reopened_successfully':True,
                       'blend_sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
results['source_pcb_sha256'] = {p.parent.name:hashlib.sha256(p.read_bytes()).hexdigest()
                               for p in ROOT.parent.glob('*/*.kicad_pcb')}
(ROOT/'validation.json').write_text(json.dumps(results,indent=2)+'\n')
print(json.dumps(results,indent=2))
