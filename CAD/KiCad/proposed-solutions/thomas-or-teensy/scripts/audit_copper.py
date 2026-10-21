"""Measure routed copper for review; this is not a signal-integrity simulation."""
from pathlib import Path
from collections import defaultdict
import json
import math
import pcbnew as p
from finish_board import ANALOG

ROOT=Path(__file__).resolve().parents[1]

def point(v):return (p.ToMM(v.x),p.ToMM(v.y))

def in_polygon(x,y,polygon):
    inside=False
    for (ax,ay),(bx,by) in zip(polygon,polygon[1:]+polygon[:1]):
        if (ay>y)!=(by>y) and x<(bx-ax)*(y-ay)/(by-ay)+ax:inside=not inside
    return inside

def main():
    board=p.LoadBoard(str(ROOT/'thomas-or-teensy.kicad_pcb'))
    summary=defaultdict(lambda:dict(track_length_mm=0.,vias=0,min_width_mm=100.,max_width_mm=0.,inside_analog_mm=0.))
    for item in board.GetTracks():
        net=item.GetNetname();row=summary[net]
        if isinstance(item,p.PCB_VIA):row['vias']+=1;continue
        a,b=point(item.GetStart()),point(item.GetEnd());length=math.dist(a,b)
        width=p.ToMM(item.GetWidth())
        row['track_length_mm']+=length
        row['min_width_mm']=min(row['min_width_mm'],width)
        row['max_width_mm']=max(row['max_width_mm'],width)
        # Centreline samples at <=0.25mm; useful for locating coil routes.
        count=max(1,math.ceil(length/.25))
        row['inside_analog_mm']+=length/count*sum(in_polygon(a[0]+(b[0]-a[0])*(i+.5)/count,a[1]+(b[1]-a[1])*(i+.5)/count,ANALOG) for i in range(count))
    result={net:{k:round(v,3) if isinstance(v,float) else v for k,v in row.items()} for net,row in sorted(summary.items())}
    report={'measurements':result,'lengths_are_total_branched_copper':True,
            'analog_membership_is_zone_outline_only':True,'ground_return_continuity_verified':False,
            'signal_integrity_simulated':False}
    (ROOT/'reports/copper-audit.json').write_text(json.dumps(report,indent=2)+'\n')
    for net in ['+5V','+12V','GND','COIL_LOW','BCLK','LRCLK','I2S_A','I2S_B','I2S_C']:
        print(net,result.get(net))

if __name__=='__main__':main()
