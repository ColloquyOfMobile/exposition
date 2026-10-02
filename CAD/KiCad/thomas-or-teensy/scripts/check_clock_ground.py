"""Measure clock ground-plane coverage after filling; not an SI simulation."""
from pathlib import Path
import pcbnew as p,math,json
from audit_copper import in_polygon
from finish_board import ANALOG
root=Path(__file__).resolve().parents[1]
b=p.LoadBoard(str(root/'thomas-or-teensy.kicad_pcb'))
planes={l:[z.GetFilledPolysList(l) for z in b.Zones() if not z.GetIsRuleArea() and z.GetLayer()==l and z.GetNetname() in ('GND','AGND')] for l in [p.In1_Cu,p.In2_Cu]}
result={};crossings=[]
for name in ['BCLK','LRCLK','I2S_A','I2S_B','I2S_C']:
 total=miss=0.;runs=[]
 for t in b.GetTracks():
  if isinstance(t,p.PCB_VIA) or t.GetNetname()!=name:continue
  a,c=t.GetStart(),t.GetEnd();length=p.ToMM(t.GetLength());count=max(1,math.ceil(length/.2));step=length/count;run=0
  am=(p.ToMM(a.x),p.ToMM(a.y));cm=(p.ToMM(c.x),p.ToMM(c.y))
  if in_polygon(*am,ANALOG)!=in_polygon(*cm,ANALOG):
   lo,hi=0.,1.
   for _ in range(30):
    m=(lo+hi)/2;q=(am[0]+(cm[0]-am[0])*m,am[1]+(cm[1]-am[1])*m)
    if in_polygon(*q,ANALOG)==in_polygon(*am,ANALOG):lo=m
    else:hi=m
   crossings.append({'net':name,'x_mm':round(q[0],3),'y_mm':round(q[1],3),'distance_to_JP1_mm':round(math.dist(q,(129,123)),3)})
  other=p.In1_Cu if t.GetLayer()==p.F_Cu else p.In2_Cu
  for i in range(count):
   point=p.VECTOR2I(round(a.x+(c.x-a.x)*(i+.5)/count),round(a.y+(c.y-a.y)*(i+.5)/count))
   hit=any(poly.Contains(point) for poly in planes[other]);total+=step
   if not hit:miss+=step;run+=step
   else:
    if run>1:runs.append(round(run,2))
    run=0
  if run>1:runs.append(round(run,2))
 result[name]={'length_mm':round(total,2),'without_adjacent_ground_fill_mm':round(miss,2),'long_gaps_mm':runs}
print(json.dumps(result,indent=2))
(root/'reports/clock-ground-review.json').write_text(json.dumps({'measurements':result,'ground_split_crossings':crossings,'method':'Centreline samples at 0.2mm against the adjacent internal ground-plane fill; excludes ground tracks and is not a field solver.'},indent=2)+'\n')
print('Ground split crossings:',crossings)
