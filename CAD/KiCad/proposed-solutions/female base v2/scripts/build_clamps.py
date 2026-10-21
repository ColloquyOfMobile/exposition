"""Revision D adjustable insulating supports; run with FreeCAD Python."""
from pathlib import Path
import FreeCAD as App
import Part

CAD=Path(__file__).resolve().parents[2]
V=App.Vector
seat_height=11
tower=Part.makeCylinder(2.25,14.2)
seat=Part.makeBox(3,2.5,seat_height,V(1.5,-1.25,0))
lip=Part.makeBox(2,2.5,1.4,V(1.5,-1.25,12.8))
slot=Part.makeCylinder(1.1,15,V(-.5,0,-.5)).fuse(
    Part.makeCylinder(1.1,15,V(.5,0,-.5))).fuse(
    Part.makeBox(1,2.2,15,V(-.5,-1.1,-.5)))
shape=tower.fuse(seat).fuse(lip).cut(slot)
assert shape.isValid()
for name in ('female base v2','male static v2'):
    root=CAD/name/'3dmodels'; root.mkdir(parents=True,exist_ok=True)
    shape.exportStep(str(root/'support_left.step'))
    shape.exportStl(str(root/'support_left.stl'))
print('Provisional supports: 11mm seat, 1.8mm module slot; 3.2x2.2mm screw slot gives +/-0.5mm adjustment. Measure purchased stack.')
