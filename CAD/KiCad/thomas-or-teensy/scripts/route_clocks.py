"""Route the five I2S signals across the ground split beside JP1.

Run after completing the generated outer-layer routing and before ground filling.
This replaces the five clock/data routes and moves their two test points.
"""
from pathlib import Path
import json
import math
import pcbnew as p
import route_repair as r
from audit_copper import in_polygon
from finish_board import ANALOG

def main():
    board=p.LoadBoard(str(r.BOARD));saved=r.BOARD.with_suffix('.kicad_pro').read_bytes()
    footprints={f.GetReference():f for f in board.GetFootprints()}
    for ref,pos in [('TP43',(119.5,117.5)),('TP44',(123,118))]:
        footprints[ref].SetPosition(r.vec(pos))
    pads={(f.GetReference(),q.GetNumber()):q for f in board.GetFootprints() for q in f.Pads()}
    clocks=['I2S_A','I2S_B','I2S_C','BCLK','LRCLK']
    plan=[('I2S_A','RT1',[('UD1','14')],125.),
          ('I2S_B','RT2',[('UD2','14')],126.2),
          ('I2S_C','RT3',[('UD3','14')],127.4),
          ('BCLK','RT5',[('UD3','13'),('UD2','13'),('UD1','13')],130.6),
          ('LRCLK','RT4',[('UD3','15'),('UD2','15'),('UD1','15')],131.8)]
    previous_tracks=list(board.GetTracks())
    by_id={t.m_Uuid.AsString():t for t in previous_tracks}
    board.BuildConnectivity();connectivity=board.GetConnectivity()
    retained=set();escapes={}
    # Keep the already DRC-checked fine-pitch escape from each DAC pad to its
    # first via. A coarse grid must not replace these short geometric fanouts.
    for net,_,targets,_ in plan:
        for key in targets:
            queue=list(connectivity.GetConnectedTracks(pads[key]));seen=set()
            while queue:
                proxy=queue.pop(0);uid=proxy.m_Uuid.AsString()
                if uid in seen:continue
                seen.add(uid);track=by_id[uid]
                if track.GetNetname()!=net:continue
                retained.add(uid)
                if isinstance(track,p.PCB_VIA):escapes[key]=track;break
                queue.extend(connectivity.GetConnectedTracks(track))
            if key not in escapes:raise RuntimeError('No existing DAC fanout for '+str(key))
    for t in previous_tracks:
        if t.GetNetname() in clocks and t.m_Uuid.AsString() not in retained:board.Remove(t)
    # Test-pad copper must clear existing traces, not merely component bodies.
    r.WIDTH=1.5;r.CLEAR=.27
    offsets=sorted(((dx*.25,dy*.25) for dx in range(-12,13) for dy in range(-12,13)),key=lambda v:math.hypot(*v))
    test_positions={}
    for ref,net in [('TP43','BCLK'),('TP44','LRCLK')]:
        pad=pads[(ref,'1')];r.TARGET=pad
        obstacle,_,_=r.build_masks(board,net,pad);ox,oy=r.xy(pad.GetPosition())
        for dx,dy in offsets:
            x,y=ox+dx,oy+dy
            if in_polygon(x,y,ANALOG):continue
            ix=round((x-r.X0)/r.STEP);iy=round((y-r.Y0)/r.STEP)
            if not obstacle[0,iy,ix]:
                footprints[ref].SetPosition(r.vec((x,y)));test_positions[ref]=[x,y];break
        else:raise RuntimeError('No clear test-pad location for '+ref)
        print('Clock test point',ref,test_positions[ref],flush=True)
    r.WIDTH=.2;r.CLEAR=.21;r.EXCLUDE_ANALOG=False;r.ONLY_ANALOG=False
    bridges={};routes=[]
    def connect(net,start,target,region):
        # The 0.65mm DAC pitch needs a finer grid than perimeter routing.
        a,c=r.xy(start.GetPosition()),r.xy(target.GetPosition())
        r.STEP=.05
        r.X0=max(44.,min(a[0],c[0])-15);r.Y0=max(52.16,min(a[1],c[1])-15)
        xmax=min(254.,max(a[0],c[0])+15);ymax=min(349.16,max(a[1],c[1])+15)
        r.NX=math.ceil((xmax-r.X0)/r.STEP)+1;r.NY=math.ceil((ymax-r.Y0)/r.STEP)+1
        r.X=r.X0+r.np.arange(r.NX)*r.STEP;r.Y=r.Y0+r.np.arange(r.NY)*r.STEP
        r.EXCLUDE_ANALOG=region=='digital';r.ONLY_ANALOG=region=='analog';r.TARGET=target
        path=r.search(board,net,start)
        if not path:raise RuntimeError(f'No {region} path for {net}')
        r.insert(board,net,start,path);routes.append({'net':net,'region':region,'grid_nodes':len(path)})
    # Place all five bridge pairs before routing to reserve the shared corridor.
    for net,ref,targets,preferred in plan:
        r.TARGET=pads[(ref,'2')]
        obstacle,viamask,_=r.build_masks(board,net,pads[(ref,'2')])
        selected=None
        for dx in [0,.1,-.1,.2,-.2,.3,-.3,.4,-.4]:
            x=preferred+dx;upper=(x,121.5);lower=(x,124.5)
            ix=round((x-r.X0)/r.STEP)
            top=round((upper[1]-r.Y0)/r.STEP);bottom=round((lower[1]-r.Y0)/r.STEP)
            if any(viamask[l,iy,ix] for l in [0,1] for iy in [top,bottom]):continue
            for layer in [0,1]:
                if not obstacle[layer,top:bottom+1,ix].any():selected=(upper,lower,layer);break
            if selected:break
        if not selected:raise RuntimeError('No clear split-crossing corridor for '+net)
        upper,lower,layer=selected;vias=[]
        for point in [upper,lower]:
            via=p.PCB_VIA(board);via.SetPosition(r.vec(point));via.SetWidth(p.FromMM(r.VIA));via.SetDrill(p.FromMM(r.DRILL))
            via.SetViaType(p.VIATYPE_THROUGH);via.SetLayerPair(p.F_Cu,p.B_Cu);via.SetNet(board.FindNet(net));board.Add(via);vias.append(via)
        track=p.PCB_TRACK(board);track.SetStart(r.vec(upper));track.SetEnd(r.vec(lower));track.SetLayer([p.F_Cu,p.B_Cu][layer]);track.SetWidth(p.FromMM(r.WIDTH));track.SetNet(board.FindNet(net));board.Add(track)
        bridges[net]=vias
        print('Ground split crossing',net,upper,lower,'layer',layer,flush=True)
    for net,ref,targets,_ in plan:
        upper,lower=bridges[net]
        connect(net,pads[(ref,'2')],upper,'digital')
        for target in targets:
            connect(net,lower,escapes[target],'analog')
            lower=escapes[target]
        tp='TP43' if net=='BCLK' else 'TP44' if net=='LRCLK' else None
        if tp:connect(net,pads[(tp,'1')],upper,'digital')
    board.BuildConnectivity()
    # A bridge endpoint routed entirely on one layer needs no drilled via.
    # Join its trace endpoints through the existing via's copper area first.
    routed_tracks=list(board.GetTracks());track_map={t.m_Uuid.AsString():t for t in routed_tracks}
    connectivity=board.GetConnectivity()
    for pair in bridges.values():
        for via in pair:
            neighbors=[track_map[t.m_Uuid.AsString()] for t in connectivity.GetConnectedTracks(via)]
            neighbors=[t for t in neighbors if not isinstance(t,p.PCB_VIA)]
            layers={t.GetLayer() for t in neighbors}
            if len(layers)!=1:continue
            centre=r.xy(via.GetPosition())
            for t in neighbors:
                ends=[r.xy(t.GetStart()),r.xy(t.GetEnd())];end=min(ends,key=lambda q:math.dist(q,centre))
                if math.dist(end,centre)<1e-6:continue
                link=p.PCB_TRACK(board);link.SetStart(r.vec(end));link.SetEnd(r.vec(centre));link.SetWidth(p.FromMM(.2));link.SetLayer(t.GetLayer());link.SetNet(via.GetNet());board.Add(link)
            board.Remove(via)
    board.BuildConnectivity()
    p.SaveBoard(str(r.BOARD),board);r.BOARD.with_suffix('.kicad_pro').write_bytes(saved)
    (r.PROJECT/'reports/clock-routing.json').write_text(json.dumps({'routes':routes,'test_points_mm':test_positions,'crossings':{n:[r.xy(v.GetPosition()) for v in vs] for n,vs in bridges.items()}},indent=2)+'\n')
    print('Saved I2S routing beside JP1; refill zones and run DRC.',flush=True)

if __name__=='__main__':main()
