"""Build an electrically identical, continuous-wire reading copy (plain Python)."""
from pathlib import Path
import copy
import importlib.util
import json

HERE = Path(__file__).resolve().parents[1]
OUT = HERE / 'wired'
NAME = 'female-base-v2-wired'
spec = importlib.util.spec_from_file_location('schematic_support', HERE.parent / 'proposed-solutions/shields/scripts/schematic_support.py')
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)
G = 2.54
ROOT = s.uid('sheetfile/' + NAME)
parts = {p['ref']: copy.deepcopy(p) for p in json.loads((HERE/'circuit.json').read_text())['components']}
for p in parts.values():
    p['sheet_path'] = '/' + ROOT


def geometry(p):
    ref = p['ref']
    if ref == 'J7':
        rows = {'14':16, '7':20, '15':24, '8':28, '0':30, '5':36,
                '6':48, '13':60, '12':76, '4':84}
        locs = [(pin, 10*G, (50-y)*G, 180) for pin,y in rows.items()]
        locs += [(pin, -10*G, (50-y)*G, 0) for pin,y in zip(['1','2','3','9','10','11'], [40,44,48,52,56,60])]
        return {1:(locs,(8*G,36*G),'block')}
    if ref in ('J2','J3','J4','J5'):
        return {1:([('3',-10*G,4*G,0),('2',-10*G,0,0),('1',-10*G,-4*G,0)],(8*G,5.5*G),'block')}
    if ref == 'J6':
        return {1:([('1',-10*G,4*G,0),('2',-10*G,-4*G,0)],(8*G,6*G),'block')}
    if ref == 'M1':
        locs = [('1',-18*G,9*G,0),('2',-18*G,G,0),
                ('5',-4*G,16*G,270),('6',4*G,16*G,270),
                ('10',18*G,5*G,180),('11',18*G,-3*G,180)]
        locs += [(pin,(x-88)*G,-15*G,90) for pin,x in zip(['3','4','7','8','9'],[76,82,88,94,100])]
        return {1:(locs,(16*G,13*G),'block')}
    if ref == 'R2':
        return {1:([('1',0,2*G,270),('2',0,-2*G,90)],(1.016,2.54),'resistor')}
    if ref.startswith('H'):
        return {1:([],(1.5*G,1.5*G),'testpoint')}
    return original_geometry(p)


original_geometry = s.sym_geometry
s.sym_geometry = geometry
s.PROJECT, s.HERE = NAME, OUT
sheet = s.Sheet(NAME,'Female base v2 / continuous wiring / revision D',parts,1)
segments = []


def text(value,x,y,size=1.15,bold=False):
    sheet.text(value,x*G,y*G,size,bold)


def place(ref,x,y):
    p = parts[ref]
    locs, (w,h), style = geometry(p)[1]
    # Keep references/values clear of wire corridors; write captions explicitly.
    sheet.objects.append(
        f'(symbol (lib_id {s.q("Colloquy:"+ref)}) (at {x*G} {y*G} 0) (unit 1) '
        f'(in_bom {"yes" if p.get("include_bom",True) else "no"}) (on_board yes) (uuid {s.q(p["uuid"])})'
        + s.prop('Reference',ref,x*G,(y-h/G-2)*G,hidden=True)
        + s.prop('Value',p['value'],x*G,y*G,hidden=True)
        + s.prop('Footprint',p['footprint'],x*G,y*G,hidden=True)
        + f'(instances (project {s.q(NAME)} (path {s.q("/"+ROOT)} (reference {s.q(ref)}) (unit 1)))))')
    for pin,px,py,_ in locs:
        if p['pins'][pin] is None:
            sheet.objects.append(f'(no_connect (at {x*G+px} {y*G-py}) (uuid {s.q(sheet.key("nc"))}))')


def wire(*points):
    for a,b in zip(points,points[1:]):
        assert a[0]==b[0] or a[1]==b[1]
        if a!=b:
            segments.append((a,b))


