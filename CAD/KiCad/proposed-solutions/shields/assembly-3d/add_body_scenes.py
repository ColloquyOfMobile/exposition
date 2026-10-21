"""Add body mounting studies to the existing combined file with Blender Python.

Preserves the existing rack scenes and edits. Does not rebuild their geometry.
Re-running requires --replace-body-scenes and replaces only these generated scenes.
"""
from pathlib import Path
import hashlib
import json
import math
import shutil
import sys

import bpy
import bmesh
from mathutils import Vector
from mathutils.geometry import tessellate_polygon

ROOT = Path(__file__).resolve().parent
WORK = ROOT.parents[4] / 'tmp' / 'body-model'
WORK.mkdir(parents=True, exist_ok=True)
OUTPUT = ROOT / 'shield-configurations.blend'
SCENES = tuple(kind+' body'+('' if orientation=='up' else ' - mic '+orientation)
               for kind in ('Female','Male') for orientation in ('up','left','right'))
PROFILE_LENGTH = 240.0  # Display length only; not the installed member length.
FRAME_GAP = 5.0
MM = .001


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def snapshot(scene):
    return {
        'camera': scene.camera.name if scene.camera else None,
        'objects': {
            obj.name: {
                'matrix_basis': [list(row) for row in obj.matrix_basis],
                'parent': obj.parent.name if obj.parent else None,
                'data': obj.data.name if obj.data else None,
                'hidden_render': obj.hide_render,
            } for obj in scene.objects
        },
        'collections': {c.name: [c.hide_viewport, c.hide_render] for c in scene.collection.children},
    }


def material(name, color, metallic=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    node = mat.node_tree.nodes.get('Principled BSDF')
    node.inputs['Base Color'].default_value = (*color, 1)
    node.inputs['Metallic'].default_value = metallic
    node.inputs['Roughness'].default_value = .38
    return mat


def move_to(obj, collection):
    for old in list(obj.users_collection):
        old.objects.unlink(obj)
    collection.objects.link(obj)


def board(scene, source, name, translation):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(ROOT / 'exports' / (source + '.glb')))
    imported = set(bpy.data.objects) - before
    coll = bpy.data.collections.new(name)
    scene.collection.children.link(coll)
    root = bpy.data.objects.new(name, None)
    coll.objects.link(root)
    for obj in imported:
        move_to(obj, coll)
        if obj.parent not in imported:
            obj.parent = root
        obj.name = name + ' / ' + obj.name
    root.location = Vector(translation) * MM
    root['source_board'] = source
    root['placement_mm'] = list(translation)
    return root, coll


def profile(collection, mat):
    # Six illustrative T-slots. Only the 1 x 2 inch envelope is manufacturer-based.
    # Slot lips, cavity depths, corner radii and core are not a machining drawing.
    verts2d = []
    corners = [(-12.7, 0), (12.7, 0), (12.7, -50.8), (-12.7, -50.8)]
    for side, a in enumerate(corners):
        b = corners[(side + 1) % 4]
        a, b = Vector(a), Vector(b)
        direction = (b - a).normalized()
        inward = Vector((direction.y, -direction.x))
        length = (b - a).length
        centres = [12.7] if side in (0, 2) else [12.7, 38.1]
        points = [(0, 0)]
        for centre in centres:
            points += [(centre-3.25, 0), (centre-3.25, 2.5),
                       (centre-7.3, 2.5), (centre-7.3, 6.5),
                       (centre+7.3, 6.5), (centre+7.3, 2.5),
                       (centre+3.25, 2.5), (centre+3.25, 0)]
        for along, depth in points:
            q = a + direction * along + inward * depth
            verts2d.append((q.x, q.y))
    n = len(verts2d)
    vertices = [(x*MM, y*MM, z*MM) for y in (12, 12-PROFILE_LENGTH) for x, z in verts2d]
    vectors = [Vector((x, z, 0)) for x, z in verts2d]
    index = {tuple(v): i for i, v in enumerate(vectors)}
    triangles = [[v if isinstance(v, int) else index[tuple(v)] for v in tri]
                 for tri in tessellate_polygon([vectors])]
    faces = [tuple(tri) for tri in triangles] + [tuple(i+n for i in reversed(tri)) for tri in triangles]
    faces += [(i, (i+1) % n, (i+1) % n+n, i+n) for i in range(n)]
    mesh = bpy.data.meshes.new('Imperial reference section - simplified slots')
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    bm = bmesh.new(); bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    assert all(e.is_manifold for e in bm.edges)
    bm.to_mesh(mesh); bm.free()
    obj = bpy.data.objects.new('UNCONFIRMED imperial extrusion - 1 x 2 in - 240 mm display length', mesh)
    collection.objects.link(obj)
    obj.data.materials.append(mat)
    obj['reference_only'] = True
    obj['installed_part_identified'] = False
    obj['section_mm'] = [25.4, 50.8]
    obj['display_length_mm'] = PROFILE_LENGTH
    obj['basis'] = 'User: American profile from TJ; no installed part number found. 80/20 1020 envelope reference.'
    obj['source_url'] = 'https://8020.net/1020.html'
    obj['simplified_geometry'] = 'Slot lips/cavities and solid core illustrative; no actual T-nut/screw fit claim.'
    return obj


