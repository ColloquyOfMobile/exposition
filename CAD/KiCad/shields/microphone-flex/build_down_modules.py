"""Rotate the side modules 180 degrees about each socket's insertion axis.

Run with FreeCAD Python. Retains the older upright/support reference files.
Coordinates are PCB X, inverted PCB Y, and Z above the carrier component face.
"""
from pathlib import Path
import hashlib
import json
import sys

sys.path.append('C:/Program Files/FreeCAD 1.0/lib')
import FreeCAD as App
import Part

ROOT = Path(__file__).resolve().parent


def main():
    source = Part.Shape()
    source.read(str(ROOT.parent/'max9814-reference/max9814-reference.step'))
    reference = json.loads((ROOT/'support-model-validation.json').read_text())
    mechanical = json.loads((ROOT/'mechanical.json').read_text())
    # Conservative solid board envelope: the assembly must also clear uncut PCB.
    carrier = Part.makeBox(32,62,1.6,App.Vector(44,-112,-1.6))
    report = {}
    for side,baseline in [('left',(56,74)),('right',(64,84.16))]:
        x,y,angle = mechanical['side_socket_centres_pcb_mm'][side]
        old = reference[side]
        # Rx(180): X remains fixed; Y and Z reverse about row centre and Z=1.27.
        rotation = [[old['module_rotation'][0][j] for j in range(3)],
                    [-old['module_rotation'][1][j] for j in range(3)],
                    [-old['module_rotation'][2][j] for j in range(3)]]
        translation = [
            old['module_translation_mm'][0]+x-baseline[0],
            -2*79.08-old['module_translation_mm'][1]-(y-baseline[1]),
            2*1.27-old['module_translation_mm'][2],
        ]
        matrix = App.Matrix()
        for i in range(3):
            for j in range(3):
                setattr(matrix,f'A{i+1}{j+1}',rotation[i][j])
        matrix.A14,matrix.A24,matrix.A34 = translation
        module = source.copy()
        module.transformShape(matrix)
        assert module.isValid()
        bounds = module.BoundBox
        assert bounds.ZMin < -20 and bounds.ZMax < 3, (side,'Module does not hang below PCB')
        overlap = module.common(carrier).Volume
        assert overlap < .01, (side,'Module intersects carrier',overlap)
        path = ROOT/'3dmodels'/f'module-{side}-down.step'
        module.exportStep(str(path))
        report[side] = {
            'module_rotation':rotation,'module_translation_mm':translation,
            'rotation_from_upright_degrees':180,'rotation_axis':'socket insertion axis / PCB X',
            'socket_contact_height_mm':1.27,
            'z_bounds_relative_to_carrier_top_mm':[bounds.ZMin,bounds.ZMax],
            'carrier_envelope_intersection_mm3':overlap,
            'module_support_holes':[],'physical_fit_verified':False,
            'model_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
        }
    (ROOT/'side-down-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Both downward side modules are valid and clear the carrier envelope.')


if __name__ == '__main__':
    main()
