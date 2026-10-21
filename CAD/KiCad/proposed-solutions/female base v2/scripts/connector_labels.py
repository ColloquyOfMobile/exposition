"""Readable connector names on both body PCBs, shared by in-place and full builds.

Run with KiCad Python to update only text on routed boards and placed checkpoints.
Coordinates are board millimetres; angles follow KiCad's text convention.
"""
from pathlib import Path
import re
import pcbnew as p

CAD = Path(__file__).resolve().parents[2]
# reference: (caption, centre X, centre Y, angle, text height)
LABELS = {
    'female-base-v2': {
        'J7': ('J7 HARNESS', 50, 38.8, 0, .9),
        'J2': ('J2 DXL MIRROR', 64.5, 51.3, 0, .95),
        'J4': ('J4 PHOTOSENSOR', 65.5, 61.6, 0, .85),
        'J5': ('J5 NEOPIXEL', 65.5, 79, 0, .95),
        'J3': ('J3 MICROPHONE', 36.5, 98.2, 0, .95),
        'J6': ('J6 SPEAKER', 69, 89.3, 90, .95),
    },
    'male-static-v2': {
        'J7': ('J7 HARNESS', 50, 38.8, 0, .9),
        'J3': ('J3 MICROPHONE', 33.5, 51.3, 0, .95),
        'J10': ('J10 STATE LED', 67.5, 51.3, 0, .9),
        'J11': ('J11 BAR NEOPIXEL', 67.5, 64.3, 0, .85),
        'J9': ('J9 PHOTOSENSOR A', 33.5, 78.4, 0, .85),
        'J8': ('J8 PHOTOSENSOR B', 33.5, 86.3, 0, .85),
        'J1': ('J1 PHOTOSENSOR C', 33.5, 96.3, 0, .85),
        'J4': ('J4 PHOTOSENSOR D', 33.5, 106.3, 0, .85),
        'J6': ('J6 SPEAKER', 62.2, 90.5, 90, .9),
        'J5': ('J5 BODY NEOPIXEL', 74.05, 98, 90, .8),
        'J2': ('J2 DXL BODY', 67.5, 102.3, 0, .9),
    },
}


def apply(board, stem):
    """Add names once and update them in place on subsequent runs."""
    labels = LABELS[stem]
    assert set(labels) == {f.GetReference() for f in board.GetFootprints()
                           if f.GetReference().startswith('J')}
    removed = []
    for item in list(board.GetDrawings()):
        if not isinstance(item, p.PCB_TEXT):
            continue
        if re.fullmatch(r'J\d+', item.GetText()) and item.GetLayer() in (p.F_SilkS, p.F_Fab):
            removed.append(item)
            board.Remove(item)
        elif item.GetText() == stem.upper() and item.GetLayer() == p.F_SilkS:
            item.SetPosition(p.VECTOR2I(p.FromMM(50), p.FromMM(41.2)))
    texts = {item.GetText(): item for item in board.GetDrawings()
             if isinstance(item, p.PCB_TEXT) and item.GetLayer() == p.F_SilkS}
    for caption, x, y, angle, size in labels.values():
        item = texts.get(caption)
        if item is None:
            item = p.PCB_TEXT(board)
            item.SetText(caption)
            board.Add(item)
        item.SetLayer(p.F_SilkS)
        item.SetPosition(p.VECTOR2I(p.FromMM(x), p.FromMM(y)))
        item.SetTextSize(p.VECTOR2I(p.FromMM(size), p.FromMM(size)))
        item.SetTextThickness(p.FromMM(.15))
        item.SetTextAngle(p.EDA_ANGLE(angle, p.DEGREES_T))
        item.SetHorizJustify(p.GR_TEXT_H_ALIGN_CENTER)
        item.SetVertJustify(p.GR_TEXT_V_ALIGN_CENTER)
        item.SetMirrored(False)
    return removed


def main():
    keep_alive = []
    for folder, stem in [('female base v2', 'female-base-v2'), ('male static v2', 'male-static-v2')]:
        for suffix in ('', '-placed'):
            path = CAD/folder/(stem+suffix+'.kicad_pcb')
            board = p.LoadBoard(str(path))
            keep_alive.append(board)
            keep_alive.extend(apply(board, stem))
            p.SaveBoard(str(path), board)
        print(stem, ':', len(LABELS[stem]), 'connector names added to front silkscreen')


if __name__ == '__main__':
    main()
