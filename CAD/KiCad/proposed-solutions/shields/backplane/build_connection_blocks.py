"""PCB-oriented reading schematic; stock D-subs and no test points."""
from collections import defaultdict
import copy
import json
import math
from pathlib import Path
import re
import sys

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/'scripts'))
import schematic_support as s
from wired_routing import Router

OUT,NAME,G=HERE/'wired','backplane-wired',2.54
ROOT=s.uid('sheetfile/'+NAME)
original=json.loads((HERE/'circuit.json').read_text())['components']
parts={p['ref']:copy.deepcopy(p) for p in original if not p['ref'].startswith('TP')}
parts['#FLG1']=dict(ref='#FLG1',value='PWR_FLAG',footprint='',description='Original GND declaration',
    pins={'1':'GND'},pin_names={'1':'~'},pin_types={'1':'power_out'},uuid=s.uid(NAME+'flag'),include_bom=False)
for p in parts.values():p['sheet_path']='/'+ROOT
s.HERE,s.PROJECT=OUT,NAME
sheet=s.Sheet(NAME,'Backplane / PCB-oriented connection blocks',parts,1)
geometry,placements,pin_locations,obstacles={},{},{},set()
obstacle_boxes=[]
native={}
sections=[]
text_boxes=[]
deferred_captions=[]
WIDTH,HEIGHT=288,440


def text(value,x,y,size=2,bold=False,angle=0):
    font=f'(font (size {size} {size}) {"(bold yes)" if bold else ""})'
    sheet.objects.append(f'(text {s.q(value)} (at {x*G:.4f} {y*G:.4f} {angle}) '
        f'(effects {font} (justify left top)) (uuid {s.q(sheet.key("text"))}))')
    width,height=len(value)*size*.9/G,size/G
    text_boxes.append((x,y-width,x+height,y) if angle==90 else (x,y,x+width,y+height))


def blocked(x0,y0,x1,y1):
    obstacle_boxes.append((x0,y0,x1,y1))
    for x in range(math.ceil(x0),math.floor(x1)+1):
        for y in range(math.ceil(y0),math.floor(y1)+1):obstacles.add((x,y))


def frame(title,x0,y0,x1,y1):
    sections.append(dict(title=title,bounds_mm=[x0*G,y0*G,x1*G,y1*G]))
    pts=' '.join(f'(xy {x*G:.4f} {y*G:.4f})' for x,y in [(x0,y0),(x1,y0),(x1,y1),(x0,y1),(x0,y0)])
    sheet.objects.append(f'(polyline (pts {pts}) (stroke (width .3) (type dash)) (fill (type none)) (uuid {s.q(sheet.key("frame"))}))')
    text(title,x0+2,y0+2,2.8,True);blocked(x0+1,y0+1,x1-1,y0+5)


def short(net):
    if not net:return '~'
    for prefix,a in [('female1','FEMALE 1'),('female2','FEMALE 2'),('female3','FEMALE 3'),('male1','MALE 1'),('male2','MALE 2')]:net=net.replace(prefix,a)
    return net.replace('/',' / ').replace('neopixel','NEOPIXEL DATA').replace('mic direct','MIC DIRECT').replace('photosensor','LIGHT SENSOR').replace('analyser out','ANALYSER OUT').replace('filter out','FILTER OUT').replace('line out','LINE OUT').replace('tone','TONE').replace('microphone','MIC').replace('driven','DRIVEN').replace('dxl_data','DYNAMIXEL DATA').upper()


def unit(ref,center,pins,box,style='block'):
    x,y=center
    assert ref not in placements,ref
    placements[ref]=(x,y,0)
    geometry[ref]={1:([(pin,(px-x)*G,(y-py)*G,a) for pin,px,py,a in pins],(box[0]*G,box[1]*G),style)}
    blocked(x-box[0],y-box[1],x+box[0],y+box[1])
    if style=='hole':text(ref,x+2,y-1,1.35)
    for pin,px,py,a in pins:
        assert px==round(px) and py==round(py),(ref,pin,px,py)
        pin_locations[ref,pin]=((int(px),int(py)),a)


