"""Generate six SHIELDS circuits. Run with KiCad 9's Python; no hardware I/O."""
from pathlib import Path
import copy
import csv
import json
import re
import uuid
import schematic_support as s

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT.parent / 'electronic box v2/colloquy-control-v2'
BODY = ['female1', 'female2', 'female3', 'male1', 'male2']
CHANNEL = dict(zip(BODY, [3, 4, 5, 1, 2]))
R = 'Resistor_SMD:R_0603_1608Metric'
C = 'Capacitor_SMD:C_0603_1608Metric'
C8 = 'Capacitor_SMD:C_0805_2012Metric'
SO8 = 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm'
SO14 = 'Package_SO:SOIC-14_3.9x8.7mm_P1.27mm'
TP = 'TestPoint:TestPoint_Pad_D1.5mm'
HOLE = 'MountingHole:MountingHole_3.2mm_M3'
JUMPER = 'Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm'
NS = uuid.UUID('a7b0ac89-c05b-4dcd-aacd-e80870eaee66')
V2 = {p['ref']: p for p in json.loads((BASE/'circuit.json').read_text())['components']}
FPMAP = json.loads((BASE/'footprint-map.json').read_text())


def analyser_pins():
    pins = {}
    for i,b in enumerate(BODY):
        pins[str(2*i+1)] = b+'/microphone'
        pins[str(2*i+2)] = 'AGND'
        pins[str(11+i)] = b+'/analyser out'
    pins.update({'16':'AGND','17':'analyser/strobe','18':'analyser/reset',
                 '19':'IOREF','20':'GND','21':'+5V'})
    return pins


def voice_pins(body=None, address=None):
    pins = dict(zip(map(str,range(1,6)), ['tone','GND','filter out','AGND','+5V']))
    if body:
        pins['1']=body+'/tone'; pins['3']=body+'/filter out'
    return pins


class Circuit:
    def __init__(self,name):
        self.name=name; self.parts={}
    def add(self,ref,value,fp,pins,sheet='circuit',description='',names=None,types=None,mpn='',ds=''):
        pins={str(k):v for k,v in pins.items()}
        p=dict(ref=ref,value=value,footprint=fp,pins=pins,sheet=sheet,description=description,
               pin_names={k:(names or {}).get(k,k) for k in pins},
               pin_types={k:(types or {}).get(k,'passive') for k in pins},
               assembly='open' if ref.startswith('JS') else 'fit',
               include_bom=not ref.startswith(('TP','H','JS')),mpn=mpn,datasheet=ds)
        self.parts[ref]=p; return p
    def r(self,ref,val,a,b,sheet='circuit',fp=R):
        return self.add(ref,val,fp,{1:a,2:b},sheet)
    def c(self,ref,val,a,b,sheet='circuit',fp=C):
        return self.add(ref,val,fp,{1:a,2:b},sheet)
    def tp(self,ref,net,sheet='circuit'):
        return self.add(ref,net,TP,{1:net},sheet)
    def quad(self,ref,value,stages,rail='+5V',sheet='circuit'):
        pins={'4':rail,'11':'AGND'}; names={'4':'VDD','11':'VSS'}; types={'4':'power_in','11':'power_in'}
        for i,((out,neg,pos),(source,dest)) in enumerate(zip([(1,2,3),(7,6,5),(8,9,10),(14,13,12)],stages)):
            pins.update({str(out):dest,str(neg):dest,str(pos):source})
            names.update({str(out):f'OUT{i+1}',str(neg):f'IN{i+1}-',str(pos):f'IN{i+1}+'})
            types.update({str(out):'output',str(neg):'input',str(pos):'input'})
        self.add(ref,value,SO14,pins,sheet,'Unity-gain followers; unused sections terminated',names,types,mpn=value)


