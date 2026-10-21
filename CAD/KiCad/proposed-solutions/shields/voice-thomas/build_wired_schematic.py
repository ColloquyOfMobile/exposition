"""Build a continuous-wire reading copy; retain the original circuit and PCB."""
from collections import Counter
import copy
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'scripts'))
import schematic_support as s

NAME = 'voice-thomas-wired'
OUT = HERE / 'wired'
ROOT = s.uid('sheetfile/' + NAME)
SCALE = 1.016  # nominal 5 drawing units = KiCad's 5.08 mm connection grid
parts = {p['ref']: copy.deepcopy(p) for p in json.loads((HERE / 'circuit.json').read_text())['components']}
for p in parts.values():
    p['sheet_path'] = '/' + ROOT
parts['JV1']['pin_names'] = {'1': 'TONE IN', '2': 'GND', '3': 'FILTER OUT', '4': 'AGND', '5': 'UNUSED'}
original_geometry = s.sym_geometry


def geometry(p):
    ref = p['ref']
    if ref == 'JV1':
        return {1: ([(str(n), 20*SCALE, (120-y)*SCALE, 180) for n, y in [(1, 75), (2, 135), (3, 105), (4, 150), (5, 165)]], (15*SCALE, 52*SCALE), 'block')}
    if ref.startswith('C'):
        return {1: ([('2', 0, 5.08, 270), ('1', 0, -5.08, 90)], (2.54, 2.54), 'capacitor')}
    if ref == 'R3':
        return {1: ([('1', 0, 5.08, 270), ('2', 0, -5.08, 90)], (1.016, 2.54), 'resistor')}
    if ref.startswith('TP'):
        return {1: ([('1', 0, -2.54, 90)], (1.27, 1.27), 'testpoint')}
    if ref == 'H1':
        return {1: ([], (1.27, 1.27), 'hole')}
    return original_geometry(p)


