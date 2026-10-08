"""Run with Blender --background --python build_assemblies.py -- mega|teensy.

The imported GLBs use metres, with KiCad Y inverted. Placement inputs are mm.
Source PCBs are never modified. The saved file has individually selectable parts.
"""
import bpy
import json
import math
import sys
from pathlib import Path
from mathutils import Matrix, Vector

ROOT = Path(__file__).resolve().parent
CONFIG = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else 'mega'
assert CONFIG in ('mega', 'teensy')
GAP = 11.04  # 8.5 mm socket body + 2.54 mm male header body
DECK = 1.6 + GAP
IDENTITY = Matrix.Identity(3)
manifest = {'configuration': CONFIG, 'units': 'mm', 'nominal_mating_gap_mm': GAP,
            'boards': [], 'alignment_checks': [], 'proxies': []}
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.name = 'Mega assembly' if CONFIG == 'mega' else 'Teensy assembly'
scene.unit_settings.system = 'METRIC'
scene.unit_settings.length_unit = 'MILLIMETERS'
scene.unit_settings.scale_length = 1.0


def material(name, color, metallic=0):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    node = mat.node_tree.nodes.get('Principled BSDF')
    node.inputs['Base Color'].default_value = (*color, 1)
    node.inputs['Metallic'].default_value = metallic
    node.inputs['Roughness'].default_value = .35
    return mat


metal = material('Nominal metal spacers', (.38, .43, .48), .75)
proxy_mat = material('AMBER = estimated body envelope', (.8, .27, .035))
dark = material('Microphone IC proxy', (.025, .03, .035))
instances = {}


def placement(rotation=IDENTITY, translation=(0, 0, 0), metres=True):
    m = rotation.to_4x4()
    m.translation = Vector(translation) * (.001 if metres else 1)
    return m


def board(source, name, translation=(0, 0, 0), rotation=IDENTITY, hidden=False):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=str(ROOT / 'exports' / (source + '.glb')))
    imported = set(bpy.data.objects) - before
    coll = bpy.data.collections.new(name)
    scene.collection.children.link(coll)
    root = bpy.data.objects.new(name, None)
    coll.objects.link(root)
    for obj in imported:
        for old in list(obj.users_collection):
            old.objects.unlink(obj)
        coll.objects.link(obj)
        if obj.parent not in imported:
            obj.parent = root
        obj.name = name + ' / ' + obj.name
    root.matrix_world = placement(rotation, translation)
    root['source_board'] = source
    root['placement_mm'] = list(translation)
    root['reference_only'] = True
    coll.hide_render = hidden
    coll.hide_viewport = hidden
    m = placement(rotation, translation, False)
    instances[name] = (source, m, root, coll)
    manifest['boards'].append({'name': name, 'source': source, 'hidden': hidden,
                              'matrix_mm': [list(row) for row in m]})
    return root


def metadata(source):
    return json.loads((ROOT / 'exports' / (source + '.json')).read_text())['footprints']


def pads(instance, refs, numbers=None):
    source, m, _, _ = instances[instance]
    data = metadata(source)
    return [m @ Vector((x, -y, 0)) for ref in refs for number, (x,y) in data[ref]['pads'].items()
            if numbers is None or number in numbers]


def check(name, moving, receiving, pending_carrier=False):
    # Verify XY coincidence of mating contacts independently of nominal Z height.
    assert moving and receiving, name
    error = max(min(math.hypot(a.x-b.x, a.y-b.y) for b in receiving) for a in moving)
    assert error < .015 or (pending_carrier and abs(error-1.27)<.015), (name, error)
    manifest['alignment_checks'].append({'name': name, 'contacts': len(moving),
                                         'maximum_xy_error_mm': round(error, 6),
                                         'aligned':error < .015,
                                         'note':'Carrier control sockets need the 1.27 mm correction' if error >= .015 else ''})


