"""Approximate SMD horizontal 3-pin connector envelope; run with FreeCAD Python."""
from pathlib import Path
import FreeCAD as App
import Part

root = Path(__file__).resolve().parent
# Matches the library SMD footprint's body outline. Identity/height are estimates.
housing = Part.makeBox(10.9, 7, 5.8, App.Vector(-5.45, -5.3, .2))
opening = Part.makeBox(9.3, 3.6, 3.8, App.Vector(-4.65, -5.4, 1.2))
housing = housing.cut(opening)
parts = [housing]
for x in (-2.5, 0, 2.5):
    parts.append(Part.makeBox(.6, 7.8, .4, App.Vector(x-.3, -3.3, 0)))
for x in (-5.7, 5.7):
    parts.append(Part.makeBox(1.2, 3.6, .3, App.Vector(x-.6, -5.1, 0)))
Part.makeCompound(parts).exportStep(str(root/'3dmodels'/'SMD_3pin_reference.step'))
print('Saved SMD envelope, no through-hole leads; 12.6 x 9.8 x 6 mm overall.')
