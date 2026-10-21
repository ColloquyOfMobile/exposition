"""Validate user-requested mechanical corrections with KiCad Python."""
import json
from pathlib import Path
import pcbnew as p

root = Path(__file__).resolve().parent
board = p.LoadBoard(str(root/'dfrobot-module.kicad_pcb'))
footprints = {f.GetReference():f for f in board.GetFootprints()}
# The drawn bounding box includes stroke width; dimensions use edge centrelines.
points = [point for d in board.GetDrawings() if d.GetLayer()==p.Edge_Cuts
          for point in (d.GetStart(),d.GetEnd())]
size = [p.ToMM(max(q.x for q in points)-min(q.x for q in points)),
        p.ToMM(max(q.y for q in points)-min(q.y for q in points))]
assert abs(size[0]-22) < .001 and abs(size[1]-34) < .001, size
pin6 = next(q for q in footprints['J2J3'].Pads() if q.GetNumber()=='6')
pin1 = next(q for q in footprints['J4'].Pads() if q.GetNumber()=='1')
assert pin6.GetPosition().x == pin1.GetPosition().x
holes = [next(iter(footprints[r].Pads())) for r in ('H1','H2')]
spacing = p.ToMM(abs(holes[1].GetPosition().x-holes[0].GetPosition().x))
assert abs(spacing-20.32)<.001
assert all(p.ToMM(q.GetSize().x)==3.6 for q in holes)
assert all(q.GetAttribute()==p.PAD_ATTRIB_SMD for q in footprints['J1'].Pads())
comments = [d.GetText() for d in board.GetDrawings() if isinstance(d,p.PCB_TEXT) and d.GetLayer()==p.Cmts_User]
assert len(comments)==2
result = {'outline_mm':size,'retained_mounting_centres_mm':spacing,
          'mounting_pad_diameter_mm':3.6,'j4_pin1_and_j2j3_pin6_x_mm':p.ToMM(pin1.GetPosition().x),
          'j1_all_pads_smd':True,'user_comments_preserved':len(comments),
          'known_reference_limitations':['3.2 mm mounting holes intersect side edges']}
(root/'validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
