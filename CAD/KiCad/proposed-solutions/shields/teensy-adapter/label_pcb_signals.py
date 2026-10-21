"""Add GPIO/signal captions on B.Silkscreen, readable from the physical back.

Run using KiCad Python after any script that regenerates operating labels.
Only board text may change. Existing traces, zones, nets, pads and placements
are compared in KiCad's canonical serialization before saving the result.
"""
from pathlib import Path
import hashlib
import json
import sys
import tempfile

import pcbnew as p

from signal_names import gpio_signals

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'scripts'))
from schematic_support import parse

GROUP = 'teensy-gpio-signal-labels'


def xy(x, y):
    return p.VECTOR2I(p.FromMM(x), p.FromMM(y))


def box(item, clearance=0):
    b=item.GetBoundingBox()
    gap=p.FromMM(clearance)
    return b.GetLeft()-gap,b.GetTop()-gap,b.GetRight()+gap,b.GetBottom()+gap


def overlaps(a,b):
    return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]


def without_text(path):
    return [item for item in parse(path.read_text(encoding='utf-8'))
            if not isinstance(item,list) or item[0] not in ('gr_text','group')]


def main():
    path=HERE/'teensy-adapter.kicad_pcb'
    board=p.LoadBoard(str(path))
    original_hash=hashlib.sha256(path.read_bytes()).hexdigest()
    parts={part['ref']:part for part in json.loads((HERE/'circuit.json').read_text())['components']}
    signals=gpio_signals(parts)
    # A named group makes rerunning this script replace only its own labels.
    for group in list(board.Groups()):
        if group.GetName()==GROUP:
            for item in list(group.GetItems()):
                board.Remove(item)
            board.Remove(group)
    group=p.PCB_GROUP(board)
    group.SetName(GROUP)
    board.Add(group)
    refs={f.GetReference():f for f in board.GetFootprints()}
    obstacles=[]
    for fp in board.GetFootprints():
        obstacles += [box(pad,.22) for pad in fp.Pads() if pad.IsOnLayer(p.B_Mask)]
        obstacles += [box(item,.15) for item in fp.GraphicalItems() if item.GetLayer()==p.B_SilkS]
        if fp.Reference().IsVisible() and fp.Reference().GetLayer()==p.B_SilkS:
            obstacles.append(box(fp.Reference(),.15))
    obstacles += [box(item,.15) for item in board.GetDrawings() if item.GetLayer()==p.B_SilkS]
    added=[]

    def label(caption, x, y, lane=None):
        item=p.PCB_TEXT(board)
        item.SetText(caption)
        item.SetLayer(p.B_SilkS)
        item.SetMirrored(True)
        item.SetTextThickness(p.FromMM(.12))
        item.SetPosition(xy(x,y))
        for width,height in ((1,1),(.95,.95),(.9,.9),(.85,.85),(.8,.8),(.72,.8)):
            item.SetTextSize(xy(width,height))
            bounds=box(item,.1)
            if lane and not (p.FromMM(lane[0])<=bounds[0] and bounds[2]<=p.FromMM(lane[1])):
                continue
            if not any(overlaps(bounds,other) for other in obstacles):
                break
        else:
            raise ValueError('No legible clear location for '+caption)
        board.Add(item)
        group.AddItem(item)
        obstacles.append(bounds)
        return item

    with tempfile.TemporaryDirectory(prefix='teensy-silk-') as tmp:
        before=Path(tmp)/'before.kicad_pcb'
        p.SaveBoard(str(before),board)
        for socket, x, lane in [('JT1',151.9,(145.2,158.5)),('JT2',183.57,(176.74,190.4))]:
            for pad in sorted(refs[socket].Pads(),key=lambda pad:int(pad.GetNumber())):
                pin=pad.GetNumber()
                gpio=parts[socket]['pin_names'][pin]
                if gpio in signals:
                    caption=gpio+' '+signals[gpio]
                elif gpio.isdigit():
                    caption=gpio+(' unused' if parts[socket]['pins'][pin] is None else ' spare')
                else:
                    caption=gpio
                item=label(caption,x,p.ToMM(pad.GetPosition().y),lane)
                added.append(dict(socket=socket,contact=pin,gpio=gpio,caption=caption,
                                  position_mm=[x,p.ToMM(pad.GetPosition().y)],
                                  text_height_mm=p.ToMM(item.GetTextSize().y)))
        label('GPIO / SIGNAL',167.62,54.85)
        label('f1-f3 = female 1-3',167.62,121.2)
        label('m1-m2 = male 1-2',167.62,123.7)
        after=Path(tmp)/'after.kicad_pcb'
        p.SaveBoard(str(after),board)
        assert without_text(before)==without_text(after), 'Non-text PCB data changed'
        p.SaveBoard(str(path),board)
    report=dict(back_silkscreen_captions=len(added),functional_signals=len(signals),
                all_text_mirrored_for_back=True,minimum_text_height_mm=min(r['text_height_mm'] for r in added),
                copper_pads_nets_zones_and_placement_unchanged=True,
                source_sha256_before=original_hash,source_sha256_after=hashlib.sha256(path.read_bytes()).hexdigest(),
                pins=added)
    reports=HERE/'reports'
    (reports/'gpio-silkscreen.json').write_text(json.dumps(report,indent=2)+'\n')
    print(f'{len(added)} back-face contact captions; {len(signals)} functional signals; non-text board data unchanged')


if __name__=='__main__':
    main()