def backplane():
    d=Circuit('backplane')
    for ref,p in V2.items():
        keep=(ref in ['A1','M1','J2','J6','J7','C1','C2','RS1','J1','J5','A-J3','B-J4','Extra1','Extra2','Extra3']
              or ref.startswith(('RN','RP','RA','JP','TP')) or re.fullmatch(r'R[1-5]03',ref))
        if not keep: continue
        p=copy.deepcopy(p);p['footprint']=FPMAP[ref];p['mpn']='';p['datasheet']=''
        if ref.startswith(('R','JP')): p['footprint']='Resistor_SMD:R_0805_2012Metric' if ref.startswith('JP') or ref.endswith('03') else R
        if ref.startswith('TP'): p['footprint']=TP
        if ref=='C2': p['footprint']=C
        if ref=='C1': p.update(footprint='Capacitor_SMD:CP_Elec_10x10.5',value='470uF 25V',mpn='EEE-FK1E471P')
        d.parts[ref]=p
    d.parts['A1']['pins'].update(IORF='IOREF')
    d.parts['A1']['pin_types'].update(IORF='power_out')
    d.add('JA1','ANALYSER - KEY 22','Shields:Header_2x11_Key22',analyser_pins(),'slots')
    for i,b in enumerate(BODY,1):
        d.add(f'JV{i}',b+' - KEY 6','Shields:Header_2x03_Key6',voice_pins(b,i-1),'slots')
        d.add(f'HV{i}','M3 card retention',HOLE,{},'mechanical')
        d.r(f'RL{i}','100K',b+'/filter out','AGND','slots')
        d.tp(f'TPV{i}',b+'/tone','slots')
    for i in [1,2]: d.add(f'HA{i}','M3 analyser retention',HOLE,{},'mechanical')
    for i in range(1,8): d.r(f'RND{i}','100K',V2[f'RN{i}']['pins']['1'],'GND','io')
    d.tp('TPI1','IOREF','slots')
    for i,b in enumerate(BODY,1):
        d.tp(f'TPL{i}',b+'/filter out','slots')
        d.tp(f'TPM{i}',b+'/microphone','slots')
        d.tp(f'TPA{i}',b+'/analyser out','slots')
    return d


def thomas():
    d=Circuit('voice-thomas')
    d.add('JV1','VOICE - KEY 6','Shields:Socket_2x03_Key6',voice_pins(),'interface')
    d.parts['JV1']['pins']['5']=None  # Passive card does not consume external +5V.
    d.add('H1','M3 retention',HOLE,{},'interface')
    d.r('R1','1K2','tone','stage1');d.r('R2','1K2','stage1','filter out')
    # Three parallel footprints per stage cover all five BOMs, including 470 nF.
    for i,net in enumerate(['stage1','filter out'],1):
        d.c(f'C{i}','150nF PPS','AGND',net,fp='Shields:PPS_6041')
        d.c(f'CX{i}','DNP PPS','AGND',net,fp='Shields:PPS_6041')['assembly']='DNP'
        d.c(f'CY{i}','DNP C0G','AGND',net,fp='Capacitor_SMD:C_1206_3216Metric')['assembly']='DNP'
    d.r('R3','100K','tone','GND')
    for i,net in [(1,'tone'),(4,'filter out'),(5,'AGND')]:d.tp(f'TP{i}',net)
    return d