def main():
    OUT.mkdir(exist_ok=True)
    s.sym_geometry = geometry
    s.HERE, s.PROJECT = OUT, NAME
    sheet = s.Sheet(NAME, 'Voice filter shield / continuous wiring', parts, 1)
    text = sheet.text
    text('VOICE FILTER SHIELD', 15, 15, 2.6, True)
    text('Thomas passive filter / second schematic / all connections drawn as wires', 15, 22, 1.4)
    text('01  VOICE CONNECTOR', 15, 38, 1.6, True)
    text('02  TWO-STAGE RC FILTER', 110, 38, 1.6, True)
    text('Same components, values and pin numbers as the original.', 110, 45, 1.1)
    pos = {'JV1': (30, 120), 'R1': (120, 75), 'R2': (190, 75),
           'C1': (155, 120), 'C2': (230, 120), 'R3': (85, 120),
           'TP1': (100, 55), 'TP4': (255, 55), 'TP5': (255, 147.5), 'H1': (20, 180)}
    pins = {}
    for ref, (x, y) in pos.items():
        actual = sheet.place(ref, x*SCALE, y*SCALE, labels=False)
        pins[ref] = {pin: tuple(round(v/SCALE, 4) for v in pt) for pin, pt in actual.items()}
        if ref == 'R3':
            raw = sheet.objects[-1]
            raw = raw.replace(s.prop('Reference', ref, x*SCALE, y*SCALE-7.62, size=1.016),
                              s.prop('Reference', ref, x*SCALE+5, y*SCALE-3, size=1.2, justify='left'))
            raw = raw.replace(s.prop('Value', parts[ref]['value'], x*SCALE, y*SCALE-5.08, size=1.016),
                              s.prop('Value', parts[ref]['value'], x*SCALE+5, y*SCALE, size=1.2, justify='left'))
            sheet.objects[-1] = raw
    # Connector caption is already printed in the section title.
    # Text notes identify signals but never provide electrical connectivity.
    segments = []

    def wire(*points):
        for a, b in zip(points, points[1:]):
            a, b = tuple(round(v, 4) for v in a), tuple(round(v, 4) for v in b)
            assert a[0] == b[0] or a[1] == b[1]
            if a != b:
                segments.append((a, b))

    wire(pins['JV1']['1'], (85, 75), (100, 75), pins['R1']['1'])
    wire(pins['R1']['2'], (155, 75), pins['R2']['1'])
    wire(pins['R2']['2'], (230, 75), (265, 75), (265, 105), pins['JV1']['3'])
    wire((85, 75), pins['R3']['1'])
    wire(pins['R3']['2'], (85, 135), pins['JV1']['2'])
    wire((155, 75), pins['C1']['2'])
    wire((230, 75), pins['C2']['2'])
    wire(pins['JV1']['4'], (155, 150), (230, 150), (255, 150))
    wire(pins['C1']['1'], (155, 150))
    wire(pins['C2']['1'], (230, 150))
    wire(pins['TP1']['1'], (100, 75))
    wire(pins['TP4']['1'], (255, 75))
    # TP5 pin is directly on the continuous AGND rail.
    nc = pins['JV1']['5']
    sheet.objects.append(f'(no_connect (at {nc[0]*SCALE} {nc[1]*SCALE}) (uuid {s.q(sheet.key("nc"))}))')
    ends = {pt for seg in segments for pt in seg} | {pins['TP5']['1']}

    def on(pt, a, b):
        return (a[0] == b[0] == pt[0] and min(a[1], b[1]) <= pt[1] <= max(a[1], b[1])) or (a[1] == b[1] == pt[1] and min(a[0], b[0]) <= pt[0] <= max(a[0], b[0]))

    split = set()
    for a, b in segments:
        pts = sorted(pt for pt in ends if on(pt, a, b))
        split.update(tuple(sorted((p, q))) for p, q in zip(pts, pts[1:]))
    degree = Counter(pt for seg in split for pt in seg)
    for a, b in sorted(split):
        sheet.line(tuple(v*SCALE for v in a), tuple(v*SCALE for v in b))
    for (x, y), n in degree.items():
        if n >= 3:
            sheet.objects.append(f'(junction (at {x*SCALE} {y*SCALE}) (diameter 1.016) (color 0 0 0 0) (uuid {s.q(sheet.key("junction"))}))')
    text('Input load', 92, 124, 1.1)
    text('GND', 93, 134, 1.2, True)
    text('AGND / filter return', 163, 153, 1.2, True)
    text('Filtered signal returns to JV1 pin 3', 110, 98, 1.1)
    text('Dots = connected. Crossings without dots = separate wires.', 75, 173, 1.2)
    text('GND (pin 2) and AGND (pin 4) stay separate on this shield.', 75, 179, 1.2)
    text('Pin 5 unused; key position 6 has no contact. H1 is mechanical only.', 75, 185, 1.1)
    sheet.save()
    path = OUT / (NAME + '.kicad_sch')
    raw = path.read_text(encoding='utf-8').replace('(paper "A3")', '(paper "A4")')
    raw = raw.replace('(date "2026-10-05") (rev "A-prototype")', '(date "2026-10-20") (rev "W1")')
    raw = raw.replace('Prototype: verify harness polarity and sensor values before connection', 'Original circuit retained; no components added')
    path.write_text(raw, encoding='utf-8')
    (OUT / 'Colloquy.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n' + '\n'.join(s.lib_symbol(p, external=True) for p in parts.values()) + ')\n', encoding='utf-8')
    (OUT / 'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "Colloquy") (type "KiCad") (uri "${KIPRJMOD}/Colloquy.kicad_sym") (options "") (descr "Reading copy symbols")))\n')
    (OUT / 'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "Shields") (type "KiCad") (uri "${KIPRJMOD}/../../Shields.pretty") (options "") (descr "Shared shield footprints")))\n')
    project = OUT / (NAME + '.kicad_pro')
    if not project.exists():
        project.write_text('{}\n')
    print(path)


if __name__ == '__main__':
    main()
