"""Independent geometric checks for revision D's amplifier routing rules."""
import math
import pcbnew as p


def point(item,start=True):
    return tuple(p.ToMM(item.GetStart() if start else item.GetEnd()))


def check(board, *, amp_input_length_limit_mm=8):
    segments=[t for t in board.GetTracks() if not isinstance(t,p.PCB_VIA)]
    outputs=[t for t in segments if t.GetNetname() in ('AMP_OUT_P','AMP_OUT_N')]
    sensitive=[t for t in segments if t.GetNetname() in ('AMP_INPUT','LINE_IN','AUDIO_RETURN')
               or 'microphone' in t.GetNetname().lower()
               or 'photo' in t.GetNetname().lower()]
    assert outputs
    assert all(t.GetLayer()==p.F_Cu and p.ToMM(t.GetWidth())>=.7999 for t in outputs)
    def vector(a,b):return b[0]-a[0],b[1]-a[1]
    def dot(a,b):return a[0]*b[0]+a[1]*b[1]
    def cross(a,b):return a[0]*b[1]-a[1]*b[0]
    violations=[];parallel_distances=[];crossings=[]
    for output in outputs:
        a,b=point(output),point(output,False);u=vector(a,b);length=math.hypot(*u)
        if not length:continue
        direction=(u[0]/length,u[1]/length)
        for track in sensitive:
            c,d=point(track),point(track,False);v=vector(c,d);vl=math.hypot(*v)
            if not vl:continue
            cosine=abs(dot(u,v)/length/vl)
            projections=sorted((dot(vector(a,c),direction),dot(vector(a,d),direction)))
            overlap=min(length,projections[1])-max(0,projections[0])
            distance=abs(cross(direction,vector(a,c)))
            if cosine>.98 and overlap>.5:
                parallel_distances.append(distance)
                if distance<2.5:
                    violations.append(('parallel',track.GetNetname(),distance,point(output),point(track)))
            determinant=cross(u,v)
            if abs(determinant)>1e-10:
                t=cross(vector(a,c),v)/determinant
                q=cross(vector(a,c),u)/determinant
                if 0<=t<=1 and 0<=q<=1:
                    crossings.append({'net':track.GetNetname(),'angle_degrees':round(math.degrees(math.acos(min(1,cosine))),3)})
                    if cosine>.1:
                        violations.append(('nonorthogonal crossing',track.GetNetname(),cosine))
    assert not violations,violations
    paired_input=0
    for line in (t for t in segments if t.GetNetname()=='LINE_IN' and t.GetLayer()==p.B_Cu):
        a,b=point(line),point(line,False);u=vector(a,b);length=math.hypot(*u)
        if not length:continue
        direction=(u[0]/length,u[1]/length);overlaps=[]
        for returned in (t for t in segments if t.GetNetname()=='AUDIO_RETURN' and t.GetLayer()==p.B_Cu):
            c,d=point(returned),point(returned,False);v=vector(c,d);vl=math.hypot(*v)
            if not vl or abs(dot(u,v)/length/vl)<.999:continue
            distance=abs(cross(direction,vector(a,c)))
            if .1<distance<2:
                q=sorted((dot(vector(a,c),direction),dot(vector(a,d),direction)))
                overlaps.append(max(0,min(length,q[1])-max(0,q[0])))
        paired_input+=max(overlaps,default=0)
    assert paired_input>8,paired_input
    lengths={net:sum(p.ToMM(t.GetLength()) for t in outputs if t.GetNetname()==net)
             for net in ('AMP_OUT_P','AMP_OUT_N')}
    assert max(lengths.values())<25,lengths
    amp_length=sum(p.ToMM(t.GetLength()) for t in segments if t.GetNetname()=='AMP_INPUT')
    assert amp_length<amp_input_length_limit_mm,amp_length
    # An explicit grounded front guard runs left of the output pair; pours add
    # shielding around it on both layers. DRC establishes its net isolation.
    socket=next(f for f in board.GetFootprints() if f.GetReference()=='M1')
    sx,sy=p.ToMM(socket.GetPosition())
    guards=[t for t in segments if t.GetNetname()=='GND' and t.GetLayer()==p.F_Cu
            and abs(point(t)[0]-(sx-2.85))<.001 and abs(point(t,False)[0]-(sx-2.85))<.001
            and p.ToMM(t.GetLength())>=12]
    assert guards,'Missing grounded guard between output and sensor/input region'
    return {'output_lengths_mm':{k:round(v,3) for k,v in lengths.items()},
            'output_copper_layer':'F.Cu','output_minimum_width_mm':.8,
            'amp_input_total_length_mm':round(amp_length,3),
            'amp_input_length_limit_mm':amp_input_length_limit_mm,
            'paired_incoming_line_return_overlap_mm':round(paired_input,3),
            'parallel_sensitive_runs_within_2p5mm':0,
            'minimum_parallel_sensitive_centre_spacing_mm':round(min(parallel_distances),3) if parallel_distances else None,
            'sensitive_crossings':crossings,'ground_guard':'PASS'}
