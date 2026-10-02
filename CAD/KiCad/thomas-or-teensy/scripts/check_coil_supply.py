"""Confirm an actual +5V copper path to each coil outside the analog region."""
from pathlib import Path
from collections import deque
import math
import json
import pcbnew as p
from audit_copper import in_polygon,point
from finish_board import ANALOG

ROOT=Path(__file__).resolve().parents[1]
board=p.LoadBoard(str(ROOT/'thomas-or-teensy.kicad_pcb'));board.BuildConnectivity()
tracks=list(board.GetTracks());pads=[q for f in board.GetFootprints() for q in f.Pads()]
items={q.m_Uuid.AsString():q for q in tracks+pads};allowed={}
for uid,item in items.items():
    if item.GetNetname()!='+5V':continue
    if isinstance(item,p.PCB_TRACK) and not isinstance(item,p.PCB_VIA):
        a,b=point(item.GetStart()),point(item.GetEnd());n=max(1,math.ceil(math.dist(a,b)/.2))
        inside=any(in_polygon(a[0]+(b[0]-a[0])*i/n,a[1]+(b[1]-a[1])*i/n,ANALOG) for i in range(n+1))
    else:inside=in_polygon(*point(item.GetPosition()),ANALOG)
    if not inside:allowed[uid]=item
connectivity=board.GetConnectivity()
sources={q.m_Uuid.AsString() for q in pads if q.GetParentFootprint().GetReference()=='J2' and q.GetNetname()=='+5V'}
results={}
for ref in ['K1','K2','K3']:
    pad=next(q for q in pads if q.GetParentFootprint().GetReference()==ref and q.GetNumber()=='1')
    queue=deque([pad.m_Uuid.AsString()]);seen=set();found=False
    while queue:
        uid=queue.popleft()
        if uid in seen or uid not in allowed:continue
        seen.add(uid)
        if uid in sources:found=True;break
        item=allowed[uid]
        queue.extend(q.m_Uuid.AsString() for q in connectivity.GetConnectedTracks(item))
        queue.extend(q.m_Uuid.AsString() for q in connectivity.GetConnectedPads(item))
    results[ref]=found
report={'coil_supply_path_outside_analog':results,'all_passed':all(results.values()),'method':'Physical connectivity graph, excluding every +5V pad/via or sampled track centreline inside the AGND zone outline.'}
(ROOT/'reports/coil-supply-review.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
