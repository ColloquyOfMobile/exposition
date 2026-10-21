"""Mechanical-only DFR0126 reconstruction. Run with KiCad's Python."""
from pathlib import Path
import math
import shutil
import re
import pcbnew as p

ROOT = Path(__file__).resolve().parent
LIB = Path('C:/Program Files/KiCad/9.0/share/kicad')
ORIGIN = (54.34, 58.0)  # retained mounting centres; corrected bounds 53.5,49 to 75.5,83

def xy(x, y):
    return p.VECTOR2I(p.FromMM(x), p.FromMM(y))

def make():
    previous = p.LoadBoard(str(ROOT/'dfrobot-module.kicad_pcb'))
    b = p.BOARD()
    b.GetDesignSettings().SetBoardThickness(p.FromMM(1.6))
    def line(a, c):
        s = p.PCB_SHAPE(); s.SetShape(p.SHAPE_T_SEGMENT)
        s.SetStart(xy(*a)); s.SetEnd(xy(*c)); s.SetLayer(p.Edge_Cuts)
        s.SetWidth(p.FromMM(.05)); b.Add(s)
    # User's 22 x 34 mm size correction; keep the existing hole centre spacing.
    for a,c in [((55.5,49),(73.5,49)),((75.5,51),(75.5,81)),
                ((73.5,83),(55.5,83)),((53.5,81),(53.5,51))]:
        line(a,c)
    for cx,cy,start in [(73.5,51,-90),(73.5,81,0),(55.5,81,90),(55.5,51,180)]:
        points=[xy(cx+2*math.cos(math.radians(start+d)),
                   cy+2*math.sin(math.radians(start+d))) for d in (0,45,90)]
        s=p.PCB_SHAPE(); s.SetShape(p.SHAPE_T_ARC)
        s.SetArcGeometry(*points); s.SetLayer(p.Edge_Cuts)
        s.SetWidth(p.FromMM(.05)); b.Add(s)
    def fp(lib,name,ref,x,y,angle=0,bottom=False):
        f=p.FootprintLoad(str(LIB/'footprints'/f'{lib}.pretty'),name)
        f.SetReference(ref); f.Reference().SetVisible(False); f.Value().SetVisible(False)
        b.Add(f)
        if bottom:
            f.Flip(xy(0,0),p.FLIP_DIRECTION_TOP_BOTTOM)
        f.SetOrientationDegrees(angle)
        f.SetPosition(xy(ORIGIN[0]+x,ORIGIN[1]+y))
        if ref == 'J1':
            f.Models().clear()
            model = p.FP_3DMODEL()
            model.m_Filename = '${KIPRJMOD}/3dmodels/SMD_3pin_reference.step'
            f.Models().push_back(model)
            return f
        for m in f.Models():
            src=LIB/'3dmodels'/m.m_Filename.split('}/')[-1]
            dst=ROOT/'3dmodels'/src.name
            dst.parent.mkdir(exist_ok=True)
            shutil.copy2(src,dst)
            m.m_Filename='${KIPRJMOD}/3dmodels/'+src.name
        return f
    for i,x in enumerate((0,20.32),1):
        hole = fp('MountingHole','MountingHole_3.2mm_M3_Pad',f'H{i}',x,0)
        for pad in hole.Pads():
            pad.SetSize(xy(3.6,3.6))
        for graphic in list(hole.GraphicalItems()):
            hole.Remove(graphic)
    fp('Package_DIP','DIP-8_W7.62mm','U1',6.35,11.43,90)
    # Modified plug-in assembly: all input/control mating pins face the carrier.
    # Mirrored footprint's row advances along +X with -90 degree rotation.
    fp('Connector_PinHeader_2.54mm','PinHeader_1x06_P2.54mm_Vertical','J2J3',3.81,-5.08,-90,True)
    fp('Connector_PinHeader_2.54mm','PinHeader_1x02_P2.54mm_Vertical','J4',16.51,17.78,-90,True)
    # Visual envelope proxy only: exact original white connector is unidentified.
    fp('Connector_JST','JST_XH_S3B-XH-SM4-TB_1x03-1MP_P2.50mm_Horizontal','J1',7.66,17,0)
    for ref,x,y in [('R1',3.3,7),('R2',3.3,12),('R3',11.5,-.5)]:
        fp('Resistor_SMD','R_0805_2012Metric',ref,x,y,90)
    for ref,x,y in [('C1',2.8,4),('C2',17,8),('C3',17,11),('C4',9,-.5)]:
        fp('Capacitor_SMD','C_0805_2012Metric',ref,x,y)
    fp('LED_SMD','LED_0805_2012Metric','D1',1.2,12,90)
    def text(value,x,y,size=1):
        t=p.PCB_TEXT(b); t.SetText(value); t.SetPosition(xy(ORIGIN[0]+x,ORIGIN[1]+y))
        t.SetTextSize(xy(size,size)); t.SetTextThickness(p.FromMM(.15)); t.SetLayer(p.F_SilkS); b.Add(t)
    text('Audio Analyzer V2.0',10.16,22.5,.9)
    text('MSGEQ7',10.16,14.1,.8)
    text('L  +  -  R  +  -',10.16,-2.8,.8)
    text('R   S',19.05,15.4,.8)
    text('PWR',-.1,9.5,.7)
    text('PHOTO MODEL',10.16,20.7,.7)
    # Keep the user's annotations as the source of these corrections.
    for drawing in previous.GetDrawings():
        if drawing.GetLayer() == p.Cmts_User:
            b.Add(drawing.Duplicate())
    p.SaveBoard(str(ROOT/'dfrobot-module.kicad_pcb'),b)
    path = ROOT/'dfrobot-module.kicad_pcb'
    path.write_text(re.sub(r'\$\{KICAD9_3DMODEL_DIR\}/[^/]+/([^"\s]+)',
                          r'${KIPRJMOD}/3dmodels/\1',path.read_text()))
    # Ensure the plug-in contacts match the existing carrier assumptions.
    f=next(f for f in b.GetFootprints() if f.GetReference()=='J2J3')
    xs=sorted(round(p.ToMM(pad.GetPosition().x)-ORIGIN[0],2) for pad in f.Pads())
    assert xs==[3.81,6.35,8.89,11.43,13.97,16.51],xs
    print('Saved mechanical model; plug-in contact coordinates checked.')

if __name__=='__main__':
    make()
