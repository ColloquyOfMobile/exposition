"""Build the Rev C three-orientation microphone holder as a separate prototype.

Run with KiCad Python. Existing Rev B / production inputs are preserved.
The board has three wired sockets; populate only one MAX9814 module.
"""
import json
import math
import shutil

import pcbnew as p
import schematic_support as s

from design import ROOT, emit
from boards import LIB, LOCAL, xy, text, project, line
import microphone_holder as old

NAME = 'microphone-flex'
FOLDER = ROOT / NAME
POSITIONS = dict(old.positions())
POSITIONS.update(J2=(56, 74, 0), J3=(64, 84.16, 180),
                 H5=(46.5, 66, 0), H6=(46.5, 90, 0),
                 H7=(73.5, 66, 0), H8=(73.5, 90, 0),
                 R4=(49, 97, 0),
                 C7=(47.8, 61.5, 90), C6=(68, 95, 90), R5=(58.5, 88.3, 0),
                 R6=(70.5, 97, 90), TP1=(68, 64, 0), TP2=(52, 64, 0))
POSITIONS.update(M1=(65,89.11,270), J2=(49.12,70.05,0), J3=(70.64,80.65,180),
                 JP1=(47.23,89.6,0), JP2=(72.83,89.99,0),
                 C6=(70.5,99.675,90), C7=(60.3,71.27,90),
                 R4=(46.945,101.15,0), R5=(59.945,84.15,0), R6=(73,100.175,90),
                 TP1=(72.9,53.88,0), TP2=(47.32,53.88,0))
for obsolete in ('R1','R2'):
    POSITIONS.pop(obsolete)


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
    # Headers include a removable shunt in the BOM. Separate footprints show the
    # initial shunt positions without representing the cap as a copper short.
    for name, centre in [('Flex_Gain_Selector',3.81),('Flex_AR_Selector',1.27)]:
        fp=p.FootprintLoad(str(LIB/'Connector_PinHeader_2.54mm.pretty'),
                           'PinHeader_1x03_P2.54mm_Vertical')
        fp.SetFPID(p.LIB_ID('Shields',name))
        for model in fp.Models():
            model.m_Filename=model.m_Filename.replace('${KICAD9_3DMODEL_DIR}', 'C:/Program Files/KiCad/9.0/share/kicad/3dmodels')
        cap=p.FP_3DMODEL()
        cap.m_Filename='${KIPRJMOD}/3dmodels/selector-shunt.wrl'
        cap.m_Offset.y=-centre
        fp.Add3DModel(cap)
        io.FootprintSave(str(LOCAL),fp)


def circuit():
    d=old.circuit(); d.name=NAME
    del d.parts['R1']; del d.parts['R2']
    for ref,signal,fp,setting in [
            ('JP1','GAIN','Flex_Gain_Selector','1-2:50dB; 2-3:40dB; open:60dB. Initially 2-3.'),
            ('JP2','AR','Flex_AR_Selector','1-2:1:500; 2-3:1:2000; open:1:4000. Initially 1-2.')]:
        d.add(ref,signal+' SELECT / HEADER + SHUNT','Shields:'+fp,
              {1:'GND',2:signal,3:'VDD'},'module',
              names={'1':'GND','2':signal,'3':'VDD'},
              description='Removable 2.54mm selector. '+setting+' Power off before moving the shunt.',
              mpn='Gold plated 1x03 2.54mm vertical header + removable 1x02 shunt')
    d.parts['M1']['footprint']='Shields:Flex_Socket_Up'
    d.parts['M1']['value']='UP / ONE MODULE ONLY'
    d.parts['M1']['description']='One MAX9814 module fitted to M1 OR J2 OR J3. Sockets are parallel; never fit multiple modules.'
    # The opposing upright modules reverse physical row order relative to
    # a conventional right-angle socket. Document and verify this explicitly.
    nets={1:'AR',2:'MICOUT',3:'GAIN',4:'VDD',5:'GND'}
    for ref, direction in [('J2','LEFT'),('J3','RIGHT')]:
        d.add(ref,direction+' / 1x05 RIGHT ANGLE',
              'Shields:Flex_Socket_'+direction.title()+'_Overhang',nets,'module',
              names={str(i):n for i,n in nets.items()},
              description='Alternative socket; AR / Out / Gain / Vdd / GND in physical pad order. One module only.',
              mpn='1x05 P2.54mm horizontal female socket; verify purchased dimensions')
    for ref in ('H1','H2'):
        d.parts[ref]['footprint']='Shields:Flex_M5_Slot12x5.5_Keepout'
        d.parts[ref]['value']='M5 SLOT 12x5.5 / TRANSVERSE'
    # User's 2026-10-20 placement retains only the two frame slots.
    for ref in ('H3','H4'):
        del d.parts[ref]
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


