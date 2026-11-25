"""Exact zone-island analysis on a filled board (KiCad polygons, union-find via vias/THT pads)."""
import math
import pcbnew


def islands(board, net='GND'):
    polys = {}
    for L, lay in (('F', pcbnew.F_Cu), ('B', pcbnew.B_Cu)):
        for z in board.Zones():
            if z.GetNetname() == net and z.IsOnLayer(lay):
                p = z.GetFilledPolysList(lay)
                for i in range(p.OutlineCount()):
                    polys[(L, len([k for k in polys if k[0] == L]))] = (p, i)
    par = {k: k for k in polys}

    def find(a):
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            par[ra] = rb

    def hits(L, pts):
        out = set()
        for k, (p, i) in polys.items():
            if k[0] != L:
                continue
            for q in pts:
                if p.Contains(q, i):
                    out.add(k)
                    break
        return out

    def ring(x, y, r, n=12):
        return [pcbnew.VECTOR2I(int(x + r * math.cos(2 * math.pi * k / n)), int(y + r * math.sin(2 * math.pi * k / n))) for k in range(n)] + [pcbnew.VECTOR2I(int(x), int(y))]

    items = []
    for t in board.GetTracks():
        if t.GetNetname() != net:
            continue
        if isinstance(t, pcbnew.PCB_VIA):
            q = t.GetPosition()
            pts = ring(q.x, q.y, t.GetWidth() / 2 + pcbnew.FromMM(0.15))
            items.append(hits('F', pts) | hits('B', pts))
        else:
            L = 'F' if t.GetLayer() == pcbnew.F_Cu else 'B'
            a, e = t.GetStart(), t.GetEnd()
            pts = [pcbnew.VECTOR2I(int(a.x + (e.x - a.x) * s / 8), int(a.y + (e.y - a.y) * s / 8)) for s in range(9)]
            items.append(hits(L, pts))
    for fp in board.GetFootprints():
        for pd in fp.Pads():
            if pd.GetNetname() != net:
                continue
            q = pd.GetPosition()
            bb = pd.GetBoundingBox()
            r = max(bb.GetWidth(), bb.GetHeight()) / 2 + pcbnew.FromMM(0.2)
            pts = ring(q.x, q.y, r, 16)
            s = set()
            if pd.IsOnLayer(pcbnew.F_Cu):
                s |= hits('F', pts)
            if pd.IsOnLayer(pcbnew.B_Cu):
                s |= hits('B', pts)
            items.append(s)
    for s in items:
        s = list(s)
        for a in s[1:]:
            union(s[0], a)
    groups = {}
    for k in polys:
        groups.setdefault(find(k), []).append(k)

    def area(k):
        p, i = polys[k]
        return abs(p.Outline(i).Area())
    gl = sorted(groups.values(), key=lambda g: -sum(area(k) for k in g))
    out = []
    for g in gl[1:]:
        xs, ys = [], []
        for k in g:
            p, i = polys[k]
            bb = p.Outline(i).BBox()
            xs += [pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetRight())]
            ys += [pcbnew.ToMM(bb.GetTop()), pcbnew.ToMM(bb.GetBottom())]
        out.append((min(xs), min(ys), max(xs), max(ys), g))
    return out


if __name__ == '__main__':
    import sys
    b = pcbnew.LoadBoard(sys.argv[1])
    for x0, y0, x1, y1, g in islands(b):
        print('island %.1f,%.1f - %.1f,%.1f  %s' % (x0, y0, x1, y1, g))
