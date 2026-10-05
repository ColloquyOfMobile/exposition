"""Place the SHIELDS set in KiCad 9, with project-local footprints.

Writes staging boards only. Routing/final boards are never overwritten here.
"""
from pathlib import Path
import json
import shutil
import pcbnew as p
from design import ROOT, BASE, BODY, CHANNEL, OUTPUTS, ANALOG

LIB=Path(r'C:\Program Files\KiCad\9.0\share\kicad\footprints')
LOCAL=ROOT/'Shields.pretty'
mm=p.FromMM
def xy(x,y):return p.VECTOR2I(mm(x),mm(y))
def pos(obj):return tuple(p.ToMM(obj.GetPosition()))


def line(owner,a,b,layer=p.Edge_Cuts,width=.1):
    g=p.PCB_SHAPE(owner);g.SetShape(p.SHAPE_T_SEGMENT);g.SetStart(xy(*a));g.SetEnd(xy(*b));g.SetLayer(layer);g.SetWidth(mm(width));owner.Add(g)
def rect(owner,x,y,w,h,layer=p.Edge_Cuts):
    for a,b in [((x,y),(x+w,y)),((x+w,y),(x+w,y+h)),((x+w,y+h),(x,y+h)),((x,y+h),(x,y))]:line(owner,a,b,layer)
def text(board,value,x,y,size=.8,layer=p.F_SilkS):
    t=p.PCB_TEXT(board);t.SetText(value);t.SetPosition(xy(x,y));t.SetTextSize(xy(size,size));t.SetTextThickness(mm(.12));t.SetLayer(layer);board.Add(t);return t


