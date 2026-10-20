"""Generate a separate continuous-wire reading copy on a 2.54 mm grid.

Run with KiCad Python. The original schematic and PCB are never modified.
Socket pins are arranged by signal, retaining the original physical pin numbers.
"""
from pathlib import Path
import copy
import json
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'scripts'))
import schematic_support as s

NAME = 'microphone-flex-wired'
OUT = HERE / 'wired'
G = 2.54
ROOT = s.uid(NAME)
parts = {p['ref']: copy.deepcopy(p) for p in json.loads((HERE / 'circuit.json').read_text())['components']}
for part in parts.values():
    part['sheet_path'] = '/' + ROOT
parts['J1']['pin_names'] = {'1': 'GND', '2': '+5V IN', '3': 'AUDIO OUT'}
for i, net in enumerate(('GND', 'VDD'), 1):
    ref = f'#FLG{i}'
    parts[ref] = dict(ref=ref, value='PWR_FLAG', footprint='', description='Retained original supply declaration',
                      pins={'1': net}, pin_names={'1': '~'}, pin_types={'1': 'power_out'},
                      uuid=s.uid(NAME + ref), sheet_path='/' + ROOT, include_bom=False)
original_geometry = s.sym_geometry


def geometry(p):
    ref = p['ref']
    if ref in ('M1', 'J2', 'J3'):
        order = ('VDD', 'GAIN', 'AR', 'MICOUT', 'GND')
        pins = [(next(k for k, n in p['pins'].items() if n == net), (i*4-8)*G, -6*G, 90)
                for i, net in enumerate(order)]
        return {1: (pins, (11*G, 4*G), 'block')}
    if ref == 'J1':
        return {1: ([('1', 10*G, -16*G, 180), ('2', 10*G, 16*G, 180),
                     ('3', 10*G, -8*G, 180)], (8*G, 20*G), 'block')}
    if ref in ('R1', 'R2', 'R5'):
        return {1: ([('2', -2*G, 0, 0), ('1', 2*G, 0, 180)], (G, .4*G), 'resistor')}
    if ref == 'R6':
        return {1: ([('1', 0, 2*G, 270), ('2', 0, -2*G, 90)], (.4*G, G), 'resistor')}
    if ref == 'D1':
        return {1: ([('2', 0, 2*G, 270), ('1', 0, -2*G, 90)], (G, G), 'led')}
    if ref.startswith('TP'):
        return {1: ([('1', 0, 2*G, 270)], (G, G), 'testpoint')}
    if ref.startswith('H'):
        return {1: ([], (2*G, G), 'hole')}
    return original_geometry(p)


s.sym_geometry = geometry
original_lib_symbol = s.lib_symbol


def lib_symbol(part, external=False):
    raw = original_lib_symbol(part, external)
    if part['ref'].startswith('TP'):
        raw = raw.replace('(length 1.524)', '(length 4.064)')
    if part['ref'] == 'D1':
        raw = raw.replace('(circle (center 0 0) (radius 1.016) (stroke (width 0.254) (type default)) (fill (type none)))', '')
        raw = raw.replace('(length 5.08)', '(length 2.54)')
        raw = raw.replace('(symbol "D1_1_1"', '(symbol "D1_1_1"\n'
            '(polyline (pts (xy -2.54 2.54) (xy 2.54 2.54) (xy 0 -2.54) (xy -2.54 2.54)) (stroke (width 0.254) (type default)) (fill (type none)))\n'
            '(polyline (pts (xy -2.54 -2.54) (xy 2.54 -2.54)) (stroke (width 0.254) (type default)) (fill (type none)))\n'
            '(polyline (pts (xy 3.81 0) (xy 6.35 2.54) (xy 5.08 2.54) (xy 6.35 2.54) (xy 6.35 1.27)) (stroke (width 0.254) (type default)) (fill (type none)))\n'
            '(polyline (pts (xy 3.81 -2.54) (xy 6.35 0) (xy 5.08 0) (xy 6.35 0) (xy 6.35 -1.27)) (stroke (width 0.254) (type default)) (fill (type none)))')
    return raw


s.lib_symbol = lib_symbol
s.PROJECT = NAME
s.HERE = OUT
sheet = s.Sheet(NAME, 'Microphone flex - continuous wiring', parts, 1)
segments = []


def text(value, x, y, size=1.27, bold=False):
    sheet.text(value, x*G, y*G, size, bold)


def place(ref, x, y):
    p = parts[ref]
    hidden = ref.startswith('#')
    symbol = 'Colloquy:' + ref.replace('#', '_')
    locs, (w, h), style = geometry(p)[1]
    rx, ry = (x*G, y*G-h-3)
    if ref in ('R6', 'D1') or ref.startswith('C'):
        rx, ry = (x*G+7.62, y*G-2.54)
    if ref == 'D1':
        rx += 2.54
    if ref.startswith('TP'):
        rx, ry = (x*G+3.81, y*G-2.54)
    sheet.objects.append(
        f'(symbol (lib_id {s.q(symbol)}) (at {x*G} {y*G} 0) (unit 1) '
        f'(in_bom {"yes" if p.get("include_bom", True) else "no"}) (on_board yes) '
        f'(uuid {s.q(p["uuid"])})'
        + s.prop('Reference', ref, rx, ry, hidden=hidden, size=1.27)
        + s.prop('Value', p['value'], x*G, y*G, hidden=True)
        + s.prop('Footprint', p['footprint'], x*G, y*G, hidden=True)
        + f'(instances (project {s.q(NAME)} (path {s.q("/"+ROOT)} '
        f'(reference {s.q(ref)}) (unit 1)))))')
    return {pin: (round(x+px/G, 6), round(y-py/G, 6)) for pin, px, py, _ in locs}


