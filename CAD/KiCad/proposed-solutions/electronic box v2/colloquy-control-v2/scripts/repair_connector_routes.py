"""Repair the v2 J5 connector escapes after the two-stage autorouter run.

Use KiCad's Python interpreter (pcbnew and NumPy). Input is a native board and
its strict KiCad JSON DRC report, before the final net-name/zone finishing step.
The search uses 0.1 mm cells, 0.3 mm traces, 0.8/0.4 mm vias and 0.26 mm
clearance. Rounded-corner board dimensions and J5 assignments are v2-specific.
This is a conservative raster routing aid, not a replacement for KiCad DRC.
Always run native DRC on the separate output before accepting it.

Example:
  python repair_connector_routes.py placed-and-routed.kicad_pcb repaired.kicad_pcb \
      --drc-report routing-drc.json

The companion project must be present beside the input so its stricter rules
are retained. No project runtime modules are imported and no hardware is used.
"""

from pathlib import Path
import argparse
import heapq
import math
import time
import json
import re
import sys

import pcbnew
import numpy as np

STEP = 0.1
X0, Y0, NX, NY = 44.0, 52.16, 2101, 2971
CLEAR, WIDTH, VIA, DRILL = 0.26, 0.3, 0.8, 0.4
X = X0 + np.arange(NX) * STEP
Y = Y0 + np.arange(NY) * STEP


def xy(v):
    return (pcbnew.ToMM(v.x), pcbnew.ToMM(v.y))


def vec(p):
    return pcbnew.VECTOR2I(pcbnew.FromMM(float(p[0])), pcbnew.FromMM(float(p[1])))


def layers(obj):
    return [i for i, k in enumerate((pcbnew.F_Cu, pcbnew.B_Cu)) if obj.IsOnLayer(k)]


def region(ax0, ay0, ax1, ay1):
    ix0 = max(0, int(math.floor((ax0 - X0) / STEP)))
    ix1 = min(NX, int(math.ceil((ax1 - X0) / STEP)) + 1)
    iy0 = max(0, int(math.floor((ay0 - Y0) / STEP)))
    iy1 = min(NY, int(math.ceil((ay1 - Y0) / STEP)) + 1)
    return ix0, iy0, ix1, iy1


def capsule(mask, lays, a, b, r):
    ix0, iy0, ix1, iy1 = region(
        min(a[0], b[0]) - r,
        min(a[1], b[1]) - r,
        max(a[0], b[0]) + r,
        max(a[1], b[1]) + r,
    )
    if ix0 >= ix1 or iy0 >= iy1:
        return
    xx = X[ix0:ix1][None, :]
    yy = Y[iy0:iy1][:, None]
    dx = b[0] - a[0]
    dy = b[1] - a[1]
    d = dx * dx + dy * dy
    t = np.clip(((xx - a[0]) * dx + (yy - a[1]) * dy) / d, 0, 1) if d else 0
    hit = (xx - a[0] - t * dx) ** 2 + (yy - a[1] - t * dy) ** 2 <= r * r
    for l in lays:
        mask[l, iy0:iy1, ix0:ix1] |= hit


def rectangle(mask, lays, box, margin):
    ax0, ay0, ax1, ay1 = box
    ix0, iy0, ix1, iy1 = region(ax0 - margin, ay0 - margin, ax1 + margin, ay1 + margin)
    if ix0 >= ix1 or iy0 >= iy1:
        return
    xx = X[ix0:ix1][None, :]
    yy = Y[iy0:iy1][:, None]
    dx = np.maximum(np.maximum(ax0 - xx, 0), xx - ax1)
    dy = np.maximum(np.maximum(ay0 - yy, 0), yy - ay1)
    hit = dx * dx + dy * dy <= margin * margin
    for l in lays:
        mask[l, iy0:iy1, ix0:ix1] |= hit