def make_slots():
    LOCAL.mkdir(exist_ok=True)
    for rows in [3,11]:
        for kind in ['Header','Socket']:
            name=f'{kind}_2x{rows:02d}_Key{rows*2}'
            temporary=p.BOARD();f=p.FOOTPRINT(temporary);temporary.Add(f);f.SetFPID(p.LIB_ID('Shields',name));f.SetAttributes(p.FP_THROUGH_HOLE)
            layer=p.F_SilkS if kind=='Header' else p.B_SilkS
            for n in range(1,rows*2):
                pad=p.PAD(f);pad.SetNumber(str(n));pad.SetAttribute(p.PAD_ATTRIB_PTH)
                pad.SetShape(p.PAD_SHAPE_RECT if n==1 else p.PAD_SHAPE_OVAL)
                layers=p.LSET.AllCuMask();layers.AddLayer(p.F_Mask);layers.AddLayer(p.B_Mask)
                pad.SetSize(xy(1.7,1.7));pad.SetDrillSize(xy(1,1));pad.SetLayerSet(layers)
                pad.SetPosition(xy((n-1)%2*2.54,(n-1)//2*2.54));f.Add(pad)
            rect(f,-1.5,-1.5,5.54,(rows-1)*2.54+3,layer)
            rect(f,-1.8,-1.8,6.14,(rows-1)*2.54+3.6,p.F_CrtYd if kind=='Header' else p.B_CrtYd)
            f.SetLibDescription('Physical top-view contact map; '+('bottom mounted socket, blocked final cavity' if kind=='Socket' else 'top mounted male, final pin removed'))
            # Canonical library view is front-side; flip back at placement.
            if kind=='Socket':
                f.SetLayer(p.B_Cu);f.Flip(f.GetPosition(),True)
            p.PCB_IO_MGR.PluginFind(p.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(LOCAL),f)
    shutil.copy2(ROOT.parent/'thomas-or-teensy/Colloquy.pretty/PPS_6041.kicad_mod',LOCAL/'PPS_6041.kicad_mod')


def placements(name,old):
    if name=='backplane':
        fixed={'A1','M1','J2','J6','J7','J5','J1','A-J3','B-J4','Extra1','Extra2','Extra3'}
        out={r:(*pos(f),f.GetOrientationDegrees()) for r,f in old.items() if r in fixed}
        out.update(C1=(218,66,0),C2=(218,76,0),JP1=(133,160,0),RS1=(202,115,0),
                   TP30=(208,115,0),TP31=(226,76,0),TP32=(138,160,0),TP33=(229,85,0),TP34=(128,160,0),
                   TP20=(205,104,0),TP21=(205,109,0),RA1=(204,165,0),RA2=(204,170,0),
                   JA1=(78,269,0),HA1=(217,269,0),HA2=(217,312,0))
        for i in range(1,8):out[f'RN{i}']=(204,120+i*5,0);out[f'RND{i}']=(211,120+i*5,90)
        for i in range(1,12):out[f'RP{i}']=(144+(i-1)%6*9,171+(i-1)//6*7,90)
        for i,b in enumerate(BODY,1):
            x=78+(i-1)*32;n=CHANNEL[b]
            out.update({f'JV{i}':(x+3,216,0),f'HV{i}':(x+24,244,0),f'RL{i}':(x+12,255,0),
                        f'R{n}03':(x+12,260,0),f'JP{n+1}':(x+21,260,0),f'TP{n}':(x+7,255,0),
                        f'TP{n+10}':(91+(i-1)*24,324,0),f'TPV{i}':(x+7,206,0)})
        for i in range(1,6):
            out[f'TPL{i}']=(90+(i-1)*32,225,0)
            out[f'TPM{i}']=(100+(i-1)*22,283,0)
            out[f'TPA{i}']=(100+(i-1)*22,305,0)
            out[f'RM{i}']=(100+(i-1)*22,289,0)
            out[f'RMD{i}']=(104+(i-1)*22,292,90)
            out[f'TPD{i}']=(100+(i-1)*22,296,0)
        out.update(RM5=(184,289,0),RMD5=(184,293,90),TPD5=(184,298,0),TPL3=(153.078,225.922,0),TPM5=(160.225909,311.092309,0),TPA5=(184.593555,322.7239,0))
        return out
    if name.startswith('voice'):

        out=dict(JV1=(53,56,0),H1=(74,84,0),UID1=(69,77,0),CID1=(74,72,0),RID1=(64,81,90),JSID1=(62,85,0),
                 TP1=(53,86,0),TP2=(57,86,0),TP3=(61,89,0),TP4=(65,89,0),TP5=(67.54,89,0))
        if name=='voice-thomas':
            out.update(R1=(61,56,0),R2=(70,56,0),R3=(58.5,60,90),C1=(65,63,0),CX1=(65,68,0),CY1=(61,73,90),
                       C2=(74,63,0),CX2=(74,68,0),CY2=(78,73,90))
        else:
            out.update(U1=(68,64,0),R1=(61,54,90),R2=(64,54,90),C1=(61,59,90),R3=(61,63,90),R4=(61,68,90),
                       C2=(65,70,0),C3=(65,73,0),R5=(76,61,90),R6=(76,66,90),C4=(72,54,0),C5=(76,57,0),
                       R7=(77,75,90),R8=(77,78.5,90),C6=(72,71,0),C7=(57,78,90),R9=(57,82,90),C8=(68,57,0),C9=(68,53,0),CID1=(77,71.5,0))
        return out
    if name.startswith('analyser'):
        out=dict(JA1=(53,54,0),H1=(192,54,0),H2=(192,97,0),UID1=(178,85,0),CID1=(184,81,90),RID1=(170,89,90),JSID1=(170,94,0))
        if name=='analyser-msgeq7':
            for i,b in enumerate(BODY):
                n=CHANNEL[b];x=69+i*24;y=65
                out.update({f'U{n}':(x,y,0),f'R{n}11':(x,80,0),f'R{n}16':(x+7,80,90),f'C{n}12':(x-6,70,90),
                            f'R{n}13':(x+7,y-2,90),f'C{n}14':(x+7,y+2,90),f'C{n}15':(x-6,y-3,90),f'C{n}16':(x+7,73,90),
                            f'JS{n}':(x,86,0),f'TP{n+10}':(x-7,y+9,0)})
            out.update(TPS=(180,56,0),TPR=(185,56,0),TPI=(178,90,0),TPG=(183,90,0))
        return out
    if name=='teensy-adapter':
        out=dict(JM1=(0,0,0),JT1=(160,57,0),JT2=(175.24,57,0),D1=(185,63,90),CV1=(181,58,90),
                 CI1=(155,57,90),CI2=(155,62,90),TPV=(188,58,0),TPI=(151,57,0),TP34=(157.175,121,0),TP35=(157.175,125,0))
        for chip in range(4):
            x=151 if chip<2 else 183;y=78+chip%2*24
            out[f'U{chip+1}']=(x,y,0);out[f'CB{chip+1}']=(x,y-5,0)
            for ch in range(4):
                idx=chip*4+ch
                if idx<15:out[f'RD{OUTPUTS[idx][0]}']=(165 if chip<2 else 170,y-4+ch*3,0)
        for i,pin in enumerate(ANALOG[5:]):
            x=151+i%6*7;y=132+i//6*9
            out[f'RA{pin}']=(x,y,90);out[f'RB{pin}']=(x+3,y,90);out[f'CA{pin}']=(x,y+4,0)
        for i,pin in enumerate([0,1,3,33,36,37,40,41]):out[f'TP{pin}']=(162+i*4,120,0)
        for i in range(1,6):out[f'CM{i}']=(178.4,87.48-(i-1)*2.54,0)
        out['CM5']=(178.4,74.5,0)
        out['TPG']=(185.666666,124.666666,0)
        return out
    raise ValueError(name)


def project(folder,name):
    data=json.loads((BASE/'colloquy-control-v2.kicad_pro').read_text())
    data['meta']['filename']=name+'.kicad_pro';data['text_variables']={'REVISION':'A-prototype'}
    settings=data['board']['design_settings'];settings['drc_exclusions']=[]
    settings['rules'].update(min_clearance=.15,min_track_width=.15,min_copper_edge_clearance=.3,
                             min_via_diameter=.6,min_through_hole_diameter=.3,min_via_annular_width=.15,min_hole_clearance=.25)
    data['net_settings']['classes']=[];data['net_settings']['netclass_patterns']=[]
    for cls,width in [('Default',.25),('Power',1.5 if name=='backplane' else .5)]:
        data['net_settings']['classes'].append(dict(name=cls,clearance=.2,track_width=width,via_diameter=.6,via_drill=.3,
              microvia_diameter=.3,microvia_drill=.1,diff_pair_gap=.2,diff_pair_width=.25,diff_pair_via_gap=.2,
              pcb_color='rgba(0, 0, 0, 0.000)',schematic_color='rgba(0, 0, 0, 0.000)',wire_width=6,bus_width=12,line_style=0))
    for net in ['+5V','+12V']:
        data['net_settings']['netclass_patterns'].append({'netclass':'Power','pattern':net})
    # All severities remain enabled. There are no ERC/DRC blanket exclusions.
    (folder/(name+'.kicad_pro')).write_text(json.dumps(data,indent=2)+'\n')


def main():
    make_slots()
    oldboard=p.LoadBoard(str(BASE/'colloquy-control-v2.kicad_pcb'));old={f.GetReference():f for f in oldboard.GetFootprints()}
    for folder in ROOT.iterdir():
        if not (folder/'circuit.json').exists():continue
        name=folder.name;data=json.loads((folder/'circuit.json').read_text());board=p.BOARD();board.SetCopperLayerCount(4 if name in ['backplane','teensy-adapter'] else 2)
        board.GetDesignSettings().SetBoardThickness(mm(1.6));board.GetDesignSettings().m_MinClearance=mm(.15)
        nets={}
        for i,net in enumerate(sorted({n for c in data['components'] for n in c['pins'].values() if n}),1):
            nets[net]=p.NETINFO_ITEM(board,net.replace('/','{slash}'),i);board.Add(nets[net])
        if name=='backplane':
            for g in oldboard.GetDrawings():
                if g.GetLayer()==p.Edge_Cuts:board.Add(g.Duplicate())
            for ref,f in old.items():
                if ref.startswith('H'):board.Add(f.Duplicate())
        elif name.startswith('voice'):rect(board,50,50,30,42)
        elif name.startswith('analyser'):rect(board,50,50,150,55)
        else:rect(board,141.16,53.32,53.34,101.6)
        places=placements(name,old)
        for c in data['components']:
            ref=c['ref'];lib,fpname=c['footprint'].split(':',1)
            if name=='backplane' and ref in old and ref in {'A1','M1','J2','J6','J7','J5','J1','A-J3','B-J4','Extra1','Extra2','Extra3'}:
                fp=old[ref].Duplicate()
            elif ref=='JM1' and name=='teensy-adapter':
                fp=p.FOOTPRINT(board);fp.SetAttributes(p.FP_THROUGH_HOLE);fp.SetLayer(p.B_Cu)
                # Mirror v2 top-view mating positions into adapter top view.
                for op in old['A1'].Pads():
                    number=op.GetNumber()
                    if number in ['MISO','MOSI','SCK','RST2','5V2','GND4']:continue
                    pad=op.Duplicate();fp.Add(pad);x,y=pos(op);pad.SetPosition(xy(335.66-x,y));pad.SetNetCode(0)
                fp.SetLibDescription('Mega contacts viewed from adapter component side; female headers on B side, Teensy on F side')
                fp.SetFPID(p.LIB_ID('Shields','Mega_Female'))
                fp.SetLayer(p.F_Cu);p.PCB_IO_MGR.PluginFind(p.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(LOCAL),fp);fp.SetLayer(p.B_Cu)
            else:
                path=LOCAL if lib=='Shields' else BASE/'Colloquy.pretty' if lib=='Colloquy' else LIB/(lib+'.pretty')
                fp=p.FootprintLoad(str(path),fpname)
                if not fp:raise RuntimeError(f'Missing {path}/{fpname}')
            board.Add(fp);fp.SetReference(ref);fp.SetValue(c['value'])
            if fpname.startswith('Socket_') or (name=='teensy-adapter' and ref.startswith('CM')):fp.Flip(fp.GetPosition(),True)
            if ref!='JM1':
                x,y,angle=places[ref];fp.SetOrientationDegrees(angle);fp.SetPosition(xy(x,y))
            path=p.KIID_PATH()
            for u in (c['sheet_path'].strip('/')+'/'+c['uuid']).split('/'):path.push_back(p.KIID(u))
            fp.SetPath(path)
            for pad in fp.Pads():
                pad.SetNetCode(0);net=c['pins'].get(pad.GetNumber())
                if net:pad.SetNet(nets[net])
            fp.Value().SetVisible(False);fp.Reference().SetVisible(True)
            x,y=pos(fp);fp.Reference().SetPosition(xy(x,y-2));fp.Reference().SetTextSize(xy(.7,.7));fp.Reference().SetTextThickness(mm(.1))
            fp.Reference().SetLayer(p.B_SilkS if fp.GetLayer()==p.B_Cu else p.F_SilkS)
            if ref in ['JM1','A1','M1']:fp.Reference().SetVisible(False)
            # Localize the full library, including SMD parts, for portability.
            localname=fpname.replace(' ','_')
            if not (LOCAL/(localname+'.kicad_mod')).exists():
                saved=fp.Duplicate();saved.SetOrientationDegrees(0);saved.SetPosition(xy(0,0));saved.SetFPID(p.LIB_ID('Shields',localname));p.PCB_IO_MGR.PluginFind(p.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(LOCAL),saved)
            fp.SetFPID(p.LIB_ID('Shields',localname));c['footprint']='Shields:'+localname
            if c.get('assembly')=='DNP':fp.SetDNP(True)
        if name=='backplane':
            text(board,'COLLOQUY / SHIELDS / A',104,179,1.4)
            text(board,'MIC DIRECT / TEENSY - EMPTY JA1',119,184,1)
            text(board,'B-J4 - NO POWER',190,326,1)
            for i,b in enumerate(BODY,1):text(board,f'JV{i} {b}',93+(i-1)*32,202,.9)
            # Card envelopes are assembly drawings, not extra board edges.
            for i in range(5):rect(board,78+i*32,210,30,42,p.Dwgs_User)
            rect(board,75,265,150,55,p.Dwgs_User)
        elif name.startswith('voice'):
            text(board,'ACTIVE 1414' if name=='voice-active' else 'THOMAS female1',65,51.5,.7)
            if name=='voice-active':
                text(board,'SWEET 849-1202',65,90.5,.6,p.B_SilkS);text(board,'ALLOW 707-1414 / IDLE 1MHz',65,52,.55,p.B_SilkS)
        elif name.startswith('analyser'):text(board,name.upper(),125,102,1)
        else:
            text(board,'TEENSY USB POWER ONLY',167,151.8,.8)
            text(board,'3.3V - NOT 5V TOLERANT',167,125,.8)
            rect(board,158.73,55.73,17.78,60.96,p.Dwgs_User)
        board.BuildListOfNets();board.BuildConnectivity()
        p.SaveBoard(str(folder/(name+'-placed.kicad_pcb')),board)
        project(folder,name)
        (folder/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "Shields") (type "KiCad") (uri "${KIPRJMOD}/../Shields.pretty") (options "") (descr "Local SHIELDS footprints")))')
        (folder/'circuit.json').write_text(json.dumps(data,indent=2)+'\n')
        print(name,len(list(board.GetFootprints())),'footprints')


if __name__=='__main__':main()




