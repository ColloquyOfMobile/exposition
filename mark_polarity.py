"""Print + and - beside the pads of every polarized part on the boards to make.

Run with KiCad Python: & 'C:/Program Files/KiCad/9.0/bin/python.exe' mark_polarity.py

So that a board can be checked by eye once it is fitted, whoever fitted it:
each LED, diode and electrolytic gets a "+" beside its positive pad and a
"-" beside its negative one, on the silkscreen of the side it sits on. The
marks are user texts inside the footprint, so they move with the part.

Which pad is which is KiCad's footprint convention, the one
`CAD/KiCad/assembly-parts.json` states for every such part it orders: LEDs
and diodes have pad 1 = cathode, electrolytics pad 1 = positive. A
footprint family missing from POLARITY gets no marks; add it there.

Run it again whenever a board is regenerated: earlier marks are removed
first. Each sign goes on the pad's axis, just past the pad and the part's
own outline, or failing that beside the pad, wherever it clears every pad
opening, via, silkscreen item and the board edge; a sign with no clear
place stops the run before anything is saved. Then re-export with
`export_jlcpcb.py`. `pytest_tests/hardware/test_polarity_marks.py` holds
the boards to it.
"""
import json
import sys
from pathlib import Path

import pcbnew as p

ROOT = Path(__file__).resolve().parent
KICAD = ROOT / "CAD/KiCad"

# Footprint name prefix -> the signs of pads 1 and 2.
POLARITY = {"LED_": ("-", "+"), "D_": ("-", "+"), "CP_": ("+", "-")}
SIZE_MM = 1.0
THICKNESS_MM = 0.15
PAD_GAP_MM = 0.25
SILK_GAP_MM = 0.15
EDGE_GAP_MM = 0.3
STEP_MM = 0.05
FURTHEST_MM = 3.0


def signs_of(footprint):
    name = str(footprint.GetFPID().GetLibItemName())
    for prefix, signs in POLARITY.items():
        if name.startswith(prefix):
            return signs
    return None


def box(item, gap_mm):
    # A text's own box is its whole character cell; a "-" inks a sliver of it.
    b = item.GetEffectiveTextShape().BBox() if isinstance(item, p.PCB_TEXT) else item.GetBoundingBox()
    g = p.FromMM(gap_mm)
    return (b.GetLeft() - g, b.GetTop() - g, b.GetRight() + g, b.GetBottom() + g)


def overlaps(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def inside(a, b):
    return b[0] <= a[0] and b[1] <= a[1] and a[2] <= b[2] and a[3] <= b[3]


def is_mark(item):
    return isinstance(item, p.PCB_TEXT) and item.GetText() in {"+", "-"} \
        and item.GetLayer() in (p.F_SilkS, p.B_SilkS)


def obstacles(board, silk, mask):
    """Everything a sign must clear, as boxes already widened by its gap."""
    found = []
    for item in board.GetDrawings():
        if item.GetLayer() == silk:
            found.append(box(item, SILK_GAP_MM))
    for via in board.GetTracks():
        if isinstance(via, p.PCB_VIA):
            found.append(box(via, PAD_GAP_MM))
    for footprint in board.GetFootprints():
        for pad in footprint.Pads():
            if pad.IsOnLayer(mask) or pad.GetAttribute() == p.PAD_ATTRIB_NPTH:
                found.append(box(pad, PAD_GAP_MM))
        for item in footprint.GraphicalItems():
            if item.GetLayer() == silk and not is_mark(item):
                found.append(box(item, SILK_GAP_MM))
        for field in footprint.GetFields():
            if field.IsVisible() and field.GetLayer() == silk:
                found.append(box(field, SILK_GAP_MM))
    return found


def place(mark, footprint, pad, blocked, limit):
    """Step the sign away from its pad until it lands somewhere clear."""
    centre = footprint.GetPosition()
    at = pad.GetPosition()
    dx, dy = at.x - centre.x, at.y - centre.y
    length = (dx * dx + dy * dy) ** 0.5
    axis = (dx / length, dy / length)
    # Along the axis first, then either side of the pad, then the corners.
    directions = [axis, (-axis[1], axis[0]), (axis[1], -axis[0])]
    directions += [((axis[0] + s[0]) / 2 ** 0.5, (axis[1] + s[1]) / 2 ** 0.5) for s in directions[1:]]
    for ux, uy in directions:
        distance = 0.0
        while distance <= FURTHEST_MM + p.ToMM(max(pad.GetSize().x, pad.GetSize().y)):
            mark.SetPosition(p.VECTOR2I(at.x + int(p.FromMM(distance) * ux), at.y + int(p.FromMM(distance) * uy)))
            here = box(mark, 0)
            if inside(here, limit) and not any(overlaps(here, o) for o in blocked):
                return here
            distance += STEP_MM
    raise ValueError(f"{footprint.GetReference()}: no clear place for '{mark.GetText()}' beside pad {pad.GetNumber()}")


def mark(board):
    edges = board.GetBoardEdgesBoundingBox()
    gap = p.FromMM(EDGE_GAP_MM)
    limit = (edges.GetLeft() + gap, edges.GetTop() + gap, edges.GetRight() - gap, edges.GetBottom() - gap)
    polarized = sorted((f for f in board.GetFootprints() if signs_of(f)), key=lambda f: f.GetReference())
    for footprint in polarized:
        for item in list(footprint.GraphicalItems()):
            if is_mark(item):
                footprint.Remove(item)
    placed = []
    blocked = {}
    for footprint in polarized:
        back = footprint.GetLayer() == p.B_Cu
        silk, mask = (p.B_SilkS, p.B_Mask) if back else (p.F_SilkS, p.F_Mask)
        if silk not in blocked:
            blocked[silk] = obstacles(board, silk, mask)
        pads = {pad.GetNumber(): pad for pad in footprint.Pads()}
        for number, sign in zip(("1", "2"), signs_of(footprint)):
            text = p.PCB_TEXT(footprint)
            text.SetText(sign)
            text.SetLayer(silk)
            text.SetMirrored(back)
            text.SetTextSize(p.VECTOR2I(p.FromMM(SIZE_MM), p.FromMM(SIZE_MM)))
            text.SetTextThickness(p.FromMM(THICKNESS_MM))
            text.SetTextAngle(p.EDA_ANGLE(0, p.DEGREES_T))
            here = place(text, footprint, pads[number], blocked[silk], limit)
            blocked[silk].append(tuple(v + s * p.FromMM(SILK_GAP_MM) for v, s in zip(here, (-1, -1, 1, 1))))
            footprint.Add(text)
            x, y = (round(p.ToMM(v), 2) for v in text.GetPosition())
            placed.append(f"{footprint.GetReference()} pad {number} '{sign}' at ({x}, {y})")
    return placed


def main():
    boards = json.loads((KICAD / "production/manifest.json").read_text())["boards"]
    only = set(sys.argv[1:])
    for entry in boards:
        if only and entry["id"] not in only:
            continue
        path = KICAD / entry["source"]
        board = p.LoadBoard(str(path))
        placed = mark(board)
        if placed:
            # The project file is left alone: nothing here is a setting.
            p.SaveBoard(str(path), board, True)
        print(f'{entry["id"]}: {len(placed)} marks', *placed, sep="\n    ", flush=True)


if __name__ == "__main__":
    main()