def active():
    d=Circuit('voice-active')
    d.add('JV1','VOICE - KEY 6','Shields:Socket_2x03_Key6',voice_pins(),'interface')
    d.parts['JV1']['pins']['2']=None  # No digital-ground circuit on the active card.
    d.add('H1','M3 retention',HOLE,{},'interface')
    d.r('R1','15K','tone','input');d.r('R2','10K','input','vref')
    d.quad('U1','MCP6024-I/SL',[('input','buffer'),('stage1/in','stage1/out'),('stage2/in','stage2/out'),('ref/raw','vref')])
    for i,(source,ra,cf,cg) in enumerate([('buffer','10K2','12nF','10nF'),('stage1/out','13K3','22nF','3.3nF')],1):
        d.r(f'R{i*2+1}',ra,source,f'stage{i}/mid');d.r(f'R{i*2+2}',ra,f'stage{i}/mid',f'stage{i}/in')
        d.c(f'C{i*2}',cf+' C0G',f'stage{i}/mid',f'stage{i}/out',fp=C8)
        d.c(f'C{i*2+1}',cg+' C0G',f'stage{i}/in','AGND',fp=C8)
    d.r('R7','10K','+5V','ref/raw');d.r('R8','10K','ref/raw','AGND')
    d.c('C6','10uF X7R','ref/raw','AGND',fp=C8)
    d.c('C7','1uF X7R','stage2/out','filter out',fp=C8);d.r('R9','100K','filter out','AGND')
    d.c('C8','100nF','+5V','AGND');d.c('C9','10uF X7R','+5V','AGND',fp=C8)
    for i,net in [(1,'tone'),(4,'filter out'),(5,'AGND')]:d.tp(f'TP{i}',net)
    return d


def msgeq():
    d=Circuit('analyser-msgeq7')
    d.add('JA1','ANALYSER - KEY 22','Shields:Socket_2x11_Key22',analyser_pins(),'interface')
    d.parts['JA1']['pins']['21']=None  # Analyser is powered exclusively by IOREF.
    d.parts['JA1']['pins']['20']=None  # Digital ground unused without identification circuitry.
    for i in [1,2]:d.add(f'H{i}','M3 retention',HOLE,{},'interface')
    for b in BODY:
        n=CHANNEL[b]
        refs=[f'U{n}',f'R{n}11',f'R{n}13',f'R{n}16',f'C{n}12',f'C{n}14',f'C{n}15',f'C{n}16',f'JS{n}',f'TP{n+10}']
        for ref in refs:
            p=copy.deepcopy(V2[ref]);p['sheet']=b;p['pins']={k:('IOREF' if v=='MEGA_5V' else v) for k,v in p['pins'].items()}
            p['footprint']=SO8 if ref.startswith('U') else R if ref.startswith('R') else C if ref.startswith('C') else TP if ref.startswith('TP') else JUMPER
            if ref.startswith('U'):p.update(value='MSGEQ7N',mpn='MSGEQ7N')
            d.parts[ref]=p
    d.tp('TPS','analyser/strobe');d.tp('TPR','analyser/reset');d.tp('TPI','IOREF');d.tp('TPG','AGND');return d


def direct():
    d=Circuit('analyser-direct')
    d.add('JA1','ANALYSER - KEY 22','Shields:Socket_2x11_Key22',analyser_pins(),'interface')
    d.parts['JA1']['pins']['20']=None  # Digital ground unused without identification circuitry.
    for pin in ['17','18']:d.parts['JA1']['pins'][pin]=None
    for i in [1,2]:d.add(f'H{i}','M3 retention',HOLE,{},'interface')
    d.add('JB1','BENCH GND +5V SIGNAL','Connector_JST:JST_EH_B3B-EH-A_1x03_P2.50mm_Vertical',{1:'AGND',2:'+5V',3:'bench/mic'},'interface')
    d.add('JSRC1','HARNESS - CH0 - BENCH','Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical',{1:BODY[0]+'/microphone',2:'ch0/source',3:'bench/mic'},'interface')
    for i,b in enumerate(BODY,1):
        src='ch0/source' if i==1 else b+'/microphone'
        d.r(f'R{i}0','1M',src,'AGND',b)
        d.r(f'R{i}1','10K',src,b+'/mid',b);d.r(f'R{i}2','10K',b+'/mid',b+'/in',b)
        d.c(f'C{i}1','2.2nF C0G',b+'/mid',b+'/buffer',b);d.c(f'C{i}2','1nF C0G',b+'/in','AGND',b)
        d.r(f'R{i}3','100R',b+'/buffer',b+'/analyser out',b);d.c(f'C{i}3','1nF C0G',b+'/analyser out','AGND',b)
        d.tp(f'TP{i}',b+'/analyser out',b)
    for i in range(2):
        stages=[(b+'/in',b+'/buffer') for b in BODY[i*4:i*4+4]]
        stages += [('AGND',f'spare/{i}/{j}') for j in range(4-len(stages))]
        d.quad(f'U{i+1}','MCP6004-I/SL',stages,'IOREF','buffers')
        d.c(f'CB{i+1}','100nF','IOREF','AGND','buffers');d.c(f'CBU{i+1}','10uF X7R','IOREF','AGND','buffers',C8)
    d.tp('TPR','IOREF');d.tp('TPG','AGND');return d


