"""Generate a continuous-wire male v2 reading copy; preserve the source and PCB."""
from pathlib import Path
import importlib.util
import json

HERE = Path(__file__).resolve().parents[1]
OUT = HERE/'wired'
NAME = 'male-static-v2-wired'
spec = importlib.util.spec_from_file_location('body_wired', HERE.parent/'female base v2/scripts/build_wired_schematic.py')
b = importlib.util.module_from_spec(spec)
spec.loader.exec_module(b)
s, G = b.s, b.G
ROOT = s.uid('sheetfile/'+NAME)
parts = {p['ref']:p for p in json.loads((HERE/'circuit.json').read_text())['components']}
for p in parts.values():
    p['sheet_path'] = '/'+ROOT
base_geometry = b.geometry


def geometry(p):
    ref = p['ref']
    if ref == 'J7':
        rows = {'10':16,'2':20,'9':24,'1':28,'0':30,'4':36,'12':48,
                '5':60,'13':72,'3':84,'11':96,'15':108,'6':120,'14':128,'7':136}
        locs = [(pin,10*G,(77-y)*G,180) for pin,y in rows.items()]
        locs += [('8',-10*G,(77-84)*G,0)]
        return {1:(locs,(8*G,64*G),'block')}
    if ref in ('J1','J2','J3','J4','J5','J8','J9','J11'):
        return {1:([('3',-10*G,4*G,0),('2',-10*G,0,0),('1',-10*G,-4*G,0)],(8*G,5.5*G),'block')}
    if ref == 'J10':
        return {1:([('2',-10*G,4*G,0),('1',-10*G,-4*G,0)],(8*G,5.5*G),'block')}
    if ref == 'J6':
        return {1:([('1',-10*G,4*G,0),('2',-10*G,-4*G,0)],(8*G,5.5*G),'block')}
    return base_geometry(p)


b.HERE, b.OUT, b.NAME, b.ROOT, b.parts, b.geometry = HERE, OUT, NAME, ROOT, parts, geometry
s.HERE, s.PROJECT, s.sym_geometry = OUT, NAME, geometry
b.sheet = s.Sheet(NAME,'Male static v2 / continuous wiring / revision D',parts,1)
sheet = b.sheet
text, place, wire = b.text, b.place, b.wire


def save():
    ends = {p for seg in b.segments for p in seg}
    split = set()
    def on(p,a,c):
        return (a[0]==c[0]==p[0] and min(a[1],c[1])<=p[1]<=max(a[1],c[1])) or (a[1]==c[1]==p[1] and min(a[0],c[0])<=p[0]<=max(a[0],c[0]))
    for a,c in b.segments:
        points=sorted(p for p in ends if on(p,a,c))
        split.update(tuple(sorted((p,q))) for p,q in zip(points,points[1:]))
    degree={}
    for a,c in sorted(split):
        sheet.line(tuple(v*G for v in a),tuple(v*G for v in c))
        for p in (a,c):
            degree[p]=degree.get(p,0)+1
    for (x,y),n in degree.items():
        if n>=3:
            sheet.objects.append(f'(junction (at {x*G} {y*G}) (diameter 0.8) (color 0 0 0 0) (uuid {s.q(sheet.key("junction"))}))')
    sheet.save()
    path=OUT/(NAME+'.kicad_sch')
    raw=path.read_text(encoding='utf-8').replace('(paper "A3")','(paper "A2")')
    raw=raw.replace('(date "2026-10-05") (rev "A-prototype")','(date "2026-10-20") (rev "D wired")')
    raw=raw.replace('Prototype: verify harness polarity and sensor values before connection','Reading copy - existing circuit unchanged; see comparison.md')
    path.write_text(raw,encoding='utf-8')
    (OUT/'Colloquy.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n'+'\n'.join(s.lib_symbol(p,external=True) for p in parts.values())+')\n',encoding='utf-8')
    (OUT/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "Colloquy") (type "KiCad") (uri "${KIPRJMOD}/Colloquy.kicad_sym") (options "") (descr "Wired reading copy")))\n')
    (OUT/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "Body") (type "KiCad") (uri "${KIPRJMOD}/../Body.pretty") (options "") (descr "Existing body footprints")))\n')
    project=OUT/(NAME+'.kicad_pro')
    if not project.exists():
        project.write_text('{}\n')
    print(path)