def spacer(name, x, y, bottom, top, outer=4, bore=3.2):
    # Annular mesh retains the screw clearance; fasteners are deliberately omitted.
    vertices = []
    segments = 40
    for z, radius in [(bottom, outer/2), (top, outer/2), (bottom, bore/2), (top, bore/2)]:
        for i in range(segments):
            a = 2*math.pi*i/segments
            vertices.append(((x+radius*math.cos(a))*.001,
                             (y+radius*math.sin(a))*.001, z*.001))
    faces = []
    for i in range(segments):
        j = (i+1) % segments
        faces.extend([(i,j,segments+j,segments+i),
                      (2*segments+j,2*segments+i,3*segments+i,3*segments+j),
                      (segments+i,segments+j,3*segments+j,3*segments+i),
                      (j,i,2*segments+i,2*segments+j)])
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    obj = bpy.data.objects.new(name, mesh)
    hardware.objects.link(obj)
    obj.data.materials.append(metal)


def proxy_box(name, center, size, mat=proxy_mat, parent=None, coll=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=Vector(center)*.001)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = Vector(size)*.001
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if parent:
        obj.parent = parent  # supplied coordinates are board-local
    if coll:
        for old in list(obj.users_collection): old.objects.unlink(obj)
        coll.objects.link(obj)
    obj['estimated_envelope'] = True
    manifest['proxies'].append(name)
    return obj


board('backplane', '01 Backplane')
hardware = bpy.data.collections.new('Nominal spacers - verify purchased hardware')
scene.collection.children.link(hardware)
proxy_box('J2 - estimated DC jack envelope', (246,-66,7.1), (15,14,11))
proxy_box('J6 - estimated screw bridge envelope', (233.68,-101.48,5.6), (15,19,8))

for i, label in enumerate(['Female 1 - 1012 Hz', 'Female 2 - 2531 Hz', 'Female 3 - 6329 Hz',
                           'Male 1 - 162 Hz', 'Male 2 - 405 Hz']):
    name = f'{i+2:02} Voice - {label}'
    board('voice-thomas', name, (28+32*i, -160, DECK))
    check(name, pads(name, ['JV1']), pads('01 Backplane', [f'JV{i+1}']))
    spacer('Voice retention '+str(i+1), 102+32*i, -244, 1.6, DECK)

back_meta = metadata('backplane')
for ref in ['HM1','HM2','HM3','HM4']:
    x,y = back_meta[ref]['xy']
    spacer('Computing '+ref+' - 4 mm OD', x,-y,1.6,DECK)

if CONFIG == 'mega':
    mega_rot = Matrix(((0,-1,0),(-1,0,0),(0,0,-1)))
    board('arduino-mega-reference', '07 Mega 2560 - components face down', (84.5,-3.32,14.24), mega_rot)
    mega_meta = metadata('arduino-mega-reference')
    # All female perimeter headers; onboard ICSP/test pads are not mating contacts.
    mega_refs = ['ADCL','ADCH','XIO','JP6','COMMUNICATION','PWML']
    mega_name = '07 Mega 2560 - components face down'
    # POWER pin 1 is the unused Rev3 reserved contact, absent from the backplane.
    mega_contacts = pads(mega_name,mega_refs)+pads(mega_name,['POWER'],{str(i) for i in range(2,9)})
    check('Mega perimeter headers (reserved POWER 1 omitted)',mega_contacts,pads('01 Backplane',['A1']))
    board('analyser-carrier', '08 Analyser carrier', (25,-215,DECK))
    check('Analyser carrier connector', pads('08 Analyser carrier',['JA1']), pads('01 Backplane',['JA1']))
    for ref in ['HA1','HA2']:
        x,y = back_meta[ref]['xy']
        spacer('Analyser '+ref,x,-y,1.6,DECK)
    mech = json.loads((ROOT.parent/'analyser-carrier'/'mechanical.json').read_text())
    for i,(x,y,angle) in enumerate(mech['module_origins_mm']):
        rot = Matrix.Rotation(math.radians(angle),3,'Z')
        trans = Vector((x+25,-y-215,DECK*2)) - rot @ Vector((54.34,-58,0))
        name = f'{i+9:02} DFRobot analyser {i+1} - modified headers'
        board('dfrobot-module',name,trans,rot)
        check(name,pads(name,['J2J3','J4']),pads('08 Analyser carrier',[f'M{i+1}']),pending_carrier=True)
        for dx in (0,20.32):
            point = rot @ Vector((54.34+dx,-58,0)) + trans
            spacer(f'DFRobot {i+1} spacer {dx}',point.x,point.y,DECK+1.6,DECK*2)