def annotate_schematics():
    for name in ('module','module_2','module_3','mechanical','mechanical_2','power','interface','supplies',NAME):
        path=FOLDER/(name+'.kicad_sch')
        if path.exists():
            raw=path.read_text(encoding='utf-8').replace('Rev A engineering prototype','Rev C orientation prototype')
            raw=raw.replace('Rev A prototype - SHIELDS.md direct microphones 2026-10-05 - read ../REVIEW.md',
                            'Rev C removable selectors - 2026-10-20 - read microphone-flex/README.md')
            raw=raw.replace('(date "2026-10-05")','(date "2026-10-20")').replace('(rev "A-prototype")','(rev "C-jumpers")')
            if name==NAME and 'REMOVABLE SELECTORS' not in raw:
                notes=s.Sheet(NAME+'-selector-notes','',{},1)
                for value,y in [
                        ('REMOVABLE SELECTORS / JP1 + JP2 / POWER OFF BEFORE MOVING SHUNTS',180),
                        ('Pad order: 1 = GND, 2 = selected signal, 3 = filtered VDD. Fit one shunt or leave open.',186),
                        ('JP1 GAIN: 1-2 = 50dB; 2-3 = 40dB; no shunt = 60dB. Initial: 2-3.',192),
                        ('JP2 A/R: 1-2 = 1:500; 2-3 = 1:2000; no shunt = 1:4000. Initial: 1-2.',198),
                        ('Fit one MAX9814 module only, in M1 OR J2 OR J3. R1/R2 fixed links are removed.',204)]:
                    notes.text(value,20.32,y,1.27)
                raw=raw.replace('(embedded_fonts no)', '\n'.join(notes.objects)+'\n(embedded_fonts no)')
            path.write_text(raw,encoding='utf-8')


def main():
    footprints(); emit(circuit())
    (FOLDER/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "Shields")(type "KiCad")(uri "${KIPRJMOD}/../Shields.pretty")(options "")(descr "Shared shield footprints")))\n')
    annotate_schematics()
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
    for value,x,y,size in [('COLLOQUY MIC C-J',60,52,.8),('ONE MODULE ONLY',60,60,.8),
                            ('LEFT',48,85.8,.8),('RIGHT',72,85.8,.8),('UP',60,93.2,.8),
                            ('GND 5V OUT',60,100,.8),
                            ('JP1 GAIN',51,85.8,.8),('JP2 A/R',69,85.8,.8),
                            ('50/60/40',51,97,.8),
                            ('500/4K/2K',70,100,.8)]:text(board,value,x,y,size)
    board.GetTitleBlock().SetTitle('Three-orientation MAX9814 holder / 32x62 / slotted M5')
    board.GetTitleBlock().SetRevision('C-jumpers');board.GetTitleBlock().SetDate('2026-10-20')
    board.BuildConnectivity();p.SaveBoard(str(FOLDER/(NAME+'-placed.kicad_pcb')),board,True)
    project(FOLDER,NAME)
    settings_path=FOLDER/(NAME+'.kicad_pro')
    settings=json.loads(settings_path.read_text())
    for cls in settings['net_settings']['classes']:
        cls['clearance']=.2
        cls['track_width']=.25 if cls['name']=='Power' else .2
    settings_path.write_text(json.dumps(settings,indent=2)+'\n')
    shutil.copyfile(FOLDER/(NAME+'.kicad_pro'),FOLDER/(NAME+'-placed.kicad_pro'))
    (FOLDER/'reports').mkdir(exist_ok=True)
    (FOLDER/'mechanical.json').write_text(json.dumps({
        'revision':'C orientation prototype','board_mm':[32,62],'outline_origin_mm':[44,50],
        'artwork_slot_centres_mm':[[16,6],[16,56]],'artwork_slot_size_mm':[12,5.5],
        'artwork_slot_axis':'X / across profile','artwork_slot_centre_travel_mm':6.5,
        'artwork_slot_keepout_mm':[18.5,12], 'positions':['left','right','up'],
        'population':'Exactly one module. Parallel sockets; shared removable gain/AR selectors.',
        'selectors':{'JP1':{'pads':['GND','GAIN','VDD'],'initial_shunt':'2-3','open_gain_db':60},
                     'JP2':{'pads':['GND','AR','VDD'],'initial_shunt':'1-2','open_ar_ratio':'1:4000'}},
        'module_source':'max9814-reference','module_support_holes':[],
        'placement_source':'User-approved microphone-flex-placed.kicad_pcb, 2026-10-20',
        'component_positions_mm':{c['ref']:list(POSITIONS[c['ref']]) for c in data['components']},
        'side_socket_centres_pcb_mm':{'left':list(POSITIONS['J2']),'right':list(POSITIONS['J3'])},
        'side_socket_physical_pin_order':['AR','Out','Gain','Vdd','GND'],
        'physical_fit_verified':False},indent=2)+'\n')
    print('Rev C microphone-flex: 32x62, 12x5.5 transverse slots, three sockets; one module only.')


if __name__=='__main__': main()
