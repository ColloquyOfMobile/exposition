"""Build a label-free, continuous-wire reading copy using existing circuit data.

Run with KiCad's Python. Coordinates and connector units are presentation only;
verify_wired_schematic.py checks the exported electrical graph independently.
"""
from pathlib import Path
from collections import Counter
import copy
import json
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'scripts'))
import schematic_support as s

NAME = 'teensy-adapter-wired'
OUT = HERE / 'wired'
ROOT = s.uid('sheetfile/' + NAME)
parts = {p['ref']: copy.deepcopy(p) for p in json.loads((HERE/'circuit.json').read_text())['components']}
for p in parts.values():
    p['sheet_path'] = '/' + ROOT
# Preserve both ERC-only declarations from the original supplies sheet.
for i,net in enumerate(('GND','VIN_USB'),1):
    ref='#FLG'+str(i)
    parts[ref]=dict(ref=ref,value='PWR_FLAG',footprint='',description='Original external supply declaration',
                    pins={'1':net},pin_names={'1':'~'},pin_types={'1':'power_out'},
                    uuid=s.uid(NAME+ref),sheet_path='/'+ROOT,include_bom=False)
s.HERE, s.PROJECT = OUT, NAME
sheet = s.Sheet(NAME, 'Teensy adapter / continuous wiring / reading copy', parts, 1)
geometries, positions, segments = {}, {}, []
placed = set()


def text(value, x, y, size=1.5, bold=False):
    sheet.text(value, x, y, size, bold)


def wire(*points):
    for a, b in zip(points, points[1:]):
        a, b = tuple(round(v, 4) for v in a), tuple(round(v, 4) for v in b)
        assert a[0] == b[0] or a[1] == b[1], (a, b)
        if a != b:
            segments.append((a, b))


def unit(ref, number, locs, center, box, style='block'):
    """Register one graphical unit, with absolute pin coordinates."""
    x, y = center
    geometries.setdefault(ref, {})[number] = (
        [(pin, round(px-x, 4), round(y-py, 4), angle) for pin, px, py, angle in locs], box, style)
    positions[ref, number] = center


def connector(ref, number, pin_rows, endpoint, body, side):
    ys = [row for _, row in pin_rows]
    y = (min(ys)+max(ys))/2
    unit(ref, number, [(pin, endpoint, row, 180 if side == 'right' else 0)
                      for pin, row in pin_rows], (body, y),
         (abs(body-endpoint)-5.08, (max(ys)-min(ys))/2+3.81))


def passive(ref, x, y, vertical=False):
    style = 'capacitor' if ref.startswith('C') else 'resistor'
    locs = [('1', x, y-5.08, 270), ('2', x, y+5.08, 90)] if vertical else [
        ('1', x-5.08, y, 0), ('2', x+5.08, y, 180)]
    unit(ref, 1, locs, (x, y), (2.54, 2.54) if style == 'capacitor' else (
        (1.016, 2.54) if vertical else (2.54, 1.016)), style)


