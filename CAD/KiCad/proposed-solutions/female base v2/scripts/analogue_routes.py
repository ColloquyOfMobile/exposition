"""Explicit revision D input/output routing, protected during autorouting.

The speaker pair stays on the lower-right front; the input pair approaches
from the upper back. A grounded front guard separates the lower regions.
"""
import pcbnew as p


def xy(point):
    return p.VECTOR2I(*(p.FromMM(v) for v in point))


def prepare(board, name):
    male=name=='male-static-v2'
    pads={(f.GetReference(),a.GetNumber()):a for f in board.GetFootprints() for a in f.Pads()}
    def at(ref,pin):return tuple(p.ToMM(pads[(ref,str(pin))].GetPosition()))
    def harness(net):
        return tuple(p.ToMM(next(a for (ref,_),a in pads.items() if ref=='J7' and a.GetNetname()==net).GetPosition()))
    def path(net,points,layer=p.F_Cu,width=.25):
        for a,b in zip(points,points[1:]):
            if a==b:continue
            track=p.PCB_TRACK(board); track.SetStart(xy(a)); track.SetEnd(xy(b))
            track.SetLayer(layer); track.SetWidth(p.FromMM(width))
            track.SetNet(board.FindNet(net)); track.SetLocked(True); board.Add(track)
    def via(net,point):
        item=p.PCB_VIA(board); item.SetPosition(xy(point)); item.SetWidth(p.FromMM(.6))
        item.SetDrill(p.FromMM(.3)); item.SetViaType(p.VIATYPE_THROUGH)
        item.SetLayerPair(p.F_Cu,p.B_Cu); item.SetNet(board.FindNet(net))
        item.SetLocked(True); board.Add(item)

    sx,sy=at('M1',1)
    if male:
        output_p=[at('M1',10),(60.5,79.06),(67,85.56),at('J6',1)]
        output_n=[at('M1',11),(60.5,81.6),(65.2,86.3),(65.2,92.5),at('J6',2)]
        line_via=(50.5,56.2)
        line=[harness('LINE_IN'),(55.54,37),(56,37.46),(56,54.5),(54.3,56.2),line_via]
    else:
        output_p=[at('M1',10),(55.06,79.06),at('J6',1)]
        output_n=[at('M1',11),(55.1,81.6),(62.2,88.7),(62.2,90.5),at('J6',2)]
        line_via=(44.5,53.5)
        line=[harness('LINE_IN'),(50.305,39),(43.5,45.805),(43.5,52.5),line_via]
    path('AMP_OUT_P',output_p,width=.8); path('AMP_OUT_N',output_n,width=.8)
    if not male:
        # User's 2026-10-21 placement: retain it and route the relocated parts.
        line_via=(38.72,55.8)
        path('LINE_IN',[harness('LINE_IN'),(50.305,39),(37,52.305),
                        (37,55.8),line_via],p.B_Cu)
        via('LINE_IN',line_via)
        path('LINE_IN',[line_via,at('R1',1)])
        rx,ry=harness('AUDIO_RETURN')
        path('AUDIO_RETURN',[harness('AUDIO_RETURN'),(rx,38.4),
                            (35.65,51.67),(35.65,58.74),at('M1',2)],p.B_Cu)
        return_via=(42.17,61.2)
        path('AUDIO_RETURN',[(42.17,58.74),return_via],p.B_Cu)
        via('AUDIO_RETURN',return_via)
        path('AUDIO_RETURN',[return_via,at('R2',2)])
        path('AMP_INPUT',[at('R1',2),(41.56,56.2),at('M1',1)])
        path('AMP_INPUT',[at('R2',1),(40.52,57.54),at('R1',2)])
        path('5V',[at('M1',5),(36.13,66.36)],width=.8)
        path('5V',[(36.13,66.36),at('C2',1)])
        path('5V',[at('C1',1),(36.59,65.9),(36.13,66.36)],width=.8)
        path('GND',[at('M1',6),(34.58,68.9)],width=.8)
        path('GND',[(34.58,68.9),at('C2',2)])
        path('GND',[at('M1',6),(sx-2.85,71.75),(sx-2.85,84.5)],width=.8)
        board.BuildConnectivity()
        return
    path('LINE_IN',line,p.B_Cu); via('LINE_IN',line_via)
    path('LINE_IN',[line_via,at('R1',1)] if male else [line_via,(43.2,54.8),at('R1',1)])
    rx,ry=harness('AUDIO_RETURN')
    return_via=(sx-3.05,60.5)
    returned=([harness('AUDIO_RETURN'),(57.35,35.265),(57.35,58.74),at('M1',2)] if male else
              [harness('AUDIO_RETURN'),(rx,38.4),(42.15,38.4+rx-42.15),
               (42.15,57.5),(43.39,58.74),at('M1',2)])
    path('AUDIO_RETURN',returned,p.B_Cu)
    if male:path('AUDIO_RETURN',[(57.35,58.74),(return_via[0],58.74)],p.B_Cu)
    path('AUDIO_RETURN',[(return_via[0],58.74),return_via],p.B_Cu)
    via('AUDIO_RETURN',return_via)
    r2=at('R2',2)
    path('AUDIO_RETURN',[return_via,(r2[0],59.2),r2])
    path('AMP_INPUT',[at('R1',2),at('M1',1)])
    r2in=at('R2',1)
    path('AMP_INPUT',[(r2in[0],sy),r2in])
    path('5V',[at('M1',5),(sx-2.35,66.36)],width=.8)
    path('5V',[(sx-2.35,66.36),(at('C2',1)[0]+1.27,66.36),at('C2',1)])
    path('GND',[at('M1',6),(sx-1.55,68.9)],width=.8)
    path('GND',[(sx-1.55,68.9),(at('C2',2)[0]+1.27,68.9),at('C2',2)])
    path('GND',[at('M1',6),(sx-2.85,71.75),(sx-2.85,90 if male else 84.5)],width=.8)
    if male:
        # Escape the relocated body-pixel connector outside the analogue region.
        net='body neopixel male input'
        path(net,[harness(net),(47.23,38.5),(69.5,38.5),(73,42)])
        via(net,(73,42))
        path(net,[(73,42),(73,98),at('J5',3)],p.B_Cu)
    board.BuildConnectivity()