def mark_pad(mask, p, margin, lays=None):
    lays = layers(p) if lays is None else lays
    a = xy(p.GetPosition())
    s = xy(p.GetSize())
    shape = p.GetShape()
    ang = math.radians(p.GetOrientationDegrees())
    if shape in (pcbnew.PAD_SHAPE_CIRCLE, pcbnew.PAD_SHAPE_OVAL):
        length = abs(s[0] - s[1]) / 2
        r = min(s) / 2 + margin
        vx, vy = (
            (math.cos(ang) * length, -math.sin(ang) * length)
            if s[0] >= s[1]
            else (math.sin(ang) * length, math.cos(ang) * length)
        )
        capsule(mask, lays, (a[0] - vx, a[1] - vy), (a[0] + vx, a[1] + vy), r)
    else:
        box = p.GetBoundingBox()
        pos = xy(box.GetPosition())
        size = xy(box.GetSize())
        rectangle(
            mask, lays, (pos[0], pos[1], pos[0] + size[0], pos[1] + size[1]), margin
        )


def build_masks(b, net, startpad):
    obstacle = np.zeros((2, NY, NX), dtype=np.bool_)
    via = np.zeros_like(obstacle)
    goal = np.zeros_like(obstacle)
    xx = X[None, :]
    yy = Y[:, None]
    # Board boundary plus rounded corners, inset by copper-edge rule and radius.
    inside = (xx >= 44.7) & (xx <= 253.3) & (yy >= 52.86) & (yy <= 348.46)
    for cx, cy, cond in [
        (49, 57.16, (xx < 49) & (yy < 57.16)),
        (249, 57.16, (xx > 249) & (yy < 57.16)),
        (49, 344.16, (xx < 49) & (yy > 344.16)),
        (249, 344.16, (xx > 249) & (yy > 344.16)),
    ]:
        inside &= ~cond | ((xx - cx) ** 2 + (yy - cy) ** 2 < 4.3**2)
    obstacle[:, ~inside] = True
    via[:, ~inside] = True
    for f in b.GetFootprints():
        for p in f.Pads():
            same = p.GetNetname() == net
            if not same:
                mark_pad(obstacle, p, WIDTH / 2 + CLEAR)
                mark_pad(via, p, VIA / 2 + CLEAR, [0, 1])
            elif p.m_Uuid.AsString() != startpad.m_Uuid.AsString():
                mark_pad(goal, p, -0.05)
            drill = xy(p.GetDrillSize())
            if max(drill) > 0:
                capsule(
                    via,
                    [0, 1],
                    xy(p.GetPosition()),
                    xy(p.GetPosition()),
                    max(drill) / 2 + DRILL / 2 + 0.28,
                )
    for t in b.GetTracks():
        same = t.GetNetname() == net
        a = xy(t.GetStart())
        c = xy(t.GetEnd())
        r = (
            pcbnew.ToMM(
                t.GetWidth(pcbnew.F_Cu)
                if isinstance(t, pcbnew.PCB_VIA)
                else t.GetWidth()
            )
            / 2
        )
        lays = layers(t)
        if same:
            capsule(goal, lays, a, c, max(0.03, r - 0.03))
        else:
            capsule(obstacle, lays, a, c, r + WIDTH / 2 + CLEAR)
            capsule(via, [0, 1], a, c, r + VIA / 2 + CLEAR)
        if isinstance(t, pcbnew.PCB_VIA):
            capsule(
                via, [0, 1], a, a, pcbnew.ToMM(t.GetDrillValue()) / 2 + DRILL / 2 + 0.28
            )
    for z in b.Zones():
        if z.GetIsRuleArea():
            box = z.GetBoundingBox()
            a = xy(box.GetPosition())
            s = xy(box.GetSize())
            rectangle(
                obstacle, [0, 1], (*a, a[0] + s[0], a[1] + s[1]), WIDTH / 2 + CLEAR
            )
            rectangle(via, [0, 1], (*a, a[0] + s[0], a[1] + s[1]), VIA / 2 + CLEAR)
    return obstacle, via, goal


