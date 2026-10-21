"""Refresh adapter copper and front reservoirs, preserving assembly transforms.

Run with Blender after export_boards.py teensy-adapter.
"""
from pathlib import Path
import hashlib
import json
import bpy

ROOT = Path(__file__).resolve().parent
report = {'revision': '2026-10-13 front SMD reservoirs', 'files': {}}
for filename in ('teensy-configuration.blend', 'shield-configurations.blend'):
    path = ROOT / filename
    bpy.ops.wm.open_mainfile(filepath=str(path))
    roots = [obj for obj in bpy.data.objects if obj.get('source_board') == 'teensy-adapter']
    assert len(roots) == 1
    root = roots[0]
    matrix = root.matrix_basis.copy()
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(ROOT / 'exports/teensy-adapter.glb'))
    imported = set(bpy.data.objects) - before
    collection = root.users_collection[0]
    for obj in list(root.children_recursive):
        bpy.data.objects.remove(obj, do_unlink=True)
    for obj in imported:
        for old in list(obj.users_collection):
            old.objects.unlink(obj)
        collection.objects.link(obj)
        if obj.parent not in imported:
            obj.parent = root
        obj.name = root.name + ' / updated ' + obj.name
    assert root.matrix_basis == matrix
    for mesh in list(bpy.data.meshes):
        if mesh.users == 0:
            bpy.data.meshes.remove(mesh)
    bpy.context.preferences.filepaths.save_version = 0
    bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(path))
    assert next(obj for obj in bpy.data.objects if obj.get('source_board') == 'teensy-adapter').matrix_basis == matrix
    report['files'][filename] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'reopened': True, 'placement_preserved': True}
    if filename == 'teensy-configuration.blend':
        bpy.context.scene.render.filepath = str(ROOT / 'teensy-preview.png')
        bpy.ops.render.render(write_still=True)
(ROOT / 'adapter-update-validation.json').write_text(json.dumps(report, indent=2) + '\n')
print(report)