else:
    board('teensy-adapter','07 Teensy adapter',(0,0,DECK))
    check('Adapter Mega contacts',pads('07 Teensy adapter',['JM1']),pads('01 Backplane',['A1']))
    board('teensy41-reference','08 Teensy 4.1',(267.62,13.79,DECK*2),Matrix.Rotation(-math.pi/2,3,'Z'))
    check('Teensy 48 contacts',pads('08 Teensy 4.1',['Teensy41'],{str(i) for i in range(1,49)}),pads('07 Teensy adapter',['JT1','JT2']))

# Remote boards are placed outside the rack and hidden by default, for inspection only.
for i in range(6):
    name = f'REMOTE microphone {i+1} - display placement only'
    root = board('microphone',name,(215+26*(i%3),-80*(i//3),0),hidden=True)
    coll = instances[name][3]
    bpy.ops.mesh.primitive_cylinder_add(vertices=48,radius=.00485,depth=.006,location=(.060,-.067,.0046))
    obj = bpy.context.object
    obj.name = 'Estimated 9.7 mm electret capsule'
    obj.parent = root
    obj.data.materials.append(metal)
    for old in list(obj.users_collection):old.objects.unlink(obj)
    coll.objects.link(obj)
    x,y = metadata('microphone')['U1']['xy']
    proxy_box('U1 - estimated TDFN body',(x,-y,2),(3,3,.8),dark,root,coll)

# Studio and saved viewport: board components remain individually selectable.
studio = bpy.data.collections.new('Studio - cameras and lights')
scene.collection.children.link(studio)
target = Vector((.149,-.200,.01))
bpy.ops.object.camera_add(location=(.44,-.57,.47))
cam = bpy.context.object
cam.name = 'Assembly overview'
cam.rotation_euler = (target-cam.location).to_track_quat('-Z','Y').to_euler()
cam.data.type = 'ORTHO'
cam.data.ortho_scale = .405
cam.data.clip_start = .001
cam.data.clip_end = 10
scene.camera = cam
for old in list(cam.users_collection):old.objects.unlink(cam)
studio.objects.link(cam)
for location, energy, size in [((.1,-.1,.55),18,.45),((-.2,-.3,.25),10,.3),((.4,0,.2),12,.3)]:
    bpy.ops.object.light_add(type='AREA',location=location)
    light = bpy.context.object
    light.data.energy = energy
    light.data.shape = 'DISK'
    light.data.size = size
    light.rotation_euler = (target-light.location).to_track_quat('-Z','Y').to_euler()
    for old in list(light.users_collection):old.objects.unlink(light)
    studio.objects.link(light)
scene.world = bpy.data.worlds.new('Neutral studio')
scene.world.use_nodes = True
scene.world.node_tree.nodes['Background'].inputs[0].default_value = (.14,.17,.21,1)
scene.world.node_tree.nodes['Background'].inputs[1].default_value = .5
scene.render.engine = 'CYCLES'
scene.cycles.samples = 24
scene.cycles.use_denoising = True
scene.render.resolution_x = 1500
scene.render.resolution_y = 1500
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = 'PNG'
scene.render.film_transparent = False
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type == 'VIEW_3D':
            space = area.spaces.active
            space.clip_start = .0001
            space.clip_end = 10
            space.shading.type = 'MATERIAL'
            space.overlay.show_floor = False
            space.region_3d.view_distance = .46
            space.region_3d.view_location = target
            space.region_3d.view_rotation = cam.rotation_euler.to_quaternion()
bpy.ops.object.select_all(action='DESELECT')
scene['readme'] = 'See README.md. Nominal 11.04 mm mating gaps. Amber bodies are estimates. Remote microphone collections hidden. No cables or U2D2 module body.'
scene['configuration'] = CONFIG
bpy.context.view_layer.update()
manifest['visible_board_count'] = sum(not b['hidden'] for b in manifest['boards'])
(ROOT/(CONFIG+'-assembly.json')).write_text(json.dumps(manifest,indent=2)+'\n')
bpy.ops.wm.save_as_mainfile(filepath=str(ROOT/(CONFIG+'-configuration.blend')),compress=True)
scene.render.filepath = str(ROOT/(CONFIG+'-preview.png'))
bpy.ops.render.render(write_still=True)
print('ASSEMBLY COMPLETE',CONFIG,manifest['alignment_checks'])
