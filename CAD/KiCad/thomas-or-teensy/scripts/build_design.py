"""Generate the reviewed Thomas/Teensy circuit. No application/hardware imports.

Run with KiCad 9 Python. Native files are editable; regeneration is explicit.
The v2 circuit is read, never modified. Datasheet choices are in REVIEW.md.
"""
from pathlib import Path
import copy
import json
import re
import math
import csv
import schematic_support as s

HERE = Path(__file__).resolve().parents[1]
BASE = HERE.parent / 'electronic box v2' / 'colloquy-control-v2'
PROJECT = 'thomas-or-teensy'
R0603 = 'Resistor_SMD:R_0603_1608Metric'
R0805 = 'Resistor_SMD:R_0805_2012Metric'
R1206 = 'Resistor_SMD:R_1206_3216Metric'
C0603 = 'Capacitor_SMD:C_0603_1608Metric'
C0805 = 'Capacitor_SMD:C_0805_2012Metric'
TP = 'TestPoint:TestPoint_Pad_D1.5mm'
BODY = ['female1','female2','female3','male1','male2','bench']
CHANNEL = {'male1':1,'male2':2,'female1':3,'female2':4,'female3':5}
DAC_DS = 'https://www.ti.com/lit/gpn/pcm5102a'
LVC_DS = 'https://www.ti.com/lit/ds/symlink/sn74lvc1t45.pdf'
MUX_DS = 'https://www.ti.com/lit/ds/symlink/tmux1511.pdf'
FILM_DS = 'https://mediap.industry.panasonic.eu/assets/imported/industrial.panasonic.com/cdbs/www-data/pdf/RDI0000/ABD0000C173.pdf'