def header(ref,center,pin_order=None,caption=None):
    x,y=center;pins=list(parts[ref]['pins']) if pin_order is None else pin_order
    h=(len(pins)-1)*2+3
    rows=[(pin,x-12,y+(i-(len(pins)-1)/2)*4,0) for i,pin in enumerate(pins)]
    unit(ref,center,rows,(10,h));text(caption or ref,x-10,y-h-5,1.8,True)
    for pin in pins:parts[ref]['pin_names'][pin]=short(parts[ref]['pins'][pin])


def passive(ref,x,y,vertical=False):
    pins=[('1',x,y-2,270),('2',x,y+2,90)] if vertical else [('1',x-2,y,0),('2',x+2,y,180)]
    unit(ref,(x,y),pins,(1,1) if vertical else (1,.4),'capacitor' if ref.startswith('C') else 'resistor')
    deferred_captions.append((ref+' '+parts[ref]['value'],x+2 if vertical else x-4,y-1 if vertical else y-4,1.75))


def led(ref,x,y,vertical=False):
    pins=[('2',x,y-2,270),('1',x,y+2,90)] if vertical else [('2',x-2,y,0),('1',x+2,y,180)]
    unit(ref,(x,y),pins,(1,1),'led');deferred_captions.append((ref,x+2,y-2,1.7))


def raw_symbol(library,name):
    data=Path('C:/Program Files/KiCad/9.0/share/kicad/symbols',library+'.kicad_sym').read_text(encoding='utf-8')
    start=data.index('(symbol "'+name+'"');depth=0;quoted=escaped=False
    for end in range(start,len(data)):
        ch=data[end]
        if escaped:escaped=False
        elif ch=='\\' and quoted:escaped=True
        elif ch=='"':quoted=not quoted
        elif not quoted:
            depth+=(ch=='(')-(ch==')')
            if depth==0:return data[start:end+1]
    raise ValueError(name)


def dsub(ref,x,y,angle):
    name='DA15_Pins_MountingHoles';raw=raw_symbol('Connector',name)
    native[ref]=raw.replace('(symbol "'+name+'"','(symbol "Connector:'+name+'"',1)
    placements[ref]=(x,y,angle);theta=math.radians(angle)
    for sub in s.children(s.parse(raw),'symbol'):
        for pin in s.children(sub,'pin'):
            at=s.children(pin,'at')[0];px,py=float(at[1])/G,float(at[2])/G
            gx=round(x+px*math.cos(theta)-py*math.sin(theta));gy=round(y-px*math.sin(theta)-py*math.cos(theta))
            pin_locations[ref,s.one(pin,'number')]=((gx,gy),(int(at[3])+angle)%360)
    if angle in (0,180):
        blocked(x-2,y-8,x+2,y+8);text(ref+' / DSUB-15',x-6,y-14,2,True)
    else:
        blocked(x-8,y-2,x+8,y+2);text(ref+' / DSUB-15',x-10,y+7,2,True)


