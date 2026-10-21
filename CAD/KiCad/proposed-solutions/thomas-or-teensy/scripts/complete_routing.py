"""Finish a freshly imported route before ground filling.

Widens automatic neck-downs to 0.20mm, connects translator DIR supplies,
and routes COIL_LOW outside the analog region. Overwrites generated copper;
run only after route_board.py, then finish_board.py and final validation.
"""
from pathlib import Path
import sys,json
import pcbnew as p
import route_repair as r
b=p.LoadBoard(str(r.BOARD));saved=r.BOARD.with_suffix('.kicad_pro').read_bytes()
pads={(f.GetReference(),q.GetNumber()):q for f in b.GetFootprints() for q in f.Pads()}
widened=[]
for t in b.GetTracks():
 if not isinstance(t,p.PCB_VIA) and t.GetWidth()<p.FromMM(.2):
  t.SetWidth(p.FromMM(.2));widened.append(t.m_Uuid.AsString())
for ref in ['UB1','UB2']:
 r.TARGET=pads[(ref,'1')]
 path=r.search(b,'+5V',pads[(ref,'5')])
 if not path:raise RuntimeError('Cannot connect '+ref)
 r.insert(b,'+5V',pads[(ref,'5')],path)
previous_tracks=list(b.GetTracks())
for t in previous_tracks:
 if t.GetNetname()=='COIL_LOW':b.Remove(t)
r.WIDTH=.4;r.EXCLUDE_ANALOG=True
pairs=[(('QK1','3'),('K1','8')),(('K1','8'),('K3','8')),(('K3','8'),('K2','8'))]+[((f'DK{n}','2'),(f'K{n}','8')) for n in range(1,4)]
for a,c in pairs:
 r.TARGET=pads[c]
 path=r.search(b,'COIL_LOW',pads[a])
 if not path:raise RuntimeError('Cannot connect coil '+str(a))
 r.insert(b,'COIL_LOW',pads[a],path)
b.BuildConnectivity();p.SaveBoard(str(r.BOARD),b);r.BOARD.with_suffix('.kicad_pro').write_bytes(saved)
(r.PROJECT/'reports/copper-refinements.json').write_text(json.dumps({'widened_to_020mm':widened,'completed_supply_branches':['UB1.5 to UB1.1','UB2.5 to UB2.1'],'coil_return_rerouted_outside_analog':True},indent=2)+'\n')
print('Saved refined copper. Run DRC.',flush=True)
