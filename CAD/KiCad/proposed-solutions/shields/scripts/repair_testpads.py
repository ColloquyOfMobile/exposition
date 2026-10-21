"""Move new probe pads onto clear portions of their own existing F.Cu routes."""
import math
import pcbnew as p
from design import ROOT
from boards import xy
from inner_routes import via

def point(obj):return tuple(p.ToMM(obj))
def distance(q,a,b):
    dx=b[0]-a[0];dy=b[1]-a[1];den=dx*dx+dy*dy
    t=max(0,min(1,((q[0]-a[0])*dx+(q[1]-a[1])*dy)/den)) if den else 0
    return math.dist(q,(a[0]+dx*t,a[1]+dy*t))

def repair(name,refs):
    path=ROOT/name/(name+'.kicad_pcb');b=p.LoadBoard(str(path));fps={f.GetReference():f for f in b.GetFootprints()}
    for ref in refs:
        fp=fps[ref];pad=next(iter(fp.Pads()));net=pad.GetNetCode();old=point(pad.GetPosition());candidates=[]
        for t in b.GetTracks():
            if t.GetNetCode()!=net or isinstance(t,p.PCB_VIA):continue
            a,z=point(t.GetStart()),point(t.GetEnd());steps=max(1,math.ceil(math.dist(a,z)/.5))
            for i in range(steps+1):
                q=(a[0]+(z[0]-a[0])*i/steps,a[1]+(z[1]-a[1])*i/steps);candidates.append((math.dist(q,old),q,t.GetLayer()))
        for _,q,layer in sorted(candidates):
            good=True
            for other in b.GetFootprints():
                if other==fp:continue
                for op in other.Pads():
                    if not op.IsOnLayer(p.F_Cu) and layer==p.F_Cu:continue
                    box=op.GetBoundingBox();x0,y0,x1,y1=[p.ToMM(v) for v in [box.GetLeft(),box.GetTop(),box.GetRight(),box.GetBottom()]]
                    if x0-1.6<q[0]<x1+1.6 and y0-1.6<q[1]<y1+1.6:good=False;break
                if not good:break
            if not good:continue
            for t in b.GetTracks():
                if t.GetNetCode()==net:
                    if isinstance(t,p.PCB_VIA) and math.dist(q,point(t.GetPosition()))<.65:good=False;break
                    continue
                if layer==p.F_Cu and not t.IsOnLayer(p.F_Cu):continue
                width=p.ToMM(t.GetWidth(p.F_Cu) if isinstance(t,p.PCB_VIA) else t.GetWidth())
                if distance(q,point(t.GetStart()),point(t.GetEnd()))<(1 if t.IsOnLayer(p.F_Cu) else .6)+width/2:good=False;break
            if good:
                fp.SetPosition(xy(*q))
                if layer!=p.F_Cu:via(b,pad.GetNet(),q)
                print(name,ref,old,'->',q,flush=True);break
        else:raise RuntimeError('No clear route for '+ref)
    b.BuildConnectivity();p.SaveBoard(str(path),b)

if __name__=='__main__':repair('backplane',['TPL3','TPM5','TPA5'])
