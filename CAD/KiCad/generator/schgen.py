"""Write a hierarchical KiCad (v7 format) schematic from a design.Design.

Every pin gets a short wire stub ending in a net label (local/global) or a power port, so the
connectivity is explicit and checkable with `kicad-cli sch export netlist`.
"""
import math
import os
import uuid
import datetime

import sexp
import symlib
from design import POWER_NETS

LIB_DIRS = [os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tj_library')]
G = 1.27
STUB = 2.54
FONT = 1.27
PAGE_SIZES = [('A3', 420, 297), ('A2', 594, 420), ('A1', 841, 594)]


def U():
    return str(uuid.uuid4())


def snap(v, g=G):
    return round(round(v / g) * g, 4)


def fmt(v):
    s = ('%.4f' % v).rstrip('0').rstrip('.')
    return '0' if s in ('-0', '') else s


def rot(vx, vy, r):
    """screen-coords vector rotation, r = CCW visual degrees"""
    c, s = round(math.cos(math.radians(r)), 6), round(math.sin(math.radians(r)), 6)
    return vx * c + vy * s, -vx * s + vy * c


def text_len(t, size=FONT):
    return len(t) * size * 0.72 + 0.6


class SymCache:
    def __init__(self):
        self.syms = {}

    def get(self, lib_id):
        if lib_id not in self.syms:
            self.syms[lib_id] = symlib.get_symbol(lib_id, LIB_DIRS)
        return self.syms[lib_id]


def default_rot(sym, unit):
    ps = [p for p in symlib.pins(sym) if p['unit'] in (0, unit)]
    if len(ps) == 2 and all(abs(p['x']) < 0.01 for p in ps):
        return 90
    if len(ps) == 3 and sym[1].endswith('R_Potentiometer_Trim'):
        return 90
    return 0


class Placed:
    """One placed unit of a part."""

    def __init__(self, part, unit, sym, r):
        self.part, self.unit, self.sym, self.r = part, unit, sym, r
        self.pins = []
        for p in symlib.pins(sym):
            if p['unit'] not in (0, unit):
                continue
            px, py = rot(p['x'], -p['y'], r)
            a = math.radians(p['angle'])
            ox, oy = rot(-math.cos(a), math.sin(a), r)
            self.pins.append(dict(p, sx=round(px, 4), sy=round(py, 4), ox=round(ox), oy=round(oy)))
        bx0, by0, bx1, by1 = symlib.bbox(sym, unit)
        corners = [rot(x, -y, r) for x, y in ((bx0, by0), (bx1, by1), (bx0, by1), (bx1, by0))]
        self.body = (min(c[0] for c in corners), min(c[1] for c in corners),
                     max(c[0] for c in corners), max(c[1] for c in corners))

    def extent(self, net_of, label_text):
        x0, y0, x1, y1 = self.body
        x0 -= 1; y0 -= 3.5; x1 += 1; y1 += 3.5     # room for ref/value text
        for p in self.pins:
            net = net_of(p)
            L = STUB + (label_text(net) if net else 0)
            ex, ey = p['sx'] + p['ox'] * L, p['sy'] + p['oy'] * L
            w = 1.6
            x0 = min(x0, ex - (w if p['ox'] == 0 else 0)); x1 = max(x1, ex + (w if p['ox'] == 0 else 0))
            y0 = min(y0, ey - (w if p['oy'] == 0 else 0)); y1 = max(y1, ey + (w if p['oy'] == 0 else 0))
        return x0, y0, x1, y1


class SheetWriter:
    def __init__(self, design, key, title, desc, project, root_uuid, sheet_uuid, page, cache, global_nets):
        self.d, self.key, self.title, self.desc = design, key, title, desc
        self.project, self.root_uuid, self.sheet_uuid, self.page = project, root_uuid, sheet_uuid, page
        self.cache = cache
        self.global_nets = global_nets
        self.items = []
        self.used_libs = set()
        self.pwr_count = [0]
        self.uuid = U()

    # ------------------------------------------------------------------ helpers
    def label_text(self, net):
        if net in POWER_NETS:
            return 3.0
        return text_len(net) + (2.6 if net in self.global_nets else 0.3)

    def inst(self, ref, unit):
        return '(instances (project "%s" (path "/%s/%s" (reference "%s") (unit %d))))' % (
            self.project, self.root_uuid, self.sheet_uuid, ref, unit)

    def add_symbol(self, lib_id, x, y, r, ref, value, unit, pins, footprint='', fields=None, dnp=False,
                   ref_pos=None, val_pos=None, hide_ref=False, hide_val=False, uid=None):
        self.used_libs.add(lib_id)
        uid = uid or U()
        rp = ref_pos or (x, y - 3)
        vp = val_pos or (x, y + 3)
        out = ['(symbol (lib_id "%s") (at %s %s %d) (unit %d)' % (lib_id, fmt(x), fmt(y), r, unit),
               '  (in_bom yes) (on_board yes) (dnp %s)' % ('yes' if dnp else 'no'),
               '  (uuid %s)' % uid]

        fa = r if r in (90, 270) else 0

        def prop(name, val, px, py, hide=False, just=None):
            j = ' (justify %s)' % just if just else ''
            out.append('  (property "%s" "%s" (at %s %s %d) (effects (font (size %s %s))%s%s))' % (
                name, val.replace('"', "'"), fmt(px), fmt(py), fa, fmt(FONT), fmt(FONT), j, ' hide' if hide else ''))
        prop('Reference', ref, rp[0], rp[1], hide_ref)
        prop('Value', value, vp[0], vp[1], hide_val)
        prop('Footprint', footprint, x, y, True)
        prop('Datasheet', '', x, y, True)
        for k, v in (fields or {}).items():
            prop(k, v, x, y, True)
        for pnum in pins:
            out.append('  (pin "%s" (uuid %s))' % (pnum, U()))
        out.append('  ' + self.inst(ref, unit))
        out.append(')')
        self.items.append('\n'.join(out))
        return uid

    def wire(self, x1, y1, x2, y2):
        self.items.append('(wire (pts (xy %s %s) (xy %s %s)) (stroke (width 0) (type default)) (uuid %s))' % (
            fmt(x1), fmt(y1), fmt(x2), fmt(y2), U()))

    def no_connect(self, x, y):
        self.items.append('(no_connect (at %s %s) (uuid %s))' % (fmt(x), fmt(y), U()))

    def text(self, t, x, y, size=FONT, bold=False):
        t = t.replace('"', "'")
        self.items.append('(text "%s" (at %s %s 0) (effects (font (size %s %s)%s) (justify left bottom)) (uuid %s))' % (
            t, fmt(x), fmt(y), fmt(size), fmt(size), ' bold' if bold else '', U()))

    def rect(self, x0, y0, x1, y1):
        for a, b, c, d in ((x0, y0, x1, y0), (x1, y0, x1, y1), (x1, y1, x0, y1), (x0, y1, x0, y0)):
            self.items.append('(polyline (pts (xy %s %s) (xy %s %s)) (stroke (width 0) (type dash)) (uuid %s))' % (
                fmt(a), fmt(b), fmt(c), fmt(d), U()))

    def net_label(self, net, x, y, ox, oy):
        ang = {(1, 0): 0, (-1, 0): 180, (0, -1): 90, (0, 1): 270}[(ox, oy)]
        if net in POWER_NETS:
            lib = POWER_NETS[net]
            gnd = net == 'GND'
            nat = (0, 1) if gnd else (0, -1)          # natural body direction of the port symbol
            if (ox, oy) == (-nat[0], -nat[1]):
                r = 180                                # vertical stub pointing against the body
            else:
                r = 0
            self.pwr_count[0] += 1
            ref = '#PWR0%d%02d' % (self.page, self.pwr_count[0])
            d = 1 if r == 0 else -1
            vy = y + nat[1] * d * 5.0
            self.add_symbol(lib, x, y, r, ref, net, 1, ['1'], hide_ref=True, val_pos=(x, vy))
            return
        just = 'left' if ang in (0, 90) else 'right'
        if net in self.global_nets:
            self.items.append(
                '(global_label "%s" (shape bidirectional) (at %s %s %d) (fields_autoplaced) '
                '(effects (font (size %s %s)) (justify %s)) (uuid %s) '
                '(property "Intersheetrefs" "${INTERSHEET_REFS}" (at %s %s 0) (effects (font (size 1 1)) hide)))' % (
                    net, fmt(x), fmt(y), ang, fmt(FONT), fmt(FONT), just, U(), fmt(x), fmt(y)))
        else:
            self.items.append('(label "%s" (at %s %s %d) (fields_autoplaced) (effects (font (size %s %s)) (justify %s bottom)) (uuid %s))' % (
                net, fmt(x), fmt(y), ang, fmt(FONT), fmt(FONT), just, U()))

    # ------------------------------------------------------------------ layout
    def build(self):
        parts = [p for p in self.d.parts if p.sheet == self.key]
        groups = []
        for p in parts:
            if not groups or groups[-1][0] != p.group:
                groups.append((p.group, []))
            groups[-1][1].append(p)
        # make cells
        gcells = []
        for gname, gparts in groups:
            cells = []
            for p in gparts:
                sym = self.cache.get(p.lib_id)
                nunits = symlib.unit_count(sym)
                for u in range(1, nunits + 1):
                    r = p.rot if p.rot is not None else default_rot(sym, u)
                    pl = Placed(p, u, sym, r)
                    missing = [q['number'] for q in pl.pins if q['number'] not in p.pins]
                    assert not missing, (p.ref, missing)
                    ext = pl.extent(lambda q: p.pins.get(q['number']), self.label_text)
                    cells.append((pl, ext))
            gcells.append((gname, cells))

        max_w = 380
        margin_x, margin_y = 15.24, 30.48
        x, y = margin_x, margin_y + 12
        row_h = 0
        placements = []
        for gname, cells in gcells:
            # lay cells of the group in rows of max group width
            gx, gy = 0, 0
            g_row_h = 0
            pos = []
            gw = 0
            for pl, (x0, y0, x1, y1) in cells:
                w, h = x1 - x0, y1 - y0
                if gx > 0 and gx + w > max_w * 0.98:
                    gx = 0
                    gy += g_row_h + 3
                    g_row_h = 0
                pos.append((pl, gx - x0, gy - y0))
                gx += w + 6.35
                gw = max(gw, gx)
                g_row_h = max(g_row_h, h)
            gh = gy + g_row_h
            if x > margin_x and x + gw > max_w + margin_x:
                x = margin_x
                y += row_h + 12
                row_h = 0
            placements.append((gname, x, y, gw, gh, pos))
            x += gw + 10
            row_h = max(row_h, gh)
        total_h = y + row_h + 20
        self.paper = 'A3'
        for name, w, h in PAGE_SIZES:
            if total_h < h - 10:
                self.paper = name
                self.page_w, self.page_h = w, h
                break
        else:
            self.paper, self.page_w, self.page_h = PAGE_SIZES[-1]
        # header text
        self.text(self.title, margin_x, margin_y - 8, 2.5, True)
        for i, line in enumerate(wrap(self.desc, 150)):
            self.text(line, margin_x, margin_y - 3 + i * 2.4, 1.5)
        # emit
        for gname, gx0, gy0, gw, gh, pos in placements:
            self.text(gname, gx0, gy0 - 3.2, 1.6, True)
            self.rect(gx0 - 2, gy0 - 2.5, gx0 + gw - 1.81, gy0 + gh + 1.5)
            for pl, dx, dy in pos:
                ox = snap(gx0 + dx, 2.54)
                oy = snap(gy0 + dy, 2.54)
                self.emit(pl, ox, oy)

    def emit(self, pl, X, Y):
        p = pl.part
        bx0, by0, bx1, by1 = pl.body
        is_pwr = p.lib_id.startswith('power:')
        self.add_symbol(p.lib_id, X, Y, pl.r, p.ref, p.value, pl.unit, [q['number'] for q in pl.pins],
                        footprint=p.footprint, fields=self.fields(p), dnp=p.dnp,
                        ref_pos=(X + (bx0 + bx1) / 2, Y + by0 - 1.6),
                        val_pos=(X + (bx0 + bx1) / 2, Y + by1 + 1.6), hide_ref=is_pwr,
                        uid=p.uuid if pl.unit == 1 else None)
        for q in pl.pins:
            px, py = X + q['sx'], Y + q['sy']
            net = p.pins.get(q['number'])
            if net is None:
                self.no_connect(px, py)
                continue
            ex, ey = px + q['ox'] * STUB, py + q['oy'] * STUB
            self.wire(px, py, ex, ey)
            self.net_label(net, ex, ey, q['ox'], q['oy'])

    def fields(self, p):
        f = dict(p.fields)
        if p.mpn:
            f['MPN'] = p.mpn
        if p.desc:
            f['Description'] = p.desc
        return f

    def render(self):
        libs = '\n'.join(sexp.dumps(self.cache.get(l), 2) for l in sorted(self.used_libs))
        # embedded lib symbol names must keep the lib prefix; sub-symbols must not
        tb = ('(title_block (title "%s") (date "%s") (rev "%s") (company "Colloquy of Mobiles - ZKM") '
              '(comment 1 "%s"))') % (self.title, datetime.date.today().isoformat(), self.d.rev, self.d.title)
        body = '\n  '.join(self.items)
        return ('(kicad_sch (version 20230121) (generator eeschema)\n  (uuid %s)\n  (paper "%s")\n  %s\n'
                '  (lib_symbols\n    %s\n  )\n  %s\n)\n') % (self.uuid, self.paper, tb, libs, body)


def wrap(t, n):
    words, lines, cur = t.split(), [], ''
    for w in words:
        if len(cur) + len(w) + 1 > n:
            lines.append(cur)
            cur = w
        else:
            cur = (cur + ' ' + w).strip()
    if cur:
        lines.append(cur)
    return lines


def fix_embedded(sym):
    """KiCad embeds 'Lib:Name' as top symbol but sub-units keep bare 'Name_u_s'."""
    return sym


def write(design, outdir, root_notes=()):
    os.makedirs(outdir, exist_ok=True)
    project = design.name
    root_uuid = U()
    cache = SymCache()
    sheet_of_net = {}
    for p in design.parts:
        for n in p.pins.values():
            if n and n not in POWER_NETS:
                sheet_of_net.setdefault(n, set()).add(p.sheet)
    global_nets = {n for n, s in sheet_of_net.items() if len(s) > 1}
    sheets = []
    for i, (key, (title, desc)) in enumerate(design.sheets.items()):
        sw = SheetWriter(design, key, title, desc, project, root_uuid, U(), i + 2, cache, global_nets)
        sw.build()
        open(os.path.join(outdir, key + '.kicad_sch'), 'w').write(sw.render())
        sheets.append(sw)
    # root sheet
    items = []
    x, y = 25.4, 76.2
    for i, sw in enumerate(sheets):
        w, h = 60.96, 25.4
        items.append(
            '(sheet (at %s %s) (size %s %s) (fields_autoplaced) (stroke (width 0.1524) (type solid)) '
            '(fill (color 0 0 0 0.0000)) (uuid %s)\n'
            '    (property "Sheetname" "%s" (at %s %s 0) (effects (font (size 1.524 1.524)) (justify left bottom)))\n'
            '    (property "Sheetfile" "%s.kicad_sch" (at %s %s 0) (effects (font (size 1.27 1.27)) (justify left top)))\n'
            '    (instances (project "%s" (path "/%s" (page "%d")))))' % (
                fmt(x), fmt(y), fmt(w), fmt(h), sw.sheet_uuid, sw.title, fmt(x), fmt(y - 0.7), sw.key,
                fmt(x), fmt(y + h + 0.6), project, root_uuid, sw.page))
        x += w + 12.7
        if (i + 1) % 5 == 0:
            x = 25.4
            y += h + 15.24
    notes = []
    ny = 15.24
    notes.append('(text "%s" (at 25.4 %s 0) (effects (font (size 3 3) bold) (justify left bottom)) (uuid %s))' % (
        design.title, fmt(ny), U()))
    ny += 6
    for line in root_notes:
        notes.append('(text "%s" (at 25.4 %s 0) (effects (font (size 1.6 1.6)) (justify left bottom)) (uuid %s))' % (
            line.replace('"', "'"), fmt(ny), U()))
        ny += 2.6
    tb = ('(title_block (title "%s") (date "%s") (rev "%s") (company "Colloquy of Mobiles - ZKM"))' % (
        design.title, datetime.date.today().isoformat(), design.rev))
    root = ('(kicad_sch (version 20230121) (generator eeschema)\n  (uuid %s)\n  (paper "A3")\n  %s\n  (lib_symbols)\n  %s\n  %s\n'
            '  (sheet_instances (path "/" (page "1")))\n)\n') % (root_uuid, tb, '\n  '.join(notes), '\n  '.join(items))
    open(os.path.join(outdir, project + '.kicad_sch'), 'w').write(root)
    return root_uuid, {sw.key: sw.sheet_uuid for sw in sheets}
