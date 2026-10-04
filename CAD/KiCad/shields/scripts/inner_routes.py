"""Finish congested signals on In2.Cu; both computing boards use four layers.

Conservative grid clearance is followed by native KiCad DRC, not a substitute
for it. The remaining inner copper is filled by planes.py after this operation.
"""
import heapq
import math
import json
import pcbnew as p
from design import ROOT
from boards import xy,mm

STEP=.25

def track(board,net,a,b,layer=p.In2_Cu):
    t=p.PCB_TRACK(board);t.SetNet(net);t.SetStart(xy(*a));t.SetEnd(xy(*b))
    t.SetLayer(layer);t.SetWidth(mm(.25));board.Add(t)

def via(board,net,point):
    v=p.PCB_VIA(board);v.SetNet(net);v.SetPosition(xy(*point));v.SetWidth(mm(.6));v.SetDrill(mm(.3))
    v.SetViaType(p.VIATYPE_THROUGH);v.SetLayerPair(p.F_Cu,p.B_Cu);board.Add(v)

def route(board,netname,start,end,layer=p.In2_Cu):
    net=next(n for n in board.GetNetsByNetcode().values() if n.GetNetname().replace('{slash}','/')==netname)
    blocked=set()
    def rect(x0,y0,x1,y1):
        for x in range(math.floor(x0/STEP),math.ceil(x1/STEP)+1):
            for y in range(math.floor(y0/STEP),math.ceil(y1/STEP)+1):blocked.add((x,y))
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetCode()==net.GetNetCode() or not pad.IsOnLayer(layer):continue
            box=pad.GetBoundingBox();margin=.4
            rect(p.ToMM(box.GetLeft())-margin,p.ToMM(box.GetTop())-margin,p.ToMM(box.GetRight())+margin,p.ToMM(box.GetBottom())+margin)
    for t in board.GetTracks():
        if t.GetNetCode()==net.GetNetCode() or not t.IsOnLayer(layer):continue
        a,b=[tuple(p.ToMM(v)) for v in [t.GetStart(),t.GetEnd()]]
        length=math.dist(a,b);radius=p.ToMM(t.GetWidth(layer) if isinstance(t,p.PCB_VIA) else t.GetWidth())/2+.4
        for i in range(max(1,math.ceil(length/.2))+1):
            f=i/max(1,math.ceil(length/.2));x=a[0]+(b[0]-a[0])*f;y=a[1]+(b[1]-a[1])*f
            rect(x-radius,y-radius,x+radius,y+radius)
    bounds=board.GetBoardEdgesBoundingBox()
    limits=[round(p.ToMM(v)/STEP) for v in [bounds.GetLeft(),bounds.GetTop(),bounds.GetRight(),bounds.GetBottom()]]
    begin=tuple(round(v/STEP) for v in start);goal=tuple(round(v/STEP) for v in end)
    assert begin not in blocked and goal not in blocked,(netname,'endpoint blocked')
    heap=[(0,0,begin)];cost={begin:0};parent={}
    while heap:
        _,g,q=heapq.heappop(heap)
        if q==goal:break
        if g!=cost[q]:continue
        for dx,dy in [(1,0),(-1,0),(0,1),(0,-1),(1,1),(1,-1),(-1,1),(-1,-1)]:
            r=(q[0]+dx,q[1]+dy)
            if not(limits[0]+3<r[0]<limits[2]-3 and limits[1]+3<r[1]<limits[3]-3):continue
            if r in blocked or (q[0]+dx,q[1]) in blocked or (q[0],q[1]+dy) in blocked:continue
            ng=g+math.hypot(dx,dy)
            if ng>=cost.get(r,float('inf')):continue
            cost[r]=ng;parent[r]=q;heapq.heappush(heap,(ng+math.dist(r,goal),ng,r))
    else:raise RuntimeError('No route '+netname)
    points=[goal]
    while points[-1]!=begin:points.append(parent[points[-1]])
    points.reverse();simple=[points[0]]
    for i in range(1,len(points)-1):
        if (points[i][0]-points[i-1][0],points[i][1]-points[i-1][1])!=(points[i+1][0]-points[i][0],points[i+1][1]-points[i][1]):simple.append(points[i])
    simple.append(goal);coords=[start]+[(x*STEP,y*STEP) for x,y in simple]+[end]
    for a,b in zip(coords,coords[1:]):
        if math.dist(a,b)>.00001:track(board,net,a,b,layer)
    print(netname,len(simple),'inner segments',flush=True)

def main():
    for name in ['backplane','teensy-adapter']:
        path=ROOT/name/(name+'.kicad_pcb');board=p.LoadBoard(str(path));board.SetCopperLayerCount(4)
        for z in list(board.Zones()):board.Remove(z)
        report=json.loads((ROOT/name/'reports/drc.json').read_text())
        dangling={i['uuid'] for v in report['violations'] if v['type'] in ['track_dangling','via_dangling'] for i in v['items']}
        for t in list(board.GetTracks()):
            if t.m_Uuid.AsString() in dangling:board.Delete(t)
        if name=='backplane':
            route(board,'male2/photosensor/A',(143.7,137.14),(186.58,337.8))
            route(board,'male2/photosensor/B',(143.7,139.68),(187.965,334.96))
        else:
            net=next(n for n in board.GetNetsByNetcode().values() if n.GetNetname().replace('{slash}','/')=='female2/tone')
            points=[(148.1375,79.3),(149.1,79.3),(149.4,79.6),(149.4,79.8)]
            for a,b in zip(points,points[1:]):track(board,net,a,b,p.F_Cu)
            via(board,net,(149.4,79.8))
            route(board,'female2/tone',(149.4,79.8),(176.72,147.3))
            next(f for f in board.GetFootprints() if f.GetReference()=='D1').SetValue('1N5819HW')
        board.BuildConnectivity();p.SaveBoard(str(path),board)

if __name__=='__main__':main()

