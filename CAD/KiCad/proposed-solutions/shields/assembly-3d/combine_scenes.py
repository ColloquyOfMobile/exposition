"""Combine the checked assemblies; run with Blender's background Python."""
import bpy
import hashlib
import json
import numpy as np
from pathlib import Path

ROOT = Path(__file__).resolve().parent
OUTPUT = ROOT / 'shield-configurations.blend'
bpy.ops.wm.open_mainfile(filepath=str(ROOT / 'mega-configuration.blend'))
mega = bpy.context.scene
mega.name = 'Mega'
with bpy.data.libraries.load(str(ROOT / 'teensy-configuration.blend'), link=False) as (source, dest):
    dest.scenes = source.scenes
assert len(dest.scenes) == 1
teensy = dest.scenes[0]
teensy.name = 'Teensy'


def material_signature(mat):
    if mat is None:
        return None
    values = [tuple(mat.diffuse_color), mat.use_nodes]
    if mat.use_nodes:
        for node in mat.node_tree.nodes:
            inputs = []
            for socket in node.inputs:
                value = getattr(socket, 'default_value', None)
                if value is not None and not isinstance(value, (str, int, float, bool)):
                    try:
                        value = list(value)
                    except TypeError:
                        value = str(value)
                inputs.append((socket.identifier, value))
            values.append((node.name, node.bl_idname, inputs))
        values.append([(link.from_node.name, link.from_socket.identifier,
                        link.to_node.name, link.to_socket.identifier)
                       for link in mat.node_tree.links])
    return values


def mesh_signature(mesh):
    digest = hashlib.sha256()
    for items, field, width, dtype in [
        (mesh.vertices, 'co', 3, np.float32),
        (mesh.loops, 'vertex_index', 1, np.int32),
        (mesh.polygons, 'loop_total', 1, np.int32),
        (mesh.polygons, 'material_index', 1, np.int32),
        (mesh.polygons, 'use_smooth', 1, np.bool_),
        (mesh.corner_normals, 'vector', 3, np.float32),
    ]:
        array = np.empty(len(items) * width, dtype=dtype)
        items.foreach_get(field, array)
        digest.update(str((field, len(items))).encode())
        digest.update(array.tobytes())
    # These exports have no textures. Preserve arbitrary UV/colour data by
    # declining to consolidate meshes which carry such attributes.
    if mesh.uv_layers or mesh.color_attributes:
        digest.update(mesh.name.encode())
    digest.update(json.dumps([material_signature(m) for m in mesh.materials]).encode())
    return digest.hexdigest()


# Share mesh datablocks only: independent objects keep per-scene transforms,
# visibility and parent relationships. No libraries are linked externally.
cache = {}
shared = 0
for obj in list(bpy.data.objects):
    if obj.type != 'MESH':
        continue
    key = mesh_signature(obj.data)
    if key in cache and cache[key] != obj.data:
        obj.data = cache[key]
        shared += 1
    else:
        cache[key] = obj.data
for mesh in list(bpy.data.meshes):
    if mesh.users == 0:
        bpy.data.meshes.remove(mesh)
for mat in list(bpy.data.materials):
    if mat.users == 0:
        bpy.data.materials.remove(mat)

for scene in (mega, teensy):
    scene['scene_switching'] = 'Use the top-right Scene selector to switch Mega / Teensy.'
    scene.render.filepath = '//'+scene.name.lower()+'-preview.png'
bpy.context.window.scene = mega
bpy.ops.wm.save_as_mainfile(filepath=str(OUTPUT), compress=True)

# Reopen the delivered artifact, then inspect each scene in its own context.
bpy.ops.wm.open_mainfile(filepath=str(OUTPUT))
assert {s.name for s in bpy.data.scenes} == {'Mega', 'Teensy'}
report = {'file': OUTPUT.name, 'shared_mesh_reassignments': shared, 'scenes': {}}
scene_meshes = []
for name, count in [('Mega', 13), ('Teensy', 8)]:
    scene = bpy.data.scenes[name]
    bpy.context.window.scene = scene
    bpy.context.view_layer.update()
    roots = [obj for obj in scene.objects if 'source_board' in obj]
    visible_roots = [obj for obj in roots if any(not c.hide_viewport for c in obj.users_collection)]
    assert len(visible_roots) == count, (name, len(visible_roots))
    assert len(roots) - count == 6
    assert scene.camera in list(scene.objects)
    assert scene.unit_settings.system == 'METRIC'
    assert not bpy.data.libraries
    manifest = json.loads((ROOT / (name.lower()+'-assembly.json')).read_text())
    for entry in manifest['boards']:
        # Appending can suffix object names; identify board roots by source and
        # their original stable prefix, then compare all saved transforms.
        matches = [obj for obj in roots if obj.name == entry['name'] or obj.name.startswith(entry['name']+'.')]
        assert len(matches) == 1, entry['name']
        obj = matches[0]
        matrix = obj.matrix_basis if entry['hidden'] else obj.matrix_world
        expected = entry['matrix_mm']
        for row in range(4):
            for col in range(4):
                value = expected[row][col] * (.001 if col == 3 and row < 3 else 1)
                assert abs(matrix[row][col]-value) < 1e-6, (name, entry['name'])
    scene_meshes.append({o.data for o in scene.objects if o.type == 'MESH'})
    report['scenes'][name] = {'visible_boards': count, 'hidden_microphones': 6,
                             'camera': scene.camera.name, 'transforms_verified': True}
report['mesh_datablocks_shared_between_scenes'] = len(scene_meshes[0] & scene_meshes[1])
assert report['mesh_datablocks_shared_between_scenes'] > 0
report['size_bytes'] = OUTPUT.stat().st_size
report['sha256'] = hashlib.sha256(OUTPUT.read_bytes()).hexdigest()
(ROOT / 'combined-validation.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
