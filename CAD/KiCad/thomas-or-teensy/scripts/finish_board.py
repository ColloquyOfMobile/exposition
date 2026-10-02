"""Add internal ground planes, split ground pours, NC nets and silkscreen.

Run after routing. Does not change placement or circuit. Re-run ERC/DRC after it.
"""
from pathlib import Path
import json
import math
import pcbnew as p
from schematic_support import parse,children,one

ROOT=Path(__file__).resolve().parents[1]
NAME='thomas-or-teensy'
mm=p.FromMM
def xy(x,y):return p.VECTOR2I(mm(x),mm(y))
ANALOG=[(133.5,71),(140.8,71),(140.8,121),(134,121),(134,135),
        (139,135),(139,175),(137,175),(137,191),(193,191),(193,215),
        (231,215),(231,303),(70,303),(70,177),(64,177),(64,135),
        (124,135),(124,123),(133.5,123)]

def zone(board,name,net,layer,points,priority):
    z=p.ZONE(board);z.SetZoneName(name);z.SetNet(board.FindNet(net));z.SetLayer(layer)
    z.SetAssignedPriority(priority);z.SetLocalClearance(mm(.25));z.SetMinThickness(mm(.2))
    z.SetPadConnection(p.ZONE_CONNECTION_FULL)
    z.SetThermalReliefGap(mm(.25));z.SetThermalReliefSpokeWidth(mm(.3))
    z.SetIslandRemovalMode(p.ISLAND_REMOVAL_MODE_ALWAYS)
    z.Outline().NewOutline()
    for x,y in points:z.Outline().Append(mm(x),mm(y))
    board.Add(z)

def rectangle(item,gap=.0):
    b=item.GetBoundingBox()
    return (p.ToMM(b.GetLeft())-gap,p.ToMM(b.GetTop())-gap,p.ToMM(b.GetRight())+gap,p.ToMM(b.GetBottom())+gap)

def intersects(a,b):return a[0]<b[2] and a[2]>b[0] and a[1]<b[3] and a[3]>b[1]

def legend(board):
    obstacles=[]
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.IsOnLayer(p.F_Mask):obstacles.append(rectangle(pad,.24))
        for g in fp.GraphicalItems():
            if g.GetLayer()==p.F_SilkS:obstacles.append(rectangle(g,.18))
    # Place service legends before reference designators.
    labels=[i for i in board.GetDrawings() if isinstance(i,p.PCB_TEXT) and i.GetLayer()==p.F_SilkS]
    labels += [fp.Reference() for fp in board.GetFootprints()]
    adjustments=[]
    for label in labels:
        if label.GetLayer()==p.B_SilkS:continue
        if not label.IsVisible():continue
        label.SetTextSize(xy(max(.8,p.ToMM(label.GetTextSize().x)),max(.8,p.ToMM(label.GetTextSize().y))))
        label.SetTextThickness(mm(.12))
        label.SetTextAngle(p.EDA_ANGLE(0,p.DEGREES_T))
        origin=label.GetPosition();ox,oy=p.ToMM(origin.x),p.ToMM(origin.y)
        if label.GetText()=='3.3V - NOT 5V TOLERANT':ox,oy=89,112
        # Deterministic search near the component, including very dense socket labels.
        offsets=[(0,0)]
        for radius in [1,2,3,4,5,6,8,10,12]:
            offsets += [(dx*radius,dy*radius) for dx,dy in [(0,-1),(0,1),(-1,0),(1,0),(-1,-1),(1,-1),(-1,1),(1,1)]]
        found=False
        for dx,dy in offsets:
            label.SetPosition(xy(ox+dx,oy+dy));bounds=rectangle(label,.12)
            if bounds[0]<44.8 or bounds[2]>253.2 or bounds[1]<53 or bounds[3]>348.2:continue
            if not any(intersects(bounds,o) for o in obstacles):found=True;break
        if not found:raise RuntimeError('No readable silk location for '+label.GetText())
        obstacles.append(bounds)
        if label.GetPosition()!=origin:adjustments.append(label.GetText())
    return adjustments

def main():
    path=ROOT/(NAME+'.kicad_pcb');project=path.with_suffix('.kicad_pro');saved=project.read_bytes()
    board=p.LoadBoard(str(path))
    # Signals remain on the routed outer layers. Dedicated internal copper
    # prevents those tracks from slicing the I2S ground reference into islands.
    board.SetCopperLayerCount(4)
    data=json.loads((ROOT/'circuit.json').read_text())
    nc={(c['ref'],pin) for c in data['components'] for pin,net in c['pins'].items() if net is None}
    pads={(fp.GetReference(),pad.GetNumber()):pad for fp in board.GetFootprints() for pad in fp.Pads()}
    native=parse((ROOT/'reports/schematic.net').read_text())
    code=max(n.GetNetCode() for n in board.GetNetInfo().NetsByNetcode().values())+1
    for net in children(children(native,'nets')[0],'net'):
        name=one(net,'name')
        for node in children(net,'node'):
            key=(one(node,'ref'),one(node,'pin'))
            if key in nc and name.startswith('unconnected-'):
                target=board.FindNet(name)
                if not target:target=p.NETINFO_ITEM(board,name,code);code+=1;board.Add(target)
                pads[key].SetNet(target)
    # Keep wrappers alive until after new zones are built (KiCad 9 SWIG lifetime).
    previous_zones=list(board.Zones())
    for z in previous_zones:
        if z.GetIsRuleArea():continue
        if not z.GetZoneName().startswith('TT_'):raise RuntimeError('Foreign copper zone; inspect manually')
        board.Remove(z)
    perimeter=[(44.75,52.91),(253.25,52.91),(253.25,348.41),(44.75,348.41)]
    for layer,suffix in [(p.F_Cu,'F'),(p.In1_Cu,'In1'),(p.In2_Cu,'In2'),(p.B_Cu,'B')]:
        zone(board,'TT_AGND_'+suffix,'AGND',layer,ANALOG,2)
        zone(board,'TT_GND_'+suffix,'GND',layer,perimeter,0)
    moved=legend(board)
    board.BuildConnectivity();p.ZONE_FILLER(board).Fill(board.Zones())
    try:p.SaveBoard(str(path),board)
    finally:project.write_bytes(saved)
    source=path.read_text(encoding='utf-8').replace('(paper "A4")','(paper "A3" portrait)')
    path.write_text(source,encoding='utf-8')
    (ROOT/'reports/finishing.json').write_text(json.dumps({'silkscreen_labels_adjusted':moved,'analog_polygon_mm':ANALOG,'zone_count':8,'copper_layers':4,'fabrication_released':False},indent=2)+'\n')
    print('Added split ground pours and placed '+str(len(moved))+' labels; run DRC.')

if __name__=='__main__':main()
