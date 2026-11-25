"""Load KiCad symbols (flattening 'extends') and compute pin geometry."""
import copy
import os
import sexp
from sexp import Sym, find, first

KICAD_SYM_DIR = os.environ.get('KICAD_SYMBOL_DIR', '/usr/share/kicad/symbols')
_cache = {}


def _load_lib(path):
    if path not in _cache:
        _cache[path] = sexp.loads(open(path, encoding='utf-8').read())
    return _cache[path]


def _lib_path(libname, extra_dirs=()):
    for d in list(extra_dirs) + [KICAD_SYM_DIR]:
        p = os.path.join(d, libname + '.kicad_sym')
        if os.path.exists(p):
            return p
    raise FileNotFoundError(libname)


def get_symbol(lib_id, extra_dirs=()):
    """Return flattened symbol s-expr named lib_id (e.g. 'Device:R')."""
    libname, name = lib_id.split(':', 1)
    lib = _load_lib(_lib_path(libname, extra_dirs))
    syms = {s[1]: s for s in find(lib, 'symbol')}
    s = copy.deepcopy(syms[name])
    ext = first(s, 'extends')
    if ext is not None:
        base = get_symbol(libname + ':' + ext[1], extra_dirs)
        base_name = base[1].split(':', 1)[-1]
        flat = [Sym('symbol'), name]
        # copy non-property, non-subsymbol tokens from base (pin_names, in_bom...)
        props_derived = {p[1]: p for p in find(s, 'property')}
        for c in base[2:]:
            if isinstance(c, list) and c[0] == 'property':
                flat.append(props_derived.pop(c[1], c))
            elif isinstance(c, list) and c[0] == 'symbol':
                sub = copy.deepcopy(c)
                sub[1] = sub[1].replace(base_name, name, 1)
                flat.append(sub)
            else:
                flat.append(c)
        # insert extra derived properties before sub-symbols
        idx = max(i for i, c in enumerate(flat) if isinstance(c, list) and c[0] == 'property') + 1
        for p in props_derived.values():
            flat.insert(idx, p)
            idx += 1
        s = flat
    s[1] = lib_id
    # rename sub-symbols to have bare name (KiCad embeds '<name>_U_S' w/o lib prefix)
    return s


def pins(sym):
    """List of dicts: number, name, unit, x, y, angle, length, type (lib coords, y up)."""
    out = []
    base = sym[1].split(':', 1)[-1]
    for sub in find(sym, 'symbol'):
        nm = sub[1]
        suffix = nm[len(base) + 1:] if nm.startswith(base + '_') else nm.rsplit('_', 2)[-2] + '_' + nm.rsplit('_', 1)[-1]
        unit = int(suffix.split('_')[0])
        for p in find(sub, 'pin'):
            at = first(p, 'at')
            out.append(dict(number=first(p, 'number')[1], name=first(p, 'name')[1],
                            unit=unit, x=float(at[1]), y=float(at[2]),
                            angle=float(at[3]) if len(at) > 3 else 0.0,
                            length=float(first(p, 'length')[1]),
                            type=str(p[1]), hidden=('hide' in p)))
    return out


def unit_count(sym):
    units = {p['unit'] for p in pins(sym)}
    units.discard(0)
    return max(units) if units else 1


def bbox(sym, unit):
    """Rough bounding box of a unit's body (lib coords)."""
    xs, ys = [], []
    base = sym[1].split(':', 1)[-1]
    for sub in find(sym, 'symbol'):
        u = int(sub[1].rsplit('_', 2)[-2])
        if u not in (0, unit):
            continue
        for item in sub[2:]:
            if not isinstance(item, list):
                continue
            if item[0] == 'rectangle':
                for k in ('start', 'end'):
                    q = first(item, k); xs.append(float(q[1])); ys.append(float(q[2]))
            elif item[0] == 'polyline':
                for q in find(first(item, 'pts'), 'xy'):
                    xs.append(float(q[1])); ys.append(float(q[2]))
            elif item[0] == 'circle':
                c = first(item, 'center'); r = float(first(item, 'radius')[1])
                xs += [float(c[1]) - r, float(c[1]) + r]; ys += [float(c[2]) - r, float(c[2]) + r]
            elif item[0] == 'pin':
                at = first(item, 'at'); xs.append(float(at[1])); ys.append(float(at[2]))
    if not xs:
        return (-2.54, -2.54, 2.54, 2.54)
    return (min(xs), min(ys), max(xs), max(ys))