def place_all():
    for (ref, number), (x, y) in positions.items():
        p = parts[ref]
        locs, (w, h), style = geometries[ref][number]
        # Keep captions beside shunt parts, above series parts and inside connectors.
        if style in ('capacitor', 'resistor'):
            vertical = locs[0][1] == locs[1][1]
            rx, ry = (x+4, y-1.5) if vertical else (x, y-5)
            just = 'left' if vertical else ''
            value_y = ry+3 if vertical else ry-3
        elif ref.startswith('U') and number<5:
            rx, ry, value_y, just = x+20.32, y-4, y-4, ''
        else:
            rx, ry, value_y, just = x, y-h+2.3, y-h+5.3, ''
        ident = p['uuid'] if number == 1 else s.uid(NAME+ref+str(number))
        obj = [f'(symbol (lib_id {s.q("Colloquy:"+ref.replace("#","_"))}) (at {x} {y} 0) (unit {number}) '
               f'(in_bom {"yes" if p.get("include_bom", True) else "no"}) (on_board yes) (uuid {s.q(ident)}))']
        # Append properties inside the instance, not after it.
        obj[0] = obj[0][:-1]
        obj += [s.prop('Reference', ref, rx, ry, size=1.3, justify=just,
                       hidden=ref.startswith(('TP','#')) or ref=='D1'),
                s.prop('Value', p['value'], rx, value_y, size=1.1, justify=just,
                       hidden=style == 'block' or ref.startswith(('TP','#')) or ref=='D1'),
                s.prop('Footprint', p['footprint'], x, y, hidden=True),
                s.prop('Description', p['description'], x, y, hidden=True)]
        obj.append(f'(instances (project {s.q(NAME)} (path {s.q("/"+ROOT)} '
                   f'(reference {s.q(ref)}) (unit {number})))))')
        sheet.objects.append('\n'.join(obj))
        for pin, px, py, _ in locs:
            assert (ref, pin) not in placed, (ref, pin)
            placed.add((ref, pin))
            if p['pins'][pin] is None:
                sheet.objects.append(f'(no_connect (at {x+px} {y-py}) (uuid {s.q(sheet.key("nc"))}))')


