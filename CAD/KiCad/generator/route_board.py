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
           protect=(), drop=()):
    """Placed board + saved routes: find nets still split, rip-up & reroute until done."""
    import collections, json
    b = pcbnew.LoadBoard(placed)
    r = Router(b, W, H, log=log)
    dropped = r.load_routes(json.load(open(routes_json)), drop=drop)
    log('routes dropped (collide with the current board): %s' % dropped)
    r.protected = {r.netid[n] for n in protect if n in r.netid}
    names = [n for n in r.netid if n not in skip]
    failed = [n for n in names if len(r.components(r.netid[n])) > 1]
    log('nets still open: %s' % failed)
    for n in list(failed):                       # plain attempt first
        w = widths.get(n, 0.25)
        okn, info = r.route_net(n, w, tuple(f for f in fallback if f < w))
        if okn:
            failed.remove(n)
    log('open after plain pass: %s' % failed)
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


def stitch(path, W, H, pitch=5.0, net='GND', log=print):
    """Add stitching vias of `net` wherever a via fits on a regular grid (joins the pours)."""
    import numpy as np
    from scipy import ndimage
    b = pcbnew.LoadBoard(path)
    r = Router(b, W, H, log=log)
    gid = r.netid[net]
    g = r.g
    Rv = (r.via_d / 2 + 0.25) / g + 1.2
    d = [ndimage.distance_transform_edt(~((r.owner[L] != 0) & (r.owner[L] != gid))) for L in (0, 1)]
    holes = ndimage.distance_transform_edt(~r.through) >= (r.via_d / 2 + 0.9) / g
    ok = (d[0] >= Rv) & (d[1] >= Rv) & ~r.smd_near & holes
    n = 0
    step = int(round(pitch / g))
    for iy in range(int(2 / g), r.ny - int(2 / g), step):
        for ix in range(int(2 / g), r.nx - int(2 / g), step):
            if ok[iy, ix]:
                v = pcbnew.PCB_VIA(b)
                v.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(ix * g), pcbnew.FromMM(iy * g)))
                v.SetWidth(pcbnew.FromMM(r.via_d)); v.SetDrill(pcbnew.FromMM(r.via_drill))
                v.SetNet(b.FindNet(net))
                b.Add(v)
                n += 1
    pcbnew.SaveBoard(path, b)
    return n


def connect_pour_islands(path, W, H, net='GND', width=0.4, log=print):
    """After a zone fill: rasterise the filled pours of `net` into the router grid and route
    short links from every isolated pour island / pad to the main plane."""
    import numpy as np
    from PIL import Image, ImageDraw
    b = pcbnew.LoadBoard(path)
    r = Router(b, W, H, log=log)
    gid = r.netid[net]
    for L, lay in ((0, pcbnew.F_Cu), (1, pcbnew.B_Cu)):
        img = Image.new('1', (r.nx, r.ny), 0)
        dr = ImageDraw.Draw(img)
        for z in b.Zones():
            if z.GetNetname() != net or not z.IsOnLayer(lay):
                continue
            polys = z.GetFilledPolysList(lay)
            for i in range(polys.OutlineCount()):
                o = polys.Outline(i)
                pts = [(pcbnew.ToMM(o.CPoint(k).x) / r.g, pcbnew.ToMM(o.CPoint(k).y) / r.g) for k in range(o.PointCount())]
                if len(pts) > 2:
                    dr.polygon(pts, fill=1)
                for j in range(polys.HoleCount(i)):
                    h = polys.Hole(i, j)
                    hp = [(pcbnew.ToMM(h.CPoint(k).x) / r.g, pcbnew.ToMM(h.CPoint(k).y) / r.g) for k in range(h.PointCount())]
                    if len(hp) > 2:
                        dr.polygon(hp, fill=0)
        m = np.array(img, dtype=bool)
        # shrink by one cell so that rasterisation never claims cells of other copper
        from scipy import ndimage
        m = ndimage.binary_erosion(m)
        r.owner[L][m & (r.owner[L] == 0)] = gid
    comps = r.components(gid)
    log('%s components after fill: %d' % (net, len(comps)))
    ok, info = r.route_net(net, width, (0.3, 0.25))
    log('pour island links: ok=%s vias=%s' % (ok, info))
    r.apply()
    pcbnew.SaveBoard(path, b)
    return ok