def spacer(collection, name, x, y, outer, bore, mat):
    segments = 48
    vertices = []
    for z, radius in [(0, outer/2), (FRAME_GAP, outer/2), (0, bore/2), (FRAME_GAP, bore/2)]:
        for i in range(segments):
            angle = math.tau * i / segments
            vertices.append(((x+radius*math.cos(angle))*MM, (y+radius*math.sin(angle))*MM, z*MM))
    faces = []
    for i in range(segments):
        j = (i+1) % segments
        faces += [(i,j,segments+j,segments+i), (2*segments+j,2*segments+i,3*segments+i,3*segments+j),
                  (segments+i,segments+j,3*segments+j,3*segments+i), (j,i,2*segments+i,2*segments+j)]
    mesh = bpy.data.meshes.new(name); mesh.from_pydata(vertices, [], faces)
    obj = bpy.data.objects.new(name, mesh); collection.objects.link(obj)
    obj.data.materials.append(mat)
    obj['reference_only'] = True
    return obj


def label(collection, name, message, position, size, mat):
    data = bpy.data.curves.new(name, 'FONT')
    data.body = message; data.size = size*MM
    data.space_line = 1.25
    obj = bpy.data.objects.new(name, data)
    collection.objects.link(obj); obj.location = Vector(position)*MM
    obj.data.materials.append(mat)


