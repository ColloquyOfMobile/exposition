"""Generate a one-sheet reading copy; never alter the carrier circuit or PCB.

Run with KiCad's Python. Pin positions are logical, not physical socket positions.
"""
from pathlib import Path
import copy
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'scripts'))
import schematic_support as s

NAME = 'analyser-carrier-wired'
OUT = HERE / 'wired'
G = 2.54
ROOT = s.uid(NAME)
parts = {p['ref']: copy.deepcopy(p) for p in json.loads((HERE/'circuit.json').read_text())['components']}
for p in parts.values():
    p['sheet_path'] = '/' + ROOT
original_geometry = s.sym_geometry


def geometry(p):
    ref = p['ref']
    if ref == 'JA1':
        pins = []
        for i in range(5):
            for pin, y, name in [(str(2*i+1), 24+16*i, f'MIC {i+1}'),
                                 (str(11+i), 28+16*i, f'OUT {i+1}'),
                                 (str(2*i+2), 32+16*i, 'AGND')]:
                pins.append((pin, 12*G, (64-y)*G, 180))
                p['pin_names'][pin] = name
        for pin, y, name in [('16',98,'AGND'), ('17',100,'STROBE'), ('18',102,'RESET'),
                              ('19',104,'+5V'), ('20',106,'UNUSED'), ('21',108,'UNUSED')]:
            pins.append((pin,12*G,(64-y)*G,180))
            p['pin_names'][pin] = name
        return {1: (pins, (10*G,46*G), 'block')}
    if ref.startswith('M'):
        p['pin_names']['4'] = 'OUT (R)'
        return {1: ([('1',-18*G,2*G,0), ('4',-18*G,-2*G,0)] +
                    [(pin,18*G,y*G,180) for pin,y in [('2',5),('5',3),('3',1),('6',-1),('7',-3),('8',-5)]],
                    (16*G,7*G), 'block')}
    if ref.startswith('TP'):
        return {1: ([('1',0,2*G,270)], (G,G), 'testpoint')}
    return {1: ([], (2*G,G), 'hole')}


s.sym_geometry = geometry
original_lib_symbol = s.lib_symbol


def lib_symbol(p, external=False):
    raw = original_lib_symbol(p, external)
    if p['ref'].startswith('TP'):
        raw = raw.replace('(length 1.524)', '(length 4.064)')
    return raw


s.lib_symbol = lib_symbol
s.PROJECT = NAME
s.HERE = OUT
sheet = s.Sheet(NAME, 'Audio analyser carrier - continuous wiring', parts, 1)
segments = []


def text(value,x,y,size=1.27,bold=False):
    sheet.text(value,x*G,y*G,size,bold)


def place(ref,x,y):
    p = parts[ref]
    locs, (_,h), _ = geometry(p)[1]
    rx,ry = x*G,y*G-h-2.54
    if ref.startswith('TP'):
        rx,ry = (x+3)*G,y*G
    sheet.objects.append(
        f'(symbol (lib_id {s.q("Colloquy:"+ref)}) (at {x*G} {y*G} 0) (unit 1) '
        f'(in_bom {"yes" if p.get("include_bom",True) else "no"}) (on_board yes) (uuid {s.q(p["uuid"])})'
        + s.prop('Reference',ref,rx,ry,size=1.27)
        + s.prop('Value',p['value'],x*G,y*G,hidden=True)
        + s.prop('Footprint',p['footprint'],x*G,y*G,hidden=True)
        + f'(instances (project {s.q(NAME)} (path {s.q("/"+ROOT)} (reference {s.q(ref)}) (unit 1)))))')


def wire(*points):
    for a,b in zip(points,points[1:]):
        assert a[0] == b[0] or a[1] == b[1]
        if a != b:
            segments.append((a,b))


