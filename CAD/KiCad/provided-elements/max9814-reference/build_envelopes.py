"""Generate approximate microphone and downward header bodies with FreeCAD Python."""
from pathlib import Path
import math
import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parent / '3dmodels'
ROOT.mkdir(exist_ok=True)
V = App.Vector
# Diameter from the original Eagle package. Height is a photo-derived estimate.
can = Part.makeCylinder(4.801, 6.5)
can = can.cut(Part.makeCylinder(4.35, .3, V(0, 0, 6.3)))
Part.makeCompound([can, Part.makeCylinder(4.3, .2, V(0, 0, 6.3))]).exportStep(
    str(ROOT / 'electret_reference.step'))
# Header is installed beneath the board, as on the user's photographed module.
parts = [Part.makeBox(2.54, 12.7, 2.54, V(-1.27, -11.43, -4.14))]
for i in range(5):
    parts.append(Part.makeBox(.64, .64, 8.8, V(-.32, -i * 2.54 - .32, -7.6)))
Part.makeCompound(parts).exportStep(str(ROOT / 'header_down_reference.step'))
Part.makeBox(3, 3, .8, V(-1.5, -1.5, 0)).exportStep(
    str(ROOT / 'TDFN-14-1EP_3x3mm_P0.4mm_EP1.78x2.35mm.step'))

# KiCad VRML coordinates use 0.1-inch units. STEP siblings provide CAD solids.
def cylinder(radius, height, z, color):
    # IndexedFaceSet is portable across KiCad's VRML loaders.
    count = 64
    points = []
    for zz in (z - height / 2, z + height / 2):
        for i in range(count):
            angle = 2 * math.pi * i / count
            points.append(f'{radius * math.cos(angle) / 2.54} '
                          f'{radius * math.sin(angle) / 2.54} {zz / 2.54}')
    faces = []
    for i in range(count):
        j = (i + 1) % count
        faces.append(f'{i} {j} {j + count} {i + count} -1')
    faces.append(' '.join(str(i) for i in reversed(range(count))) + ' -1')
    faces.append(' '.join(str(i + count) for i in range(count)) + ' -1')
    return f'''Shape {{
 appearance Appearance {{ material Material {{ diffuseColor {color} }} }}
 geometry IndexedFaceSet {{ coord Coordinate {{ point [ {', '.join(points)} ] }}
 coordIndex [ {', '.join(faces)} ] }} }}'''


def box(width, length, height, x, y, z, color):
    return f'''Transform {{ translation {x / 2.54} {y / 2.54} {z / 2.54}
 children [ Shape {{
 appearance Appearance {{ material Material {{ diffuseColor {color} }} }}
 geometry Box {{ size {width / 2.54} {length / 2.54} {height / 2.54} }}
 }} ] }}'''


(ROOT / 'electret_reference.wrl').write_text('#VRML V2.0 utf8\n' +
    cylinder(4.801, 6.5, 3.25, '.65 .65 .65') + '\n' +
    cylinder(4.3, .12, 6.53, '.025 .025 .025'))
header = box(2.54, 12.7, 2.54, 0, -5.08, -2.87, '.04 .04 .045')
for i in range(5):
    header += '\n' + box(.64, .64, 8.8, 0, -i * 2.54, -3.2, '.75 .62 .22')
(ROOT / 'header_down_reference.wrl').write_text('#VRML V2.0 utf8\n' + header)