def search(b, net, startpad):
    a = xy(startpad.GetPosition())
    sx = round((a[0] - X0) / STEP)
    sy = round((a[1] - Y0) / STEP)
    goalpads = [
        p
        for f in b.GetFootprints()
        for p in f.Pads()
        if p.GetNetname() == net and p.m_Uuid.AsString() != startpad.m_Uuid.AsString()
    ]
    dest = min([xy(p.GetPosition()) for p in goalpads], key=lambda c: math.dist(a, c))
    tx = (dest[0] - X0) / STEP
    ty = (dest[1] - Y0) / STEP
    obstacle, viamask, goalmask = build_masks(b, net, startpad)

    def ident(x, y, l):
        return (l * NY + y) * NX + x

    def coord(k):
        l, rem = divmod(k, NX * NY)
        y, x = divmod(rem, NX)
        return x, y, l

    def heur(x, y):
        return int(math.hypot(x - tx, y - ty) * 110)

    dist = np.full((2, NY, NX), 2147483647, dtype=np.int32)
    parent = {}
    heap = []
    for l in layers(startpad):
        if obstacle[l, sy, sx]:
            print("START BLOCKED", net, l, a, flush=True)
            continue
        k = ident(sx, sy, l)
        dist[l, sy, sx] = 0
        heapq.heappush(heap, (heur(sx, sy), 0, k))
        parent[k] = None
    moves = [
        (-1, 0, 100),
        (1, 0, 100),
        (0, -1, 100),
        (0, 1, 100),
        (-1, -1, 141),
        (1, 1, 141),
        (-1, 1, 141),
        (1, -1, 141),
    ]
    count = 0
    t0 = time.time()
    while heap:
        _, cost, k = heapq.heappop(heap)
        x, y, l = coord(k)
        if cost != dist[l, y, x]:
            continue
        count += 1
        if goalmask[l, y, x]:
            route = []
            while k is not None:
                route.append(coord(k))
                k = parent[k]
            route.reverse()
            print(
                "FOUND",
                net,
                len(route),
                "nodes",
                count,
                "seconds",
                round(time.time() - t0, 2),
                flush=True,
            )
            return route
        for dx, dy, stepcost in moves:
            nx, ny = x + dx, y + dy
            if nx < 0 or nx >= NX or ny < 0 or ny >= NY or obstacle[l, ny, nx]:
                continue
            if dx and dy and (obstacle[l, y, nx] or obstacle[l, ny, x]):
                continue
            nc = cost + stepcost
            if nc < dist[l, ny, nx]:
                nk = ident(nx, ny, l)
                dist[l, ny, nx] = nc
                parent[nk] = k
                heapq.heappush(heap, (nc + heur(nx, ny), nc, nk))
        nl = 1 - l
        if not viamask[0, y, x] and not viamask[1, y, x] and not obstacle[nl, y, x]:
            nc = cost + 5000
            if nc < dist[nl, y, x]:
                nk = ident(x, y, nl)
                dist[nl, y, x] = nc
                parent[nk] = k
                heapq.heappush(heap, (nc + heur(x, y), nc, nk))
        if count % 200000 == 0:
            print(
                "SEARCH",
                net,
                count,
                len(heap),
                "seconds",
                round(time.time() - t0),
                flush=True,
            )
    print("NO PATH", net, count, flush=True)
    return None