def main():
    OUT.mkdir(exist_ok=True)
    text('AUDIO ANALYSER CARRIER / WIRED SCHEMATIC',8,6,2.3,True)
    text('Same circuit and pin numbers as the original. All connections are continuous wires.',8,11)
    text('JA1 / BACKPLANE',8,15,1.4,True)
    text('FIVE MODIFIED DFR0126 MODULES',70,15,1.4,True)
    for net,x in [('+5V',120),('AGND',126),('RESET',132),('STROBE',138)]:
        text(net,x-2,18,1.05,True)
    place('JA1',20,64)
    for i,body in enumerate(('FEMALE 1','FEMALE 2','FEMALE 3','MALE 1','MALE 2')):
        y=26+16*i
        place(f'M{i+1}',90,y)
        text(body,81,y-6,1.5,True)
        text('DFR0126 / modified',81,y-3,1.05)
        wire((32,y-2),(72,y-2))
        wire((32,y+2),(72,y+2))
        wire((32,y+6),(42,y+6))
        text('microphone',48,y-3.5,1.0)
        text('analyser out',48,y+.5,1.0)
        place(f'TPA{i}',60,y+6)
        wire((60,y+2),(60,y+4))
        wire((108,y-5),(112,y-5),(112,y-3),(108,y-3))
        wire((112,y-5),(120,y-5))
        wire((108,y-1),(114,y-1),(114,y+1),(108,y+1))
        wire((114,y+1),(126,y+1))
        wire((108,y+3),(132,y+3))
        wire((108,y+5),(138,y+5))
    wire((42,32),(42,98),(126,98))
    wire((32,98),(42,98))
    for pin,y,x in [('17',100,138),('18',102,132),('19',104,120)]:
        wire((32,y),(x,y))
    for x,start,end in [(120,20,104),(126,27,98),(132,29,102),(138,31,100)]:
        wire((x,start),(x,end))
    for y in (106,108):
        sheet.objects.append(f'(no_connect (at {32*G} {y*G}) (uuid {s.q(sheet.key("nc"))}))')
    place('TP5',147,33)
    wire((120,20),(147,20),(147,31))
    text('+5V',150,35,1.0)
    place('TPG',147,46)
    wire((126,41),(147,41),(147,44))
    text('AGND',150,48,1.0)
    text('MODULE CONVERSION (already required in original):',47,107,1.1,True)
    text('Remove module R3; jumper isolated R to OUT; microphone stays on L.',47,109,1.05)
    text('Dots join wires. Crossings without dots are separate. Pin placement is logical, not physical.',8,113,1.05)
    place('H1',149,60)
    place('H2',149,67)
    text('M3 retention',144,70,1.0)
    text('No new parts.',144,76,1.0)
    # Split at endpoints, but keep interior/interior crossings electrically separate.
    ends = {pt for seg in segments for pt in seg}
    split = set()
    def on(pt,a,b):
        return (a[0]==b[0]==pt[0] and min(a[1],b[1])<=pt[1]<=max(a[1],b[1])) or (a[1]==b[1]==pt[1] and min(a[0],b[0])<=pt[0]<=max(a[0],b[0]))
    for a,b in segments:
        points = sorted(pt for pt in ends if on(pt,a,b))
        split.update(tuple(sorted((p,q))) for p,q in zip(points,points[1:]))
    degree = {}
    for a,b in sorted(split):
        sheet.line(tuple(v*G for v in a),tuple(v*G for v in b))
        for pt in (a,b):
            degree[pt] = degree.get(pt,0)+1
    for (x,y),n in degree.items():
        if n>=3:
            sheet.objects.append(f'(junction (at {x*G} {y*G}) (diameter 1.016) (color 0 0 0 0) (uuid {s.q(sheet.key("junction"))}))')
    sheet.save()
    path = OUT/(NAME+'.kicad_sch')
    raw = path.read_text(encoding='utf-8').replace(s.uid('sheetfile/'+NAME),ROOT)
    raw = raw.replace('(date "2026-10-05") (rev "A-prototype")','(date "2026-10-20") (rev "Wired")')
    raw = raw.replace('Prototype: verify harness polarity and sensor values before connection','Same circuit as original - no added components')
    raw = raw.replace('(paper "A3")', '(paper "User" 420 330)')
    path.write_text(raw,encoding='utf-8')
    (OUT/'Colloquy.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n' + '\n'.join(s.lib_symbol(p,external=True) for p in parts.values())+')\n',encoding='utf-8')
    (OUT/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "Colloquy") (type "KiCad") (uri "${KIPRJMOD}/Colloquy.kicad_sym") (options "") (descr "Wired reading copy")))\n')
    (OUT/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "Shields") (type "KiCad") (uri "${KIPRJMOD}/../../Shields.pretty") (options "") (descr "Shared shield footprints")))\n')
    project = OUT/(NAME+'.kicad_pro')
    if not project.exists():
        project.write_text('{}\n')
    print(path)


if __name__ == '__main__':
    main()