def build_contract():
    data = json.loads((BASE / 'circuit.json').read_text())
    parts = {c['ref']: copy.deepcopy(c) for c in data['components']}
    fpmap = json.loads((BASE / 'footprint-map.json').read_text())
    for ref, p in parts.items():
        p['footprint'] = fpmap[ref]
        if ref.startswith('R'):
            p['footprint'] = R1206 if ref.startswith('RP') else R0805 if ref.startswith(('RN','RA')) or re.fullmatch(r'R[1-5]03',ref) else R0603
        elif ref.startswith('JP'):
            p['footprint'] = R1206
        elif ref.startswith('C'):
            p['footprint'] = C0603
        elif ref.startswith('TP'):
            p['footprint'] = TP
        elif re.fullmatch(r'U[1-5]', ref):
            p.update(value='MSGEQ7N', footprint='Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
                     datasheet='https://mix-sig.com/images/datasheets/MSGEQ7.pdf')
            p['description'] = p['description'].replace('MSGEQ7P','MSGEQ7N')
        p['mpn'] = ''
    parts['C1'].update(value='470uF 25V', footprint='Capacitor_SMD:CP_Elec_10x10.5',
                       mpn='EEE-FK1E471P', description='25V SMD aluminium electrolytic; positive pad 1')
    for c in range(1,6):
        for stage in [1,2]:
            p = parts[f'C{c}0{stage}']
            if c <= 3:
                p.update(footprint='Colloquy:PPS_6041', mpn={1:'ECHU1H224JX9',2:'ECHU1H224JX9',3:'ECHU1H154JX9'}[c],
                         datasheet=FILM_DS, description='5% PPS film, Panasonic ECHU(X), 6041 lands; do not substitute X7R')
                p['value'] += ' PPS 5%'
                if c == 1:
                    # The current ECHU(X) range stops at 220nF. Use a verified
                    # parallel sum, not an invented 470nF manufacturer number.
                    p['value']='220nF PPS 5%'
                    for extra_ref,value,fp,mpn in [(f'CF10{stage}','220nF PPS 5%','Colloquy:PPS_6041','ECHU1H224JX9'),
                                                  (f'CF11{stage}','30nF C0G 5%','Capacitor_SMD:C_1206_3216Metric','')]:
                        extra=copy.deepcopy(p)
                        extra.update(ref=extra_ref,value=value,footprint=fp,mpn=mpn,
                                     description='Parallel with '+p['ref']+': 220nF + 220nF + 30nF = 470nF')
                        parts[extra['ref']]=extra
            else:
                p.update(footprint='Capacitor_SMD:C_1206_3216Metric', description='C0G/NP0 5%, >=25V; do not substitute X7R')
                p['value'] += ' C0G 5%'
        body = next(b for b,n in CHANNEL.items() if n==c)
        parts[f'R{c}03']['pins']['1'] = f'{body}/selected'
    def add(ref, value, fp, pins, sheet, description='', names=None, types=None, mpn='', ds=''):
        p = dict(ref=ref,value=value,footprint=fp,pins={str(k):v for k,v in pins.items()},
                 sheet=sheet,description=description,mpn=mpn or value,datasheet=ds,
                 assembly='fit',include_bom=not ref.startswith('TP'))
        p['pin_names'] = {k:(names or {}).get(k,k) for k in p['pins']}
        p['pin_types'] = {k:(types or {}).get(k,'passive') for k in p['pins']}
        parts[ref]=p
        return p
    def resistor(ref,val,a,b,sheet,desc=''):
        return add(ref,val,R0603,{'1':a,'2':b},sheet,desc,mpn='')
    def cap(ref,val,a,b,sheet,large=False):
        return add(ref,val,C0805 if large else C0603,{'1':a,'2':b},sheet,'Local bypass/filter capacitor; >=16V unless stated')
    def tp(ref,net,sheet):
        return add(ref,net,TP,{'1':net},sheet,'Bare copper test pad')
    # Teensy top view, USB towards north; two separate 24-way sockets.
    left = ['GND']+list(map(str,range(13)))+['3V3']+list(map(str,range(24,33)))
    right = ['VIN','GND','3V3']+list(map(str,range(23,12,-1)))+['GND']+list(map(str,range(41,32,-1)))
    mapping={'GND':'GND','VIN':'TEENSY_VIN','3V3':'TEENSY_3V3','0':'link/to_teensy','1':'link/teensy_tx',
             '2':'DAC_XSMT','3':'MODE_TEENSY','7':'I2S_A_raw','32':'I2S_B_raw','9':'I2S_C_raw',
             '20':'LRCLK_raw','21':'BCLK_raw','22':'TEENSY_A8'}
    mapping.update({str(14+i):f'{b}/adc' for i,b in enumerate(BODY)})
    for ref, pinlist in [('JT1',left),('JT2',right)]:
        names={str(i+1):name for i,name in enumerate(pinlist)}
        add(ref,'Teensy 4.1 '+('LEFT' if ref=='JT1' else 'RIGHT'),
            'Connector_PinSocket_2.54mm:PinSocket_1x24_P2.54mm_Vertical',
            {str(i+1):mapping.get(pin) for i,pin in enumerate(pinlist)},'teensy',
            'USB north. Physical socket pad numbers are not Teensy GPIO numbers.',names=names,
            ds='https://www.pjrc.com/teensy/card11a_rev4_web.pdf',mpn='1x24 2.54mm female socket')
    # Source declarations belong to the socket that actually supplies the rails.
    for pin in ['1','3']:
        parts['JT2']['pin_types'][pin]='power_out'
    for i,name in enumerate(['I2S_A','I2S_B','I2S_C','LRCLK','BCLK'],1):
        resistor(f'RT{i}','33R',name+'_raw',name,'teensy','Source termination at Teensy socket')
    resistor('RT6','10K','DAC_XSMT','GND','teensy','Hardware mute during boot/reset/empty socket')
    for i,net in enumerate(['TEENSY_3V3','DAC_3V3','TEENSY_A8','BCLK','LRCLK'],40):
        tp(f'TP{i}',net,'teensy')
    cap('CT1','100nF','TEENSY_3V3','GND','teensy')
    cap('CT2','10uF','TEENSY_3V3','GND','teensy',True)
    # DAC rail: VIN is an OUTPUT from USB. No board/Mega rail can feed it.
    add('UL1','TLV75533PDBVR','Package_TO_SOT_SMD:SOT-23-5',
        {'1':'TEENSY_VIN','2':'AGND','3':'TEENSY_VIN','4':None,'5':'DAC_3V3'},'dac_power',
        '500mA LDO; EN tied to input; input/output capacitors required',
        names={'1':'IN','2':'GND','3':'EN','4':'NC','5':'OUT'},
        types={'1':'power_in','2':'power_in','3':'input','5':'power_out'},ds='https://www.ti.com/lit/ds/symlink/tlv755p.pdf')
    cap('CL1','10uF','TEENSY_VIN','AGND','dac_power',True)
    cap('CL2','10uF','DAC_3V3','AGND','dac_power',True)
    for n,letter in enumerate('ABC'):
        sheet='dac_'+letter.lower()
        prefix=f'DAC_{letter}'
        pins={'1':'DAC_3V3','2':prefix+'/CAPP','3':'AGND','4':prefix+'/CAPM','5':prefix+'/VNEG',
              '6':BODY[n*2]+'/dac raw','7':BODY[n*2+1]+'/dac raw','8':'DAC_3V3','9':'AGND',
              '10':'AGND','11':'AGND','12':'AGND','13':'BCLK','14':'I2S_'+letter,'15':'LRCLK',
              '16':'AGND','17':'DAC_XSMT','18':prefix+'/LDOO','19':'AGND','20':'DAC_3V3'}
        names=dict(zip(map(str,range(1,21)),['CPVDD','CAPP','CPGND','CAPM','VNEG','OUTL','OUTR','AVDD','AGND','DEMP','FLT','SCK','BCK','DIN','LRCK','FMT','XSMT','LDOO','DGND','DVDD']))
        types={str(i):'power_in' if i in [1,3,8,9,19,20] else 'output' if i in [2,4,5,6,7] else 'power_out' if i==18 else 'input' for i in range(1,21)}
        add('UD'+str(n+1),'PCM5102APWR','Package_SO:TSSOP-20_4.4x6.5mm_P0.65mm',pins,sheet,
            '3-wire I2S; SCK/FMT/FLT/DEMP grounded. All ground pins use local AGND.',names,types,ds=DAC_DS)
        for supply in range(3):
            cap(f'CD{n+1}{supply*2+1}','100nF','DAC_3V3','AGND',sheet)
            cap(f'CD{n+1}{supply*2+2}','10uF','DAC_3V3','AGND',sheet,True)
        cap(f'CD{n+1}7','2.2uF',prefix+'/CAPP',prefix+'/CAPM',sheet,True)
        cap(f'CD{n+1}8','2.2uF',prefix+'/VNEG','AGND',sheet,True)
        cap(f'CD{n+1}9','100nF',prefix+'/LDOO','AGND',sheet)
        for j,b in enumerate(BODY[n*2:n*2+2]):
            resistor(f'RD{n+1}{j+1}','470R',b+'/dac raw',b+'/dac',sheet)
            cap(f'CD{n+1}{j+10}','2.2nF C0G',b+'/dac','AGND',sheet)
            tp(f'TPD{n*2+j+1}',b+'/dac',sheet)
    add('JB1','BENCH MIC GND +5V SIGNAL','Connector_JST:JST_EH_B3B-EH-A_1x03_P2.50mm_Vertical',
        {'1':'AGND','2':'+5V','3':'bench/microphone'},'bench','Matches female base microphone connector')
    add('JB2','BENCH LINE / AGND','Connector_JST:JST_EH_B2B-EH-A_1x02_P2.50mm_Vertical',
        {'1':'bench/dac','2':'AGND'},'bench','Line level only; powered speaker, not a passive speaker')
    # Receive path: switch after first 10K isolates cable from unpowered filter.
    for chip in range(2):
        p_amp={'4':'TEENSY_3V3','11':'AGND'}
        n_amp={'4':'VDD','11':'VSS'}
        t_amp={'4':'power_in','11':'power_in'}
        p_mux={'14':'TEENSY_3V3','7':'AGND'}
        n_mux={'14':'VDD','7':'GND'}
        t_mux={'14':'power_in','7':'power_in'}
        sheet=f'ears{chip+1}'
        for local,(out,neg,pos) in enumerate([(1,2,3),(7,6,5),(8,9,10),(14,13,12)]):
            # Three ears per quad; one properly terminated spare follower.
            i=chip*3+local
            b=BODY[i] if local<3 else f'spare{chip+1}'
            p_amp.update({str(out):b+'/buffer',str(neg):b+'/buffer',str(pos):b+'/filter' if local<3 else 'AGND'})
            n_amp.update({str(out):f'OUT{local+1}',str(neg):f'IN{local+1}-',str(pos):f'IN{local+1}+'})
            t_amp.update({str(out):'output',str(neg):'input',str(pos):'input'})
            sel,src,dst=[(1,2,3),(4,5,6),(10,9,8),(13,12,11)][local]
            p_mux.update({str(sel):'TEENSY_3V3' if local<3 else 'AGND',str(src):b+'/isolator in' if local<3 else 'AGND',str(dst):b+'/mid' if local<3 else None})
            n_mux.update({str(sel):f'SEL{local+1}',str(src):f'S{local+1}',str(dst):f'D{local+1}'})
            t_mux[str(sel)]='input'
            if local==3: continue
            k=i+1
            resistor(f'RE{k}1','10K 1%',b+'/microphone',b+'/isolator in',sheet)
            resistor(f'RE{k}2','10K 1%',b+'/mid',b+'/filter',sheet)
            cap(f'CE{k}1','2.2nF C0G',b+'/mid',b+'/buffer',sheet)
            cap(f'CE{k}2','1nF C0G',b+'/filter','AGND',sheet)
            resistor(f'RE{k}3','100R',b+'/buffer',b+'/adc',sheet)
            cap(f'CE{k}3','1nF C0G',b+'/adc','AGND',sheet)
            tp(f'TPE{k}',b+'/adc',sheet)
        add(f'UE{chip+1}','MCP6004-I/SL','Package_SO:SOIC-14_3.9x8.7mm_P1.27mm',p_amp,sheet,
            '3 unity gain Sallen-Key filters and one grounded spare follower',n_amp,t_amp,
            ds='https://ww1.microchip.com/downloads/aemDocuments/documents/MSLD/ProductDocuments/DataSheets/MCP6001-1R-1U-2-4-1-MHz-Low-Power-Op-Amp-DS20001733L.pdf')
        add(f'UX{chip+1}','TMUX1511PWR','Package_SO:TSSOP-14_4.4x5mm_P0.65mm',p_mux,sheet,
            'Powered-off protection; six ears always enabled when Teensy rail is present, independent of MODE',n_mux,t_mux,ds=MUX_DS)
        cap(f'CX{chip+1}','100nF','TEENSY_3V3','AGND',sheet)
        cap(f'CU{chip+1}','100nF','TEENSY_3V3','AGND',sheet)
    # Mode is hardware-controlled. Relay 1/+ coil; pin8/-; common3,6; NC2,7; NO4,5.
    for n in range(3):
        pins={'1':'+5V','8':'COIL_LOW'}
        for j,(nc,common,no) in enumerate([(2,3,4),(7,6,5)]):
            i=2*n+j
            b=BODY[i]
            pins.update({str(nc):b+'/filter out' if i<5 else None,str(common):b+'/selected' if i<5 else None,str(no):b+'/dac' if i<5 else None})
            if i<5: tp(f'TPL{i+1}',b+'/selected','relays')
        add(f'K{n+1}','G6K-2F-Y DC5','Relay_SMD:Relay_DPDT_Omron_G6K-2F-Y',pins,'relays',
            'Non-latching DPDT: released=THOMAS; +coil1/-coil8; NC2/7, COM3/6, NO4/5',
            names={'1':'COIL+','8':'COIL-','2':'NC1','3':'COM1','4':'NO1','7':'NC2','6':'COM2','5':'NO2'},
            ds='https://omronfs.omron.com/en_US/ecb/products/pdf/en-g6k.pdf')
        add(f'DK{n+1}','1N4148W','Diode_SMD:D_SOD-123',{'1':'+5V','2':'COIL_LOW'},'relays','Flyback cathode to +5V',names={'1':'K','2':'A'})
    add('QK1','2N7002','Package_TO_SOT_SMD:SOT-23',{'1':'COIL_GATE','2':'GND','3':'COIL_LOW'},'relays',
        'Logic MOSFET low-side, total nominal relay coil current 63.3mA',names={'1':'G','2':'S','3':'D'})
    resistor('RK1','100R','MODE','COIL_GATE','relays')
    resistor('RK2','100K','MODE','GND','relays')
    add('JM1','THOMAS / MODE / TEENSY','Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical',
        {'1':'GND','2':'MODE','3':'+5V'},'relays','No shunt=THOMAS; fit exactly one 2-pin shunt')
    tp('TPM1','MODE','relays')
    # Four independent power-domain crossings; A->B, DIR tied VCCA.
    links=[('MODE','MODE_MEGA','+5V','MEGA_5V'),('MODE','MODE_TEENSY','+5V','TEENSY_3V3'),
           ('link/mega_tx','link/to_teensy','MEGA_5V','TEENSY_3V3'),('link/teensy_tx','link/to_mega','TEENSY_3V3','MEGA_5V')]
    for n,(a,b,va,vb) in enumerate(links,1):
        add(f'UB{n}','SN74LVC1T45DBVR','Package_TO_SOT_SMD:SOT-23-6',
            {'1':va,'2':'GND','3':a,'4':b,'5':va,'6':vb},'logic',
            'Ioff + either-rail-off isolation; DIR high gives A to B',
            names={'1':'VCCA','2':'GND','3':'A','4':'B','5':'DIR','6':'VCCB'},
            types={'1':'power_in','2':'power_in','3':'input','4':'output','5':'input','6':'power_in'},ds=LVC_DS)
        resistor(f'RB{n}1','100K',a,'GND','logic')
        resistor(f'RB{n}2','100K',b,'GND','logic')
        cap(f'CB{n}1','100nF',va,'GND','logic')
        cap(f'CB{n}2','100nF',vb,'GND','logic')
    parts['A1']['pins'].update(D18='link/mega_tx',D19='link/to_mega',D30='MODE_MEGA')
    parts['A1']['pin_types'].update(D18='output',D19='input',D30='input')
    for p in parts.values():
        p['uuid']=s.uid('component/'+p['ref'])
        p['sheet_path']=f'/{s.ROOT_UUID}/{s.uid("sheet/"+p["sheet"])}'
        p.setdefault('datasheet','')
        if p['ref'].startswith('TP'): p['assembly']='copper only'
    result=dict(project=PROJECT,revision='A-review',root_uuid=s.ROOT_UUID,components=list(parts.values()),
                nets=sorted({net for p in parts.values() for net in p['pins'].values() if net}),
                source='THOMAS_OR_TEENSY.md + v2 circuit.json; reviewed corrections in REVIEW.md',
                production_release=False)
    (HERE/'circuit.json').write_text(json.dumps(result,indent=2)+'\n')
    return result


