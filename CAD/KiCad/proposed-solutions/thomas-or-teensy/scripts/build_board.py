"""Place this revision with pcbnew. Writes -placed; never overwrites routed work."""
from pathlib import Path
import json
import re
import shutil
import pcbnew as p
from build_design import HERE, BASE, PROJECT, BODY, CHANNEL

LIB=Path(r'C:\Program Files\KiCad\9.0\share\kicad\footprints')
LOCAL=HERE/'Colloquy.pretty'
mm=p.FromMM
def xy(x,y): return p.VECTOR2I(mm(x),mm(y))

def text(board,value,x,y,size=1.0,layer=p.F_SilkS):
    obj=p.PCB_TEXT(board);obj.SetText(value);obj.SetPosition(xy(x,y));obj.SetLayer(layer)
    obj.SetTextSize(xy(size,size));obj.SetTextThickness(mm(.12));board.Add(obj)
    return obj

def positions():
    old=p.LoadBoard(str(BASE/'colloquy-control-v2.kicad_pcb'))
    fixed={'A1','M1','J2','J6','J7','J5','J1','A-J3','B-J4','Extra1','Extra2','Extra3'}
    pos={fp.GetReference():(p.ToMM(fp.GetPosition().x),p.ToMM(fp.GetPosition().y),fp.GetOrientationDegrees())
         for fp in old.GetFootprints() if fp.GetReference() in fixed}
    pos.update(JT1=(116,55,0),JT2=(131.24,55,0),C1=(215,64,0),C2=(217,77,0),
               JP1=(129,123,90),RS1=(205,114,0),TP30=(212,114,0),TP20=(205,105,0),TP21=(205,109,0),
               TP31=(227,76,0),TP32=(140,126,0),TP33=(229,86,0),TP34=(133,123,0),
               UL1=(112,128,0),CL1=(108,122,90),CL2=(114,134,90),
               CT1=(137,61,90),CT2=(137,65,90),RT6=(111,63,90),
               JM1=(224,185,0),QK1=(239,200,0),RK1=(236,192,90),RK2=(230,192,90),TPM1=(225,197,0),
               K1=(214,309,0),K2=(103,314,0),K3=(184,313,0),
               DK1=(228,312,90),DK2=(93,312,90),DK3=(194,312,90),
               JB1=(205,202,0),JB2=(220,209,0))
    for i,(x,y) in enumerate([(109,75),(111,113),(109,86),(137,68.5),(140,68.5)],1): pos[f'RT{i}']=(x,y,90)
    for i,(x,y) in enumerate([(139,58),(121,126),(137,91),(119.5,117.5),(123,118)],40): pos[f'TP{i}']=(x,y,0)
    for i in range(1,8): pos[f'RN{i}']=(207,121+i*5,0)
    pos.update(RA1=(209,165,0),RA2=(209,170,0))
    for i in range(1,12): pos[f'RP{i}']=(148+(i-1)%6*11,161+(i-1)//6*7,90)
    for n in range(1,5):
        x=149+(n-1)*21
        pos[f'UB{n}']=(x,183,0)
        pos[f'RB{n}1']=(x-5,177,90);pos[f'RB{n}2']=(x+5,177,90)
        pos[f'CB{n}1']=(x-5,183,90);pos[f'CB{n}2']=(x+5,183,90)
    # DACs clustered below Teensy; compact support networks, output filtering south.
    for n in range(1,4):
        x=77+(n-1)*24;y=149
        pos[f'UD{n}']=(x,y,0)
        for k,dx,dy,ang in [(1,-6,-4,90),(2,-10,-4,90),(3,-6,1,90),(4,-10,1,90),
                            (5,6,-3,90),(6,10,-3,90),(7,-7,-9,0),(8,-7,6,0),(9,6,3,90),
                            (10,-5,14,90),(11,5,14,90)]:pos[f'CD{n}{k}']=(x+dx,y+dy,ang)
        for k,dx in [(1,-5),(2,5)]:
            pos[f'RD{n}{k}']=(x+dx,y+10,90)
            pos[f'TPD{(n-1)*2+k}']=(x+dx,y+19,0)
    # Thomas filters and analysers form five independent short vertical strips.
    for n in range(1,6):
        x=80+(n-1)*32
        for ref,dx,dy,ang in [(f'R{n}01',0,222,0),(f'C{n}01',10,228,90),
            (f'R{n}02',0,237,0),(f'C{n}02',10,244,90),(f'R{n}03',0,298,0),
            (f'TP{n}',0,250,0),(f'JP{n+1}',12,294,0),(f'U{n}',4,267,0),
            (f'R{n}11',0,283,0),(f'R{n}16',12,283,90),(f'C{n}12',-3,274,90),
            (f'R{n}13',11,262,90),(f'C{n}14',11,267,90),
            (f'C{n}15',-3,264,90),(f'C{n}16',11,273,90),
            (f'JS{n}',0,288,0),(f'TP{n+10}',-3,279,0)]:pos[ref]=(x+dx,dy,ang)
    for stage,y in [(1,228),(2,244)]:
        pos[f'CF10{stage}']=(99,y,90);pos[f'CF11{stage}']=(89,y+7,0)
    # Six filters grouped three per quad. ADC kick capacitors placed at sockets below.
    for chip in range(2):
        x=86+chip*67;y=199
        pos[f'UE{chip+1}']=(x+23,y,0);pos[f'UX{chip+1}']=(x,y,0)
        pos[f'CX{chip+1}']=(x+6,y-3,90);pos[f'CU{chip+1}']=(x+29,y-3,90)
        for local in range(3):
            n=chip*3+local+1
            # Distinct rows and compact 10K/C network keep oscillator paths away.
            xx=x-6+local*12
            for ref,dx,dy,ang in [(f'RE{n}1',0,-12,90),(f'RE{n}2',0,12,0),
                                (f'CE{n}1',5,7,90),(f'CE{n}2',5,14,90)]:pos[ref]=(xx+dx,y+dy,ang)
            adc_y=85.48-(n-1)*2.54
            pos[f'RE{n}3']=(138.5,adc_y,0)
            pos[f'CE{n}3']=(135,adc_y,0)
            pos[f'TPE{n}']=(158,74+(n-1)*4,0)
    for i,b in enumerate(BODY[:5],1):
        n=CHANNEL[b];pos[f'TPL{i}']=(80+(n-1)*32+8,299,0)
    return pos,old


def custom_film():
    # Panasonic 6041 D1/D3/D4 lands: gap4.0, overall7.0, width3.8mm.
    content='''(footprint "PPS_6041" (version 20241229) (generator "pcbnew") (layer "F.Cu")
      (descr "Panasonic ECHU(X) 6041 D1/D3/D4. Datasheet lands A4 B7 C3.8") (attr smd)
      (property "Reference" "REF**" (at 0 -3.2) (layer "F.SilkS") (effects (font (size 1 1) (thickness 0.12))))
      (property "Value" "PPS_6041" (at 0 3.2) (layer "F.Fab") (effects (font (size 1 1) (thickness 0.12))))
      (fp_rect (start -3 -2.05) (end 3 2.05) (stroke (width 0.1) (type default)) (fill none) (layer "F.Fab"))
      (fp_rect (start -3.75 -2.3) (end 3.75 2.3) (stroke (width 0.05) (type default)) (fill none) (layer "F.CrtYd"))
      (fp_line (start -1.8 -2.15) (end 1.8 -2.15) (stroke (width 0.12) (type default)) (layer "F.SilkS"))
      (fp_line (start -1.8 2.15) (end 1.8 2.15) (stroke (width 0.12) (type default)) (layer "F.SilkS"))
      (pad "1" smd rect (at -2.75 0) (size 1.5 3.8) (layers "F.Cu" "F.Paste" "F.Mask"))
      (pad "2" smd rect (at 2.75 0) (size 1.5 3.8) (layers "F.Cu" "F.Paste" "F.Mask"))
      (embedded_fonts no))'''
    (LOCAL/'PPS_6041.kicad_mod').write_text(content)


def main():
    data=json.loads((HERE/'circuit.json').read_text());pos,old=positions()
    custom_film()
    board=p.BOARD();board.SetCopperLayerCount(2);board.GetDesignSettings().SetBoardThickness(mm(1.6))
    for shape in old.GetDrawings():
        if shape.GetLayer()==p.Edge_Cuts:board.Add(shape.Duplicate())
    for z in old.Zones():
        if z.GetIsRuleArea():board.Add(z.Duplicate())
    for fp in old.GetFootprints():
        if fp.GetReference() in ['H1','H2','H3','H4']:board.Add(fp.Duplicate())
    nets={}
    for i,name in enumerate(data['nets'],1):
        ni=p.NETINFO_ITEM(board,name.replace('/','{slash}'),i);board.Add(ni);nets[name]=ni
    io=p.PCB_IO_MGR.PluginFind(p.PCB_IO_MGR.KICAD_SEXP)
    for comp in data['components']:
        ref=comp['ref'];lib,name=comp.get('source_footprint',comp['footprint']).split(':',1)
        path=(LOCAL if name=='PPS_6041' else BASE/'Colloquy.pretty') if lib=='Colloquy' else LIB/(lib+'.pretty')
        fp=p.FootprintLoad(str(path),name)
        if fp is None:raise ValueError(comp['footprint'])
        fp.SetFPID(p.LIB_ID('Colloquy',name));fp.SetReference('REF**')
        io.FootprintSave(str(LOCAL),fp)
        comp['source_footprint']=comp.get('source_footprint',comp['footprint'])
        comp['footprint']='Colloquy:'+name
        fp.SetReference(ref);fp.SetValue(comp['value']);board.Add(fp)
        x,y,angle=pos[ref];fp.SetOrientationDegrees(angle);fp.SetPosition(xy(x,y))
        pathid=p.KIID_PATH()
        for uid in (comp['sheet_path'].strip('/')+'/'+comp['uuid']).split('/'):pathid.push_back(p.KIID(uid))
        fp.SetPath(pathid)
        present={pad.GetNumber() for pad in fp.Pads() if pad.GetNumber()}
        if present != set(comp['pins']):raise ValueError(f'{ref}: pad mismatch {present ^ set(comp["pins"])}')
        for pad in fp.Pads():
            name_net=comp['pins'].get(pad.GetNumber())
            if name_net:pad.SetNet(nets[name_net])
        fp.Reference().SetVisible(True);fp.Reference().SetLayer(p.F_SilkS);fp.Reference().SetMirrored(False)
        fp.Reference().SetTextSize(xy(.8,.8));fp.Reference().SetTextThickness(mm(.12))
        fp.Reference().SetTextAngle(p.EDA_ANGLE(0,p.DEGREES_T));fp.Reference().SetPosition(xy(x,y-2.6))
        fp.Value().SetVisible(False)
        if ref.startswith(('U','K')):fp.Reference().SetPosition(xy(x,y-6.5))
    for fp in board.GetFootprints():
        if fp.GetReference().startswith('H'):
            name='MountingHole_3.2mm_M3';shutil.copyfile(BASE/'Colloquy.pretty'/(name+'.kicad_mod'),LOCAL/(name+'.kicad_mod'))
    text(board,'COLLOQUY / THOMAS OR TEENSY',151,322,2)
    text(board,'REV A / REVIEW PROTOTYPE / 2026-10-01',154,326,1.1)
    text(board,'B-J4 / NO POWER',185,330,1.2)
    text(board,'THOMAS  < >  TEENSY',224,179,1.1)
    text(board,'NO SHUNT = THOMAS',224,175,1.0)
    text(board,'TEENSY USB POWER',122,117,1.1)
    text(board,'3.3V - NOT 5V TOLERANT',123,50,1.0)
    text(board,'USB',123.5,53,1)
    text(board,'BOARD +5V',222,58,1.1)
    text(board,'MEGA 5V',145,129,1)
    text(board,'JP1 ONLY AGND / GND BOND',148,135,.9)
    text(board,'D2 D3 D4 - AUDIO CONTROL',222,100,.85)
    text(board,'BENCH MIC: GND / +5V / SIG',213,198,.8)
    text(board,'BENCH LINE / AGND',220,214,.8)
    for b,n in CHANNEL.items():
        x=80+(n-1)*32
        pin,hz={'male1':('D11','160Hz'),'male2':('D5','400Hz'),'female1':('D6','1kHz'),'female2':('D46','2.5kHz'),'female3':('D10','6.25kHz')}[b]
        i=BODY.index(b);dac='ABC'[i//2]+' '+('L' if i%2==0 else 'R')
        text(board,b.upper(),x+6,217,1.2)
        text(board,f'{pin} {hz} | DAC {dac}',x+6,253,.8)
        text(board,f'module {i} / {b}',x+7,259,.8)
        text(board,f'LINE OUT / AUDIO RTN',x+6,304,.75)
        text(board,f'{b} - Teensy {14+i} (A{i})',x+6,292,.7)
    # Preserve mechanical envelope on the fabrication layer, no front components under module.
    outline=p.PCB_SHAPE();outline.SetShape(p.SHAPE_T_RECT);outline.SetStart(xy(114.73,53.73));outline.SetEnd(xy(132.51,114.69));outline.SetLayer(p.Dwgs_User);outline.SetWidth(mm(.2));board.Add(outline)
    settings=json.loads((BASE/'colloquy-control-v2.kicad_pro').read_text())
    settings['meta']['filename']=PROJECT+'.kicad_pro'
    ds=settings['board']['design_settings'];ds['drc_exclusions']=[]
    ds['rules'].update(min_clearance=.2,min_track_width=.2,min_via_diameter=.6,min_through_hole_diameter=.3,min_hole_clearance=.25)
    # Do not inherit any v2 ERC/DRC suppression or previous release identity.
    settings['text_variables']={'REVISION':'A-review'}
    classes=settings['net_settings']['classes']
    for nc in classes:
        nc.update(clearance=.2,track_width=.25,via_diameter=.7,via_drill=.35)
        if nc['name']=='Power':nc.update(track_width=2.0,via_diameter=1.2,via_drill=.6)
        if nc['name']=='Analog':nc.update(track_width=.4)
    settings['net_settings']['netclass_patterns']=[{'netclass':'Power','pattern':n} for n in ['+5V','+12V']]+[{'netclass':'Analog','pattern':n} for n in ['MEGA_5V','AGND','GND','TEENSY_VIN','TEENSY_3V3','DAC_3V3','COIL_LOW']]
    project=json.dumps(settings,indent=2)+'\n'
    (HERE/(PROJECT+'.kicad_pro')).write_text(project)
    (HERE/(PROJECT+'-placed.kicad_pro')).write_text(project)
    board.SetFileName(str(HERE/(PROJECT+'-placed.kicad_pcb')))
    p.SaveBoard(str(HERE/(PROJECT+'-placed.kicad_pcb')),board)
    (HERE/(PROJECT+'-placed.kicad_pro')).write_text(project)
    (HERE/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "Colloquy") (type "KiCad") (uri "${KIPRJMOD}/Colloquy.pretty") (options "") (descr "Vendored KiCad and reviewed fixed/PPS footprints")))')
    (HERE/'circuit.json').write_text(json.dumps(data,indent=2)+'\n')
    (HERE/'placement.json').write_text(json.dumps(pos,indent=2)+'\n')
    print(f'Placed {len(list(board.GetFootprints()))} footprints; native geometry retained')

if __name__=='__main__':main()
