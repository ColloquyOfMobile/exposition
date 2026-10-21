"""Generate a second, continuously wired reading copy, preserving the circuit.

Run with KiCad's Python. Connector contacts are logical units, not new sockets.
"""
from collections import Counter, defaultdict
import copy
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'scripts'))
import schematic_support as s

NAME = 'backplane-wired'
OUT = HERE / 'wired'
ROOT = s.uid('sheetfile/' + NAME)
parts = {p['ref']: copy.deepcopy(p) for p in json.loads((HERE/'circuit.json').read_text())['components']}
parts['#FLG1'] = dict(ref='#FLG1', value='PWR_FLAG', footprint='',
    description='Original GND supply declaration; no physical component',
    pins={'1': 'GND'}, pin_names={'1': '~'}, pin_types={'1': 'power_out'},
    uuid=s.uid(NAME+'flag'), include_bom=False)
for p in parts.values():
    p['sheet_path'] = '/' + ROOT
s.HERE, s.PROJECT = OUT, NAME
sheet = s.Sheet(NAME, 'Backplane / continuous wiring / reading copy', parts, 1)
geometries, positions, used, segments = {}, {}, set(), []
rail_x = {net: x*2.54 for net,x in zip(
    ['GND','AGND','+5V','MEGA_5V','+12V','dxl_data','analyser/strobe','analyser/reset','amp shutdown'],
    range(310,337,3))}
rail_taps = defaultdict(list)
sections = []


def snap(value):
    return round(round(value/1.27)*1.27,4)


def text(value,x,y,size=1.5,bold=False):
    sheet.text(value,x/2,y,size*1.3,bold)


def wire(*points):
    for a,b in zip(points,points[1:]):
        a,b = (snap(a[0]/2),snap(a[1])),(snap(b[0]/2),snap(b[1]))
        assert a[0]==b[0] or a[1]==b[1],(a,b)
        if a!=b:
            segments.append((a,b))


def unit(ref,locs,center,box,style='block'):
    number = len(geometries.setdefault(ref,{}))+1
    x,y = snap(center[0]/2),snap(center[1])
    geometries[ref][number] = ([(pin,round(snap(px/2)-x,4),round(y-snap(py),4),angle)
        for pin,px,py,angle in locs],(box[0]/2,box[1]),style)
    positions[ref,number] = (x,y)
    for pin,*_ in locs:
        assert (ref,pin) not in used,(ref,pin)
        used.add((ref,pin))
    return number


def contact(ref,pin,x,y,side='left'):
    # Single-contact units keep connector identities legible near each wire.
    delta = -20.32 if side=='left' else 20.32
    parts[ref]['pin_names'][pin] = '~'
    unit(ref,[(pin,x,y,180 if side=='left' else 0)],(x+delta,y),(15.24,3.81))
    text(ref,x+delta-12,y-2,1.4,True)
    return x,y


def pin_for(ref,net):
    return next(pin for pin,n in parts[ref]['pins'].items() if n==net and (ref,pin) not in used)


def terminal(ref,net,x,y,side='left'):
    return contact(ref,pin_for(ref,net),x,y,side)


def passive(ref,x,y,vertical=False):
    style = 'capacitor' if ref.startswith('C') else 'resistor'
    locs = [('1',x,y-5.08,270),('2',x,y+5.08,90)] if vertical else [
        ('1',x-5.08,y,0),('2',x+5.08,y,180)]
    unit(ref,locs,(x,y),(2.54,2.54) if style=='capacitor' else (
        (1.016,2.54) if vertical else (2.54,1.016)),style)
    text(ref+'  '+parts[ref]['value'],x+5 if vertical else x-18,y-2 if vertical else y-8,1.25)
    return {pin:(px,py) for pin,px,py,_ in locs}


def rail(net,point):
    x=rail_x[net]
    wire(point,(x,point[1]))
    rail_taps[net].append(point[1])