def layout():
    text('BACKPLANE / CONNECTION BLOCKS',12,8,5,True)
    text('PCB-oriented top view | Continuous wires | Test points omitted | 21 Oct 2026',12,13,2)
    frame('U2D2 / DYNAMIXEL',12,22,78,78)
    unit('M1',(38,46),[],(12,10));text('M1 / U2D2',28,39,2,True)
    text('USB to host computer',27,44,1.6);text('Mount: no PCB signal pads',27,49,1.5)
    header('J7',(66,62),['3','2','1'],'J7 / SERVO BUS')
    frame('ARDUINO MEGA / TEENSY ADAPTER',89,20,185,104)
    p=parts['A1'];inputs=[pin for pin,n in p['pins'].items() if n and (pin.startswith('A') or '/mic direct' in n)]
    outputs=[pin for pin,n in p['pins'].items() if n and pin not in inputs and not pin.startswith(('GND','5V'))]
    power=[pin for pin,n in p['pins'].items() if n in ('GND','MEGA_5V')];unused=[pin for pin,n in p['pins'].items() if n is None]
    pins=[]
    for group,x,angle in [(inputs,101,0),(outputs,173,180)]:pins.extend((pin,x,61+2*i-(len(group)-1),angle) for i,pin in enumerate(group))
    pins.extend((pin,137+2*i-(len(power)-1),99,90) for i,pin in enumerate(power))
    pins.extend((pin,137+i-len(unused)//2,25,270) for i,pin in enumerate(unused))
    unit('A1',(137,61),pins,(32,34))
    for pin in p['pins']:p['pin_names'][pin]=short(p['pins'][pin]) if pin not in power else '~'
    text('A1 / MEGA-PATTERN SOCKET',109,88,1.8,True);text('Alternative: Teensy on adapter',110,92,1.7)
    text('UNUSED CONTACTS / NC',112,31,1.6);text('GND + MEGA_5V contacts',116,96,1.3)
    frame('POWER ENTRY / SUPPLIES',220,22,270,142)
    header('J2',(248,40),['1','2'],'J2 / 5 V INPUT');header('J6',(248,67),caption='J6 / SCREW BRIDGE')
    passive('C1',233,91,True);passive('C2',254,91,True);passive('JP1',244,106);text('AGND / GND bond',230,111,1.5)
    for ref,d,x in [('RLP5','DP5',230),('RLP12','DP12',245),('RLPUSB','DPUSB',260)]:passive(ref,x,122,True);led(d,x,134,True)
    frame('LIGHT SENSOR LOADS',90,113,178,157)
    for i in range(11):passive('RP'+str(i+1),100+(i%6)*13,126+(i//6)*19,True)
    frame('LED DATA / AUX OUTPUTS',182,113,218,226)
    passive('RS1',198,127);text('AMP SHUTDOWN PULLUP',184,132,1.3)
    for i in range(1,8):
        y=143+(i-1)*10;passive('RN'+str(i),193,y);passive('RND'+str(i),208,y+2,True)
    passive('RA1',193,215);passive('RA2',208,221)
    frame('VOICES / FIVE CARD SOCKETS',48,229,223,303)
    for i,ch in enumerate(['FEMALE 1','FEMALE 2','FEMALE 3','MALE 1','MALE 2'],1):
        x=66+(i-1)*34;text(ch,x-12,237,2,True);ref='JV'+str(i)
        pins=[('1',x-14,252,0),('2',x-14,258,0),('3',x+14,252,180),('4',x+14,258,180),('5',x,241,270)]
        unit(ref,(x,251),pins,(12,8));parts[ref]['pin_names'].update({'1':'TONE','2':'GND','3':'AUDIO OUT','4':'AGND','5':'+5V'})
        text(ref,x-4,246,1.7,True);passive('RLT'+str(i),x-6,270);led('DT'+str(i),x+6,270)
        passive('RL'+str(i),x-7,283,True);passive('R'+str([303,403,503,103,203][i-1]),x+5,282)
        passive('JP'+str([4,5,6,2,3][i-1]),x+5,296);unit('HV'+str(i),(x-7,297),[],(1,1),'hole')
    frame('AUDIO ANALYSERS / FIVE CHANNELS',76,306,196,366)
    ref='JA1';order=['1','2','11','3','4','12','5','6','13','7','8','14','9','10','15','16','17','18','19','20','21']
    unit(ref,(120,335),[(pin,159,316+2*i,180) for i,pin in enumerate(order)],(35,24))
    for pin in order:parts[ref]['pin_names'][pin]=short(parts[ref]['pins'][pin])
    text('JA1',91,320,2.3,True);text('DFR0126 ANALYSER CARRIER',90,328,2,True)
    text('5 microphones -> 5 analogue outputs',89,335,1.7);text('Shared RESET / STROBE',89,341,1.7)
    text('MEGA_5V supply / AGND returns',89,347,1.7)
    unit('HA1',(184,320),[],(1,1),'hole');unit('HA2',(184,354),[],(1,1),'hole')
    frame('DIRECT MICROPHONE INPUTS',48,370,230,398)
    for i in range(1,6):
        x=66+(i-1)*34;text(['FEMALE 1','FEMALE 2','FEMALE 3','MALE 1','MALE 2'][i-1],x-9,376,1.5,True)
        passive('RM'+str(i),x,383);passive('RMD'+str(i),x+7,393,True)
    dsub('J1',19,326,180);text('FEMALE 2 HARNESS',11,309,1.6,True)
    dsub('J5',261,326,0);text('FEMALE 1 HARNESS',243,309,1.6,True)
    dsub('A-J3',86,420,270);text('FEMALE 3 / MALE 1 HARNESS',70,431,1.6,True)
    dsub('B-J4',199,420,270);text('MALE 1 / MALE 2 / BAR HARNESS',183,431,1.6,True)
    header('Extra1',(37,277),caption='EXTRA1 / F2 SPARES');header('Extra2',(250,277),caption='EXTRA2 / F1 SPARES')
    header('Extra3',(247,405),caption='CENTRE SPARE')
    unit('#FLG1',(8,24),[('1',8,24,90)],(0,0),'flag')
    # Plain-text pin/function keys use the clear centre of the PCB layout.
    # They label the stock D-sub symbols without changing their artwork.
    for ref,x,y,title in [('J1',98,162,'J1 / FEMALE 2'),('J5',137,162,'J5 / FEMALE 1'),
                          ('A-J3',98,195,'A-J3 / FEMALE 3 + MALE 1'),
                          ('B-J4',137,195,'B-J4 / MALES + BAR')]:
        frame(title,x,y,x+36,y+30)
        blocked(x,y,x+36,y+30)
        for index,pin in enumerate(['0']+[str(i) for i in range(1,16)]):
            text(f'{pin:>2}  '+short(parts[ref]['pins'][pin]),x+1,y+5+index*1.5,1.75)


def reuse_wires(router,owner):
    """Reuse only when every symbol and actual pin endpoint still matches."""
    root=s.parse((OUT/(NAME+'.kicad_sch')).read_text(encoding='utf-8'))
    libraries={node[1]:node for node in s.children(s.children(root,'lib_symbols')[0],'symbol')}
    actual={};positions={}
    for obj in s.children(root,'symbol'):
        ref=next(prop[2] for prop in s.children(obj,'property') if prop[1]=='Reference')
        at=s.children(obj,'at')[0];x,y,a=map(float,at[1:]);theta=math.radians(a)
        positions[ref]=(round(x/G),round(y/G),round(a))
        for sub in s.children(libraries[s.one(obj,'lib_id')],'symbol'):
            for pin in s.children(sub,'pin'):
                loc=s.children(pin,'at')[0];px,py=float(loc[1])/G,float(loc[2])/G
                actual[ref,s.one(pin,'number')]=(round(x/G+px*math.cos(theta)-py*math.sin(theta)),round(y/G-px*math.sin(theta)-py*math.cos(theta)))
    assert positions==placements,'Symbol placement changed: reroute wires'
    assert actual=={key:point for key,(point,_) in pin_locations.items()},'Pin layout changed: reroute wires'
    lines=[];parent={}
    def find(p):
        parent.setdefault(p,p)
        if parent[p]!=p:parent[p]=find(parent[p])
        return parent[p]
    for obj in s.children(root,'wire'):
        points=s.children(s.children(obj,'pts')[0],'xy')
        a,b=[tuple(round(float(v)/G) for v in point[1:]) for point in points]
        parent[find(a)]=find(b);lines.append((a,b))
    groups={}
    for point,net in owner.items():
        key=find(point)
        assert key not in groups or groups[key]==net,'Existing wires short two nets'
        groups[key]=net
    for a,b in lines:
        net=groups[find(a)]
        router.line(net,a,b)
    assert not((set(router.nodes)&router.obstacles)-set(owner)),'Symbol boundary changed: reroute wires'


def place_captions(segments):
    """Keep part references between wire lanes instead of printing over wires."""
    lines=[line for group in segments.values() for line in group]
    failures=[]
    def overlap(a,b):return a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]
    for value,x,y,size in deferred_captions:
        width=len(value)*size*.9/G+.5
        height=size/G+.05
        offsets=sorted(((dx,dy) for dy in [0,-1,1,-2,2,-3,3,-4,4,-6,6,-8,8,-10,10,-12,12]
                    for dx in [0,1,-1,2,-2,4,-4,6,-6,8,-8,10,-10,12,-12]),key=lambda p:1.5*abs(p[0])+abs(p[1]))
        candidates=[(x+dx,y+dy+.2,0) for dx,dy in offsets]
        if value.startswith('RLP5 '):
            candidates=[(230+dx,122+dy,90) for dy in [8,9,10,7,6,11,12,-3,-4]
                        for dx in [1.2,2.2,-1.8,3.2,-2.8]]
        for px,py,angle in candidates:
            box=(px-.05,py-width,px+height,py+.05) if angle==90 else (px-.1,py-.05,px+width,py+height)
            if any(overlap(box,b) for b in text_boxes):continue
            if any(overlap(box,b) for b in obstacle_boxes):continue
            if any((ix,iy) in obstacles for ix in range(math.ceil(box[0]),math.floor(box[2])+1)
                   for iy in range(math.ceil(box[1]),math.floor(box[3])+1)):continue
            crossed=False
            for a,b in lines:
                if a[0]==b[0] and box[0]<=a[0]<=box[2] and max(a[1],b[1])>=box[1] and min(a[1],b[1])<=box[3]:crossed=True;break
                if a[1]==b[1] and box[1]<=a[1]<=box[3] and max(a[0],b[0])>=box[0] and min(a[0],b[0])<=box[2]:crossed=True;break
            if crossed:continue
            text(value,px,py,size,angle=angle)
            break
        else:
            failures.append(value);text(value,x,y+.2,size)
    assert not failures,('Part captions need manual placement',failures)


def main():
    OUT.mkdir(exist_ok=True);layout()
    assert set(placements)==set(parts),set(parts)-set(placements)
    assert set(pin_locations)=={(ref,pin) for ref,p in parts.items() for pin in p['pins']}
    owner={};endpoints=defaultdict(list)
    for (ref,pin),(point,angle) in pin_locations.items():
        net=parts[ref]['pins'][pin]
        if net is None:
            obstacles.add(point);sheet.objects.append(f'(no_connect (at {point[0]*G:.4f} {point[1]*G:.4f}) (uuid {s.q(sheet.key("nc"))}))')
        else:
            assert point not in owner or owner[point]==net,(ref,pin,point)
            owner[point]=net;endpoints[net].append((point,angle))
    router=Router(WIDTH,HEIGHT,obstacles,owner)
    reuse=(OUT/(NAME+'.kicad_sch')).exists() and '--reroute' not in sys.argv
    if reuse:
        try:
            reuse_wires(router,owner)
        except (AssertionError,KeyError,ValueError) as error:
            if '--reuse-wires' in sys.argv:raise
            print('Connection layout changed; routing afresh:',error,flush=True)
            router=Router(WIDTH,HEIGHT,obstacles,owner);reuse=False
    for net,pins in ([] if reuse else endpoints.items()):
        for point,angle in pins:
            dx,dy={0:(-1,0),180:(1,0),90:(0,1),270:(0,-1)}[angle]
            escape=point[0]+2*dx,point[1]+2*dy
            assert escape not in obstacles,(net,point,escape)
            router.line(net,point,escape)
    spines={'GND':8,'AGND':12,'+5V':274,'MEGA_5V':278,'+12V':282}
    text('AGND = ANALOG RETURN | MEGA_5V = CONTROLLER 5 V | Dots join wires; crossings without dots stay separate.',12,437,1.65)
    if not reuse:
        for net,x in spines.items():router.line(net,(x,24),(x,424))
    def span(net):
        ps=[p for p,_ in endpoints[net]]
        return max(p[0] for p in ps)-min(p[0] for p in ps)+max(p[1] for p in ps)-min(p[1] for p in ps)
    nets=sorted(endpoints,key=lambda n:(n in spines,span(n),n))
    for index,net in ([] if reuse else enumerate(nets,1)):
        points=[]
        for point,angle in endpoints[net]:
            dx,dy={0:(-1,0),180:(1,0),90:(0,1),270:(0,-1)}[angle];points.append((point[0]+2*dx,point[1]+2*dy))
        tree={(spines[net],y) for y in range(24,425)} if net in spines else {points.pop(0)}
        while points:
            point=min(points,key=lambda q:min(abs(q[0]-t[0])+abs(q[1]-t[1]) for t in tree));points.remove(point)
            before=set(router.trees[net]);router.route(net,point,tree);tree.update(router.trees[net]-before);tree.add(point)
        print(f'{index}/{len(nets)} {net}',flush=True)
    segments,junctions=router.segments(set(owner))
    for net,x in spines.items():
        rail=[(a,b) for a,b in segments[net] if a[0]==b[0]==x]
        if rail:
            top=min(min(a[1],b[1]) for a,b in rail)
            bottom=max(max(a[1],b[1]) for a,b in rail)
            text(net,x-1,top-3,1.7,True)
            text(net,x-1,bottom+1,1.7,True)
    for net,lines in segments.items():
        for a,b in lines:sheet.line((a[0]*G,a[1]*G),(b[0]*G,b[1]*G))
    place_captions(segments)
    for x,y in junctions:sheet.objects.append(f'(junction (at {x*G:.4f} {y*G:.4f}) (diameter .7) (color 0 0 0 0) (uuid {s.q(sheet.key("junction"))}))')
    s.sym_geometry=lambda p:geometry[p['ref']]
    original_lib=s.lib_symbol
    def lib(p,external=False):
        if p['ref'] in native:return native[p['ref']]
        raw=original_lib(p,external)
        if geometry[p['ref']][1][2]=='block':
            raw=raw.replace('(size 1.016 1.016)','(size 1.6 1.6)').replace('(size 0.889 0.889)','(size 1.35 1.35)')
            locs,(w,h),_=geometry[p['ref']][1]
            for pin,px,py,angle in locs:
                length={0:-px-w,180:px-w,90:-py-h,270:py-h}[angle]
                # Exact prefix replacement leaves stock symbol artwork untouched.
                prefix=f'(at {px} {py} {angle}) (length 5.08)'
                raw=raw.replace(prefix,f'(at {px} {py} {angle}) (length {length})')
        if p['ref'].startswith(('DT','DP')):
            circle='(circle (center 0 0) (radius 1.016) (stroke (width 0.254) (type default)) (fill (type none)))'
            vertical=geometry[p['ref']][1][0][0][1]==0
            def poly(points):
                if vertical:points=[(-y,-x) for x,y in points]
                return '(polyline (pts '+' '.join(f'(xy {x} {y})' for x,y in points)+') (stroke (width .254) (type default)) (fill (type none)))'
            raw=raw.replace(circle,poly([(-2.54,-2.54),(-2.54,2.54),(2.54,0),(-2.54,-2.54)])+poly([(2.54,-2.54),(2.54,2.54)])+poly([(0,4),(3,7),(1.5,6.7),(3,7),(2.7,5.5)]))
            raw=raw.replace('(length 5.08)','(length 2.54)')
        return raw
    s.lib_symbol=lib
    for ref,(x,y,angle) in placements.items():
        p=parts[ref];name='Connector:DA15_Pins_MountingHoles' if ref in native else 'Colloquy:'+re.sub(r'[^A-Za-z0-9_]','_',ref)
        sheet.objects.append(f'(symbol (lib_id {s.q(name)}) (at {x*G:.4f} {y*G:.4f} {angle}) (unit 1) '
            f'(in_bom {"yes" if p.get("include_bom",True) else "no"}) (on_board yes) (uuid {s.q(p["uuid"])})'
            +s.prop('Reference',ref,x*G,y*G,hidden=True)+s.prop('Value',p['value'],x*G,y*G,hidden=True)
            +s.prop('Footprint',p['footprint'],x*G,y*G,hidden=True)
            +f'(instances (project {s.q(NAME)} (path {s.q("/"+ROOT)} (reference {s.q(ref)}) (unit 1)))))')
    first=next(iter(native));sheet.parts={ref:p for ref,p in parts.items() if ref not in native or ref==first}
    sheet.save();path=OUT/(NAME+'.kicad_sch')
    raw=path.read_text(encoding='utf-8').replace('(paper "A3")',f'(paper "User" {WIDTH*G} {HEIGHT*G})')
    raw=raw.replace('2026-10-05','2026-10-21').replace('A-prototype','B connection blocks').replace('Prototype: verify harness polarity and sensor values before connection','Reading copy: test points omitted; original PCB retained')
    path.write_text(raw,encoding='utf-8')
    custom=[p for ref,p in parts.items() if ref not in native]
    (OUT/'Colloquy.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n'+'\n'.join(lib(p,True) for p in custom)+')\n',encoding='utf-8')
    (OUT/'routing.json').write_text(json.dumps(dict(nets=len(segments),wire_segments=sum(map(len,segments.values())),omitted_testpoints=[p['ref'] for p in original if p['ref'].startswith('TP')],stock_dsub_symbol='Connector:DA15_Pins_MountingHoles',sheet_mm=[WIDTH*G,HEIGHT*G]),indent=2)+'\n')
    (OUT/'sections.json').write_text(json.dumps(sections,indent=2)+'\n')
    print(path)


if __name__=='__main__':main()