def main():
    OUT.mkdir(exist_ok=True)
    text('MALE STATIC v2 / CONTINUOUS WIRING',8,6,2.5,True)
    text('Revision D reading copy | Same circuit and physical pin numbers | No label-based connections',8,10,1.3)
    place('J7',18,77)
    text('J7 / RACK',10,15,1.5,True)
    text('DA-15 connector',10,18)
    text('Pins grouped',10,21)
    text('by function',10,23)
    text('Unused pin 8',10,80)
    for caption,y in [('DXL DATA',16),('12 V',20),('+5 V',24),('GND',28),('SHELL / PAD 0',32),('PHOTOSENSOR A',36),('PHOTOSENSOR B',48),('PHOTOSENSOR C',60),('PHOTOSENSOR D',72),('MICROPHONE',84),('BODY NEOPIXEL DATA',96),('BAR NEOPIXEL DATA',108),('STATE LED',120),('LINE IN',128),('AUDIO RETURN',136)]:
        text(caption,29,y-2,1.15)
    ports=[('J2',20,'BODY SERVO'),('J9',40,'PHOTOSENSOR A'),('J8',52,'PHOTOSENSOR B'),
           ('J1',64,'PHOTOSENSOR C'),('J4',76,'PHOTOSENSOR D'),('J3',88,'MICROPHONE'),
           ('J5',100,'BODY NEOPIXELS'),('J11',112,'BAR NEOPIXELS')]
    for ref,y,caption in ports:
        for pin in parts[ref]['pins']:
            parts[ref]['pin_names'][pin]={'1':'GND','2':'12V' if ref=='J2' else '5V','3':'DATA' if ref in ('J2','J5','J11') else 'OUT'}[pin]
        place(ref,200,y)
        text(ref+'\n'+caption,197,y-2,1.3,True)
        wire((28,y-4),(190,y-4))
        wire(((155 if ref=='J2' else 160),y),(190,y))
        wire((165,y+4),(190,y+4))
    place('J10',200,124)
    text('J10\nSTATE LED',197,122,1.3,True)
    parts['J10']['pin_names']={'1':'GND','2':'SIGNAL'}
    wire((28,120),(190,120))
    wire((165,128),(190,128))
    wire((28,20),(155,20))
    wire((28,24),(160,24),(160,118),(104,118),(104,121))
    wire((28,28),(40,28),(40,32),(165,32))
    wire((28,30),(35,30),(35,28))
    wire((165,24),(165,128))
    wire((165,116),(112,116),(112,121))
    text('Shared supply rails',144,12,1.3,True)
    for ref,x,caption in [('C1',60,'C1  220uF / 10V'),('C2',82,'C2  100nF')]:
        place(ref,x,28)
        wire((x,24),(x,26))
        wire((x,30),(x,32))
        text(caption,x-4,34,1.15)
    text('+',57,26,1.3,True)
    text('Local amplifier decoupling; C1 value provisional',55,40,1.2)
    text('READING THE DRAWING',55,52,1.6,True)
    text('Dots join wires. Crossings without dots are separate.',55,57,1.3)
    text('X marks an unused pin. Pin numbers match the PCB.',55,61,1.3)
    text('Connector pins are grouped by function, not physical position.',55,65,1.3)
    text('Four sensor channels, body/bar lights and state LED are independent.',55,73,1.3)
    text('No components or electrical connections added in this copy.',55,80,1.3)
    text('LOCAL AUDIO AMPLIFIER',45,123,1.6,True)
    place('R1',55,128)
    text('R1  22K',51,125,1.3)
    wire((28,128),(53,128))
    wire((57,128),(90,128))
    place('R2',80,132)
    text('R2  3K3',68,131,1.3)
    wire((80,128),(80,130))
    wire((80,134),(80,136))
    wire((28,136),(90,136))
    place('M1',108,137)
    text('M1 / GF1002',96,140,1.5,True)
    text('1 x 11 plug-in socket',96,143,1.3)
    text('5 V ONLY',96,146,1.3,True)
    place('J6',200,136)
    text('J6\nSPEAKER',197,134,1.3,True)
    wire((126,132),(190,132))
    wire((126,140),(190,140))
    text('ROUT+ / verify',135,130,1.2)
    text('ROUT- / verify',135,138,1.2)
    text('Neither output goes to GND.',172,149,1.2,True)
    text('AUDIO_RETURN and GND stay separate on this PCB.',8,143,1.2)
    text('Confirm their expected bond inside the actual module.',8,146,1.2)
    for ref,x in [('H1',15),('H2',27)]:
        place(ref,x,153)
        text(ref,x-1,156,1.1)
    text('Insulating supports / nominal 11 mm',33,152,1.2)
    text('M1 unused: 3 = L input; 4/7 = gaps; 8/9 = L outputs.',92,155,1.15)
    text('Rack J7.14/J7.7: line-level audio / return only.',8,158,1.15,True)
    text('Disconnect the old remote speaker output first.',8,160,1.15,True)
    save()


if __name__=='__main__':
    main()