def probe(ref,x,y):
    unit(ref,[('1',x,y,90)],(x,y-2.54),(1.27,1.27),'testpoint')
    text(ref,x+3,y-5,1.15)


def shunt(ref,x,y,net):
    p=passive(ref,x,y+5.08,True)
    assert parts[ref]['pins']['2']==net
    rail(net,p['2'])


def main():
    OUT.mkdir(exist_ok=True)
    text('BACKPLANE / CONTINUOUS-WIRE SCHEMATIC',20,15,4,True)
    text('137 original components | Actual pin numbers | No electrical net labels | 20 Oct 2026',20,25,1.8)
    text('Dots join wires. Crossings without dots do not join. Blue captions are plain text only.',20,33,1.7)
    text('Repeated connector references are contacts of the SAME physical connector. This is a logical wiring drawing.',20,40,1.7)
    text('A1 = Mega-pattern controller socket | JA1 = analyser socket | JV1-JV5 = voice sockets | J5/J1/A-J3/B-J4 = harness',20,47,1.6)
    for net,x in rail_x.items():
        # Stagger rail headings to avoid horizontal caption collisions.
        text(net,x-2,55+list(rail_x).index(net)*5,1.2,True)

    channels=['female1','female2','female3','male1','male2']
    audio_res=[303,403,503,103,203]
    top=110
    for i,ch in enumerate(channels,1):
        text(f'{i:02d}  {ch.upper()} / SIGNAL PATHS',20,top-10,2.6,True)
        text('CONTROLLER / SOURCE',20,top,1.5,True)
        text('EXISTING CONDITIONING / TEST PADS',230,top,1.5,True)
        text('CARD / HARNESS CONTACT',640,top,1.5,True)
        y=top+20
        # Tone with the original LED and current-limiting resistor branch.
        net=ch+'/tone'
        wire(terminal('A1',net,75,y),terminal('JV'+str(i),net,700,y,'right'))
        text('TONE',90,y-7,1.5)
        probe('TPV'+str(i),180,y)
        r=passive('RLT'+str(i),350,y+15.24)
        wire((250,y),(250,y+15.24),r['1'])
        # Use proper diode/LED artwork, with cathode pin 1 and anode pin 2.
        led='DT'+str(i)
        unit(led,[('2',430,y+15.24,0),('1',440.16,y+15.24,180)],(435.08,y+15.24),(2.54,2.54),'led')
        wire(r['2'],(430,y+15.24))
        rail('GND',(440.16,y+15.24))
        text(led+' YELLOW',450,y+9,1.2)
        y+=40.64
        # Voice filter output, series resistor, load and audio return.
        net=ch+'/filter out'
        wire(terminal('JV'+str(i),net,75,y),(344.92,y))
        r=passive('R'+str(audio_res[i-1]),350,y)
        out=ch+'/line out'
        harness=next(p['ref'] for p in parts.values() if p['ref'] in ['J5','J1','A-J3','B-J4'] and out in p['pins'].values())
        wire(r['2'],terminal(harness,out,700,y,'right'))
        text('FILTER OUT  ->  LINE OUT',90,y-7,1.5)
        probe('TP'+str([3,4,5,1,2][i-1]),180,y)
        probe('TPL'+str(i),240,y)
        shunt('RL'+str(i),300,y,'AGND')
        y+=25.4
        net=ch+'/audio return'
        wire(terminal(next(p['ref'] for p in parts.values() if p['ref'] in ['J5','J1','A-J3','B-J4'] and net in p['pins'].values()),net,75,y),(344.92,y))
        r=passive('JP'+str([4,5,6,2,3][i-1]),350,y)
        rail('AGND',r['2'])
        text('AUDIO RETURN',90,y-7,1.5)
        y+=25.4
        # Raw microphone, analyser branch, and direct-controller input.
        net=ch+'/microphone'
        harness=next(p['ref'] for p in parts.values() if p['ref'] in ['J5','J1','A-J3','B-J4'] and net in p['pins'].values())
        wire(terminal(harness,net,75,y),(344.92,y))
        r=passive('RM'+str(i),350,y)
        wire(r['2'],terminal('A1',ch+'/mic direct',700,y,'right'))
        wire((150,y),(150,y+15.24),terminal('JA1',net,200,y+15.24,'right'))
        probe('TPM'+str(i),250,y)
        probe('TPD'+str(i),450,y)
        shunt('RMD'+str(i),530,y,'AGND')
        text('MICROPHONE  ->  4K7  ->  DIRECT INPUT',90,y-7,1.5)
        y+=40.64
        net=ch+'/analyser out'
        wire(terminal('JA1',net,75,y),terminal('A1',net,700,y,'right'))
        probe('TPA'+str(i),450,y)
        text('ANALYSER OUTPUT',90,y-7,1.5)
        y+=25.4
        # NeoPixel data and the two male bar / auxiliary data lines.
        targets=[(ch+'/neopixel',i,'RN','RND')]
        if i>=4:
            targets += [(ch+'/bar neopixel',i+2,'RN','RND'),(ch+'/aux',i-3,'RA',None)]
        for net,num,series,pull in targets:
            driven=net+('/driven' if '/aux' not in net else ' driven')
            wire(terminal('A1',driven,75,y),(344.92,y))
            r=passive(series+str(num),350,y)
            harness=next(p['ref'] for p in parts.values() if p['ref'] in ['J5','J1','A-J3','B-J4'] and net in p['pins'].values())
            wire(r['2'],terminal(harness,net,700,y,'right'))
            if pull:
                shunt(pull+str(num),280,y,'GND')
            text(net.split('/',1)[1].upper(),90,y-7,1.5)
            y+=25.4
        sensors=[ch+'/photosensor'] if i<=3 else [ch+'/photosensor/'+a for a in 'ABCD']
        for k,net in enumerate(sensors):
            ref=next(p['ref'] for p in parts.values() if p['ref'].startswith('RP') and net in p['pins'].values())
            harness=next(p['ref'] for p in parts.values() if p['ref'] in ['J5','J1','A-J3','B-J4'] and net in p['pins'].values())
            wire(terminal(harness,net,75,y),terminal('A1',net,700,y,'right'))
            shunt(ref,350,y,'AGND')
            text('PHOTOSENSOR'+(' '+net[-1] if i>=4 else '')+' / 10K PROVISIONAL',90,y-7,1.5)
            y+=25.4
        sections.append((ch,top-10,y+5))
        top=y+30

    # All remaining connected contacts use short explicit branches to shared rails,
    # or direct two-terminal wires for the spare harness contacts.
    top+=10
    sections.append(('Power, control and spare contacts',top-10,top+650))
    text('06  POWER / SHARED CONTROL / SPARES',20,top-10,2.6,True)
    y=top+12
    # Remaining two-pin parts: power capacitors, ground bridge and shutdown pullup.
    for ref in ['C1','C2','JP1','RS1','RLP5','RLP12','RLPUSB']:
        p=passive(ref,350,y)
        for pin,point in p.items():
            net=parts[ref]['pins'][pin]
            if net.startswith('led/'):
                led={'RLP5':'DP5','RLP12':'DP12','RLPUSB':'DPUSB'}[ref]
                unit(led,[('2',430,y,0),('1',440.16,y,180)],(435.08,y),(2.54,2.54),'led')
                wire(point,(430,y))
                rail('GND',(440.16,y))
                text(led+' GREEN',450,y-7,1.3)
            else:
                # Put the left lead on a distinct row so parallel rails never overlap.
                if pin=='1':
                    wire(point,(320,y),(320,y-10.16))
                    rail(net,(320,y-10.16))
                else:
                    rail(net,point)
        y+=30.48
    for ref in ['TP20','TP21','TP30','TP31','TP32','TP33','TP34','TPUSB','TPVG','TPEG']:
        net=parts[ref]['pins']['1']
        probe(ref,350,y)
        rail(net,(350,y))
        text(net,90,y-3,1.5)
        y+=15.24
    # Group supply contacts along short horizontal branches, under each wire.
    remaining=[(p['ref'],pin,net) for p in parts.values() for pin,net in p['pins'].items()
               if (p['ref'],pin) not in used and net in rail_x and not p['ref'].startswith('#')]
    y+=20
    for net in rail_x:
        contacts=[(ref,pin) for ref,pin,n in remaining if n==net]
        for start in range(0,len(contacts),10):
            group=contacts[start:start+10]
            text(net,20,y-7,1.5,True)
            rail(net,(65,y))
            for k,(ref,pin) in enumerate(group):
                x=65+k*68.58
                parts[ref]['pin_names'][pin]='~'
                unit(ref,[(pin,x,y+5.08,270)],(x,y+10.16),(27.94,5.08))
                text(ref,x-24,y+9,1.3,True)
                wire((x,y),(x,y+5.08))
            y+=30.48
    # Spare signal pairs, deliberately not tied into power or other spares.
    y+=20
    extras=defaultdict(list)
    for p in parts.values():
        for pin,net in p['pins'].items():
            if (p['ref'],pin) not in used and net and net not in rail_x:
                extras[net].append((p['ref'],pin))
    for net,pins in extras.items():
        assert len(pins)==2,(net,pins)
        wire(contact(*pins[0],75,y),contact(*pins[1],700,y,'right'))
        text(net,230,y-6,1.4)
        y+=15.24
    # Original ERC declaration, wired into the actual GND rail.
    unit('#FLG1',[('1',rail_x['GND'],100,90)],(rail_x['GND'],100),(1.27,2.54),'flag')
    rail_taps['GND'].append(100)
    y+=20
    text('07  UNUSED CONTACTS / MECHANICAL ITEMS',20,y,2.4,True)
    unused=[(p['ref'],pin) for p in parts.values() for pin,net in p['pins'].items() if net is None]
    for k,(ref,pin) in enumerate(unused):
        col,row=divmod(k,12)
        contact(ref,pin,75+col*110,y+20+row*12.7)
    for k,p in enumerate(p for p in parts.values() if not p['pins']):
        xx=60+(k%6)*125
        yy=y+200+(k//6)*35
        unit(p['ref'],[],(xx,yy),(45,10),'block')
        text(p['ref']+' / '+p['value'],xx-40,yy-3,1.4)
    bottom=y+300
    sections[-1]=(sections[-1][0],top-10,bottom)
    for net,x in rail_x.items():
        taps=rail_taps[net]
        wire((x,min(taps)),(x,max(taps)))
        text(net,x-2,bottom-10-list(rail_x).index(net)*5,1.2,True)

    s.sym_geometry=lambda p:geometries[p['ref']]
    original_lib=s.lib_symbol
    def lib(p,external=False):
        raw=original_lib(p,external)
        # Horizontal dimensions are compacted; vertical lengths remain unchanged.
        raw=re.sub(r'(\(pin \w+ line \(at [^()]+ (?:0|180)\) \(length )5\.08',r'\g<1>2.54',raw)
        if p['ref'].startswith(('R','JP')):
            raw=re.sub(r'(\(pin \w+ line \(at [^()]+ (?:0|180)\) \(length )2\.54',r'\g<1>1.27',raw)
        if p['ref'].startswith(('DT','DP')):
            circle='(circle (center 0 0) (radius 1.016) (stroke (width 0.254) (type default)) (fill (type none)))'
            artwork='(polyline (pts (xy -2.54 -2.54) (xy -2.54 2.54) (xy 2.54 0) (xy -2.54 -2.54)) (stroke (width 0.254) (type default)) (fill (type none)))\n(polyline (pts (xy 2.54 -2.54) (xy 2.54 2.54)) (stroke (width 0.254) (type default)) (fill (type none)))\n'
            for dx in [0,3]:
                artwork+=f'(polyline (pts (xy {dx} 3.5) (xy {dx+3} 6.5) (xy {dx+1.5} 6.2) (xy {dx+3} 6.5) (xy {dx+2.7} 5)) (stroke (width 0.254) (type default)) (fill (type none)))\n'
            raw=raw.replace(circle,artwork).replace('(length 5.08)','(length 2.54)')
        return raw
    s.lib_symbol=lib
    for (ref,number),(x,y) in positions.items():
        p=parts[ref]
        name=re.sub(r'[^A-Za-z0-9_]','_',ref)
        locs,box,style=geometries[ref][number]
        ident=p['uuid'] if number==1 else s.uid(NAME+ref+str(number))
        sheet.objects.append(f'(symbol (lib_id {s.q("Colloquy:"+name)}) (at {x} {y} 0) (unit {number}) '
            f'(in_bom {"yes" if p.get("include_bom",True) else "no"}) (on_board yes) (uuid {s.q(ident)})'
            +s.prop('Reference',ref,x,y,hidden=True)+s.prop('Value',p['value'],x,y,hidden=True)
            +s.prop('Footprint',p['footprint'],x,y,hidden=True)
            +f'(instances (project {s.q(NAME)} (path {s.q("/"+ROOT)} (reference {s.q(ref)}) (unit {number})))))')
        for pin,px,py,_ in locs:
            if p['pins'][pin] is None:
                sheet.objects.append(f'(no_connect (at {x+px} {y-py}) (uuid {s.q(sheet.key("nc"))}))')
    assert used=={(p['ref'],pin) for p in parts.values() for pin in p['pins']}
    ends={point for seg in segments for point in seg}
    pin_positions=set()
    for (ref,number),(x,y) in positions.items():
        pin_positions.update((round(x+px,4),round(y-py,4)) for _,px,py,_ in geometries[ref][number][0])
    ends.update(pin_positions)
    def on(pt,a,b):
        return (a[0]==b[0]==pt[0] and min(a[1],b[1])<=pt[1]<=max(a[1],b[1])) or (a[1]==b[1]==pt[1] and min(a[0],b[0])<=pt[0]<=max(a[0],b[0]))
    split=set()
    for a,b in segments:
        pts=sorted(pt for pt in ends if on(pt,a,b))
        split.update(tuple(sorted((p,q))) for p,q in zip(pts,pts[1:]))
    # A shared net used on just one row needs no dangling rail extension.
    while True:
        degrees=Counter(pt for seg in split for pt in seg)
        trimmed={seg for seg in split if any(degrees[p]==1 and p not in pin_positions for p in seg)}
        if not trimmed:
            break
        split-=trimmed
    for a,b in sorted(split):
        sheet.line(a,b)
    for (x,y),degree in Counter(pt for seg in split for pt in seg).items():
        if degree>=3:
            sheet.objects.append(f'(junction (at {x} {y}) (diameter 0.8) (color 0 0 0 0) (uuid {s.q(sheet.key("junction"))}))')
    sheet.save()
    path=OUT/(NAME+'.kicad_sch')
    raw=path.read_text(encoding='utf-8').replace('(paper "A3")',f'(paper "User" 460 {bottom+30})')
    raw=raw.replace('2026-10-05','2026-10-20').replace('A-prototype','A wired copy').replace('Prototype: verify harness polarity and sensor values before connection','Reading copy: original components and connections preserved')
    path.write_text(raw,encoding='utf-8')
    (OUT/'Colloquy.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n'+'\n'.join(lib(p,True) for p in parts.values())+')\n',encoding='utf-8')
    (OUT/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "Colloquy") (type "KiCad") (uri "${KIPRJMOD}/Colloquy.kicad_sym") (options "") (descr "Wired reading copy")))\n')
    (OUT/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "Shields") (type "KiCad") (uri "${KIPRJMOD}/../../Shields.pretty") (options "") (descr "Existing footprints")))\n')
    (OUT/(NAME+'.kicad_pro')).write_text('{}\n')
    (OUT/'sections.json').write_text(json.dumps(sections,indent=2)+'\n')
    print(path)


if __name__=='__main__':
    main()
