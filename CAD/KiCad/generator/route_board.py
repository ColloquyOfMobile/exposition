"""Autoroute a placed board with router.Router, pour zones, run KiCad DRC."""
import os
import sys
import time
import pcbnew
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from router import Router


def route(placed, out, W, H, widths, order_first=(), skip=('GND',), fallback=(0.3, 0.25), log=print, routes_json=None,
          protect=(), rounds=8):
    import json
    b = pcbnew.LoadBoard(placed)
    t0 = time.time()
    r = Router(b, W, H, log=log)
    log('grid %dx%d ready in %.1fs' % (r.nx, r.ny, time.time() - t0))
    # net list with pad counts / spread
    import collections
    pads = collections.defaultdict(list)
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetname():
                q = p.GetPosition()
                pads[p.GetNetname()].append((pcbnew.ToMM(q.x), pcbnew.ToMM(q.y)))
    nets = [n for n in pads if n not in skip and len(pads[n]) > 1]

    def spread(n):
        xs = [p[0] for p in pads[n]]; ys = [p[1] for p in pads[n]]
        return (max(xs) - min(xs)) + (max(ys) - min(ys))
    first = [n for n in order_first if n in nets]
    rest = sorted([n for n in nets if n not in first], key=spread)
    failed = []
    for n in first + rest:
        w = widths.get(n, 0.25)
        t1 = time.time()
        ok, info = r.route_net(n, w, tuple(f for f in fallback if f < w))
        log('%-14s w=%.2f %s %s (%.1fs)' % (n, w, 'ok' if ok else 'FAILED', info, time.time() - t1))
        if not ok:
            failed.append(n)
    log('failed nets after first pass: %s' % failed)
    if routes_json:
        json.dump(r.dump_routes(), open(routes_json + '.pass1', 'w'))
    r.protected = {r.netid[n] for n in protect if n in r.netid}
    # rip-up and reroute
    history = collections.Counter()
    for rnd in range(rounds):
        if not failed:
            break
        queue, failed = failed, []
        for n in queue:
            history[n] += 1
            w = widths.get(n, 0.25)
            ripped, ok = r.force_route(n, w, pen_val=20.0 + 15.0 * history[n])
            log('round %d force %-12s ok=%s ripped=%s' % (rnd, n, ok, sorted(r.netname[x] for x in ripped)))
            if not ok:
                failed.append(n)
            for x in ripped:
                nm = r.netname[x]
                okx, info = r.route_net(nm, widths.get(nm, 0.25), tuple(f for f in fallback if f < widths.get(nm, 0.25)))
                if not okx:
                    log('    reroute of %s failed' % nm)
                    failed.append(nm)
        failed = sorted(set(n for n in failed if len(r.components(r.netid[n])) > 1))
        log('after round %d failed: %s' % (rnd, failed))
        if routes_json:
            json.dump(r.dump_routes(), open(routes_json, 'w'))
    if routes_json:
        json.dump(r.dump_routes(), open(routes_json, 'w'))
    r.apply()
    pcbnew.SaveBoard(out, b)
    return failed


def finish(path, drc_report):
    b = pcbnew.LoadBoard(path)
    f = pcbnew.ZONE_FILLER(b)
    f.Fill(b.Zones())
    pcbnew.SaveBoard(path, b)
    ok = pcbnew.WriteDRCReport(b, drc_report, pcbnew.EDA_UNITS_MILLIMETRES, True)
    return ok


def repair(placed, routes_json, out, W, H, widths, skip=('GND',), fallback=(0.3, 0.25), rounds=10, log=print,
           protect=()):
    """Placed board + saved routes: find nets still split, rip-up & reroute until done."""
    import collections, json
    b = pcbnew.LoadBoard(placed)
    r = Router(b, W, H, log=log)
    dropped = r.load_routes(json.load(open(routes_json)))
    log('routes dropped (collide with the current board): %s' % dropped)
    r.protected = {r.netid[n] for n in protect if n in r.netid}
    names = [n for n in r.netid if n not in skip]
    failed = [n for n in names if len(r.components(r.netid[n])) > 1]
    log('nets still open: %s' % failed)
    history = collections.Counter()
    for rnd in range(rounds):
        if not failed:
            break
        queue, failed = failed, []
        for n in queue:
            if len(r.components(r.netid[n])) <= 1:
                continue
            history[n] += 1
            w = widths.get(n, 0.25)
            ripped, ok = r.force_route(n, w, pen_val=20.0 + 15.0 * history[n])
            log('round %d force %-12s ok=%s ripped=%s' % (rnd, n, ok, sorted(r.netname[x] for x in ripped)))
            if not ok:
                failed.append(n)
            for x in ripped:
                nm = r.netname[x]
                wx = widths.get(nm, 0.25)
                okx, info = r.route_net(nm, wx, tuple(f for f in fallback if f < wx))
                if not okx:
                    log('    reroute of %s failed' % nm)
                    failed.append(nm)
        failed = sorted(set(failed))
        log('after round %d open: %s' % (rnd, failed))
        json.dump(r.dump_routes(), open(routes_json, 'w'))
    r.apply()
    pcbnew.SaveBoard(out, b)
    return failed


def extract_routes(routed_board, routes_json):
    """Convert unlocked tracks/vias of an already routed board into a routes JSON."""
    import json
    b = pcbnew.LoadBoard(routed_board)
    out = {}
    for t in b.GetTracks():
        if t.IsLocked():
            continue
        n = t.GetNetname()
        if isinstance(t, pcbnew.PCB_VIA):
            q = t.GetPosition()
            out.setdefault(n, []).append(['V', pcbnew.ToMM(q.x), pcbnew.ToMM(q.y)])
        else:
            a, e = t.GetStart(), t.GetEnd()
            out.setdefault(n, []).append(['T', 0 if t.GetLayer() == pcbnew.F_Cu else 1, pcbnew.ToMM(a.x), pcbnew.ToMM(a.y),
                                          pcbnew.ToMM(e.x), pcbnew.ToMM(e.y), pcbnew.ToMM(t.GetWidth())])
    json.dump(out, open(routes_json, 'w'))
    return sum(len(v) for v in out.values())
