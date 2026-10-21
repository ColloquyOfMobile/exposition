"""FreeCAD Python: seat the local module reference on the holder's socket."""
from pathlib import Path
import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parent
OUT = ROOT / '3dmodels'
OUT.mkdir(exist_ok=True)
shape = Part.Shape()
shape.read(str(ROOT.parent / 'max9814-reference/max9814-reference.step'))
# Original STEP: planar outline origin, PCB bottom Z=0. Socket pad 1 is
# source (24.003,-2.159). Place module underside at 8.5+2.54 mm.
shape.translate(App.Vector(-24.003, 2.159, 11.04))
shape.exportStep(str(OUT / 'MAX9814_Module_reference.step'))
post = Part.makeCylinder(2, 11.04).cut(Part.makeCylinder(1.1, 11.04))
shaft = Part.makeCylinder(1, 15.64, App.Vector(0, 0, -3))
head = Part.makeCylinder(2, 1.3, App.Vector(0, 0, 12.64))
Part.makeCompound([post, shaft, head]).exportStep(str(OUT / 'M2_insulating_support_reference.step'))
parts = ['#VRML V2.0 utf8']
for solid in shape.Solids:
    box = solid.BoundBox
    color = '.15 .15 .15'
    if box.XLength > 24:
        color = '.39 .23 .54'  # Violet PCB.
    elif box.ZMax > 18 and box.ZLength > 1:
        color = '.65 .65 .65'  # Capsule can.
    elif box.ZMax > 18:
        color = '.025 .025 .025'  # Microphone face.
    elif box.ZLength > 8:
        color = '.75 .62 .22'  # Header pins.
    vertices, faces = solid.tessellate(.08)
    points = ', '.join(f'{v.x/2.54} {v.y/2.54} {v.z/2.54}' for v in vertices)
    indices = ', '.join(' '.join(str(i) for i in f) + ' -1' for f in faces)
    parts.append(f'''Shape {{ appearance Appearance {{ material Material {{ diffuseColor {color} }} }}
 geometry IndexedFaceSet {{ coord Coordinate {{ point [ {points} ] }} coordIndex [ {indices} ] }} }}''')
(OUT / 'MAX9814_Module_reference.wrl').write_text('\n'.join(parts))
print('Saved seated module STEP and coloured VRML reference')
