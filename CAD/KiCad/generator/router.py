"""Small two-layer grid autorouter for KiCad boards (A* with exact-ish clearance).

Copper of every net is rasterised on a fine grid; for the net being routed, a Euclidean distance
transform of all *other* copper gives, per cell, how far a track centre may come.  Each
connection is found with A* (8 directions + vias), with layer-direction preference and turn
penalty, then written back as KiCad tracks/vias.  KiCad DRC is the final judge.
"""
import heapq
import math
import time

import numpy as np
import pcbnew
from scipy import ndimage

INF = np.float32(1e30)
try:
    from astar_nb import astar_core as _NB
except Exception:      # numba not installed: pure Python fallback
    _NB = None


def mm(v):
    return pcbnew.FromMM(float(v))


def tomm(v):
    return pcbnew.ToMM(v)


class Router:
    def __init__(self, board, width, height, grid=0.125, clearance=0.2, edge=0.5, corner_r=3.0,
                 via_d=0.8, via_drill=0.4, log=print):
        self.b = board
        self.g = grid
        self.clr = clearance
        self.via_d, self.via_drill = via_d, via_drill
        self.W, self.H = width, height
        self.nx = int(math.ceil(width / grid)) + 1
        self.ny = int(math.ceil(height / grid)) + 1
        self.N = self.nx * self.ny
        self.owner = np.zeros((2, self.ny, self.nx), np.int32)
        self.through = np.zeros((self.ny, self.nx), bool)
        self.smd = np.zeros((self.ny, self.nx), bool)
        self.netid = {}
        self.netname = {0: ''}
        self.log = log
        self.added = []   # (net, kind, data) for rip-up
        self.width_of = {}
        # board outline (rounded rectangle), inset so copper keeps `edge` from the edge
        ys, xs = np.mgrid[0:self.ny, 0:self.nx]
        X, Y = xs * grid, ys * grid
        ins = edge - clearance
        r = corner_r
        inside = (X >= ins) & (X <= width - ins) & (Y >= ins) & (Y <= height - ins)
        for cx, cy in ((r, r), (width - r, r), (r, height - r), (width - r, height - r)):
            corner = ((X - cx) * np.sign(cx - width / 2) > 0) & ((Y - cy) * np.sign(cy - height / 2) > 0)
            inside &= ~(corner & (np.hypot(X - cx, Y - cy) > r - ins))
        self.owner[:, ~inside] = -1
        self._rasterise_board()
        self.fixed = self.owner != 0          # pads, pre-routed tracks, board edge: never ripped up
        self.routes = {}                      # net id -> list of ('T', L, ax, ay, bx, by, w) / ('V', x, y)
        self.protected = set()                # net ids never ripped up by force_route
        self.smd_near = ndimage.distance_transform_edt(~self.smd) < (self.via_d / 2 + 0.25) / grid + 1

    # ----------------------------------------------------------------- helpers
    def nid(self, name):
        if not name:
            return -1
        if name not in self.netid:
            i = len(self.netid) + 1
            self.netid[name] = i
            self.netname[i] = name
        return self.netid[name]

    def cell(self, x, y):
        return int(round(x / self.g)), int(round(y / self.g))

    def _box(self, x0, y0, x1, y1):
        g = self.g
        ix0 = max(0, int(math.floor(x0 / g))); iy0 = max(0, int(math.floor(y0 / g)))
        ix1 = min(self.nx - 1, int(math.ceil(x1 / g))); iy1 = min(self.ny - 1, int(math.ceil(y1 / g)))
        return ix0, iy0, ix1, iy1

    def capsule_mask(self, ax, ay, bx, by, rad):
        ix0, iy0, ix1, iy1 = self._box(min(ax, bx) - rad, min(ay, by) - rad, max(ax, bx) + rad, max(ay, by) + rad)
        ys, xs = np.mgrid[iy0:iy1 + 1, ix0:ix1 + 1]
        X, Y = xs * self.g, ys * self.g
        dx, dy = bx - ax, by - ay
        L = dx * dx + dy * dy
        if L < 1e-12:
            d = np.hypot(X - ax, Y - ay)
        else:
            t = np.clip(((X - ax) * dx + (Y - ay) * dy) / L, 0, 1)
            d = np.hypot(X - (ax + t * dx), Y - (ay + t * dy))
        return (slice(iy0, iy1 + 1), slice(ix0, ix1 + 1)), d <= rad

    def mark_capsule(self, layer, ax, ay, bx, by, rad, net):
        sl, m = self.capsule_mask(ax, ay, bx, by, rad)
        view = self.owner[layer][sl]
        view[m & (view == 0)] = net
        return sl, m

    def _rasterise_board(self):
        g = self.g
        for fp in self.b.GetFootprints():
            for pad in fp.Pads():
                net = self.nid(pad.GetNetname())
                attr = pad.GetAttribute()
                bb = pad.GetBoundingBox()
                ix0, iy0, ix1, iy1 = self._box(tomm(bb.GetLeft()), tomm(bb.GetTop()), tomm(bb.GetRight()), tomm(bb.GetBottom()))
                if attr == pcbnew.PAD_ATTRIB_NPTH:
                    q = pad.GetPosition()
                    rad = tomm(max(pad.GetDrillSize().x, pad.GetDrillSize().y)) / 2 + 0.05
                    for L in (0, 1):
                        sl, m = self.capsule_mask(tomm(q.x), tomm(q.y), tomm(q.x), tomm(q.y), rad)
                        self.owner[L][sl][m] = -1
                    continue
                layers = [L for L, lay in ((0, pcbnew.F_Cu), (1, pcbnew.B_Cu)) if pad.IsOnLayer(lay)]
                for iy in range(iy0, iy1 + 1):
                    for ix in range(ix0, ix1 + 1):
                        p = pcbnew.VECTOR2I(mm(ix * g), mm(iy * g))
                        if pad.HitTest(p):
                            for L in layers:
                                self.owner[L, iy, ix] = net
                            if attr == pcbnew.PAD_ATTRIB_PTH:
                                self.through[iy, ix] = True
                            if attr == pcbnew.PAD_ATTRIB_SMD:
                                self.smd[iy, ix] = True
        for t in self.b.GetTracks():
            net = self.nid(t.GetNetname())
            if isinstance(t, pcbnew.PCB_VIA):
                q = t.GetPosition()
                x, y = tomm(q.x), tomm(q.y)
                for L in (0, 1):
                    sl, m = self.mark_capsule(L, x, y, x, y, tomm(t.GetWidth()) / 2, net)
                self.through[sl][m] = True
            else:
                L = 0 if t.GetLayer() == pcbnew.F_Cu else 1
                a, b_ = t.GetStart(), t.GetEnd()
                self.mark_capsule(L, tomm(a.x), tomm(a.y), tomm(b_.x), tomm(b_.y), tomm(t.GetWidth()) / 2, net)

    def _refix_pads(self):
        for fp in self.b.GetFootprints():
            for pad in fp.Pads():
                bb = pad.GetBoundingBox()
                ix0, iy0, ix1, iy1 = self._box(tomm(bb.GetLeft()), tomm(bb.GetTop()), tomm(bb.GetRight()), tomm(bb.GetBottom()))
                for L, lay in ((0, pcbnew.F_Cu), (1, pcbnew.B_Cu)):
                    if pad.IsOnLayer(lay) or pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                        self.fixed[L, iy0:iy1 + 1, ix0:ix1 + 1] |= self.owner[L, iy0:iy1 + 1, ix0:ix1 + 1] != 0

    # ----------------------------------------------------------------- per-net state
    def components(self, net):
        F = self.owner[0] == net
        B = self.owner[1] == net
        st = np.ones((3, 3), bool)
        lf, nf = ndimage.label(F, st)
        lb, nb = ndimage.label(B, st)
        parent = list(range(nf + nb + 1))

        def find(a):
            while parent[a] != a:
                parent[a] = parent[parent[a]]
                a = parent[a]
            return a
        both = self.through & F & B
        for a, b_ in set(zip(lf[both].tolist(), lb[both].tolist())):
            ra, rb = find(a), find(nf + b_)
            if ra != rb:
                parent[ra] = rb
        comps = {}
        for k in range(1, nf + 1):
            comps.setdefault(find(k), []).append((0, k))
        for k in range(1, nb + 1):
            comps.setdefault(find(nf + k), []).append((1, k))
        out = []
        for key, members in comps.items():
            m = np.zeros((2, self.ny, self.nx), bool)
            for L, k in members:
                m[L] |= (lf if L == 0 else lb) == k
            out.append(m)
        return out

    def clearance_maps(self, net, width):
        g = self.g
        R = (width / 2 + self.clr) / g + 1.2
        Rv = (self.via_d / 2 + self.clr) / g + 1.2
        dist = []
        for L in (0, 1):
            obst = (self.owner[L] != 0) & (self.owner[L] != net)
            dist.append(ndimage.distance_transform_edt(~obst))
        passable = np.stack([dist[0] >= R, dist[1] >= R])
        via_ok = (dist[0] >= Rv) & (dist[1] >= Rv) & ~self.smd_near
        return passable, via_ok

    # ----------------------------------------------------------------- A*
    def astar(self, src, dst, passable, via_ok, window, via_cost=10.0, b_cost=1.25, turn=0.6, max_nodes=600_000, hw=1.7, penalty=None):
        if _NB is not None:
            tys, txs = np.nonzero(dst[0] | dst[1])
            if len(tys) == 0:
                return None
            pen = penalty.reshape(-1).astype(np.float32) if penalty is not None else np.zeros(1, np.float32)
            ix0, iy0, ix1, iy1 = window
            hmap = ndimage.distance_transform_edt(~(dst[0] | dst[1])).astype(np.float32).reshape(-1)
            p = _NB(src.reshape(-1), dst.reshape(-1), passable.reshape(-1), via_ok.reshape(-1), pen,
                    penalty is not None, hmap, self.nx, self.N, ix0, iy0, ix1, iy1,
                    via_cost, b_cost, turn, hw, max_nodes * 15)
            return p.tolist() if len(p) else None
        return self._astar_py(src, dst, passable, via_ok, window, via_cost, b_cost, turn, max_nodes, hw, penalty)

    def _astar_py(self, src, dst, passable, via_ok, window, via_cost=10.0, b_cost=1.25, turn=0.6, max_nodes=600_000, hw=1.7, penalty=None):
        nx, N = self.nx, self.N
        ix0, iy0, ix1, iy1 = window
        pas = passable.reshape(-1)
        pen = penalty.reshape(-1) if penalty is not None else None
        vok = via_ok.reshape(-1)
        tgt = dst.reshape(-1)
        tys, txs = np.nonzero(dst[0] | dst[1])
        tbx0, tbx1, tby0, tby1 = txs.min(), txs.max(), tys.min(), tys.max()
        gsc = {}
        came = {}
        dirs = {}
        heap = []
        S = np.flatnonzero(src.reshape(-1) & pas)
        if len(S) == 0:
            return None
        for s in S.tolist():
            gsc[s] = 0.0
            came[s] = -1
            dirs[s] = -1
            L, rem = divmod(s, N)
            iy, ix = divmod(rem, nx)
            dx = max(tbx0 - ix, 0, ix - tbx1); dy = max(tby0 - iy, 0, iy - tby1)
            h = max(dx, dy) + 0.414 * min(dx, dy)
            heapq.heappush(heap, (hw * h, s))
        steps = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
                 (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142)]
        expanded = 0
        while heap:
            f, cur = heapq.heappop(heap)
            gc = gsc[cur]
            L, rem = divmod(cur, N)
            iy, ix = divmod(rem, nx)
            dx = max(tbx0 - ix, 0, ix - tbx1); dy = max(tby0 - iy, 0, iy - tby1)
            if f > gc + hw * (max(dx, dy) + 0.414 * min(dx, dy)) + 1e-6:
                continue
            if tgt[cur]:
                path = []
                while cur != -1:
                    path.append(cur)
                    cur = came[cur]
                return path[::-1]
            expanded += 1
            if expanded > max_nodes:
                return None
            pd = dirs[cur]
            lf = 1.0 if L == 0 else b_cost
            for k, (sx, sy, c) in enumerate(steps):
                jx, jy = ix + sx, iy + sy
                if jx < ix0 or jx > ix1 or jy < iy0 or jy > iy1:
                    continue
                nxt = L * N + jy * nx + jx
                if not pas[nxt]:
                    continue
                if sy == 0:
                    pref = 1.0 if L == 0 else 1.15
                elif sx == 0:
                    pref = 1.0 if L == 1 else 1.15
                else:
                    pref = 1.05
                ng = gc + c * pref * lf + (turn if (pd != -1 and pd != k) else 0.0)
                if pen is not None:
                    ng += pen[nxt]
                if ng < gsc.get(nxt, INF):
                    gsc[nxt] = ng
                    came[nxt] = cur
                    dirs[nxt] = k
                    ddx = max(tbx0 - jx, 0, jx - tbx1); ddy = max(tby0 - jy, 0, jy - tby1)
                    heapq.heappush(heap, (ng + hw * (max(ddx, ddy) + 0.414 * min(ddx, ddy)), nxt))
            # via
            if vok[rem]:
                nxt = (1 - L) * N + rem
                if pas[nxt]:
                    ng = gc + via_cost + (pen[nxt] * 4 if pen is not None else 0.0)
                    if ng < gsc.get(nxt, INF):
                        gsc[nxt] = ng
                        came[nxt] = cur
                        dirs[nxt] = -1
                        heapq.heappush(heap, (ng + hw * (max(dx, dy) + 0.414 * min(dx, dy)), nxt))
        return None

    # ----------------------------------------------------------------- commit
    def commit(self, net, path, width):
        g, N, nx = self.g, self.N, self.nx
        pts = []
        for idx in path:
            L, rem = divmod(idx, N)
            iy, ix = divmod(rem, nx)
            pts.append((L, ix, iy))
        run = [pts[0]]
        runs, vias = [], []
        for p in pts[1:]:
            if p[0] != run[-1][0]:
                vias.append((p[1], p[2]))
                runs.append(run)
                run = [p]
            else:
                run.append(p)
        runs.append(run)
        items = self.routes.setdefault(net, [])
        for run in runs:
            if len(run) < 2:
                continue
            corners = [run[0]]
            for a, b_, c in zip(run, run[1:], run[2:]):
                if (b_[1] - a[1], b_[2] - a[2]) != (c[1] - b_[1], c[2] - b_[2]):
                    corners.append(b_)
            corners.append(run[-1])
            L = run[0][0]
            for a, b_ in zip(corners, corners[1:]):
                seg = ('T', L, a[1] * g, a[2] * g, b_[1] * g, b_[2] * g, width)
                items.append(seg)
                self._mark_item(net, seg)
        for ix, iy in vias:
            v = ('V', ix * g, iy * g)
            items.append(v)
            self._mark_item(net, v)
        return len(vias)

    def _mark_item(self, net, it):
        if it[0] == 'T':
            _, L, ax, ay, bx, by, w = it
            self.mark_capsule(L, ax, ay, bx, by, w / 2, net)
        else:
            _, x, y = it
            for L in (0, 1):
                sl, m = self.mark_capsule(L, x, y, x, y, self.via_d / 2, net)
            self.through[sl][m] = True

    def _conflicts(self, net, it):
        if it[0] == 'T':
            _, L, ax, ay, bx, by, w = it
            layers, rad = (L,), w / 2 + self.clr
        else:
            _, ax, ay = it
            bx, by = ax, ay
            layers, rad = (0, 1), self.via_d / 2 + self.clr
        for L in layers:
            sl, m = self.capsule_mask(ax, ay, bx, by, rad)
            o = self.owner[L][sl][m]
            if np.any((o != 0) & (o != net)):
                return True
        return False

    def load_routes(self, routes, drop=()):
        """Replay saved routes; a net whose copper collides with anything now on the board
        (e.g. a footprint change) is dropped so that it gets routed again."""
        dropped = []
        for name, items in routes.items():
            net = self.netid.get(name)
            if net is None:
                continue
            items = [tuple(i) for i in items]
            if name in drop or any(self._conflicts(net, it) for it in items):
                dropped.append(name)
                continue
            for it in items:
                self.routes.setdefault(net, []).append(it)
                self._mark_item(net, it)
        return dropped

    def dump_routes(self):
        return {self.netname[n]: [list(i) for i in items] for n, items in self.routes.items()}

    def fix_tjunctions(self):
        """A route may end on the middle of another track of its net (T junction). KiCad only
        connects such an end if it lies on that track's centre line, so move the end there
        (short extra segment) and split the other track at that point."""
        def segs(net, L):
            return [i for i, it in enumerate(self.routes.get(net, [])) if it[0] == 'T' and it[1] == L]
        for net, items in self.routes.items():
            ends = {}
            for it in items:
                if it[0] == 'T':
                    for p in ((it[2], it[3]), (it[4], it[5])):
                        ends.setdefault((it[1], round(p[0], 4), round(p[1], 4)), 0)
                        ends[(it[1], round(p[0], 4), round(p[1], 4))] += 1
                else:
                    for L in (0, 1):
                        ends.setdefault((L, round(it[1], 4), round(it[2], 4)), 0)
                        ends[(L, round(it[1], 4), round(it[2], 4))] += 2
            changed = True
            while changed:
                changed = False
                for (L, x, y), cnt in list(ends.items()):
                    if cnt != 1:
                        continue
                    if self._on_pad(net, L, x, y):
                        continue
                    for i in segs(net, L):
                        _, _, ax, ay, bx, by, w = items[i]
                        dx, dy = bx - ax, by - ay
                        LL = dx * dx + dy * dy
                        if LL < 1e-12:
                            continue
                        t = ((x - ax) * dx + (y - ay) * dy) / LL
                        if not (0.02 < t < 0.98):
                            continue
                        px, py = ax + t * dx, ay + t * dy
                        if math.hypot(px - x, py - y) > w / 2 + 0.13:
                            continue
                        px, py = round(px, 4), round(py, 4)
                        items[i] = ('T', L, ax, ay, px, py, w)
                        items.append(('T', L, px, py, bx, by, w))
                        wi = max(w, 0.25)
                        if (px, py) != (x, y):
                            items.append(('T', L, x, y, px, py, wi))
                        ends[(L, x, y)] = 2
                        ends[(L, px, py)] = ends.get((L, px, py), 0) + 3
                        changed = True
                        break

    def _on_pad(self, net, L, x, y):
        q = pcbnew.VECTOR2I(mm(x), mm(y))
        lay = pcbnew.F_Cu if L == 0 else pcbnew.B_Cu
        nm = self.netname[net]
        if not hasattr(self, '_padcache'):
            self._padcache = {}
            for fp in self.b.GetFootprints():
                for pad in fp.Pads():
                    self._padcache.setdefault(pad.GetNetname(), []).append(pad)
            self._trackcache = {}
            for t in self.b.GetTracks():
                self._trackcache.setdefault(t.GetNetname(), []).append(t)
        for pad in self._padcache.get(nm, []):
            if pad.IsOnLayer(lay) and pad.HitTest(q):
                return True
        for t in self._trackcache.get(nm, []):     # pre-routed copper already on the board
            if isinstance(t, pcbnew.PCB_VIA) or t.GetLayer() == lay:
                if t.HitTest(q):
                    return True
        return False

    def merge_close_vias(self, gap=1.1):
        """A new via closer than `gap` to a same-net via / THT hole breaks the hole-to-hole rule:
        move it onto that hole (and drag the attached track ends along)."""
        holes = {}
        for t in self.b.GetTracks():
            if isinstance(t, pcbnew.PCB_VIA):
                q = t.GetPosition()
                holes.setdefault(t.GetNetname(), []).append((tomm(q.x), tomm(q.y), True))
        for fp in self.b.GetFootprints():
            for pad in fp.Pads():
                if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
                    q = pad.GetPosition()
                    holes.setdefault(pad.GetNetname(), []).append((tomm(q.x), tomm(q.y), False))
        for net, items in self.routes.items():
            nm = self.netname[net]
            known = list(holes.get(nm, []))
            moves = {}
            keep = []
            for it in items:
                if it[0] != 'V':
                    continue
                x, y = it[1], it[2]
                near = [h for h in known if math.hypot(h[0] - x, h[1] - y) < gap]
                if near:
                    hx, hy, _ = min(near, key=lambda h: math.hypot(h[0] - x, h[1] - y))
                    moves[(round(x, 4), round(y, 4))] = (hx, hy)
                else:
                    known.append((x, y, True))
                    keep.append(it)
            if not moves:
                continue
            new = []
            for it in items:
                if it[0] == 'V':
                    if (round(it[1], 4), round(it[2], 4)) in moves:
                        continue
                    new.append(it)
                else:
                    _, L, ax, ay, bx, by, w = it
                    ax, ay = moves.get((round(ax, 4), round(ay, 4)), (ax, ay))
                    bx, by = moves.get((round(bx, 4), round(by, 4)), (bx, by))
                    new.append(('T', L, ax, ay, bx, by, w))
            self.routes[net] = new

    def apply(self):
        """Write all router-made copper into the KiCad board (call once at the end)."""
        self.merge_close_vias()
        self.fix_tjunctions()
        for net, items in self.routes.items():
            nm = self.netname[net]
            ni = self.b.FindNet(nm)
            for it in items:
                if it[0] == 'T':
                    _, L, ax, ay, bx, by, w = it
                    t = pcbnew.PCB_TRACK(self.b)
                    t.SetStart(pcbnew.VECTOR2I(mm(ax), mm(ay))); t.SetEnd(pcbnew.VECTOR2I(mm(bx), mm(by)))
                    t.SetWidth(mm(w)); t.SetLayer(pcbnew.F_Cu if L == 0 else pcbnew.B_Cu)
                    t.SetNet(ni)
                    self.b.Add(t)
                else:
                    _, x, y = it
                    v = pcbnew.PCB_VIA(self.b)
                    v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
                    v.SetWidth(mm(self.via_d)); v.SetDrill(mm(self.via_drill))
                    v.SetNet(ni)
                    self.b.Add(v)

    def ripup(self, net):
        self.routes.pop(net, None)
        self.owner[(self.owner == net) & ~self.fixed] = 0

    def _remark_fixed(self, net):
        nm = self.netname[net]
        g = self.g
        for fp in self.b.GetFootprints():
            for pad in fp.Pads():
                if pad.GetNetname() != nm:
                    continue
                bb = pad.GetBoundingBox()
                ix0, iy0, ix1, iy1 = self._box(tomm(bb.GetLeft()), tomm(bb.GetTop()), tomm(bb.GetRight()), tomm(bb.GetBottom()))
                layers = [L for L, lay in ((0, pcbnew.F_Cu), (1, pcbnew.B_Cu)) if pad.IsOnLayer(lay)]
                for iy in range(iy0, iy1 + 1):
                    for ix in range(ix0, ix1 + 1):
                        if pad.HitTest(pcbnew.VECTOR2I(mm(ix * g), mm(iy * g))):
                            for L in layers:
                                if self.owner[L, iy, ix] == 0:
                                    self.owner[L, iy, ix] = net
        for t in self.b.GetTracks():
            if t.GetNetname() != nm:
                continue
            if isinstance(t, pcbnew.PCB_VIA):
                q = t.GetPosition()
                for L in (0, 1):
                    self.mark_capsule(L, tomm(q.x), tomm(q.y), tomm(q.x), tomm(q.y), tomm(t.GetWidth()) / 2, net)
            else:
                L = 0 if t.GetLayer() == pcbnew.F_Cu else 1
                a, b_ = t.GetStart(), t.GetEnd()
                self.mark_capsule(L, tomm(a.x), tomm(a.y), tomm(b_.x), tomm(b_.y), tomm(t.GetWidth()) / 2, net)

    # ----------------------------------------------------------------- route a net
    def route_net(self, name, width, fallback=(), margin=12.0):
        net = self.netid.get(name)
        if net is None:
            return True, 0
        fails = 0
        vias = 0
        for w in (width,) + tuple(fallback):
            comps = self.components(net)
            if len(comps) <= 1:
                return True, vias
            passable, via_ok = self.clearance_maps(net, w)
            # reachability labels: same-layer 8-connected regions joined where a via fits
            st = np.ones((3, 3), bool)
            lf, nf = ndimage.label(passable[0], st)
            lb, nb = ndimage.label(passable[1], st)
            par = list(range(nf + nb + 1))

            def fnd(a):
                while par[a] != a:
                    par[a] = par[par[a]]
                    a = par[a]
                return a
            jv = via_ok & passable[0] & passable[1]
            for a_, b_ in set(zip(lf[jv].tolist(), lb[jv].tolist())):
                ra, rb = fnd(a_), fnd(nf + b_)
                if ra != rb:
                    par[ra] = rb

            def regions(m):
                s_ = set(fnd(v) for v in np.unique(lf[m[0] & passable[0]]).tolist() if v)
                s_ |= set(fnd(nf + v) for v in np.unique(lb[m[1] & passable[1]]).tolist() if v)
                return s_
            # grow the tree from the biggest component
            comps.sort(key=lambda m: -m.sum())
            tree = comps.pop(0)
            remaining = comps
            failed = []
            while remaining:
                tys, txs = np.nonzero(tree[0] | tree[1])
                tc = np.array([txs.mean(), tys.mean()])

                def dist(m):
                    ys_, xs_ = np.nonzero(m[0] | m[1])
                    # distance between bounding boxes (cells)
                    dx = max(xs_.min() - txs.max(), txs.min() - xs_.max(), 0)
                    dy = max(ys_.min() - tys.max(), tys.min() - ys_.max(), 0)
                    return math.hypot(dx, dy)
                remaining.sort(key=dist)
                comp = remaining.pop(0)
                ok = False
                if not (regions(comp) & regions(tree)):
                    failed.append(comp)
                    continue
                for mg in (margin, 1e9):
                    ys_, xs_ = np.nonzero(comp[0] | comp[1])
                    tys2, txs2 = np.nonzero(tree[0] | tree[1])
                    mgc = mg / self.g
                    win = (int(max(0, min(xs_.min(), txs2.min()) - mgc)), int(max(0, min(ys_.min(), tys2.min()) - mgc)),
                           int(min(self.nx - 1, max(xs_.max(), txs2.max()) + mgc)), int(min(self.ny - 1, max(ys_.max(), tys2.max()) + mgc)))
                    path = self._astar_spaced(comp, tree & passable, passable, via_ok, win)
                    if path:
                        vias += self.commit(net, path, w)
                        # recompute the tree as union (track cells now owned by net)
                        tree = tree | comp
                        newc = self.owner == net
                        # add freshly marked cells
                        if remaining:
                            tree |= newc & ~np.any(remaining, axis=0)
                        else:
                            tree |= newc
                        ok = True
                        break
                if not ok:
                    failed.append(comp)
            if not failed:
                return True, vias
            fails = len(failed)
        return False, fails


    def _via_cells(self, path):
        N, nx = self.N, self.nx
        out = []
        for a, b_ in zip(path, path[1:]):
            if a // N != b_ // N:
                rem = b_ % N
                out.append((rem // nx, rem % nx))
        return out

    def _astar_spaced(self, src, dst, passable, via_ok, win, min_via_gap=1.2, tries=6, **kw):
        """A* that refuses two vias closer than `min_via_gap` mm (hole-to-hole rule)."""
        vok = via_ok
        for _ in range(tries):
            path = self.astar(src, dst, passable, vok, win, **kw)
            if not path:
                return path
            vc = self._via_cells(path)
            bad = None
            for (y1, x1), (y2, x2) in zip(vc, vc[1:]):
                if math.hypot(x1 - x2, y1 - y2) * self.g < min_via_gap:
                    bad = (y2, x2)
                    break
            if bad is None:
                return path
            vok = vok.copy()
            rr = int(math.ceil(min_via_gap / self.g))
            vok[max(0, bad[0] - rr):bad[0] + rr + 1, max(0, bad[1] - rr):bad[1] + rr + 1] = False
        return None

    # ----------------------------------------------------------------- rip-up & reroute
    def _soft_maps(self, net, width, pen_val):
        g = self.g
        R = (width / 2 + self.clr) / g + 1.2
        Rv = (self.via_d / 2 + self.clr) / g + 1.2
        hard_d, soft_d = [], []
        for L in (0, 1):
            other = (self.owner[L] != 0) & (self.owner[L] != net)
            prot = np.isin(self.owner[L], list(self.protected)) if self.protected else np.zeros_like(other)
            hard = other & (self.fixed[L] | prot)
            soft = other & ~self.fixed[L] & ~prot
            hard_d.append(ndimage.distance_transform_edt(~hard))
            soft_d.append(ndimage.distance_transform_edt(~soft))
        passable = np.stack([hard_d[0] >= R, hard_d[1] >= R])
        penalty = np.stack([(soft_d[0] < R) * pen_val, (soft_d[1] < R) * pen_val]).astype(np.float32)
        via_ok = (hard_d[0] >= Rv) & (hard_d[1] >= Rv) & ~self.smd_near
        return passable, via_ok, penalty, R, Rv

    def blockers(self, net, path, R, Rv):
        """Nets whose router-made copper is too close to `path`."""
        N, nx = self.N, self.nx
        m = np.zeros((2, self.ny, self.nx), bool)
        vias = np.zeros((self.ny, self.nx), bool)
        prev = None
        for idx in path:
            L, rem = divmod(idx, N)
            iy, ix = divmod(rem, nx)
            m[L, iy, ix] = True
            if prev is not None and prev != L:
                vias[iy, ix] = True
            prev = L
        out = set()
        for L in (0, 1):
            d = ndimage.distance_transform_edt(~m[L]) < R
            d |= ndimage.distance_transform_edt(~vias) < Rv
            o = self.owner[L][d & ~self.fixed[L]]
            out |= set(int(v) for v in np.unique(o) if v > 0 and v != net)
        return out

    def force_route(self, name, width, pen_val=30.0):
        """Route the missing connections of `name` allowing it to push through other nets'
        router-made copper; returns the set of nets that were ripped up (to be rerouted)."""
        net = self.netid[name]
        ripped = set()
        for _ in range(12):
            comps = self.components(net)
            if len(comps) <= 1:
                return ripped, True
            comps.sort(key=lambda m: -m.sum())
            tree = comps[0]
            passable, via_ok, penalty, R, Rv = self._soft_maps(net, width, pen_val)
            ys_, xs_ = np.nonzero(tree[0] | tree[1])

            def dist(m):
                y2, x2 = np.nonzero(m[0] | m[1])
                return math.hypot(max(x2.min() - xs_.max(), xs_.min() - x2.max(), 0),
                                  max(y2.min() - ys_.max(), ys_.min() - y2.max(), 0))
            comp = min(comps[1:], key=dist)
            path = self._astar_spaced(comp, tree & passable, passable, via_ok, (0, 0, self.nx - 1, self.ny - 1),
                                      penalty=penalty, max_nodes=1_500_000, hw=1.4)
            if not path:
                return ripped, False
            bl = self.blockers(net, path, R, Rv)
            for n in bl:
                self.ripup(n)
            ripped |= bl
            self.commit(net, path, width)
        return ripped, len(self.components(net)) <= 1
