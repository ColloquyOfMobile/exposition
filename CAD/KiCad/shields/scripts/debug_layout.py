"""LED/test-header placement and the body microphone board mechanics."""
import math
import shutil
import pcbnew as p
from design import ROOT

mm=p.FromMM
RETIRED=[]  # Retain removed SWIG objects until process exit.
def xy(x,y):return p.VECTOR2I(mm(x),mm(y))


def positions(name):
    if name=='backplane':
        out={'TP31':(211,93,0),'TP33':(216.08,93,0),'TPUSB':(221.16,93,0),'TP34':(223.7,93,0),
             'TPVG':(222.24,202,0),'TPEG':(151.64,322,0)}
        for i in range(1,6):
            x=82.54+(i-1)*30.48
            out.update({f'TPV{i}':(x,202,0),f'TPL{i}':(x+2.54,202,0),
                        f'DT{i}':(x,194,0),f'RLT{i}':(x,197,0),
                        f'TPD{i}':(98.3+(i-1)*10.16,322,0),f'TPA{i}':(100.84+(i-1)*10.16,322,0)})
        for i,ref in enumerate(['P5','P12','PUSB']):
            out[f'D{ref}']=(210+i*7,84,0);out[f'RL{ref}']=(210+i*7,87,0)
        return out
    if name=='teensy-adapter':return {'TP0':(157.1,59.54,0),'TPV':(181,55,0),'TPI':(183.54,55,0),'TPG':(186.08,55,0)}
    if name.startswith('voice'):return {'TP4':(65,89,0),'TP5':(67.54,89,0),
        'R1':(61,55,0),'R2':(61,60,0),'C1':(62,67,0),'C2':(62,76,0),'R3':(57,66,90)}
    if name=='microphone':
        return dict(H1=(60,56,0),H2=(60,106,0),MK1=(60,67,0),U1=(64.5,76,0),
                    R1=(56,74,0),R2=(56,80,0),R3=(60,81.2,0),R4=(56,83,0),R5=(64.5,82,0),R6=(66,86.5,0),
                    C1=(67.6,72.5,90),C2=(56,77,0),C3=(60.5,73.5,0),C4=(67.5,79.2,90),
                    C5=(60.5,76,0),C6=(60.5,78.5,0),C7=(60.5,83,0),D1=(66,89,0),
                    JP1=(54.5,86,90),JP2=(54.5,91,90),TP1=(65,92,0),TP2=(67.54,92,0),J1=(57.5,96.8,0))
    return {}


def shape(owner,kind,layer,width=.12):
    item=p.PCB_SHAPE(owner);item.SetShape(kind);item.SetLayer(layer);item.SetWidth(mm(width));owner.Add(item)
    return item


def circle(owner,x,y,r,layer):
    item=shape(owner,p.SHAPE_T_CIRCLE,layer);item.SetCenter(xy(x,y));item.SetEnd(xy(x+r,y));return item