def build(kind, orientation='up'):
    scene = bpy.data.scenes.new(kind + ' body'+('' if orientation=='up' else ' - mic '+orientation))
    bpy.context.window.scene = scene
    scene.unit_settings.system = 'METRIC'
    scene.unit_settings.length_unit = 'MILLIMETERS'
    scene.unit_settings.scale_length = 1
    scene['reference_only'] = True
    scene['microphone_revision'] = 'C'
    scene['profile_status'] = 'Imperial 1 x 2 in reference only; TJ installed part number not found.'
    scene['mounting_status'] = 'Display placement. 5 mm frame gap; body standoff and board spacing provisional.'
    scene['microphone_status'] = 'Rev C 32x62 slotted holder; ONE module facing '+orientation+'. Provisional support geometry.'
    stem = 'female-base-v2' if kind == 'Female' else 'male-static-v2'
    scene['body_board_revision']='D'
    body, coll = board(scene, stem, kind + ' v2 PCB + socketed GF1002 + adjustable supports', (-50, 20, FRAME_GAP))
    mic_source = 'microphone-flex-'+orientation
    mic, _ = board(scene, mic_source, kind + ' microphone holder + ONE MAX9814 facing '+orientation, (-60, -80, FRAME_GAP))
    hardware = bpy.data.collections.new(kind + ' frame and insulating spacer references')
    scene.collection.children.link(hardware)
    metal = material(kind + ' satin aluminium reference', (.48, .53, .58), .8)
    nylon = material(kind + ' insulating spacer reference', (.72, .76, .69))
    ink = material(kind + ' annotation ink', (.11, .17, .22))
    amber = material(kind + ' unconfirmed reference annotation', (.65, .24, .035))
    frame = profile(hardware, metal)
    body_ys = [-27, -70] if kind == 'Female' else [-30, -80]
    for i, y in enumerate(body_ys):
        spacer(hardware, f'{kind} body fixing {i+1} - nominal insulating support, hardware unverified', 0, y, 12, 8, nylon)
    for i, y in enumerate([-136, -186]):
        spacer(hardware, f'{kind} microphone M5 frame spacer {i+1} - 5 mm high', 0, y, 10, 5.5, nylon)
    annotations = bpy.data.collections.new(kind + ' mounting study annotations')
    scene.collection.children.link(annotations)
    label(annotations, kind+' title', kind.upper()+' BODY\nMicrophone facing '+orientation.upper(), (-63, 28, 8), 5, ink)
    label(annotations, kind+' amp note', 'GF1002 / PLUG-IN\n11 mm nominal stack\nadjustable supports', (42, -43, 8), 3.2, ink)
    label(annotations, kind+' mic note', 'MAX9814 / '+orientation.upper()+'\n32 x 62 mm holder\n12 x 5.5 mm slots', (30, -150, 12), 3.2, ink)
    label(annotations, kind+' profile note', 'IMPERIAL REFERENCE ONLY\n1 x 2 in / 25.4 x 50.8 mm\nTJ part number unconfirmed', (-63, -216, 5), 3.1, amber)
    studio = bpy.data.collections.new(kind + ' body studio'); scene.collection.children.link(studio)
    target = Vector((.006, -.100, -.003))
    bpy.ops.object.camera_add(location=(.245, -.35, .39))
    cam = bpy.context.object; cam.name = kind+' body overview'; move_to(cam, studio)
    cam.rotation_euler = (target-cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.type = 'ORTHO'; cam.data.ortho_scale = .345
    cam.data.clip_start = .001; cam.data.clip_end = 10; scene.camera = cam
    for location, energy in [((.05, -.05, .4), 14), ((-.2, -.12, .18), 8), ((.13, -.3, .12), 7)]:
        bpy.ops.object.light_add(type='AREA', location=location)
        light = bpy.context.object; light.name = kind+' softbox'; move_to(light, studio)
        light.data.energy = energy; light.data.shape = 'DISK'; light.data.size = .3
        light.rotation_euler = (target-light.location).to_track_quat('-Z','Y').to_euler()
    scene.world = bpy.data.worlds.new(kind+' neutral studio'); scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.72, .76, .8, 1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = .6
    scene.render.engine = 'CYCLES'; scene.cycles.samples = 24; scene.cycles.use_denoising = True
    scene.render.resolution_x = 1500; scene.render.resolution_y = 1500; scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    bpy.ops.object.select_all(action='DESELECT')
    bpy.context.view_layer.update()
    # Validate both PCB mounting centre lines against the frame's narrow-face slot.
    micdata = json.loads((ROOT / 'exports' / (mic_source+'.json')).read_text())['footprints']
    mount_positions = []
    for ref in ('H1', 'H2'):
        x, y = micdata[ref]['xy']
        point = mic.matrix_world @ Vector((x*MM, -y*MM, 0))
        mount_positions.append([round(v/MM, 6) for v in point])
    assert all(abs(pos[0]) < .001 for pos in mount_positions), mount_positions
    assert sorted(round(pos[1]) for pos in mount_positions) == [-186, -136], mount_positions
    frame_size = [max(v.co[i] for v in frame.data.vertices)-min(v.co[i] for v in frame.data.vertices) for i in range(3)]
    assert all(abs(a/MM-b)<.001 for a,b in zip(frame_size, [25.4,PROFILE_LENGTH,50.8]))
    # One amplifier assembly has five M1 meshes: socket, module and 3 headers.
    meshes = [o for o in coll.all_objects if o.type == 'MESH']
    assert len([o for o in meshes if 'M1' in o.name]) == 5
    assert len([o for o in meshes if 'H1' in o.name or 'H2' in o.name]) == 2
    return {'scene': scene.name, 'body_source': stem, 'microphone_source':mic_source,
            'microphone_orientation':orientation,'module_population':1,'body_board_revision':'D',
            'amplifier_assembly_meshes':5,'module_underside_gap_mm_nominal':11,
            'body_transform_mm': [-50,20,FRAME_GAP],
            'microphone_transform_mm': [-60,-80,FRAME_GAP], 'microphone_mount_centres_mm': mount_positions,
            'body_mount_centres_mm': [[0,y,FRAME_GAP] for y in body_ys],
            'profile_dimensions_mm': [25.4,PROFILE_LENGTH,50.8], 'profile_installed_part_verified': False,
            'body_meshes': len(meshes)}


def main():
    before_hash = sha(OUTPUT)
    bpy.ops.wm.open_mainfile(filepath=str(OUTPUT))
    for name in SCENES:
        if name in bpy.data.scenes:
            if bpy.data.scenes[name].get('microphone_revision') != 'C':
                # The user can have edited the earlier body mounting study.
                # Keep that complete scene rather than destroying those edits.
                bpy.data.scenes[name].name = name+' - Rev B reference'
                continue
            if '--replace-body-scenes' not in sys.argv:
                raise RuntimeError('Generated body scenes already exist; use --replace-body-scenes intentionally.')
            old = bpy.data.scenes[name]
            for obj in list(old.objects):
                if obj.users_scene == (old,):
                    bpy.data.objects.remove(obj, do_unlink=True)
            bpy.data.scenes.remove(old)
    original_scene = bpy.context.scene.name
    original = {s.name: snapshot(s) for s in bpy.data.scenes}
    report = {'combined_sha256_before': before_hash, 'existing_scenes': list(original), 'bodies': []}
    for kind in ('Female', 'Male'):
        for orientation in ('up','left','right'):
            report['bodies'].append(build(kind,orientation))
    for name, expected in original.items():
        assert snapshot(bpy.data.scenes[name]) == expected, name
    # Preserve the original opening scene and its viewport setup.
    bpy.context.window.scene = bpy.data.scenes[original_scene]
    bpy.context.preferences.filepaths.save_version = 0
    staged = WORK / 'shield-configurations-with-bodies.blend'
    bpy.ops.wm.save_as_mainfile(filepath=str(staged), compress=True)
    bpy.ops.wm.open_mainfile(filepath=str(staged))
    for name, expected in original.items():
        assert snapshot(bpy.data.scenes[name]) == expected, name
    assert all(name in bpy.data.scenes for name in SCENES)
    assert not bpy.data.libraries
    assert not [im.filepath for im in bpy.data.images if im.source == 'FILE' and im.filepath and not im.packed_file]
    backup = WORK / ('shield-configurations-before-'+before_hash[:12]+'.blend')
    if not backup.exists(): shutil.copyfile(OUTPUT, backup)
    shutil.copyfile(staged, OUTPUT)
    report['combined_sha256_after'] = sha(OUTPUT)
    report['existing_scene_objects_and_transforms_preserved'] = True
    report['reopened_successfully'] = True
    report['source_sha256'] = {}
    for source in ['female-base-v2', 'male-static-v2', 'microphone-flex-up','microphone-flex-left','microphone-flex-right']:
        report['source_sha256'][source+'.glb'] = sha(ROOT / 'exports' / (source+'.glb'))
    for source in ['female-base-v2', 'male-static-v2']:
        report['source_sha256'][source+'.kicad_pcb'] = json.loads((ROOT/'exports'/(source+'.json')).read_text())['sha256']
    (ROOT/'body-scenes-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    for kind in ('Female', 'Male'):
        for orientation in ('up','left','right'):
            scene = bpy.data.scenes[kind+' body'+('' if orientation=='up' else ' - mic '+orientation)]
            bpy.context.window.scene = scene
            suffix='' if orientation=='up' else '-'+orientation
            scene.render.filepath = str(ROOT / (kind.lower()+'-body'+suffix+'-preview.png'))
            bpy.ops.render.render(write_still=True)
    print('BODY SCENES COMPLETE', json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
