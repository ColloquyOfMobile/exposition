"""numba-compiled A* used by router.Router (same semantics as Router.astar)."""
import heapq
import numpy as np
from numba import njit

STEPS = np.array([(1, 0), (-1, 0), (0, 1), (0, -1), (1, 1), (1, -1), (-1, 1), (-1, -1)], dtype=np.int64)




@njit(cache=True)
def astar_core(src, tgt, pas, vok, pen, use_pen, hmap, nx, N, ix0, iy0, ix1, iy1,
               via_cost, b_cost, turn, hw, max_nodes):
    # hmap: per-cell Euclidean distance (cells) to the nearest target cell, admissible
    gsc = np.full(2 * N, np.inf, dtype=np.float64)
    came = np.full(2 * N, -1, dtype=np.int64)
    dirs = np.full(2 * N, -1, dtype=np.int8)
    heap = [(0.0, np.int64(0))]
    heap.pop()
    for s in np.flatnonzero(src):
        if not pas[s]:
            continue
        gsc[s] = 0.0
        rem = s % N
        iy = rem // nx
        ix = rem % nx
        heapq.heappush(heap, (hw * hmap[rem], np.int64(s)))
    expanded = 0
    found = -1
    while len(heap) > 0:
        f, cur = heapq.heappop(heap)
        gc = gsc[cur]
        L = cur // N
        rem = cur % N
        iy = rem // nx
        ix = rem % nx
        hcur = hmap[rem]
        if f > gc + hw * hcur + 1e-4:
            continue
        if tgt[cur]:
            found = cur
            break
        expanded += 1
        if expanded > max_nodes:
            break
        pd = dirs[cur]
        lf = 1.0 if L == 0 else b_cost
        for k in range(8):
            sx = STEPS[k, 0]
            sy = STEPS[k, 1]
            jx = ix + sx
            jy = iy + sy
            if jx < ix0 or jx > ix1 or jy < iy0 or jy > iy1:
                continue
            nxt = L * N + jy * nx + jx
            if not pas[nxt]:
                continue
            if sy == 0:
                pref = 1.0 if L == 0 else 1.15
                c = 1.0
            elif sx == 0:
                pref = 1.0 if L == 1 else 1.15
                c = 1.0
            else:
                pref = 1.05
                c = 1.4142
            ng = gc + c * pref * lf
            if pd != -1 and pd != k:
                ng += turn
            if use_pen:
                ng += pen[nxt]
            if ng < gsc[nxt]:
                gsc[nxt] = ng
                came[nxt] = cur
                dirs[nxt] = k
                heapq.heappush(heap, (ng + hw * hmap[jy * nx + jx], np.int64(nxt)))
        if vok[rem]:
            nxt = (1 - L) * N + rem
            if pas[nxt]:
                ng = gc + via_cost
                if use_pen:
                    ng += pen[nxt] * 4
                if ng < gsc[nxt]:
                    gsc[nxt] = ng
                    came[nxt] = cur
                    dirs[nxt] = -1
                    heapq.heappush(heap, (ng + hw * hcur, np.int64(nxt)))
    if found < 0:
        return np.empty(0, dtype=np.int64)
    n = 0
    c2 = found
    while c2 != -1:
        n += 1
        c2 = came[c2]
    out = np.empty(n, dtype=np.int64)
    c2 = found
    i = n - 1
    while c2 != -1:
        out[i] = c2
        i -= 1
        c2 = came[c2]
    return out
