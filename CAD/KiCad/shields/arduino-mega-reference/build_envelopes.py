"""FreeCAD Python: reference body envelopes from Eagle package outlines.
Heights are representative, not sourced manufacturer component tolerances.
"""
from pathlib import Path
import FreeCAD as A
import Part
ROOT=Path(__file__).resolve().parent/'3dmodels'
ROOT.mkdir(exist_ok=True)
V=A.Vector
usb=Part.makeBox(11.8,15.75,10.6,V(-5.9,-10.15,0))
usb=usb.cut(Part.makeBox(9.8,14.2,8.6,V(-4.9,-10.3,1)))
usb=usb.fuse(Part.makeBox(4.2,8,3,V(-2.1,-7,3)))
usb.exportStep(str(ROOT/'PN61729_envelope.step'))
Part.makeBox(3.2,1.6,1,V(-1.6,-.8,0)).exportStep(str(ROOT/'RESONATOR_envelope.step'))
Part.makeBox(6.858,4.572,2,V(-3.429,-2.286,0)).exportStep(str(ROOT/'QS_envelope.step'))
switch=Part.makeBox(6,6,3,V(-3,-3,0)).fuse(Part.makeCylinder(1.6,1.5,V(0,0,3)))
switch.exportStep(str(ROOT/'TS42_envelope.step'))
Part.makeBox(5,5,1,V(-2.5,-2.5,0)).exportStep(str(ROOT/'MLF32_envelope.step'))
Part.makeBox(4.5,3.2,1,V(-2.25,-1.6,0)).exportStep(str(ROOT/'L1812_envelope.step'))