OUTPUTS=[(2,'D6'),(4,'D46'),(5,'D10'),(6,'D11'),(28,'D5'),(7,'D14'),(8,'D7'),(9,'D8'),
         (10,'D9'),(11,'D15'),(12,'D17'),(29,'D16'),(30,'D24'),(31,'D25'),(32,'D2')]
ANALOG=[14,15,16,17,18,19,20,21,22,23,24,25,26,27,38,39]


def teensy():
    d=Circuit('teensy-adapter')
    pins=copy.deepcopy(V2['A1']['pins']);pins.update(IORF='IOREF')
    for pin in ['MISO','MOSI','SCK','RST2','5V2','GND4']:pins.pop(pin,None)
    d.add('JM1','MEGA PATTERN FEMALE','Shields:Mega_Female',pins,'mega','Same physical contact coordinates as the v2 computing slot')
    mapping={'GND':'GND','VIN':'VIN_USB','3V3':'IOREF','13':None}
    for pin,mega in OUTPUTS:mapping[str(pin)]=f'gpio/{pin}'
    for i,pin in enumerate(ANALOG): mapping[str(pin)]=pins[f'A{i}'] if i<5 else f'adc/{pin}'
    for pin,mega in [(34,'D4'),(35,'D3')]:mapping[str(pin)]=f'gpio/{pin}';d.r(f'RC{pin}','100R',f'gpio/{pin}',pins[mega],'controls')
    for pin in [0,1,3,33,36,37,40,41]:mapping[str(pin)]=f'gpio/{pin}';d.tp(f'TP{pin}',f'gpio/{pin}','controls')
    left=['GND']+list(map(str,range(13)))+['3V3']+list(map(str,range(24,33)))
    right=['VIN','GND','3V3']+list(map(str,range(23,12,-1)))+['GND']+list(map(str,range(41,32,-1)))
    for ref,row in [('JT1',left),('JT2',right)]:
        d.add(ref,'Teensy 4.1 '+ref,'Connector_PinSocket_2.54mm:PinSocket_1x24_P2.54mm_Vertical',
              {i+1:mapping.get(pin) for i,pin in enumerate(row)},'teensy',
              'Socket pad 1 at USB end; numbers here are physical socket pads',
              names={str(i+1):pin for i,pin in enumerate(row)})
    for chip in range(4):
        pp={'14':'VIN_USB','7':'GND'};nn={'14':'VCC','7':'GND'};tt={'14':'power_in','7':'power_in'}
        for ch,(oe,a,y) in enumerate([(1,2,3),(4,5,6),(10,9,8),(13,12,11)]):
            i=chip*4+ch;pin,mega=OUTPUTS[i] if i<15 else (None,None)
            pp.update({str(oe):'GND',str(a):f'gpio/{pin}' if pin is not None else 'GND',str(y):pins[mega] if mega else None})
            nn.update({str(oe):f'OE{ch+1}',str(a):f'A{ch+1}',str(y):f'Y{ch+1}'})
            tt.update({str(oe):'input',str(a):'input',str(y):'output'})
            if pin is not None:d.r(f'RD{pin}','100K',f'gpio/{pin}','GND','translators')
        d.add(f'U{chip+1}','SN74LV4T125PWR','Package_SO:TSSOP-14_4.4x5mm_P0.65mm',pp,'translators',names=nn,types=tt,mpn='SN74LV4T125PWR',ds='https://www.ti.com/lit/ds/symlink/sn74lv4t125.pdf')
        d.c(f'CB{chip+1}','100nF','VIN_USB','GND','translators')
    for i,pin in enumerate(ANALOG[5:],5):
        d.r(f'RA{pin}','100K',pins[f'A{i}'],f'adc/{pin}','sensors')
        d.r(f'RB{pin}','150K',f'adc/{pin}','GND','sensors');d.c(f'CA{pin}','10nF C0G',f'adc/{pin}','GND','sensors')
    d.add('D1','1N5819HW','Diode_SMD:D_SOD-123',{1:'MEGA_5V',2:'VIN_USB'},'power','Cathode to MEGA_5V; USB alone supplies VIN',names={'1':'K','2':'A'},mpn='1N5819HW')
    d.c('CV1','10uF X7R','VIN_USB','GND','power',C8);d.c('CI1','10uF X7R','IOREF','GND','power',C8);d.c('CI2','100nF','IOREF','GND','power')
    d.tp('TPV','VIN_USB','power');d.tp('TPI','IOREF','power');d.tp('TPG','GND','power')
    return d


