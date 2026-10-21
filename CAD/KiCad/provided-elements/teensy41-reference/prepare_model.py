"""Run with FreeCAD Python: remove PCB slab supplied natively by KiCad."""
from pathlib import Path
import FreeCAD as A
import Part
ROOT=Path(__file__).resolve().parent
s=Part.read(str(ROOT/'source/Teensy_4.1_Assembly.STEP'))
# Source PCB planar faces are z=0.001 and z=1.599 mm. Its rectangular outline
# is exactly 60.96 x 17.78 mm. Retain top AND underside component geometry.
slab=Part.makeBox(60.9602,17.7802,1.6002,A.Vector(-30.4801,-8.8901,-.0001))
components=s.cut(slab)
components.translate(A.Vector(0,0,-1.6))
components.exportStep(str(ROOT/'3dmodels/Teensy41_components.step'))
print('Removed source PCB slab; retained component geometry and inserted SD card.')
