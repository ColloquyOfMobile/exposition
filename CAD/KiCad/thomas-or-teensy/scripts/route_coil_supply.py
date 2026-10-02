"""Move the imported relay supply trunk outside the analog area.

Coordinates identify the reviewed generated route; stop if it has been edited.
Run after complete_routing.py and before final ground filling and validation.
"""
import math
import json
import pcbnew as p
import route_repair as r

def main():
    b=p.LoadBoard(str(r.BOARD));saved=r.BOARD.with_suffix('.kicad_pro').read_bytes()
    upper=(207.4983,210.7213);bend=(202.82,215.3996);lower=(202.82,309.8037)
    previous=list(b.GetTracks());remove=[]
    for a,c in [(lower,bend),(bend,upper)]:
        match=[t for t in previous if not isinstance(t,p.PCB_VIA) and t.GetNetname()=='+5V' and
               ((math.dist(r.xy(t.GetStart()),a)<.01 and math.dist(r.xy(t.GetEnd()),c)<.01) or
                (math.dist(r.xy(t.GetStart()),c)<.01 and math.dist(r.xy(t.GetEnd()),a)<.01))]
        if len(match)!=1:raise RuntimeError('Expected supply trunk changed; inspect routing before applying this repair')
        remove.extend(match)
    for t in remove:b.Remove(t)
    # Virtual routing terminals lie within the retained 2mm endpoint copper;
    # they are not added to the board or bill of materials.
    holder=p.FOOTPRINT(b);terminals=[]
    for point in [upper,lower]:
        pad=p.PAD(holder);pad.SetPosition(r.vec(point));pad.SetSize(r.vec((1.,1.)))
        pad.SetShape(p.PAD_SHAPE_CIRCLE);pad.SetAttribute(p.PAD_ATTRIB_SMD)
        layers=p.LSET();layers.AddLayer(p.F_Cu)
        pad.SetLayerSet(layers);pad.SetNet(b.FindNet('+5V'));terminals.append(pad)
    r.WIDTH=2.;r.VIA=1.2;r.DRILL=.6;r.CLEAR=.25;r.EXCLUDE_ANALOG=True;r.ONLY_ANALOG=False
    r.TARGET=terminals[1]
    path=r.search(b,'+5V',terminals[0])
    if not path:raise RuntimeError('No clear perimeter supply path; original PCB is untouched')
    r.insert(b,'+5V',terminals[0],path);b.BuildConnectivity()
    p.SaveBoard(str(r.BOARD),b);r.BOARD.with_suffix('.kicad_pro').write_bytes(saved)
    (r.PROJECT/'reports/coil-supply-routing.json').write_text(json.dumps({'removed_trunk_mm':[lower,bend,upper],'replacement_width_mm':2.,'grid_nodes':len(path)},indent=2)+'\n')
    print('Saved perimeter relay supply; refill planes and run DRC.',flush=True)

if __name__=='__main__':main()