def main():
    OUT.mkdir(exist_ok=True)
    text('TEENSY ADAPTER / CONTINUOUS WIRING', 20, 16, 4, True)
    text('Same circuit and PCB pin numbers | One sheet, no electrical net labels | Review copy 20 Oct 2026', 20, 24, 1.8)
    text('Dots join wires. Crossings without dots do not join. Connector units are parts of the SAME physical socket.', 20, 31, 1.6)
    text('TEENSY 4.1 SOCKETS', 20, 41, 2, True)
    text('MEGA-PATTERN SOCKET / BACKPLANE', 493, 41, 2, True)
    text('01  DIGITAL OUTPUTS  /  Teensy -> 5 V buffers -> backplane', 110, 48, 2, True)
    # Rails stay outside the signal section, with each ground branch explicitly wired.
    ground, vin, ioref, mega = 640.08, 650.24, 660.40, 670.56
    signal_ground = 558.80
    text('GND',signal_ground-1,46,1.1)
    for caption, x in [('GND', ground), ('5 V USB', vin), ('3V3', ioref), ('MEGA 5V', mega)]:
        text(caption, x-1, 46, 1.1)
    jm_digital, jt_digital = [], []
    for index in range(15):
        y = 60.96 + index*12.7
        u = 'U'+str(index//4+1)
        gate = index%4
        oe, inp, out = [('1','2','3'),('4','5','6'),('10','9','8'),('13','12','11')][gate]
        net = parts[u]['pins'][inp]
        jt_pin = next(pin for pin, n in parts['JT1']['pins'].items() if n == net)
        jm_pin = next(pin for pin, n in parts['JM1']['pins'].items() if n == parts[u]['pins'][out])
        jt_digital.append((jt_pin, y))
        jm_digital.append((jm_pin, y))
        unit(u, gate+1, [(inp, 254, y, 0), (out, 284.48, y, 180),
                         (oe, 269.24, y+6.35, 90)], (269.24, y), (10.16, 3.81))
        rd = 'RD'+net.split('/')[1]
        passive(rd, 180.34, y+5.08, True)
        wire((100.33,y),(254,y))
        wire((284.48,y),(579.12,y))
        wire((180.34,y+10.16),(signal_ground,y+10.16))
        wire((269.24,y+6.35),(269.24,y+10.16))
        text(parts[u]['pins'][out].replace('/driven','').replace('/',' / '), 400, y-4.2, 1.6)
        text('GPIO '+net.split('/')[1], 110, y-4.2, 1.3)
    connector('JT1',1,jt_digital,100.33,80.01,'right')
    connector('JM1',1,jm_digital,579.12,599.44,'left')
    # Spare fourth gate of U4: input/OE grounded, output left unused, as original.
    unit('U4',4,[('12',706.12,205.74,0),('11',736.60,205.74,180),('13',721.36,212.09,90)],
         (721.36,205.74),(10.16,3.81))
    wire((ground,215.90),(721.36,215.90),(721.36,212.09))
    wire((706.12,205.74),(698.50,205.74),(698.50,215.90))
    text('Unused buffer gate', 698, 195, 1.3)

    text('02  PHOTOSENSORS  /  backplane -> divider + filter -> Teensy ADC', 110, 255, 2, True)
    sensor_jt = {'JT1':[], 'JT2':[]}
    sensor_jm = []
    for index, adc in enumerate([19,20,21,22,23,24,25,26,27,38,39]):
        y = 274.32 + index*12.7
        ref = 'RA'+str(adc)
        net = 'adc/'+str(adc)
        socket = next(j for j in ('JT1','JT2') if net in parts[j]['pins'].values())
        pin = next(pin for pin,n in parts[socket]['pins'].items() if n == net)
        sensor_jt[socket].append((pin,y))
        sensor_jm.append((next(pin for pin,n in parts['JM1']['pins'].items()
                               if n == parts[ref]['pins']['1']),y))
        passive(ref,430.53,y)
        # RA pin 1 faces the backplane; pin 2 faces the ADC.
        locs, box, style = geometries[ref][1]
        geometries[ref][1] = ([(pin,-px,py,180-angle) for pin,px,py,angle in locs],box,style)
        passive('RB'+str(adc),320.04,y+5.08,True)
        passive('CA'+str(adc),370.84,y+5.08,True)
        wire((100.33,y),(425.45,y))
        wire((435.61,y),(579.12,y))
        wire((320.04,y+10.16),(signal_ground,y+10.16))
        text(parts[ref]['pins']['1'].replace('/',' / '),450,y-4.2,1.3)
        text('ADC '+str(adc),110,y-4.2,1.3)
    connector('JT1',2,sensor_jt['JT1'],100.33,80.01,'right')
    connector('JT2',1,sensor_jt['JT2'],100.33,80.01,'right')
    connector('JM1',2,sensor_jm,579.12,599.44,'left')
    text('03  MICROPHONES  /  direct analog input + 1 nF shunt',110,421,2,True)
    jt_mic, jm_mic = [], []
    for i in range(5):
        y = 441.96 + i*12.7
        ref = 'CM'+str(i+1)
        net = parts[ref]['pins']['1']
        jt_mic.append((next(pin for pin,n in parts['JT2']['pins'].items() if n == net),y))
        jm_mic.append((next(pin for pin,n in parts['JM1']['pins'].items() if n == net),y))
        passive(ref,370.84,y+5.08,True)
        wire((100.33,y),(579.12,y))
        wire((370.84,y+10.16),(signal_ground,y+10.16))
        text(net.replace('/',' / '),478,y-4.2,1.4)
    connector('JT2',2,jt_mic,100.33,80.01,'right')
    connector('JM1',3,jm_mic,579.12,599.44,'left')

    text('04  POWER / SAME SHARED RAILS',695,42,1.8,True)
    jm_power = [(pin,60.96+i*5.08) for i,pin in enumerate(
        ['5V1','5V3','5V4','GND1','GND2','GND3','GND5','GND6'])]
    connector('JM1',4,jm_power,706.12,726.44,'left')
    for pin,y in jm_power:
        wire((mega if parts['JM1']['pins'][pin]=='MEGA_5V' else ground,y),(706.12,y))
    jt1rows = [('1',121.92),('15',127)]
    connector('JT1',3,jt1rows,706.12,726.44,'left')
    for pin,y in jt1rows:
        wire((ground if pin=='1' else ioref,y),(706.12,y))
    jt2rows = [(pin,162.56+i*5.08) for i,pin in enumerate(['1','2','3','15'])]
    connector('JT2',3,jt2rows,782.32,802.64,'left')
    for pin,y in jt2rows:
        wire(({'GND':ground,'VIN_USB':vin,'IOREF':ioref}[parts['JT2']['pins'][pin]],y),(782.32,y))
    # Diode drawn using the original symbol, not a resistor-like replacement.
    unit('D1',1,[('1',mega,238.76,270),('2',mega,248.92,90)],(mega,243.84),(2.54,2.54),'diode')
    wire((mega,60.96),(mega,238.76))
    wire((mega,248.92),(vin,248.92))
    text('D1  1N5819HW',681,252,1.3)
    text('USB supply -> Mega 5 V',681,256,1.2)
    for ref,x,y,rail in [('CV1',713.74,231.14,vin),('CI1',769.62,233.68,ioref),('CI2',812.80,236.22,ioref)]:
        passive(ref,x,y,True)
        top = 220.98 if ref=='CV1' else 218.44
        wire((rail,top),(x,top),(x,y-5.08))
        wire((x,y+5.08),(x,y+10.16),(ground,y+10.16))
    for i in range(1,5):
        x,y=721.36,269.24+(i-1)*22.86
        u='U'+str(i)
        unit(u,5,[('14',x-15.24,y,0),('7',x+15.24,y,180)],(x,y),(10.16,5.08))
        wire((vin,y),(x-15.24,y))
        wire((x+15.24,y),(x+17.78,y),(x+17.78,y+10.16),(ground,y+10.16))
        passive('CB'+str(i),792.48,y+5.08,True)
        wire((vin,y-7.62),(792.48,y-7.62),(792.48,y))
        wire((792.48,y+10.16),(ground,y+10.16))
    for ref,rail,y in [('TPV',vin,363.22),('TPI',ioref,373.38),('TPG',ground,383.54)]:
        unit(ref,1,[('1',706.12,y,0)],(708.66,y),(1.27,1.27),'testpoint')
        wire((rail,y),(706.12,y))
        text(ref+' / '+parts[ref]['value'],716,y-2,1.3)
    unit('#FLG1',1,[('1',ground,60.96,90)],(ground,60.96),(1.27,2.54),'flag')
    unit('#FLG2',1,[('1',vin,50.8,90)],(vin,50.8),(1.27,2.54),'flag')
    wire((ground,60.96),(ground,502.92))
    wire((signal_ground,71.12),(signal_ground,502.92),(ground,502.92))
    wire((vin,50.8),(vin,363.22))
    wire((ioref,127),(ioref,373.38))

    text('05  SPARE GPIO / TEST POINTS',20,517,1.8,True)
    for ref, un in [('JT1',4),('JT2',4)]:
        pins = [(pin,net) for pin,net in parts[ref]['pins'].items()
                if net and net.startswith('gpio/') and 'TP'+net.split('/')[1] in parts]
        x = 40.64 if ref=='JT1' else 238.76
        rows = [(pin,535.94+i*5.08) for i,(pin,_) in enumerate(pins)]
        connector(ref,un,rows,x+20.32,x,'right')
        for i,(pin,net) in enumerate(pins):
            y=rows[i][1]
            tp='TP'+net.split('/')[1]
            unit(tp,1,[('1',x+81.28,y,0)],(x+83.82,y),(1.27,1.27),'testpoint')
            wire((x+20.32,y),(x+81.28,y))
            text(tp+' / '+net,x+87,y-2,1.2)
    text('06  UNUSED SOCKET CONTACTS / X = NO CONNECTION',445,517,1.8,True)
    unused = [pin for pin,n in parts['JM1']['pins'].items() if n is None]
    for k in range(3):
        group=unused[k*18:(k+1)*18]
        if group:
            connector('JM1',5+k,[(pin,533.4+i*2.54) for i,pin in enumerate(group)],
                      480.06+k*93.98,459.74+k*93.98,'right')
    connector('JT2',5,[('14',411.48)],787.4,767.08,'right')
    text('Unused Teensy socket contact',716,401,1.3)
    text('U1-U4: SN74LV4T125PWR | RDx: 100K pulldown | PWR_FLAG symbols retained from original; no physical parts.',20,507,1.5)
    text('No added parts or connections. Plain text captions identify wires; they do not connect them.',20,511,1.5)

    s.sym_geometry = lambda p: geometries[p['ref']]
    # Replace diode and vertical resistor artwork while keeping actual pin definitions.
    original_lib = s.lib_symbol
    def lib(p, external=False):
        raw=original_lib(p,external)
        if p['ref'].startswith('U'):
            # OE enters the lower edge; its pin stops at the body boundary.
            raw=re.sub(r'(\(pin input line \(at 0\.0 -6\.35 90\) \(length )5\.08',r'\g<1>2.54',raw)
        if p['ref']=='D1':
            raw=raw.replace('(circle (center 0 0) (radius 1.016) (stroke (width 0.254) (type default)) (fill (type none)))',
                '(polyline (pts (xy -2.54 -2.54) (xy 2.54 -2.54) (xy 0 2.54) (xy -2.54 -2.54)) (stroke (width 0.254) (type default)) (fill (type none)))\n'
                '(polyline (pts (xy -2.54 3.81) (xy -2.54 2.54) (xy 2.54 2.54) (xy 2.54 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))')
            raw=raw.replace('(length 5.08)','(length 2.54)')
        return raw
    s.lib_symbol=lib
    place_all()
    assert placed == {(p['ref'],pin) for p in parts.values() for pin in p['pins']}
    ends = {pt for seg in segments for pt in seg}
    for (ref, number),(x,y) in positions.items():
        ends.update((round(x+px,4),round(y-py,4))
                    for _,px,py,_ in geometries[ref][number][0])
    def on(pt,a,b):
        return (a[0]==b[0]==pt[0] and min(a[1],b[1])<=pt[1]<=max(a[1],b[1])) or (
            a[1]==b[1]==pt[1] and min(a[0],b[0])<=pt[0]<=max(a[0],b[0]))
    split=set()
    for a,b in segments:
        points=sorted(pt for pt in ends if on(pt,a,b))
        split.update(tuple(sorted((p,q))) for p,q in zip(points,points[1:]))
    degree=Counter(pt for seg in split for pt in seg)
    for a,b in sorted(split):
        sheet.line(a,b)
    for (x,y),n in degree.items():
        if n>=3:
            sheet.objects.append(f'(junction (at {x} {y}) (diameter 0.8) (color 0 0 0 0) (uuid {s.q(sheet.key("junction"))}))')
    sheet.save()
    path=OUT/(NAME+'.kicad_sch')
    raw=path.read_text(encoding='utf-8').replace('(paper "A3")','(paper "A1")')
    raw=raw.replace('(date "2026-10-05") (rev "A-prototype")','(date "2026-10-20") (rev "A wired copy")')
    raw=raw.replace('Prototype: verify harness polarity and sensor values before connection','Reading copy: same circuit; original schematic and PCB retained')
    path.write_text(raw,encoding='utf-8')
    (OUT/'Colloquy.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n'
        +'\n'.join(lib(p,external=True) for p in parts.values())+')\n',encoding='utf-8')
    (OUT/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "Colloquy") (type "KiCad") (uri "${KIPRJMOD}/Colloquy.kicad_sym") (options "") (descr "Continuous wire reading copy")))\n')
    (OUT/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "Shields") (type "KiCad") (uri "${KIPRJMOD}/../../Shields.pretty") (options "") (descr "Existing footprints")))\n')
    if not (OUT/(NAME+'.kicad_pro')).exists():
        (OUT/(NAME+'.kicad_pro')).write_text('{}\n')
    print(path)


if __name__=='__main__':
    main()
