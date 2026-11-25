"""Build a KiCad board from a design.Design + placement (footprints, nets, tracks, zones, silkscreen)."""
import os
import pcbnew

HERE = os.path.dirname(os.path.abspath(__file__))
FP_DIRS = {'TJ': os.path.join(HERE, '..', 'tj_library', 'TJ.pretty')}


def mm(v):
    return pcbnew.FromMM(float(v))


def V(x, y):
    return pcbnew.VECTOR2I(mm(x), mm(y))


def fp_path(lib):
    return FP_DIRS.get(lib, '/usr/share/kicad/footprints/%s.pretty' % lib)


class Builder:
    def __init__(self, design, uuids, width, height):
        self.d = design
        self.uuids = uuids
        self.W, self.H = width, height
        self.board = pcbnew.BOARD()
        self.nets = {}
        self.fps = {}
        bs = self.board.GetDesignSettings()
        bs.SetCopperLayerCount(2)
        bs.SetBoardThickness(mm(1.6))

    # ------------------------------------------------------------ outline
    def outline(self, r=3.0):
        W, H = self.W, self.H
        segs = [((r, 0), (W - r, 0)), ((W, r), (W, H - r)), ((W - r, H), (r, H)), ((0, H - r), (0, r))]
        for a, b in segs:
            s = pcbnew.PCB_SHAPE(self.board)
            s.SetShape(pcbnew.SHAPE_T_SEGMENT)
            s.SetStart(V(*a)); s.SetEnd(V(*b))
            s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
            self.board.Add(s)
        for cx, cy, sa in ((r, r, 180), (W - r, r, 270), (W - r, H - r, 0), (r, H - r, 90)):
            s = pcbnew.PCB_SHAPE(self.board)
            s.SetShape(pcbnew.SHAPE_T_ARC)
            s.SetCenter(V(cx, cy))
            import math
            a0 = math.radians(sa)
            s.SetStart(V(cx + r * math.cos(a0), cy + r * math.sin(a0)))
            s.SetArcAngleAndEnd(pcbnew.EDA_ANGLE(90, pcbnew.DEGREES_T), True)
            s.SetLayer(pcbnew.Edge_Cuts); s.SetWidth(mm(0.1))
            self.board.Add(s)

    def net(self, name):
        if name not in self.nets:
            n = pcbnew.NETINFO_ITEM(self.board, name)
            self.board.Add(n)
            self.nets[name] = n
        return self.nets[name]

    # ------------------------------------------------------------ footprints
    def add_parts(self, placement):
        for p in self.d.parts:
            if p.ref.startswith('#') or not p.footprint:
                continue
            lib, name = p.footprint.split(':')
            fp = pcbnew.FootprintLoad(fp_path(lib), name)
            assert fp is not None, p.footprint
            fp.SetFPID(pcbnew.LIB_ID(lib, name))
            fp.SetReference(p.ref)
            fp.SetValue(p.value)
            sheet_uuid = self.uuids['sheets'][p.sheet]
            fp.SetPath(pcbnew.KIID_PATH('/%s/%s' % (sheet_uuid, p.uuid)))
            x, y, rot = placement[p.ref][:3]
            side = placement[p.ref][3] if len(placement[p.ref]) > 3 else 'F'
            self.board.Add(fp)
            fp.SetPosition(V(x, y))
            fp.SetOrientationDegrees(rot)
            if side == 'B':
                fp.Flip(fp.GetPosition(), False)
            ref = fp.Reference()
            ref.SetTextSize(V(0.8, 0.8)); ref.SetTextThickness(mm(0.12))
            for pad in fp.Pads():
                num = pad.GetNumber()
                if num == '':
                    continue
                netname = p.pins.get(num)
                if netname:
                    pad.SetNet(self.net(netname))
            if p.dnp:
                fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_EXCLUDE_FROM_BOM)
            self.fps[p.ref] = fp

    def hide_ref(self, refs):
        for r in refs:
            self.fps[r].Reference().SetVisible(False)

    def move_ref(self, ref, dx, dy, size=None):
        t = self.fps[ref].Reference()
        fpos = self.fps[ref].GetPosition()
        t.SetPosition(pcbnew.VECTOR2I(fpos.x + mm(dx), fpos.y + mm(dy)))
        t.SetTextAngle(pcbnew.EDA_ANGLE(0, pcbnew.DEGREES_T))
        if size:
            t.SetTextSize(V(size, size))

    # ------------------------------------------------------------ graphics
    def text(self, s, x, y, size=1.0, layer=pcbnew.F_SilkS, bold=False, angle=0, just=0):
        t = pcbnew.PCB_TEXT(self.board)
        t.SetText(s)
        t.SetPosition(V(x, y))
        t.SetLayer(layer)
        t.SetTextSize(V(size, size))
        t.SetTextThickness(mm(size * (0.2 if bold else 0.15)))
        t.SetTextAngle(pcbnew.EDA_ANGLE(angle, pcbnew.DEGREES_T))
        if just < 0:
            t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_LEFT)
        elif just > 0:
            t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_RIGHT)
        self.board.Add(t)
        return t

    def silk_rect(self, x0, y0, x1, y1, w=0.15, layer=pcbnew.F_SilkS):
        s = pcbnew.PCB_SHAPE(self.board)
        s.SetShape(pcbnew.SHAPE_T_RECT)
        s.SetStart(V(x0, y0)); s.SetEnd(V(x1, y1))
        s.SetLayer(layer); s.SetWidth(mm(w))
        self.board.Add(s)

    # ------------------------------------------------------------ copper
    def track(self, pts, width, layer, netname, lock=True):
        out = []
        for a, b in zip(pts, pts[1:]):
            t = pcbnew.PCB_TRACK(self.board)
            t.SetStart(V(*a)); t.SetEnd(V(*b))
            t.SetWidth(mm(width)); t.SetLayer(layer)
            t.SetNet(self.net(netname))
            t.SetLocked(lock)
            self.board.Add(t)
            out.append(t)
        return out

    def via(self, x, y, netname, d=1.0, drill=0.5, lock=True):
        v = pcbnew.PCB_VIA(self.board)
        v.SetPosition(V(x, y))
        v.SetWidth(mm(d)); v.SetDrill(mm(drill))
        v.SetNet(self.net(netname))
        v.SetLocked(lock)
        self.board.Add(v)
        return v

    def pad_pos(self, ref, num):
        for p in self.fps[ref].Pads():
            if p.GetNumber() == str(num):
                q = p.GetPosition()
                return (pcbnew.ToMM(q.x), pcbnew.ToMM(q.y))
        raise KeyError((ref, num))

    def zone(self, netname, layer, poly, priority=0, clearance=0.3, min_w=0.25, thermal_gap=0.4,
             spoke=0.5, solid_pads=False, keepout=False):
        z = pcbnew.ZONE(self.board)
        z.SetLayer(layer)
        if netname:
            z.SetNet(self.net(netname))
        ol = z.Outline()
        ol.NewOutline()
        for x, y in poly:
            ol.Append(mm(x), mm(y))
        z.SetAssignedPriority(priority)
        z.SetLocalClearance(mm(clearance))
        z.SetMinThickness(mm(min_w))
        z.SetThermalReliefGap(mm(thermal_gap))
        z.SetThermalReliefSpokeWidth(mm(spoke))
        z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL if solid_pads else pcbnew.ZONE_CONNECTION_THERMAL)
        z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
        self.board.Add(z)
        return z

    def keepout(self, layer_set, poly, tracks=True, vias=True, pours=False):
        z = pcbnew.ZONE(self.board)
        z.SetIsRuleArea(True)
        z.SetDoNotAllowTracks(tracks)
        z.SetDoNotAllowVias(vias)
        z.SetDoNotAllowCopperPour(pours)
        z.SetDoNotAllowPads(False)
        z.SetDoNotAllowFootprints(False)
        z.SetLayerSet(layer_set)
        ol = z.Outline()
        ol.NewOutline()
        for x, y in poly:
            ol.Append(mm(x), mm(y))
        self.board.Add(z)

    def gnd_fanout(self, net='GND'):
        """Drop a via next to every SMD pad of `net` so it reaches the bottom plane."""
        import math
        W, H = self.W, self.H
        pads_all = [pd for fp in self.board.GetFootprints() for pd in fp.Pads()]

        def free(x, y, rad=0.9):
            for pd in pads_all:
                bb = pd.GetBoundingBox()
                if (pcbnew.ToMM(bb.GetLeft()) - rad < x < pcbnew.ToMM(bb.GetRight()) + rad and
                        pcbnew.ToMM(bb.GetTop()) - rad < y < pcbnew.ToMM(bb.GetBottom()) + rad):
                    return False
            for t in self.board.GetTracks():
                if t.GetNetname() == net:
                    continue
                if isinstance(t, pcbnew.PCB_VIA):
                    q = t.GetPosition()
                    if math.hypot(pcbnew.ToMM(q.x) - x, pcbnew.ToMM(q.y) - y) < 1.6:
                        return False
                else:
                    a_, b_ = t.GetStart(), t.GetEnd()
                    ax, ay, bx_, by_ = map(pcbnew.ToMM, (a_.x, a_.y, b_.x, b_.y))
                    dx, dy = bx_ - ax, by_ - ay
                    L = dx * dx + dy * dy or 1e-9
                    tt = max(0, min(1, ((x - ax) * dx + (y - ay) * dy) / L))
                    if math.hypot(ax + tt * dx - x, ay + tt * dy - y) < pcbnew.ToMM(t.GetWidth()) / 2 + 0.75:
                        return False
            return 1.5 < x < W - 1.5 and 1.5 < y < H - 1.5

        n = 0
        for fp in self.board.GetFootprints():
            c = fp.GetPosition()
            cx, cy = pcbnew.ToMM(c.x), pcbnew.ToMM(c.y)
            for pd in fp.Pads():
                if pd.GetNetname() != net or pd.GetAttribute() != pcbnew.PAD_ATTRIB_SMD:
                    continue
                q = pd.GetPosition()
                px, py = pcbnew.ToMM(q.x), pcbnew.ToMM(q.y)
                bb = pd.GetBoundingBox()
                sz = max(pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight()))
                ang0 = math.atan2(py - cy, px - cx) if (abs(px - cx) + abs(py - cy)) > 0.05 else 0
                done = False
                for k in range(16):
                    ang = ang0 + ((k + 1) // 2) * (math.pi / 8) * (1 if k % 2 else -1)
                    for dist in (sz / 2 + 0.9, sz / 2 + 1.4):
                        vx, vy = px + dist * math.cos(ang), py + dist * math.sin(ang)
                        if free(vx, vy):
                            self.track([(px, py), (vx, vy)], 0.4, pcbnew.F_Cu, net)
                            self.via(vx, vy, net, 0.8, 0.4)
                            n += 1
                            done = True
                            break
                    if done:
                        break
                if not done:
                    print('no fanout via for', fp.GetReference(), pd.GetNumber())
        return n

    def fill(self):
        f = pcbnew.ZONE_FILLER(self.board)
        f.Fill(self.board.Zones())

    def save(self, path):
        self.board.SetFileName(path)
        pcbnew.SaveBoard(path, self.board)