_geometry=s.sym_geometry
def geometry(p):
    if p['ref'].startswith(('#FLG','R','C','JP','JSID','TP')) or len(p['pins'])<=1:return _geometry(p)
    pins=list(p['pins']);groups=[pins[i:i+24] for i in range(0,len(pins),24)];out={}
    for unit,group in enumerate(groups,1):
        left,right=group[:12],group[12:]
        locs=[(pin,-20.32,(len(left)-1)*2.54-i*5.08,0) for i,pin in enumerate(left)]
        locs += [(pin,20.32,(len(right)-1)*2.54-i*5.08,180) for i,pin in enumerate(right)]
        out[unit]=(locs,(15.24,max(len(left)*2.54,7.62)),'block')
    return out
s.sym_geometry=geometry


def emit(d):
    folder=ROOT/d.name;folder.mkdir(exist_ok=True)
    s.HERE=folder;s.PROJECT=d.name;s.NS=uuid.uuid5(NS,d.name);s.ROOT_UUID=s.uid('root')
    for p in d.parts.values():
        p['uuid']=s.uid('component/'+p['ref']);p.setdefault('description','');p.setdefault('datasheet','')
        p.pop('sheet_path',None)
        p['footprint']='Shields:'+p['footprint'].split(':',1)[-1].replace(' ','_')
    groups=list(dict.fromkeys(p['sheet'] for p in d.parts.values()));pages=[]
    library=dict(d.parts)
    for group in groups:
        parts=[p for p in d.parts.values() if p['sheet']==group]
        big=[(p,u) for p in parts if len(p['pins'])>2 for u in geometry(p)]
        small=[p for p in parts if len(p['pins'])<=2]
        chunks=[]
        while big or small:
            bb=big[:2];big=big[2:];n=9 if bb else 18;ss=small[:n];small=small[n:];chunks.append((bb,ss))
        for idx,(bb,ss) in enumerate(chunks):
            name=group+('_'+str(idx+1) if idx else '')
            chunk={p['ref']:p for p,u in bb};chunk.update({p['ref']:p for p in ss})
            for p in chunk.values():
                # Multi-unit blocks stay on their first sheet for board identity.
                p.setdefault('sheet_path',f'/{s.ROOT_UUID}/{s.uid("sheet/"+name)}')
            page=s.Sheet(name,d.name+' / '+group,chunk,len(pages)+2)
            page.text('COLLOQUY / '+d.name.upper()+' / '+group.upper(),15.24,15.24,2.032,True)
            page.text('Rev A engineering prototype | Global labels join nets | See ../REVIEW.md',15.24,25.4,1.016)
            for i,(p,u) in enumerate(bb):page.place(p['ref'],101.6+i*205.74,83.82,u)
            for i,p in enumerate(ss):page.place(p['ref'],66.04+i%3*129.54,(154.94 if bb else 50.8)+(i//3)*30.48)
            page.save();pages.append(name)
    # Explicit external rail declarations, on a separate power-source sheet.
    power=sorted({net for part in d.parts.values() for pin,net in part['pins'].items()
                  if net and part['pin_types'].get(pin)=='power_in'})
    driven={net for part in d.parts.values() for pin,net in part['pins'].items()
            if part['pin_types'].get(pin)=='power_out'}
    flags={}
    for i,net in enumerate(n for n in power if n not in driven):
        ref=f'#FLG{i+1}'
        flags[ref]=dict(ref=ref,value='PWR_FLAG',footprint='',description='External rail via computing/slot connector; verify supply during bring-up',
                       pins={'1':net},pin_names={'1':'pwr'},pin_types={'1':'power_out'},uuid=s.uid(ref),
                       sheet_path=f'/{s.ROOT_UUID}/{s.uid("sheet/supplies")}')
    if flags:
        page=s.Sheet('supplies','External power declarations',flags,len(pages)+2)
        page.text('Rails supplied by the connected board / USB / backplane',20.32,20.32,2,True)
        for i,ref in enumerate(flags):page.place(ref,60.96+i%4*76.2,60.96+i//4*50.8)
        page.save();pages.append('supplies');library.update(flags)
    root=s.Sheet('root',d.name,{},1)
    root.text('COLLOQUY / SHIELDS / '+d.name.upper(),20.32,20.32,3.048,True)
    root.text('Rev A prototype - SHIELDS.md simplified 2026-10-04 - read ../REVIEW.md before fabrication',20.32,30.48,1.27)
    for i,name in enumerate(pages):
        x,y=25.4+i%3*129.54,55.88+i//3*35.56
        root.objects.append(f'(sheet (at {x} {y}) (size 111.76 20.32) (stroke (width 0.254) (type default)) (fill (color 0 0 0 0)) (uuid {s.q(s.uid("sheet/"+name))}) '+s.prop('Sheetname',name,x+55.88,y-2.54,size=1.016)+s.prop('Sheetfile',name+'.kicad_sch',x+55.88,y+22.86,size=1.016)+f'(instances (project {s.q(d.name)} (path {s.q("/"+s.ROOT_UUID)} (page {s.q(i+2)})))))')
    content=f'(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0") (uuid {s.q(s.ROOT_UUID)}) (paper "A3") (title_block (title {s.q(d.name)}) (date "2026-10-04") (rev "A-prototype")) (lib_symbols) '+ '\n'.join(root.objects)+' (sheet_instances (path "/" (page "1"))) (embedded_fonts no))'
    (folder/(d.name+'.kicad_sch')).write_text(content,encoding='utf-8')
    (folder/'Colloquy.kicad_sym').write_text('(kicad_symbol_lib (version 20231120) (generator "kicad_symbol_editor")\n'+'\n'.join(s.lib_symbol(p,True) for p in library.values())+')',encoding='utf-8')
    (folder/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "Colloquy") (type "KiCad") (uri "${KIPRJMOD}/Colloquy.kicad_sym") (options "") (descr "SHIELDS symbols")))')
    (folder/'circuit.json').write_text(json.dumps(dict(project=d.name,root_uuid=s.ROOT_UUID,components=list(d.parts.values()),production_release=False),indent=2)+'\n')
    with (folder/'bom.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['Reference','Value','Footprint','MPN','Assembly'])
        for p in d.parts.values():
            if p.get('include_bom',True):w.writerow([p['ref'],p['value'],p['footprint'],p.get('mpn',''),p['assembly']])
    print(d.name,len(d.parts),'components',len(pages)+1,'sheets')


if __name__=='__main__':
    for build in [backplane,teensy,msgeq,direct,thomas,active]:emit(build())
