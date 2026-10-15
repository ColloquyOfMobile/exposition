"""Build the Rev C three-orientation microphone holder as a separate prototype.

Run with KiCad Python. Existing Rev B / production inputs are preserved.
The board has three wired sockets; populate only one MAX9814 module.
"""
import json
import math
import shutil

import pcbnew as p

from design import ROOT, emit
from boards import LIB, LOCAL, xy, text, project, line
import microphone_holder as old

NAME = 'microphone-flex'
FOLDER = ROOT / NAME
POSITIONS = dict(old.positions())
POSITIONS.update(J2=(56, 74, 0), J3=(64, 84.16, 180),
                 H5=(46.5, 66, 0), H6=(46.5, 90, 0),
                 H7=(73.5, 66, 0), H8=(73.5, 90, 0),
                 R1=(61, 82, 90), R2=(59, 82, 90), R4=(49, 97, 0),
                 C7=(47.8, 61.5, 90), C6=(68, 95, 90), R5=(58.5, 88.3, 0),
                 R6=(70.5, 97, 90), TP1=(68, 64, 0), TP2=(52, 64, 0))


def slot_keepout(fp):
    # A 12 x 5.5 drill slot has 6.5 mm centre travel. Expand its entire
    # swept footprint to retain the former 6 mm radial copper keepout.
    for layer in (p.F_Cu, p.B_Cu):
        z = p.ZONE(fp); z.SetIsRuleArea(True); z.SetLayer(layer)
        z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True)
        z.SetDoNotAllowPads(False); z.SetDoNotAllowCopperPour(True)
        z.SetDoNotAllowFootprints(True); z.Outline().NewOutline()
        for i in range(96):
            a = i * math.tau / 96
            x = 6*math.cos(a) + (3.25 if math.cos(a) >= 0 else -3.25)
            z.Outline().Append(p.FromMM(x), p.FromMM(6*math.sin(a)))
        fp.Add(z)


def footprints():
    io = p.PCB_IO_MGR.PluginFind(p.PCB_IO_MGR.KICAD_SEXP)
    temporary = p.BOARD()
    for name, drill, radius in [('Flex_M5_Slot12x5.5_Keepout', (12,5.5), None),
                                ('Flex_M2_Base', (2.2,2.2), 2.5)]:
        fp = p.FOOTPRINT(temporary); temporary.Add(fp)
        fp.SetFPID(p.LIB_ID('Shields', name))
        fp.SetAttributes(p.FP_EXCLUDE_FROM_BOM | p.FP_EXCLUDE_FROM_POS_FILES)
        pad=p.PAD(fp); pad.SetAttribute(p.PAD_ATTRIB_NPTH)
        pad.SetShape(p.PAD_SHAPE_OVAL if radius is None else p.PAD_SHAPE_CIRCLE)
        pad.SetDrillShape(p.PAD_DRILL_SHAPE_OBLONG if radius is None else p.PAD_DRILL_SHAPE_CIRCLE)
        pad.SetDrillSize(xy(*drill)); pad.SetSize(xy(*drill)); pad.SetLayerSet(p.LSET.AllCuMask()); fp.Add(pad)
        if radius is None: slot_keepout(fp)
        else: old.keepout(fp,0,0,radius)
        io.FootprintSave(str(LOCAL),fp)
    for name, libname in [('Flex_Socket_Up','PinSocket_1x05_P2.54mm_Vertical'),
                           ('Flex_Socket_Side','PinSocket_1x05_P2.54mm_Horizontal')]:
        fp=p.FootprintLoad(str(LIB/'Connector_PinSocket_2.54mm.pretty'),libname)
        fp.SetFPID(p.LIB_ID('Shields',name))
        for model in fp.Models():
            model.m_Filename=model.m_Filename.replace('${KICAD9_3DMODEL_DIR}', 'C:/Program Files/KiCad/9.0/share/kicad/3dmodels')
        io.FootprintSave(str(LOCAL),fp)
    # Unique top supports: do not alter the Rev B shared footprint/model.
    fp=p.FootprintLoad(str(LOCAL),'MountingHole_2.2mm_M2_Keepout6')
    fp.SetFPID(p.LIB_ID('Shields','Flex_M2_Top'))
    fp.Models().clear()
    io.FootprintSave(str(LOCAL),fp)


def circuit():
    d=old.circuit(); d.name=NAME
    d.parts['M1']['footprint']='Shields:Flex_Socket_Up'
    d.parts['M1']['value']='UP / ONE MODULE ONLY'
    d.parts['M1']['description']='One MAX9814 module fitted to M1 OR J2 OR J3. Sockets are parallel; never fit multiple modules.'
    # The opposing upright modules reverse physical row order relative to
    # a conventional right-angle socket. Document and verify this explicitly.
    nets={1:'AR',2:'MICOUT',3:'GAIN',4:'VDD',5:'GND'}
    for ref, direction in [('J2','LEFT'),('J3','RIGHT')]:
        d.add(ref,direction+' / 1x05 RIGHT ANGLE','Shields:Flex_Socket_Side',nets,'module',
              names={str(i):n for i,n in nets.items()},
              description='Alternative socket; AR / Out / Gain / Vdd / GND in physical pad order. One module only.',
              mpn='1x05 P2.54mm horizontal female socket; verify purchased dimensions')
    for ref in ('H1','H2'):
        d.parts[ref]['footprint']='Shields:Flex_M5_Slot12x5.5_Keepout'
        d.parts[ref]['value']='M5 SLOT 12x5.5 / TRANSVERSE'
    for ref in ('H3','H4'): d.parts[ref]['footprint']='Shields:Flex_M2_Top'
    for i in range(5,9):
        d.add('H'+str(i),'M2 SIDE SUPPORT BASE','Shields:Flex_M2_Base',{},'mechanical')
    return d


