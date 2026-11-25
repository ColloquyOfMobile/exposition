"""Write KiCad project files and fabrication outputs for a generated board."""
import collections
import csv
import json
import os
import shutil
import subprocess
import zipfile

import pcbnew

for _k, _v in (('KICAD7_FOOTPRINT_DIR', '/usr/share/kicad/footprints'), ('KICAD7_SYMBOL_DIR', '/usr/share/kicad/symbols')):
    if os.path.isdir(_v):
        os.environ.setdefault(_k, _v)

HERE = os.path.dirname(os.path.abspath(__file__))


def project_file(path, name, netclasses):
    classes = [dict(name='Default', clearance=0.2, track_width=0.25, via_diameter=0.8, via_drill=0.4,
                    microvia_diameter=0.3, microvia_drill=0.1, diff_pair_gap=0.25, diff_pair_via_gap=0.25,
                    diff_pair_width=0.2, line_style=0, bus_width=12, wire_width=6,
                    pcb_color='rgba(0, 0, 0, 0.000)', schematic_color='rgba(0, 0, 0, 0.000)')]
    patterns = []
    for cname, width, nets in netclasses:
        c = dict(classes[0]); c['name'] = cname; c['track_width'] = width
        classes.append(c)
        patterns += [dict(netclass=cname, pattern=n) for n in nets]
    pro = {
        'board': {'design_settings': {
            'defaults': {'board_outline_line_width': 0.1, 'copper_line_width': 0.2, 'copper_text_size_h': 1.5,
                         'copper_text_size_v': 1.5, 'copper_text_thickness': 0.3, 'silk_line_width': 0.15,
                         'silk_text_size_h': 1.0, 'silk_text_size_v': 1.0, 'silk_text_thickness': 0.15},
            'rules': {'min_clearance': 0.2, 'min_copper_edge_clearance': 0.5, 'min_hole_clearance': 0.25,
                      'min_hole_to_hole': 0.25, 'min_through_hole_diameter': 0.3, 'min_track_width': 0.2,
                      'min_via_annular_width': 0.1, 'min_via_diameter': 0.6, 'min_silk_clearance': 0.0,
                      'min_text_height': 0.6, 'min_text_thickness': 0.1, 'allow_blind_buried_vias': False,
                      'allow_microvias': False, 'max_error': 0.005, 'solder_mask_to_copper_clearance': 0.0,
                      'use_height_for_length_calcs': True},
            'track_widths': [0.0, 0.25, 0.4, 0.6, 0.8, 1.0, 1.5, 2.0, 3.0],
            'via_dimensions': [{'diameter': 0.0, 'drill': 0.0}, {'diameter': 0.8, 'drill': 0.4},
                               {'diameter': 1.0, 'drill': 0.5}],
        }},
        'meta': {'filename': name + '.kicad_pro', 'version': 1},
        'net_settings': {'classes': classes, 'meta': {'version': 3}, 'net_colors': None,
                         'netclass_assignments': None, 'netclass_patterns': patterns},
        'libraries': {'pinned_footprint_libs': [], 'pinned_symbol_libs': []},
        'sheets': [], 'text_variables': {},
    }
    json.dump(pro, open(path, 'w'), indent=2)


def lib_tables(outdir):
    open(os.path.join(outdir, 'sym-lib-table'), 'w').write(
        '(sym_lib_table\n  (lib (name "TJ")(type "KiCad")(uri "${KIPRJMOD}/../tj_library/TJ.kicad_sym")(options "")(descr "Colloquy TJ boards"))\n)\n')
    open(os.path.join(outdir, 'fp-lib-table'), 'w').write(
        '(fp_lib_table\n  (lib (name "TJ")(type "KiCad")(uri "${KIPRJMOD}/../tj_library/TJ.pretty")(options "")(descr "Colloquy TJ boards"))\n)\n')


def run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(' '.join(cmd) + '\n' + r.stdout + r.stderr)
    return r.stdout


