"""Replace current board meshes in place, then audit the saved Blender files.

Run in Blender after the three KiCad export scripts. Board placements, scene
edits, cameras and historical Rev B geometry are preserved. Archived scenes
are named explicitly so they cannot be mistaken for the current PCBs.
"""
from pathlib import Path
import hashlib
import json
import shutil
import sys

import bpy

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT.parents[2] / 'tmp' / 'model-audit' / 'backups'
FILES = ('shield-configurations.blend', 'mega-configuration.blend', 'teensy-configuration.blend')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(obj, ancestor=None):
    matrix = obj.matrix_local.copy()
    parent = obj.parent
    while parent and parent != ancestor:
        matrix = parent.matrix_local @ matrix
        parent = parent.parent
    return matrix


def signature(objects, ancestor=None):
    """Hash actual vertex coordinates, face topology and assigned material colours."""
    result = []
    for obj in objects:
        if obj.type != 'MESH':
            continue
        matrix = relative(obj, ancestor)
        # Normalize signed zero: the inverted Mega can produce -0.0 on reload.
        vertices = [tuple(round(v, 4) + 0.0 for v in (matrix @ vertex.co) * 1000)
                    for vertex in obj.data.vertices]
        colors = [tuple(round(c, 5) for c in mat.diffuse_color) if mat else None
                  for mat in obj.data.materials]
        faces = [(tuple(face.vertices), colors[face.material_index] if colors else None)
                 for face in obj.data.polygons]
        result.append({'vertices': len(vertices), 'faces': len(faces),
                       'bounds_mm': [[min(v[i] for v in vertices), max(v[i] for v in vertices)]
                                     for i in range(3)] if vertices else [],
                       'geometry_material_sha256': hashlib.sha256(repr((vertices, faces)).encode()).hexdigest()})
    return sorted(result, key=lambda item: item['geometry_material_sha256'])


def archive(root):
    return bool(root.users_scene) and all('Rev B reference' in scene.name for scene in root.users_scene)


