"""KiCad mechanical-view wrapper for the upstream Teensy 4.1 assembly."""
from pathlib import Path
import re
import shutil
import pcbnew as p
ROOT=Path(__file__).resolve().parent
LIB=Path('C:/Program Files/KiCad/9.0/share/kicad')
(ROOT/'3dmodels').mkdir(exist_ok=True)
shutil.copy2(ROOT/'source/Teensy_4.1_Assembly.STEP',ROOT/'3dmodels/Teensy_4.1_Assembly.STEP')
b=p.BOARD(); b.GetDesignSettings().SetBoardThickness(p.FromMM(1.6))
def xy(x,y): return p.VECTOR2I(p.FromMM(x),p.FromMM(y))
f=p.FootprintLoad(str(ROOT/'source'),'Teensy41')
f.SetReference('Teensy41'); f.Reference().SetVisible(False); f.Value().SetVisible(False)
f.SetPosition(xy(100,100)); b.Add(f)
# prepare_model.py removed the original slab; KiCad supplies it once here.
for a,c in [((-30.48,-8.89),(30.48,-8.89)),((30.48,-8.89),(30.48,8.89)),
            ((30.48,8.89),(-30.48,8.89)),((-30.48,8.89),(-30.48,-8.89))]:
    s=p.PCB_SHAPE(); s.SetShape(p.SHAPE_T_SEGMENT); s.SetLayer(p.Edge_Cuts)
    s.SetStart(xy(100+a[0],100+a[1])); s.SetEnd(xy(100+c[0],100+c[1])); s.SetWidth(p.FromMM(.1)); b.Add(s)
for i,y in enumerate((-7.62,7.62),1):
    h=p.FootprintLoad(str(LIB/'footprints/Connector_PinHeader_2.54mm.pretty'),'PinHeader_1x24_P2.54mm_Vertical')
    h.SetReference(f'J{i}'); h.Reference().SetVisible(False); h.Value().SetVisible(False)
    b.Add(h)
    h.Flip(xy(0,0),p.FLIP_DIRECTION_TOP_BOTTOM); h.SetOrientationDegrees(-90)
    h.SetPosition(xy(100-29.21,100+y))
    for m in h.Models():
        src=LIB/'3dmodels'/m.m_Filename.split('}/')[-1]; shutil.copy2(src,ROOT/'3dmodels'/src.name)
path=ROOT/'teensy41-reference.kicad_pcb'; p.SaveBoard(str(path),b)
text=path.read_text()
text=text.replace('${KICAD_USER_DIR}/teensy.pretty/Teensy_4.1_Assembly.STEP','${KIPRJMOD}/3dmodels/Teensy41_components.step')
text=text.replace('(xyz 0 0 0.762)','(xyz 0 0 0)')
text=re.sub(r'\$\{KICAD9_3DMODEL_DIR\}/[^/\"]+/([^\"]+)',r'${KIPRJMOD}/3dmodels/\1',text)
path.write_text(text)
print('Saved Teensy 4.1 reference with imported component geometry and downward headers.')