def bom(design, path):
    groups = collections.OrderedDict()
    for p in design.parts:
        if p.ref.startswith('#') or not p.footprint:
            continue
        key = (p.value, p.footprint.split(':')[-1], p.mpn, 'DNP' if p.dnp else '')
        groups.setdefault(key, []).append(p)

    def refkey(r):
        import re
        m = re.match(r'([A-Z]+)(\d+)', r)
        return (m.group(1), int(m.group(2))) if m else (r, 0)
    rows = []
    for (val, fp, mpn, dnp), ps in groups.items():
        refs = sorted((p.ref for p in ps), key=refkey)
        desc = '; '.join(sorted(set(p.desc for p in ps if p.desc)))
        rows.append([', '.join(refs), len(refs), val, fp, mpn, dnp, desc])
    rows.sort(key=lambda r: refkey(r[0].split(',')[0]))
    with open(path, 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['References', 'Qty', 'Value', 'Footprint', 'Manufacturer part / note', 'Populate', 'Description'])
        w.writerows(rows)
    return len(rows)


def fab(board_path, outdir, name, design, png_width=2400):
    fabdir = os.path.join(outdir, 'fab')
    gdir = os.path.join(fabdir, 'gerbers')
    shutil.rmtree(fabdir, ignore_errors=True)
    os.makedirs(gdir)
    layers = 'F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts'
    run(['kicad-cli', 'pcb', 'export', 'gerbers', '-l', layers, '--subtract-soldermask', '-o', gdir + '/', board_path])
    run(['kicad-cli', 'pcb', 'export', 'drill', '--format', 'excellon', '--excellon-separate-th',
         '--generate-map', '--map-format', 'pdf', '-o', gdir + '/', board_path])
    z = zipfile.ZipFile(os.path.join(fabdir, name + '-gerbers.zip'), 'w', zipfile.ZIP_DEFLATED)
    for f in sorted(os.listdir(gdir)):
        z.write(os.path.join(gdir, f), f)
    z.close()
    run(['kicad-cli', 'pcb', 'export', 'pos', '--format', 'csv', '--units', 'mm', '--side', 'both',
         '-o', os.path.join(fabdir, name + '-positions.csv'), board_path])
    bom(design, os.path.join(fabdir, name + '-bom.csv'))
    run(['kicad-cli', 'sch', 'export', 'pdf', '-o', os.path.join(fabdir, name + '-schematic.pdf'),
         os.path.join(outdir, name + '.kicad_sch')])
    for side, lay in (('top', 'F.Cu,F.Silkscreen,F.Mask,Edge.Cuts'), ('bottom', 'B.Cu,B.Silkscreen,Edge.Cuts')):
        svg = os.path.join(fabdir, '%s-%s.svg' % (name, side))
        cmd = ['kicad-cli', 'pcb', 'export', 'svg', '--exclude-drawing-sheet', '--page-size-mode', '2', '-l', lay, '-o', svg, board_path]
        if side == 'bottom':
            cmd.insert(4, '--mirror')
        run(cmd)
        run(['rsvg-convert', '-w', str(png_width), '-b', 'white', svg, '-o', svg[:-4] + '.png'])
        os.remove(svg)
    run(['kicad-cli', 'pcb', 'export', 'pdf', '-l', 'F.Cu,F.Silkscreen,F.Fab,Edge.Cuts', '--include-border-title',
         '-o', os.path.join(fabdir, name + '-assembly-top.pdf'), board_path])


def drc(board_path, report):
    b = pcbnew.LoadBoard(board_path)
    pcbnew.WriteDRCReport(b, report, pcbnew.EDA_UNITS_MILLIMETRES, True)
    txt = open(report).read()
    counts = collections.Counter()
    for line in txt.splitlines():
        if line.startswith('['):
            counts[line.split(']')[0][1:]] += 1
    unconnected = [l for l in txt.splitlines() if 'unconnected pads' in l]
    return counts, unconnected