def _raster_pours(r, board, net):
    import numpy as np
    from PIL import Image, ImageDraw
    from scipy import ndimage
    masks = []
    for L, lay in ((0, pcbnew.F_Cu), (1, pcbnew.B_Cu)):
        img = Image.new('1', (r.nx, r.ny), 0)
        dr = ImageDraw.Draw(img)
        for z in board.Zones():
            if z.GetNetname() != net or not z.IsOnLayer(lay):
                continue
            polys = z.GetFilledPolysList(lay)
            for i in range(polys.OutlineCount()):
                o = polys.Outline(i)
                pts = [(pcbnew.ToMM(o.CPoint(k).x) / r.g, pcbnew.ToMM(o.CPoint(k).y) / r.g) for k in range(o.PointCount())]
                if len(pts) > 2:
                    dr.polygon(pts, fill=1)
        masks.append(np.array(img, dtype=bool))
    return masks


def repair_islands(placed, routes_json, filled_board, W, H, widths, protect=(), net='GND', width=0.3,
                   fallback=(0.3, 0.25), log=print):
    """Use the filled pours of the last finished board to find isolated pour islands, force a
    GND link out of each (ripping up signal tracks in the way), then reroute what was ripped."""
    import json
    b = pcbnew.LoadBoard(placed)
    r = Router(b, W, H, log=log)
    r.load_routes(json.load(open(routes_json)))
    r.protected = {r.netid[n] for n in protect if n in r.netid}
    fb = pcbnew.LoadBoard(filled_board)
    gid = r.netid[net]
    pour = _raster_pours(r, fb, net)
    import numpy as np
    through0 = r.through.copy()
    # stitching vias of the finished board join the two pour layers
    vias = np.zeros_like(r.through)
    for t in fb.GetTracks():
        if isinstance(t, pcbnew.PCB_VIA) and t.GetNetname() == net:
            q = t.GetPosition()
            x, y = pcbnew.ToMM(q.x), pcbnew.ToMM(q.y)
            sl, m = r.capsule_mask(x, y, x, y, r.via_d / 2)
            for L in (0, 1):
                pour[L][sl] |= m
            vias[sl] |= m
    marked = []
    for L in (0, 1):
        m = pour[L] & (r.owner[L] == 0)
        r.owner[L][m] = gid
        marked.append(m)
    r.through |= vias                      # only vias (and THT pads) join the two layers
    log('%s components with pours: %d' % (net, len(r.components(gid))))
    ripped, ok = r.force_route(net, width, pen_val=40.0)
    log('island links ok=%s ripped=%s' % (ok, sorted(r.netname[x] for x in ripped)))
    r.through = through0
    for L in (0, 1):                       # forget the pour again, keep only the GND link tracks
        r.owner[L][marked[L] & (r.owner[L] == gid)] = 0
        for it in r.routes.get(gid, []):
            r._mark_item(gid, it)
    left = []
    for x in ripped:
        nm = r.netname[x]
        w = widths.get(nm, 0.25)
        okx, _ = r.route_net(nm, w, tuple(f for f in fallback if f < w))
        if not okx:
            ripped2, okf = r.force_route(nm, w)
            for y in ripped2:
                ny_ = r.netname[y]
                if not r.route_net(ny_, widths.get(ny_, 0.25), fallback)[0]:
                    left.append(ny_)
            if not okf:
                left.append(nm)
    log('left open after island repair: %s' % left)
    json.dump(r.dump_routes(), open(routes_json, 'w'))
    return left


def apply_routes(placed, routes_json, out, W, H, skip=('GND',)):
    """Placed board + routes JSON -> routed board; returns the nets that are still open."""
    import json
    b = pcbnew.LoadBoard(placed)
    r = Router(b, W, H)
    r.load_routes(json.load(open(routes_json)))
    open_nets = [n for n in r.netid if n not in skip and len(r.components(r.netid[n])) > 1]
    r.apply()
    pcbnew.SaveBoard(out, b)
    return open_nets
