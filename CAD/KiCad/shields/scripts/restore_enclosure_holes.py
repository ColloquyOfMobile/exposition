"""Restore the four original enclosure cutouts, relative to the board outline.

Only the four 8 mm circles are copied, not the older U2D2 mounting pattern.
Run with KiCad Python. Refill copper and run native DRC after this operation.
"""
from pathlib import Path
import hashlib
import json

import pcbnew as p

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT.parent / 'archive1/electronic box/electronic box.kicad_pcb'
TARGET = ROOT / 'backplane'


def mm_point(point):
    return tuple(round(p.ToMM(v), 6) for v in point)


def outline_bounds(board):
    points = []
    for shape in board.GetDrawings():
        if shape.GetLayer() != p.Edge_Cuts or shape.GetShape() == p.SHAPE_T_CIRCLE:
            continue
        points.extend([mm_point(shape.GetStart()), mm_point(shape.GetEnd())])
    return [min(x for x, _ in points), min(y for _, y in points),
            max(x for x, _ in points), max(y for _, y in points)]


def main():
    old = p.LoadBoard(str(SOURCE))
    source_bounds = outline_bounds(old)
    circles = [shape for shape in old.GetDrawings()
               if shape.GetLayer() == p.Edge_Cuts and shape.GetShape() == p.SHAPE_T_CIRCLE
               and abs(p.ToMM(shape.GetRadius()) - 4) < 0.000001]
    assert len(circles) == 4, 'Expected exactly four original 8 mm enclosure holes'
    source_centers = sorted(mm_point(shape.GetStart()) for shape in circles)
    assert source_centers == [(20, 150), (105, 20), (105, 150), (190, 150)]
    report = dict(source=str(SOURCE.relative_to(ROOT.parent)),
                  source_sha256=hashlib.sha256(SOURCE.read_bytes()).hexdigest(),
                  original_outline_bounds_mm=source_bounds, diameter_mm=8,
                  original_centers_mm=source_centers, targets={})
    for filename in ['backplane.kicad_pcb', 'backplane-placed.kicad_pcb']:
        path = TARGET / filename
        board = p.LoadBoard(str(path))
        bounds = outline_bounds(board)
        assert [round(bounds[i+2]-bounds[i], 6) for i in (0, 1)] == [210, 297]
        assert [source_bounds[i+2]-source_bounds[i] for i in (0, 1)] == [210, 297]
        dx, dy = bounds[0]-source_bounds[0], bounds[1]-source_bounds[1]
        centers = [(round(x+dx, 6), round(y+dy, 6)) for x, y in source_centers]
        for center in centers:
            found = [shape for shape in board.GetDrawings()
                     if shape.GetLayer() == p.Edge_Cuts and shape.GetShape() == p.SHAPE_T_CIRCLE
                     and mm_point(shape.GetStart()) == center]
            if found:
                assert len(found) == 1 and abs(p.ToMM(found[0].GetRadius())-4) < 0.000001
                continue
            hole = p.PCB_SHAPE(board)
            hole.SetShape(p.SHAPE_T_CIRCLE)
            hole.SetLayer(p.Edge_Cuts)
            hole.SetStart(p.VECTOR2I(p.FromMM(center[0]), p.FromMM(center[1])))
            hole.SetEnd(p.VECTOR2I(p.FromMM(center[0]+4), p.FromMM(center[1])))
            hole.SetWidth(p.FromMM(.1))
            board.Add(hole)
        # The centre enclosure hole overlaps the later L3 probe location.
        # Relocate this test point only; native routing/DRC must follow.
        probe = next(fp for fp in board.GetFootprints() if fp.GetReference() == 'TPL3')
        probe.SetPosition(p.VECTOR2I(p.FromMM(141), p.FromMM(206)))
        for footprint in board.GetFootprints():
            if footprint.GetReference() in ('TPL3', 'TPV3'):
                # The existing L3/T3 captions identify these probe pads.
                footprint.Reference().SetVisible(False)
        for item in board.GetDrawings():
            if item.GetClass() != 'PCB_TEXT':
                continue
            if item.GetText() == 'L3':
                item.SetPosition(p.VECTOR2I(p.FromMM(141), p.FromMM(209.5)))
            elif item.GetText() == 'T = TONE / L = LINE':
                item.SetPosition(p.VECTOR2I(p.FromMM(145), p.FromMM(187.8)))
        # Same routed circular cutouts as the original, without adding schematic parts.
        p.ZONE_FILLER(board).Fill(board.Zones())
        p.SaveBoard(str(path), board)
        report['targets'][filename] = dict(outline_bounds_mm=bounds,
            translation_mm=[dx, dy], centers_mm=centers,
            relocated_test_point=dict(reference='TPL3', center_mm=[141, 206],
                reason='Previous probe pad overlapped the centre enclosure hole'),
            fabrication='Four diameter-8 mm routed circular cutouts on Edge.Cuts',
            sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (TARGET/'enclosure-mounting.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