def wire(*points):
    for a, b in zip(points, points[1:]):
        assert a[0] == b[0] or a[1] == b[1]
        if a != b:
            segments.append((a, b))


def main():
    OUT.mkdir(exist_ok=True)
    text('MICROPHONE FLEX / WIRED SCHEMATIC', 8, 7, 2.3, True)
    text('Rev C reading copy  |  Continuous wires  |  Fit ONE MAX9814 module only', 8, 12)
    text('01  HARNESS & FILTER', 8, 23, 1.5, True)
    text('02  THREE ALTERNATIVE SOCKETS - SHARED SIGNALS', 61, 17, 1.5, True)
    rows = dict(VDD=40, GAIN=48, AR=56, MICOUT=64, GND=72)
    for ref, x, caption in [('M1', 72, 'UP / vertical'), ('J2', 103, 'LEFT / right angle'), ('J3', 134, 'RIGHT / right angle')]:
        pins = place(ref, x, 27)
        text(caption, x-10, 24)
        for pin, (px, py) in pins.items():
            wire((px, py), (px, rows[parts[ref]['pins'][pin]]))
    place('J1', 12, 56)
    place('R4', 35, 40)
    text('33R / supply filter', 29, 36)
    wire((22,40), (33,40))
    wire((37,40), (150,40))
    place('R5', 35, 64)
    text('470R / output', 29, 60)
    wire((22,64), (33,64))
    wire((37,64), (143,64))
    wire((22,72), (150,72))
    place('R1', 49, 48)
    text('0R / 40 dB', 45, 45)
    wire((44,40), (44,48), (47,48))
    wire((51,48), (130,48))
    place('R2', 49, 56)
    text('0R / A:R 1:500', 44, 53)
    wire((42,72), (42,56), (47,56))
    wire((51,56), (134,56))
    text('03  POWER INDICATOR', 14, 77, 1.3, True)
    place('R6', 28, 83)
    text('2K2', 32, 84)
    wire((26,40), (26,79), (28,79), (28,81))
    place('D1', 28, 92)
    text('GREEN LED', 33, 93)
    wire((28,85), (28,90))
    wire((28,94), (28,98), (150,98), (150,72))
    text('04  DECOUPLING', 96, 78, 1.3, True)
    for ref, x, val in [('C7',92,'22uF / 10V X5R'), ('C6',112,'100nF')]:
        place(ref, x, 87)
        text(val, x+3, 88, 1.1)
        wire((x,40), (x,85))
        wire((x,89), (x,98))
    place('TP1',143,84)
    place('TP2',132,88)
    text('MICOUT',145,85,1.1)
    text('GND',134,89,1.1)
    wire((143,64),(143,82))
    wire((132,72),(132,86))
    place('#FLG1',150,72)
    place('#FLG2',150,40)
    for net,y in rows.items():
        text(net,152,y-1,1.3,True)
    text('Dots join wires. Crossings without dots are separate. Pins are arranged by signal; numbers match the PCB.',8,101,1.1)
    text('Mounting only:',8,106,1.1)
    for i in range(1,9):
        place('H'+str(i),29+(i-1)*9,108)
    text('H1/H2: M5 slots  |  H3/H4: top M2  |  H5-H8: side M2',8,110,1.0)
    # Split wires at existing endpoints, never at interior/interior crossings.
    ends = {pt for seg in segments for pt in seg}
    split = set()
    def on(pt, a, b):
        return (a[0]==b[0]==pt[0] and min(a[1],b[1])<=pt[1]<=max(a[1],b[1])) or (a[1]==b[1]==pt[1] and min(a[0],b[0])<=pt[0]<=max(a[0],b[0]))
    for a,b in segments:
        points=sorted((pt for pt in ends if on(pt,a,b)), key=lambda pt:(pt[0],pt[1]))
        split.update(tuple(sorted((p,q))) for p,q in zip(points,points[1:]))
    degree={}
    for a,b in sorted(split):
        sheet.line(tuple(v*G for v in a),tuple(v*G for v in b))
        for pt in (a,b):
            degree[pt]=degree.get(pt,0)+1
    for (x,y),n in degree.items():
        if n>=3:
            sheet.objects.append(f'(junction (at {x*G} {y*G}) (diameter 1.016) (color 0 0 0 0) (uuid {s.q(sheet.key("junction"))}))')
    sheet.save()
    path=OUT/(NAME+'.kicad_sch')
    raw=path.read_text(encoding='utf-8').replace(s.uid('sheetfile/'+NAME),ROOT)
    raw=raw.replace('(date "2026-10-05") (rev "A-prototype")','(date "2026-10-20") (rev "C-wired")')
    raw=raw.replace('Prototype: verify harness polarity and sensor values before connection','Electrical reading copy - original PCB and schematic retained')
    path.write_text(raw,encoding='utf-8')
    (OUT/'Colloquy.kicad_sym').write_text(
        '(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n'
        + '\n'.join(lib_symbol(p, external=True) for p in parts.values()) + ')\n', encoding='utf-8')
    (OUT/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "Colloquy") (type "KiCad") (uri "${KIPRJMOD}/Colloquy.kicad_sym") (options "") (descr "Wired reading copy symbols")))\n')
    (OUT/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "Shields") (type "KiCad") (uri "${KIPRJMOD}/../../Shields.pretty") (options "") (descr "Shared shield footprints")))\n')
    project = OUT/(NAME+'.kicad_pro')
    if not project.exists():
        project.write_text('{}\n', encoding='utf-8')
    print(path)


if __name__ == '__main__':
    main()