_original_geometry=s.sym_geometry
def geometry(p):
    if p['ref']=='A1' or p['ref'].startswith(('#FLG','R','C','JP','JS','TP')) or len(p['pins'])<=1:
        return _original_geometry(p)
    pins=list(p['pins'])
    # Named blocks with both sides, enough room for labels. All pins explicitly shown.
    left,right=pins[:(len(pins)+1)//2],pins[(len(pins)+1)//2:]
    locs=[(pin,-20.32,(len(left)-1)*5.08/2-i*5.08,0) for i,pin in enumerate(left)]
    locs += [(pin,20.32,(len(right)-1)*5.08/2-i*5.08,180) for i,pin in enumerate(right)]
    return {1:(locs,(15.24,max(len(left)*2.54,7.62)),'block')}
s.sym_geometry=geometry


def schematic(data):
    parts={p['ref']:p for p in data['components']}
    library=dict(parts)
    pages=[]
    # Five ordinary v2 audio pages plus purpose-specific new sheets.
    groups=list(dict.fromkeys(p['sheet'] for p in parts.values()))
    for group in groups:
        subset=[p for p in parts.values() if p['sheet']==group]
        # Retain stable references but use continuation pages so no A3 sheet is crowded.
        blocks=[p for p in subset if len(p['pins'])>2]
        small=[p for p in subset if len(p['pins'])<=2]
        if group=='controller':
            chunks=[subset]
        else:
            chunks=[]
            while blocks or small:
                chunk=blocks[:2];blocks=blocks[2:]
                budget=12 if chunk else 24
                chunk+=small[:budget];small=small[budget:]
                chunks.append(chunk)
        for j,chunk in enumerate(chunks):
            name=group if j==0 else group+'_'+str(j+1)
            for p in chunk:
                p['sheet_path']=f'/{s.ROOT_UUID}/{s.uid("sheet/"+name)}'
            page=s.Sheet(name,group.replace('_',' ').upper(),{p['ref']:p for p in chunk},len(pages)+2)
            page.text('THOMAS / TEENSY - '+group.replace('_',' ').upper(),15.24,15.24,2.032,True)
            page.text('Rev A review | Global net labels join sheets. Pin names and pad numbers are distinct.',15.24,25.4,1.016)
            if group=='controller':
                for unit,x,y in [(1,106.68,99.06),(2,294.64,91.44),(3,106.68,220.98),(4,294.64,220.98)]:
                    page.place('A1',x,y,unit)
            else:
                big=[p for p in chunk if len(p['pins'])>2]
                sml=[p for p in chunk if len(p['pins'])<=2]
                for i,p in enumerate(big): page.place(p['ref'],101.6+i*205.74,88.9)
                start=154.94 if big else 50.8
                pitch=25.4 if big else 27.94
                for i,p in enumerate(sml): page.place(p['ref'],66.04+(i%3)*129.54,start+(i//3)*pitch)
            if group=='power' and j==0:
                for i,net in enumerate(['+5V','+12V','GND','AGND']):
                    ref=f'#FLG{i+1}'
                    flag=dict(ref=ref,value='PWR_FLAG',footprint='',description='External supply / ground reference',
                              pins={'1':net},pin_names={'1':'pwr'},pin_types={'1':'power_out'},uuid=s.uid(ref),sheet_path=f'/{s.ROOT_UUID}/{s.uid("sheet/"+name)}')
                    page.parts[ref]=flag;library[ref]=flag
                    page.place(ref,50.8+i*76.2,251.46)
            page.save();pages.append((name,group))
    # Root sheet navigation arranged on A2 for all continuation sheets.
    root=s.Sheet('root','Thomas or Teensy',{},1)
    root.text('COLLOQUY / THOMAS OR TEENSY',20.32,20.32,3.048,True)
    root.text('One mode shunt - five unchanged body interfaces - Teensy USB powered only',20.32,30.48,1.524)
    for i,(name,title) in enumerate(pages):
        x,y=25.4+(i%4)*139.7,55.88+(i//4)*34.29
        root.objects.append(f'(sheet (at {x} {y}) (size 119.38 20.32) (stroke (width 0.254) (type default)) (fill (color 0 0 0 0)) (uuid {s.q(s.uid("sheet/"+name))}) '
            +s.prop('Sheetname',name,x+59.69,y-2.54,size=1.016)+s.prop('Sheetfile',name+'.kicad_sch',x+59.69,y+22.86,size=1.016)
            +f'(instances (project {s.q(PROJECT)} (path {s.q("/"+s.ROOT_UUID)} (page {s.q(i+2)})))))')
        root.text(f'{i+2:02d}  '+title.replace('_',' ').upper(),x+5.08,y+10.16,1.27)
    root.text('REVIEW PROTOTYPE: read REVIEW.md and validation reports before fabrication.\nNC relay contacts select Thomas. No shunt = Thomas. Teensy 3.3V GPIO are not 5V tolerant.\nProtected translators replace LV1T34; powered-off microphone isolation added after first 10K.\nFive SMD MSGEQ7N; default attenuation bypasses OPEN. RP1..RP11 remain provisional 10K.',20.32,370.84,1.27)
    content=f'(kicad_sch (version 20250114) (generator "eeschema") (generator_version "9.0") (uuid {s.q(s.ROOT_UUID)}) (paper "A2") (title_block (title "Thomas or Teensy / system") (date "2026-10-01") (rev "A-review")) (lib_symbols) '+ '\n'.join(root.objects)+' (sheet_instances (path "/" (page "1"))) (embedded_fonts no))'
    (HERE/(PROJECT+'.kicad_sch')).write_text(content,encoding='utf-8')
    (HERE/'Colloquy.kicad_sym').write_text('(kicad_symbol_lib (version 20231120) (generator "kicad_symbol_editor")\n'+'\n'.join(s.lib_symbol(p,True) for p in library.values())+')',encoding='utf-8')
    (HERE/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "Colloquy") (type "KiCad") (uri "${KIPRJMOD}/Colloquy.kicad_sym") (options "") (descr "Reviewed project symbols")))')
    (HERE/'circuit.json').write_text(json.dumps(data,indent=2)+'\n')
    print(f'{len(parts)} components; {len(pages)+1} schematic sheets; {len(data["nets"])} nets')


if __name__=='__main__':
    schematic(build_contract())
