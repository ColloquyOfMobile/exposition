"""Refresh only backplane meshes in existing assemblies, preserving other work.

Run with Blender. Other boards may be undergoing independent revisions; this
operation validates the backplane export only and does not certify those boards.
"""
from pathlib import Path
import hashlib
import json
import shutil
import sys

import bpy

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from update_visual_geometry import signature, transform


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = ROOT.parent/'backplane/backplane.kicad_pcb'
    model = ROOT/'exports/backplane.glb'
    meta = json.loads(model.with_suffix('.json').read_text())['visual_export']
    assert digest(source) == meta['source_sha256']
    assert digest(model) == meta['glb_sha256']
    backup = ROOT.parents[3]/'tmp/backplane-mounts/assembly-backups'
    backup.mkdir(parents=True, exist_ok=True)
    report = dict(backplane_source_sha256=digest(source), model_sha256=digest(model),
        scope='Backplane only; all other board geometry and placements preserved', files={})
    for name in ['shield-configurations.blend', 'mega-configuration.blend', 'teensy-configuration.blend']:
        path = ROOT/name
        original = digest(path)
        saved = backup/(path.stem+'-'+original[:12]+'.blend')
        if not saved.exists():
            shutil.copy2(path, saved)
        bpy.ops.wm.open_mainfile(filepath=str(path))
        roots = [obj for obj in bpy.data.objects if obj.get('source_board') == 'backplane']
        assert roots, name
        replaced = {child for root in roots for child in root.children_recursive}
        preserved = {obj.name: transform(obj) for obj in bpy.data.objects if obj not in replaced}
        other_meshes = [obj for obj in bpy.data.objects if obj not in replaced and obj.type == 'MESH']
        other_signature = signature(other_meshes)
        existing = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(model))
        template = set(bpy.data.objects)-existing
        expected = signature(template)
        for root in roots:
            collection = root.users_collection[0]
            for child in list(root.children_recursive):
                bpy.data.objects.remove(child, do_unlink=True)
            copies = {obj: obj.copy() for obj in template}
            for original_obj, obj in copies.items():
                collection.objects.link(obj)
                obj.parent = copies.get(original_obj.parent, root)
                obj.matrix_parent_inverse = original_obj.matrix_parent_inverse.copy()
                obj.matrix_basis = original_obj.matrix_basis.copy()
                obj.name = root.name+' / KiCad '+original_obj.name
            root['visual_export_sha256'] = digest(model)
        for obj in template:
            bpy.data.objects.remove(obj, do_unlink=True)
        root_names = [root.name for root in roots]
        for obj_name, state in preserved.items():
            assert transform(bpy.data.objects[obj_name]) == state, obj_name
        assert signature(other_meshes) == other_signature
        assert digest(path) == original, 'Assembly changed concurrently; preserve the newer file'
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
        bpy.ops.wm.open_mainfile(filepath=str(path))
        for obj_name, state in preserved.items():
            assert transform(bpy.data.objects[obj_name]) == state, obj_name
        changed_children = {child for root_name in root_names
                            for child in bpy.data.objects[root_name].children_recursive}
        assert signature([obj for obj in bpy.data.objects
                          if obj.type == 'MESH' and obj not in changed_children]) == other_signature
        for root_name in root_names:
            root = bpy.data.objects[root_name]
            assert signature(root.children_recursive, root) == expected
        report['files'][name] = dict(sha256=digest(path), reopened=True,
            backplane_geometry_matches_export=True, other_meshes_and_placements_preserved=True)
        print(name, 'backplane enclosure holes updated and verified', flush=True)
    (ROOT/'backplane-mounting-validation.json').write_text(json.dumps(report, indent=2)+'\n')


if __name__ == '__main__':
    main()