def outline(board):
    x,y,w,h,r=44,50,32,62,2
    for a,b in [((x+r,y),(x+w-r,y)),((x+w,y+r),(x+w,y+h-r)),
                ((x+w-r,y+h),(x+r,y+h)),((x,y+h-r),(x,y+r))]:line(board,a,b)
    for cx,cy,start in [(x+w-r,y+r,-90),(x+w-r,y+h-r,0),(x+r,y+h-r,90),(x+r,y+r,180)]:
        arc=p.PCB_SHAPE(board);arc.SetShape(p.SHAPE_T_ARC)
        def point(a): return xy(cx+r*math.cos(math.radians(a)),cy+r*math.sin(math.radians(a)))
        arc.SetArcGeometry(point(start),point(start+45),point(start+90))
        arc.SetWidth(p.FromMM(.1));arc.SetLayer(p.Edge_Cuts);board.Add(arc)


def main():
    footprints(); emit(circuit())
    (FOLDER/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "Shields")(type "KiCad")(uri "${KIPRJMOD}/../Shields.pretty")(options "")(descr "Shared shield footprints")))\n')
    for name in ('module','module_2','mechanical','mechanical_2','power','interface','supplies',NAME):
        path=FOLDER/(name+'.kicad_sch')
        if path.exists():
            raw=path.read_text(encoding='utf-8').replace('Rev A engineering prototype','Rev C orientation prototype')
            path.write_text(raw,encoding='utf-8')
    data=json.loads((FOLDER/'circuit.json').read_text())
    board=p.BOARD(); board.SetCopperLayerCount(2);board.GetDesignSettings().SetBoardThickness(p.FromMM(1.6))
    outline(board)
    nets={}
    for name in sorted({n for part in data['components'] for n in part['pins'].values() if n}):
        net=p.NETINFO_ITEM(board,name);board.Add(net);nets[name]=net
    for part in data['components']:
        fp=p.FootprintLoad(str(LOCAL),part['footprint'].split(':')[1]);assert fp
        board.Add(fp);fp.SetFPID(p.LIB_ID('Shields',part['footprint'].split(':')[1]))
        fp.SetReference(part['ref']);fp.SetValue(part['value'])
        x,y,angle=POSITIONS[part['ref']];fp.SetOrientationDegrees(angle);fp.SetPosition(xy(x,y))
        fp.Value().SetVisible(False);fp.Reference().SetVisible(False)
        ids=p.KIID_PATH()
        for uid in (part['sheet_path'].strip('/')+'/'+part['uuid']).split('/'): ids.push_back(p.KIID(uid))
        fp.SetPath(ids)
        for pad in fp.Pads():
            net=part['pins'].get(pad.GetNumber());pad.SetNet(nets[net] if net else board.FindNet(0))
    for value,x,y,size in [('COLLOQUY MIC C',60,52,.8),('ONE MODULE ONLY',60,60,.8),
                            ('LEFT',48,85.8,.8),('RIGHT',72,85.8,.8),('UP',60,93.2,.8),
                            ('GND 5V OUT',60,100,.8)]:text(board,value,x,y,size)
    board.GetTitleBlock().SetTitle('Three-orientation MAX9814 holder / 32x62 / slotted M5')
    board.GetTitleBlock().SetRevision('C-prototype');board.GetTitleBlock().SetDate('2026-10-15')
    board.BuildConnectivity();p.SaveBoard(str(FOLDER/(NAME+'-placed.kicad_pcb')),board,True)
    project(FOLDER,NAME)
    settings_path=FOLDER/(NAME+'.kicad_pro')
    settings=json.loads(settings_path.read_text())
    for cls in settings['net_settings']['classes']:
        cls['clearance']=.15
        cls['track_width']=.25 if cls['name']=='Power' else .15
    settings_path.write_text(json.dumps(settings,indent=2)+'\n')
    shutil.copyfile(FOLDER/(NAME+'.kicad_pro'),FOLDER/(NAME+'-placed.kicad_pro'))
    (FOLDER/'reports').mkdir(exist_ok=True)
    (FOLDER/'mechanical.json').write_text(json.dumps({
        'revision':'C orientation prototype','board_mm':[32,62],'outline_origin_mm':[44,50],
        'artwork_slot_centres_mm':[[16,6],[16,56]],'artwork_slot_size_mm':[12,5.5],
        'artwork_slot_axis':'X / across profile','artwork_slot_centre_travel_mm':6.5,
        'artwork_slot_keepout_mm':[18.5,12], 'positions':['left','right','up'],
        'population':'Exactly one module. Parallel sockets; shared gain/AR straps.',
        'module_source':'max9814-reference','side_support_base_centres_pcb_mm':[[46.5,66],[46.5,90],[73.5,66],[73.5,90]],
        'side_socket_centres_pcb_mm':{'left':[56,74,0],'right':[64,84.16,180]},
        'side_socket_physical_pin_order':['AR','Out','Gain','Vdd','GND'],
        'physical_fit_verified':False},indent=2)+'\n')
    print('Rev C microphone-flex: 32x62, 12x5.5 transverse slots, three sockets; one module only.')


if __name__=='__main__': main()