def transform(obj):
    return tuple(tuple(row) for row in obj.matrix_basis), tuple(tuple(row) for row in obj.matrix_parent_inverse)


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    report = {'method': 'Actual saved meshes: board-local vertices (0.0001 mm), face topology and material colours; source model dependency hashes.',
              'physical_fit_verified': False, 'files': {}, 'exports': {}}
    only = next((arg.split('=', 1)[1].split(',') for arg in sys.argv if arg.startswith('--only=')), None)
    if only:
        assert set(only) <= set(FILES), only
        existing = ROOT / 'reports/visual-geometry-validation.json'
        if existing.exists():
            report = json.loads(existing.read_text())
    for metadata in sorted((ROOT / 'exports').glob('*.json')):
        data = json.loads(metadata.read_text())
        if 'visual_export' in data:
            visual = data['visual_export']
            assert digest(metadata.with_suffix('.glb')) == visual['glb_sha256']
            source = ROOT.parents[2] / visual['source']
            assert digest(source) == visual['source_sha256'], source
            for model in visual['models']:
                model_path = Path(model['file'].replace('${KICAD9_3DMODEL_DIR}',
                                  'C:/Program Files/KiCad/9.0/share/kicad/3dmodels'))
                if not model_path.is_absolute():
                    model_path = ROOT.parents[2] / model_path
                assert digest(model_path) == model['sha256'], model_path
            report['exports'][metadata.stem] = visual
    for filename in FILES:
        if only and filename not in only:
            continue
        path = ROOT / filename
        before_hash = digest(path)
        backup = WORK / (path.stem + '-' + before_hash[:12] + '.blend')
        if not backup.exists():
            shutil.copyfile(path, backup)
        bpy.ops.wm.open_mainfile(filepath=str(path))
        roots = [obj for obj in bpy.data.objects if obj.get('source_board')]
        legacy = {root.name: signature(root.children_recursive, root) for root in roots if archive(root)}
        replaced = {child for root in roots if not archive(root) for child in root.children_recursive}
        preserved = {obj.name: transform(obj) for obj in bpy.data.objects if obj not in replaced}
        populations = {scene.name: sorted(root.name for root in roots if scene in root.users_scene)
                       for scene in bpy.data.scenes}
        templates = {}
        expected = {}
        for source in sorted({root['source_board'] for root in roots if not archive(root)}):
            assert source in report['exports'], source
            before = set(bpy.data.objects)
            bpy.ops.import_scene.gltf(filepath=str(ROOT / 'exports' / (source + '.glb')))
            objects = set(bpy.data.objects) - before
            templates[source] = objects
            expected[source] = signature(objects)
        for root in roots:
            if archive(root):
                continue
            template = templates[root['source_board']]
            collection = root.users_collection[0]
            for child in list(root.children_recursive):
                bpy.data.objects.remove(child, do_unlink=True)
            copies = {obj: obj.copy() for obj in template}
            for original, obj in copies.items():
                collection.objects.link(obj)
                obj.parent = copies.get(original.parent, root)
                obj.matrix_parent_inverse = original.matrix_parent_inverse.copy()
                obj.matrix_basis = original.matrix_basis.copy()
                obj.name = root.name + ' / KiCad ' + original.name
            root['visual_export_sha256'] = report['exports'][root['source_board']]['glb_sha256']
        for objects in templates.values():
            for obj in objects:
                bpy.data.objects.remove(obj, do_unlink=True)
        for name, values in preserved.items():
            assert transform(bpy.data.objects[name]) == values, name
        for scene in bpy.data.scenes:
            actual = sorted(root.name for root in roots if scene in root.users_scene)
            assert actual == populations[scene.name], scene.name
            if 'Rev B reference' in scene.name and not scene.name.startswith('ARCHIVE - '):
                scene.name = 'ARCHIVE - ' + scene.name
                scene['current_pcb'] = False
            else:
                scene['visual_geometry_audit'] = 'native KiCad visual exports, geometry and material comparison after reopening'
        for mesh in list(bpy.data.meshes):
            if mesh.users == 0:
                bpy.data.meshes.remove(mesh)
        for material in list(bpy.data.materials):
            if material.users == 0:
                bpy.data.materials.remove(material)
        bpy.context.preferences.filepaths.save_version = 0
        bpy.ops.wm.save_as_mainfile(filepath=str(path), compress=True)
        bpy.ops.wm.open_mainfile(filepath=str(path))
        assert not bpy.data.libraries
        assert not [im for im in bpy.data.images if im.source == 'FILE' and im.filepath and not im.packed_file]
        for name, values in preserved.items():
            assert transform(bpy.data.objects[name]) == values, name
        boards = []
        for root in [obj for obj in bpy.data.objects if obj.get('source_board')]:
            actual = signature(root.children_recursive, root)
            historical = archive(root)
            assert actual == (legacy[root.name] if historical else expected[root['source_board']]), root.name
            assert transform(root) == preserved[root.name], root.name
            boards.append({'root': root.name, 'source': root['source_board'],
                           'scenes': [scene.name for scene in root.users_scene],
                           'status': 'archived geometry preserved' if historical else 'matches fresh KiCad visual export',
                           'meshes': actual})
        report['files'][filename] = {'sha256': digest(path), 'reopened': True,
                                    'placements_and_unrelated_objects_preserved': True, 'boards': boards}
        (ROOT / 'reports/visual-geometry-validation.json').write_text(json.dumps(report, indent=2) + '\n')
        print(filename, 'verified', len(boards), 'board instances', flush=True)
        if '--render' in sys.argv or ('--render-racks' in sys.argv and filename != FILES[0]):
            if filename == 'shield-configurations.blend':
                scenes = [(scene, scene.name.lower().replace(' - mic ', '-').replace(' ', '-') + '-preview.png')
                          for scene in bpy.data.scenes if scene.name.startswith(('Female body', 'Male body'))]
            elif filename == 'mega-configuration.blend':
                scenes = [(bpy.context.scene, 'mega-preview.png')]
            else:
                scenes = [(bpy.context.scene, 'teensy-preview.png')]
            for scene, image in scenes:
                bpy.context.window.scene = scene
                scene.render.filepath = str(ROOT / 'previews' / image)
                bpy.ops.render.render(write_still=True)
        (ROOT / 'reports/visual-geometry-validation.json').write_text(json.dumps(report, indent=2) + '\n')
    assert all(name in report['files'] and report['files'][name]['sha256'] == digest(ROOT / name)
               for name in FILES), 'Run the remaining assembly audits before marking the whole set current'
    for filename in ('validation.json', 'combined-validation.json', 'dfrobot-update-validation.json',
                     'carrier-update-validation.json', 'adapter-update-validation.json', 'body-scenes-validation.json'):
        path = ROOT / 'reports' / filename
        data = json.loads(path.read_text())
        data['superseded_by'] = 'visual-geometry-validation.json (current Blender/export hashes, saved geometry and materials)'
        path.write_text(json.dumps(data, indent=2) + '\n')
    print('ALL CURRENT BOARD GEOMETRY AND MATERIALS MATCH', flush=True)


if __name__ == '__main__':
    main()