def main():
    OUT.mkdir(exist_ok=True)
    text('FEMALE BASE v2 / CONTINUOUS WIRING',8,6,2.2,True)
    text('Revision D reading copy | Same circuit and physical pin numbers | No label-based connections',8,10)
    place('J7',18,50)
    text('J7 / RACK',10,15,1.5,True)
    text('DA-15 connector',10,18)
    text('Pins grouped by function',10,21,.95)
    text('Unused',10,36)
    for caption,y in [('DXL DATA',16),('12 V',20),('+5 V',24),('GND',28),('Shell / pad 0',32),('PHOTOSENSOR',36),('MICROPHONE',48),('NEOPIXEL DATA',60),('LINE IN',76),('AUDIO RETURN',84)]:
        text(caption,29,y-2,.95)
    for ref,y,caption in [('J2',20,'MIRROR SERVO'),('J4',40,'PHOTOSENSOR'),('J3',52,'MICROPHONE'),('J5',64,'NEOPIXELS')]:
        place(ref,140,y)
        text(ref+'\n'+caption,137,y-2,1.25,True)
        for pin,net in parts[ref]['pins'].items():
            parts[ref]['pin_names'][pin] = {'1':'GND','2':'12V' if ref=='J2' else '5V','3':'DATA' if ref in ('J2','J5') else 'OUT'}[pin]
        wire((28,y-4),(130,y-4))
        wire(((105 if ref=='J2' else 110),y),(130,y))
        wire((115,y+4),(130,y+4))
    wire((28,20),(105,20))
    wire((28,24),(110,24),(110,68),(84,68),(84,69))
    wire((28,28),(40,28),(40,32),(115,32))
    wire((115,24),(115,68))
    wire((115,66),(92,66),(92,69))
    wire((28,30),(35,30),(35,28))
    text('Shared supply rails',88,12,1.2,True)
    text('All crossing wires without a dot are separate.',47,44,1.1)
    text('Dots mark electrical joins; X marks an unused pin.',47,47,1.1)
    for ref,x,caption in [('C1',50,'C1  220uF / 10V SMD'),('C2',67,'C2  100nF')]:
        place(ref,x,28)
        wire((x,24),(x,26))
        wire((x,30),(x,32),(115,32))
        text(caption,x-4,34,.95)
    text('Local amplifier decoupling; C1 value provisional',47,38,1.0)
    text('LOCAL AUDIO AMPLIFIER',42,71,1.4,True)
    place('R1',45,76)
    text('R1  22K',41,73)
    wire((28,76),(43,76))
    wire((47,76),(70,76))
    place('R2',60,80)
    text('R2  3K3',48,79)
    wire((60,76),(60,78))
    wire((60,82),(60,84))
    wire((28,84),(70,84))
    place('M1',88,85)
    text('M1 / GF1002',76,88,1.4,True)
    text('1 x 11 plug-in socket',76,91)
    text('5 V ONLY',76,94,1.1,True)
    place('J6',140,84)
    text('J6 / SPEAKER',130,74,1.4,True)
    wire((106,80),(130,80))
    wire((106,88),(130,88))
    text('ROUT+ / verify',111,78,1.0)
    text('ROUT- / verify',111,86,1.0)
    text('Neither output goes to GND.',110,92,1.05,True)
    text('AUDIO_RETURN and GND stay separate on this PCB.',8,91,1.0)
    text('Confirm their expected bond inside the actual module.',8,94,1.0)
    for ref,x in [('H1',15),('H2',27)]:
        if ref in parts:
            place(ref,x,101)
            text(ref,x-1,104,1.05)
    if 'H1' in parts or 'H2' in parts:
        text('Insulating module supports / nominal 11 mm',33,100,1.05)
    text('M1 unused: 3 = L input; 4/7 = gaps; 8/9 = L outputs.',72,103,1.0)
    text('Rack J7.12/J7.4 must supply line-level audio / return; disconnect the old remote speaker output first.',8,110,1.05,True)
    # Split only at existing endpoints. Interior/interior crossings do not connect.
    ends = {p for seg in segments for p in seg}
    split = set()
    def on(p,a,b):
        return (a[0]==b[0]==p[0] and min(a[1],b[1])<=p[1]<=max(a[1],b[1])) or (a[1]==b[1]==p[1] and min(a[0],b[0])<=p[0]<=max(a[0],b[0]))
    for a,b in segments:
        points=sorted(p for p in ends if on(p,a,b))
        split.update(tuple(sorted((p,q))) for p,q in zip(points,points[1:]))
    degree={}
    for a,b in sorted(split):
        sheet.line(tuple(v*G for v in a),tuple(v*G for v in b))
        for p in (a,b):
            degree[p]=degree.get(p,0)+1
    for (x,y),n in degree.items():
        if n>=3:
            sheet.objects.append(f'(junction (at {x*G} {y*G}) (diameter 0.8) (color 0 0 0 0) (uuid {s.q(sheet.key("junction"))}))')
    sheet.save()
    path=OUT/(NAME+'.kicad_sch')
    raw=path.read_text(encoding='utf-8').replace('(date "2026-10-05") (rev "A-prototype")','(date "2026-10-20") (rev "D wired")')
    if 'H1' not in parts and 'H2' not in parts:
        raw=raw.replace('(date "2026-10-20")','(date "2026-10-21")')
    raw=raw.replace('Prototype: verify harness polarity and sensor values before connection','Reading copy - existing circuit unchanged; see comparison.md')
    path.write_text(raw,encoding='utf-8')
    (OUT/'Colloquy.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n'+'\n'.join(s.lib_symbol(p,external=True) for p in parts.values())+')\n',encoding='utf-8')
    (OUT/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "Colloquy") (type "KiCad") (uri "${KIPRJMOD}/Colloquy.kicad_sym") (options "") (descr "Wired reading copy")))\n')
    (OUT/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "Body") (type "KiCad") (uri "${KIPRJMOD}/../Body.pretty") (options "") (descr "Existing body footprints")))\n')
    project=OUT/(NAME+'.kicad_pro')
    if not project.exists():
        project.write_text('{}\n')
    print(path)


if __name__ == '__main__':
    main()