def footprints():
    removed=RETIRED
    local=ROOT/'Shields.pretty';lib=p.PCB_IO_MGR.PluginFind(p.PCB_IO_MGR.KICAD_SEXP)
    for folder,name in [('LED_SMD','LED_0603_1608Metric'),
                        ('Package_DFN_QFN','TDFN-14-1EP_3x3mm_P0.4mm_EP1.78x2.35mm'),
                        ('Connector_PinHeader_2.54mm','PinHeader_1x03_P2.54mm_Vertical'),
                        ('Connector_JST','JST_EH_B3B-EH-A_1x03_P2.50mm_Vertical')]:
        source=__import__('pathlib').Path(r'C:\Program Files\KiCad\9.0\share\kicad\footprints')/(folder+'.pretty')/(name+'.kicad_mod')
        shutil.copy2(source,local/source.name)
    standard=p.FootprintLoad(r'C:\Program Files\KiCad\9.0\share\kicad\footprints\Connector_PinHeader_2.54mm.pretty','PinHeader_1x01_P2.54mm_Vertical')
    standard.SetFPID(p.LIB_ID('Shields','TestPin_1x01_P2.54mm'))
    # A row of single 2.54 mm bodies abuts: its courtyard is the body cell.
    for item in list(standard.GraphicalItems()):
        if item.GetLayer() in [p.F_CrtYd,p.F_SilkS]:removed.append(item);standard.Remove(item)
    box=shape(standard,p.SHAPE_T_RECT,p.F_CrtYd,.05);box.SetStart(xy(-1.27,-1.27));box.SetEnd(xy(1.27,1.27))
    box=shape(standard,p.SHAPE_T_RECT,p.F_SilkS,.12);box.SetStart(xy(-1.1,-1.1));box.SetEnd(xy(1.1,1.1))
    lib.FootprintSave(str(local),standard)
    board=p.BOARD();f=p.FOOTPRINT(board);board.Add(f)
    f.SetFPID(p.LIB_ID('Shields','Electret_9.7mm_P2.5mm'));f.SetAttributes(p.FP_THROUGH_HOLE)
    f.SetLibDescription('Provisional 9.7 mm electret; 2.5 mm pin pitch. Confirm actual stocked capsule before fabrication.')
    for num,x in [('1',-1.25),('2',1.25)]:
        pad=p.PAD(f);pad.SetNumber(num);pad.SetAttribute(p.PAD_ATTRIB_PTH);pad.SetShape(p.PAD_SHAPE_CIRCLE)
        pad.SetPosition(xy(x,0));pad.SetSize(xy(1.6,1.6));pad.SetDrillSize(xy(.8,.8))
        layers=p.LSET.AllCuMask();layers.AddLayer(p.F_Mask);layers.AddLayer(p.B_Mask);pad.SetLayerSet(layers);f.Add(pad)
    circle(f,0,0,4.85,p.F_SilkS);circle(f,0,0,4.85,p.F_Fab);circle(f,0,0,4.95,p.F_CrtYd)
    lib.FootprintSave(str(local),f)
    f=p.FootprintLoad(r'C:\Program Files\KiCad\9.0\share\kicad\footprints\MountingHole.pretty','MountingHole_5.5mm')
    f.SetFPID(p.LIB_ID('Shields','MountingHole_5.5mm_Keepout12'))
    for item in list(f.GraphicalItems()):
        if item.GetLayer() in [p.F_CrtYd,p.B_CrtYd]:removed.append(item);f.Remove(item)
    circle(f,0,0,6,p.F_CrtYd);circle(f,0,0,6,p.B_CrtYd)
    for layer in [p.F_Cu,p.B_Cu]:
        z=p.ZONE(f);z.SetIsRuleArea(True);z.SetLayer(layer);z.SetDoNotAllowTracks(True);z.SetDoNotAllowVias(True)
        z.SetDoNotAllowPads(False);z.SetDoNotAllowCopperPour(True);z.SetDoNotAllowFootprints(True)
        z.Outline().NewOutline()
        for i in range(96):z.Outline().Append(mm(6*math.cos(i*math.tau/96)),mm(6*math.sin(i*math.tau/96)))
        f.Add(z)
    lib.FootprintSave(str(local),f)


def outline(board):
    for a,z in [((52,50),(68,50)),((70,52),(70,110)),((68,112),(52,112)),((50,110),(50,52))]:
        t=shape(board,p.SHAPE_T_SEGMENT,p.Edge_Cuts,.05);t.SetStart(xy(*a));t.SetEnd(xy(*z))
    for a,m,z in [((68,50),(69.414213562,50.585786438),(70,52)),
                  ((70,110),(69.414213562,111.414213562),(68,112)),
                  ((52,112),(50.585786438,111.414213562),(50,110)),
                  ((50,52),(50.585786438,50.585786438),(52,50))]:
        t=shape(board,p.SHAPE_T_ARC,p.Edge_Cuts,.05);t.SetArcGeometry(xy(*a),xy(*m),xy(*z))
