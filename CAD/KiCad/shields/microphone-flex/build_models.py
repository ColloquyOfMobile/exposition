"""Make provisional upright module/support geometry with FreeCAD Python.

Model coordinates are absolute PCB XY (Cartesian Y inverted), relative to
the carrier's component face in Z. Purchased socket geometry sets the datum.
"""
from pathlib import Path
import json
import sys

sys.path.append('C:/Program Files/FreeCAD 1.0/lib')
import FreeCAD as App
import Part

ROOT=Path(__file__).resolve().parent
OUT=ROOT/'3dmodels';OUT.mkdir(exist_ok=True)
V=App.Vector


def beam(a,b,r=1.8):
    direction=b-a
    return Part.makeCylinder(r,direction.Length,a,direction)


def main():
    source=Part.Shape();source.read(str(ROOT.parent/'max9814-reference/max9814-reference.step'))
    info={}
    for side,rotation,translation,feet,module_holes,plane in [
        ('left',((0,0,-1),(0,-1,0),(-1,0,0)),(43.43,-86.319,25.273),46.5,
         [(-74.254,66),(-84.287,90)],43.43),
        ('right',((0,0,1),(0,1,0),(-1,0,0)),(76.57,-71.841,25.273),73.5,
         [(-73.873,66),(-83.906,90)],76.57),
    ]:
        matrix=App.Matrix()
        for i in range(3):
            for j in range(3):setattr(matrix,f'A{i+1}{j+1}',rotation[i][j])
        matrix.A14,matrix.A24,matrix.A34=translation
        module=source.copy();module.transformShape(matrix)
        assert module.isValid()
        module.exportStep(str(OUT/f'module-{side}.step'))
        # Two independent insulating arms: board screw in foot, upright M2
        # module fixing through a horizontal post. These need prototype fitting.
        sign=1 if side=='left' else -1
        arms=[]
        for module_y,foot_y in module_holes:
            centre_x=plane+sign*2.7
            foot=Part.makeBox(4.6,4.6,2,V(feet-2.3,-foot_y-2.3,0))
            rail=beam(V(feet,-foot_y,1),V(centre_x,module_y,23.241))
            # Extends behind the module underside; never through its board.
            post=Part.makeCylinder(2,5.0,V(plane,module_y,23.241),V(sign,0,0))
            arm=foot.fuse(rail).fuse(post)
            arm=arm.cut(Part.makeCylinder(1.1,4,V(feet,-foot_y,-1)))
            arm=arm.cut(Part.makeCylinder(1.1,6,V(plane-sign*.5,module_y,23.241),V(sign,0,0)))
            assert arm.isValid() and len(arm.Solids)==1,(side,'disconnected arm')
            # Touching support faces are allowed; interpenetrating module solids are not.
            overlap=arm.common(module).Volume
            assert overlap<.02,(side,'module/support overlap',overlap)
            arms.append(arm)
        supports=Part.makeCompound(arms)
        supports.exportStep(str(OUT/f'supports-{side}.step'))
        for i,arm in enumerate(arms,1):arm.exportStl(str(OUT/f'{side}-arm-{i}.stl'))
        info[side]={'module_rotation':[list(r) for r in rotation],'module_translation_mm':list(translation),
                    'module_hole_height_above_carrier_top_mm':23.241,'support_arms':len(arms),
                    'support_material':'insulating polymer, provisional','support_module_intersection_mm3':0,
                    'physical_fit_verified':False}
    (ROOT/'support-model-validation.json').write_text(json.dumps(info,indent=2)+'\n')
    print('Both upright module transforms and four connected insulating arms validated.')


if __name__=='__main__':main()
