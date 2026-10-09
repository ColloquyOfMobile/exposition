"""Photo-derived mechanical envelopes; run with FreeCAD 1.0 Python."""
from pathlib import Path
import math
import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parent / '3dmodels'
ROOT.mkdir(exist_ok=True)
V = App.Vector


def box(x, y, z, w, d, h, color):
    return ('box', (x, y, z, w, d, h), color)


def cylinder(x, y, z, r, length, axis, color):
    return ('cylinder', (x, y, z, r, length, axis), color)


def export(name, items):
    solids, vrml = [], ['#VRML V2.0 utf8']
    for kind, values, color in items:
        if kind == 'box':
            x, y, z, w, d, h = values
            solids.append(Part.makeBox(w, d, h, V(x, y, z)))
            geometry = f'Box {{ size {w/2.54} {d/2.54} {h/2.54} }}'
            centre = (x+w/2, y+d/2, z+h/2)
            rotation = ''
        else:
            x, y, z, r, length, axis, = values
            direction = V(1, 0, 0) if axis == 'x' else V(0, 0, 1)
            solids.append(Part.makeCylinder(r, length, V(x, y, z), direction))
            # KiCad's VRML loader requires tessellated cylinders.
            points, faces, count = [], [], 48
            for end in (0, length):
                for i in range(count):
                    a = i*2*math.pi/count
                    point = ((x+end, y+r*math.cos(a), z+r*math.sin(a))
                             if axis == 'x' else
                             (x+r*math.cos(a), y+r*math.sin(a), z+end))
                    points.append(' '.join(str(v/2.54) for v in point))
            for i in range(count):
                j = (i+1)%count
                faces.append(f'{i} {j} {j+count} {i+count} -1')
            faces += [' '.join(str(i) for i in reversed(range(count)))+' -1',
                      ' '.join(str(i+count) for i in range(count))+' -1']
            geometry = ('IndexedFaceSet { coord Coordinate { point [ '+
                        ', '.join(points)+' ] } coordIndex [ '+
                        ', '.join(faces)+' ] }')
            centre, rotation = (0, 0, 0), ''
        vrml.append(f'''Transform {{ translation {' '.join(str(v/2.54) for v in centre)}
 {rotation} children [ Shape {{ appearance Appearance {{ material Material {{
 diffuseColor {color} }} }} geometry {geometry} }} ] }}''')
    compound = Part.makeCompound(solids)
    assert compound.isValid(), name
    compound.exportStep(str(ROOT / (name + '.step')))
    (ROOT / (name + '.wrl')).write_text('\n'.join(vrml))


# Local Cartesian origin is module upper-left; -Y follows PCB-editor +Y.
pot = [box(-1, -11, 3, 16, 13, 12, '.08 .38 .21'),
       cylinder(-7, -4.5, 9, 3.5, 6, 'x', '.6 .6 .6'),
       cylinder(-20, -4.5, 9, 3, 13, 'x', '.65 .65 .65')]
cap = [cylinder(0, 0, 0, 3.2, 7, 'z', '.18 .18 .18'),
       cylinder(0, 0, 7, 3.2, .15, 'z', '.7 .7 .7')]
chip = [box(-5, -2, .2, 10, 4, 1.5, '.04 .04 .04')]
for x in range(8):
    for y in (-3, 2):
        chip.append(box(-4.6+x*1.27, y, 0, .45, 1, .35, '.65 .65 .65'))
export('volume_control', pot)
export('capacitor', cap)
export('unknown_16pin_ic', chip)


def moved(items, dx, dy, dz):
    return [(kind, (v[0]+dx, v[1]+dy, v[2]+dz, *v[3:]), c)
            for kind, v, c in items]


assembly = [box(0, -30, -1.6, 20, 30, 1.6, '.025 .32 .13')]
assembly += pot + moved(cap, 12, -13, 0) + moved(chip, 11, -23, 0)
for x, y in [(3, -13), (3, -18), (3, -23), (3, -28), (11, -28), (17, -28)]:
    assembly.append(box(x-1, y-.6, .1, 2, 1.2, .6, '.5 .37 .2'))
export('module_assembly', assembly)
terminal = [box(-2.54, -4, 0, 10.16, 8, 8, '.025 .3 .65')]
for x in (0, 5.08):
    terminal.append(cylinder(x, 0, 8, 1.8, .3, 'z', '.65 .65 .65'))
export('speaker_terminal', terminal)
print('Generated approximate module envelopes and assembly; all solids valid.')
