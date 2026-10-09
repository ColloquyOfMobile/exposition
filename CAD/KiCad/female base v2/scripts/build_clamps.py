"""Provisional insulating module edge clamps; run with FreeCAD Python."""
from pathlib import Path
import FreeCAD as App
import Part

CAD=Path(__file__).resolve().parents[2]
V=App.Vector
for side,sign in [('left',1),('right',-1)]:
    tower=Part.makeCylinder(2.25,6)
    x=1.5 if sign==1 else -4
    seat=Part.makeBox(2.5,1.5,3,V(x,-.75,0))
    lip=Part.makeBox(2.5,1.5,1.4,V(x,-.75,4.6))
    shape=tower.fuse(seat).fuse(lip).cut(Part.makeCylinder(1.1,7,V(0,0,-.5)))
    assert shape.isValid()
    for name in ('female base v2','male static v2'):
        root=CAD/name/'3dmodels'; root.mkdir(parents=True,exist_ok=True)
        shape.exportStep(str(root/('clamp_'+side+'.step')))
        shape.exportStl(str(root/('clamp_'+side+'.stl')))
print('Provisional clamps: 3mm seat, 1.6mm module slot, 2.2mm screw hole.')