def insert(b, net, startpad, route):
    n = b.FindNet(net)

    def point(q):
        return (X[q[0]], Y[q[1]])

    def track(a, c, l):
        if math.dist(a, c) < 1e-6:
            return
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(vec(a))
        t.SetEnd(vec(c))
        t.SetWidth(pcbnew.FromMM(WIDTH))
        t.SetLayer((pcbnew.F_Cu, pcbnew.B_Cu)[l])
        t.SetNet(n)
        b.Add(t)

    track(xy(startpad.GetPosition()), point(route[0]), route[0][2])
    anchor = route[0]
    last = route[0]
    direction = None
    for q in route[1:]:
        if q[2] != last[2]:
            track(point(anchor), point(last), last[2])
            v = pcbnew.PCB_VIA(b)
            v.SetPosition(vec(point(q)))
            v.SetWidth(pcbnew.FromMM(VIA))
            v.SetDrill(pcbnew.FromMM(DRILL))
            v.SetViaType(pcbnew.VIATYPE_THROUGH)
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
            v.SetNet(n)
            b.Add(v)
            anchor = q
            last = q
            direction = None
            continue
        d = (q[0] - last[0], q[1] - last[1])
        if direction is not None and d != direction:
            track(point(anchor), point(last), last[2])
            anchor = last
        direction = d
        last = q
    track(point(anchor), point(last), last[2])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--drc-report", type=Path, required=True)
    args = parser.parse_args()
    source, output = args.board.resolve(), args.output.resolve()
    if source == output:
        parser.error("Use a separate output path to retain the original routing")
    source_project = source.with_suffix(".kicad_pro")
    if not source_project.exists():
        parser.error("Input companion .kicad_pro is required to preserve design rules")
    project_bytes = source_project.read_bytes()
    report = json.loads(args.drc_report.read_text(encoding="utf-8"))
    incomplete = set()
    for violation in report.get("unconnected_items", []):
        for item in violation["items"]:
            match = re.search(r"\[([^]]+)\]", item["description"])
            if match:
                incomplete.add(match.group(1))
    order = [
        ("female1/spare2", "2"),
        ("dxl_data", "14"),
        ("female1/photosensor", "5"),
        ("female1/spare5", "10"),
    ]
    unknown = incomplete - {net for net, _ in order}
    if unknown:
        parser.error(
            f"This local repair does not handle other incomplete nets: {unknown}"
        )
    board = pcbnew.LoadBoard(str(source))
    tracks_by_id = {t.m_Uuid.AsString(): t for t in board.GetTracks()}
    for violation in report.get("violations", []):
        if (
            violation["type"] != "clearance"
            or "actual 0.24" not in violation["description"]
            or not any("of JS" in i["description"] for i in violation["items"])
        ):
            continue
        for item in violation["items"]:
            track = tracks_by_id.get(item["uuid"])
            if track is not None and not isinstance(track, pcbnew.PCB_VIA):
                if track.GetWidth() == pcbnew.FromMM(0.3):
                    track.SetWidth(pcbnew.FromMM(0.28))
    # Route the long photosensor escape before spare5: reversing these two
    # can enclose the photosensor pad between copper on the two layers.
    for track in list(board.GetTracks()):
        if track.GetNetname() in incomplete & {"female1/spare2", "female1/spare5"}:
            board.Delete(track)
    board.BuildConnectivity()
    failed = []
    for net, pin in order:
        if net not in incomplete:
            continue
        start = next(
            p
            for f in board.GetFootprints()
            if f.GetReference() == "J5"
            for p in f.Pads()
            if p.GetNumber() == pin
        )
        route = search(board, net, start)
        if route is None:
            failed.append(net)
            continue
        insert(board, net, start, route)
        board.BuildConnectivity()
    for track in board.GetTracks():
        if track.GetNetname() in {"GND", "+5V", "+12V"}:
            track.SetLocked(True)
    output.parent.mkdir(parents=True, exist_ok=True)
    pcbnew.SaveBoard(str(output), board)
    output.with_suffix(".kicad_pro").write_bytes(project_bytes)
    print(f"Saved {output}; native KiCad DRC is required before accepting it.")
    if failed:
        print(f"Unresolved routes: {failed}")
        sys.exit(2)


if __name__ == "__main__":
    main()
