"""Compare a KiCad exported netlist (kicadsexpr) with the design description."""
import subprocess
import sexp


def export(sch, out):
    r = subprocess.run(['kicad-cli', 'sch', 'export', 'netlist', '--format', 'kicadsexpr', '-o', out, sch],
                       capture_output=True, text=True)
    if r.returncode:
        raise RuntimeError(r.stdout + r.stderr)
    return sexp.loads(open(out).read())


def compare(design, netfile_tree):
    nets = sexp.first(netfile_tree, 'nets')
    got = {}
    for n in sexp.find(nets, 'net'):
        name = sexp.first(n, 'name')[1]
        nodes = frozenset((sexp.first(x, 'ref')[1], sexp.first(x, 'pin')[1]) for x in sexp.find(n, 'node'))
        got[name] = nodes
    want = {k: frozenset(v) for k, v in design.nets().items()}
    # drop virtual parts (#FLG etc.)
    got = {k: frozenset(x for x in v if not x[0].startswith('#')) for k, v in got.items()}
    want = {k: frozenset(x for x in v if not x[0].startswith('#')) for k, v in want.items()}
    got = {k: v for k, v in got.items() if v}
    want = {k: v for k, v in want.items() if v}
    # match by node sets
    got_sets = {v: k for k, v in got.items()}
    problems = []
    for name, nodes in want.items():
        if nodes not in got_sets:
            # find best overlapping
            best = max(got.items(), key=lambda kv: len(kv[1] & nodes))
            problems.append('net %s: want %s ; closest %s %s' % (name, sorted(nodes), best[0], sorted(best[1])))
        else:
            gname = got_sets[nodes].lstrip('/').split('/')[-1]
            if gname != name:
                problems.append('net %s exported as %s' % (name, got_sets[nodes]))
    extra = [k for k, v in got.items() if v not in set(want.values())]
    for k in extra:
        if not k.startswith('unconnected-'):
            problems.append('unexpected net %s %s' % (k, sorted(got[k])))
    comps = sexp.first(netfile_tree, 'components')
    refs = {sexp.first(c, 'ref')[1] for c in sexp.find(comps, 'comp')}
    missing = {p.ref for p in design.parts if not p.ref.startswith('#')} - refs
    if missing:
        problems.append('missing components %s' % sorted(missing))
    return problems
