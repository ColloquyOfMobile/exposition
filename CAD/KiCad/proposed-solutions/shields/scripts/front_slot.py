"""Apply SHIELDS 2026-10-08 front computing slot geometry (no net changes)."""
import json
import pcbnew as p
from design import ROOT
from boards import xy, text

MIRROR_X=167.83
# Conservative housing envelopes, transformed from the original Mega CAD.
# The part of the USB/jack overhanging the backplane needs no PCB rule area.
HOUSINGS={'USB':(150.0,53.4,163.0,64.0),'POWER_JACK':(181.95,53.4,191.45,65.25)}

def slim_mount(fp):
    """Rear screw head, <=4 mm round spacer/post on the connector face."""
    if str(fp.GetFPID().GetLibItemName())=='MountingHole_3.2mm_M3_SlimFront':return
    for g in fp.GraphicalItems():
        if g.GetLayer()==p.F_CrtYd:g.SetLayer(p.B_CrtYd)
    g=p.PCB_SHAPE(fp);g.SetShape(p.SHAPE_T_CIRCLE);g.SetCenter(fp.GetPosition())
    g.SetEnd(fp.GetPosition()+xy(2.05,0));g.SetWidth(p.FromMM(.05));g.SetLayer(p.F_CrtYd);fp.Add(g)
    fp.SetFPID(p.LIB_ID('Shields','MountingHole_3.2mm_M3_SlimFront'))
    fp.SetValue('M3; front spacer OD <=4mm; screw head on rear')

def connector_courtyards(fp):
    """Module outline is an assembly envelope; courtyards belong to its headers."""
    import math
    from boards import rect
    seen=set();removed=[]
    for g in list(fp.GraphicalItems()):
        if g.GetLayer()==p.F_CrtYd:g.SetLayer(p.F_Fab)
        if isinstance(g,p.PCB_TEXT):
            key=(g.GetText(),g.GetLayer(),g.GetPosition().x,g.GetPosition().y)
            if key in seen:removed.append(g);fp.Remove(g)
            seen.add(key)
    points=[tuple(p.ToMM(pad.GetPosition())) for pad in fp.Pads() if pad.GetNumber()]
    while points:
        group=[points.pop()];changed=True
        while changed:
            changed=False
            for point in points[:]:
                if any(math.dist(point,other)<2.55 for other in group):
                    points.remove(point);group.append(point);changed=True
        xs,ys=zip(*group)
        rect(fp,min(xs)-1.5,min(ys)-1.5,max(xs)-min(xs)+3,max(ys)-min(ys)+3,p.F_CrtYd)
    # Keep removed SWIG wrappers alive through all mutations.
    return removed

def mirror_mega(fp):
    if str(fp.GetFPID().GetLibItemName())=='Mega_Front_Mirrored':return
    fp.Flip(xy(MIRROR_X,0),p.FLIP_DIRECTION_LEFT_RIGHT)
    fp.SetLayer(p.F_Cu)
    layers={p.B_SilkS:p.F_SilkS,p.B_Fab:p.F_Fab,p.B_CrtYd:p.F_CrtYd}
    for item in list(fp.GraphicalItems())+[fp.Reference(),fp.Value()]:
        if item.GetLayer() in layers:item.SetLayer(layers[item.GetLayer()])
        if hasattr(item,'SetMirrored'):item.SetMirrored(False)
    fp.SetFPID(p.LIB_ID('Shields','Mega_Front_Mirrored'))
    fp.SetLibDescription('Front male headers for upside-down Mega; mirrored about x=167.83mm')
    connector_courtyards(fp)

def housing_rules(board):
    for name,(x0,y0,x1,y1) in HOUSINGS.items():
        z=p.ZONE(board);z.SetIsRuleArea(True);z.SetZoneName('SH_MEGA_'+name)
        z.SetLayerSet(p.LSET.AllCuMask())
        z.SetDoNotAllowPads(True);z.SetDoNotAllowVias(True)
        z.SetDoNotAllowTracks(False);z.SetDoNotAllowCopperPour(False);z.SetDoNotAllowFootprints(False)
        z.Outline().NewOutline()
        for x,y in [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]:z.Outline().Append(p.FromMM(x),p.FromMM(y))
        board.Add(z)

def main():
    folder=ROOT/'backplane';board=p.LoadBoard(str(folder/'backplane.kicad_pcb'))
    parts={f.GetReference():f for f in board.GetFootprints()}
    mirror_mega(parts['A1'])
    from mechanical import EAGLE_HOLES
    for i,(ex,ey) in enumerate(EAGLE_HOLES,1):
        parts[f'HM{i}'].SetPosition(xy(194.50-ey,53.32+ex));slim_mount(parts[f'HM{i}'])
    # A fresh route avoids retaining stubs tied to the old mirrored pad map.
    for t in list(board.GetTracks()):board.Delete(t)
    old=list(board.Zones())
    for z in old:board.Remove(z)
    housing_rules(board)
    old_text=list(board.GetDrawings())
    for item in old_text:
        if isinstance(item,p.PCB_TEXT) and any(s in item.GetText() for s in ['COMPUTING SLOT','USB END']):board.Remove(item)
    text(board,'COMPUTING SLOT / MEGA 2560 OR TEENSY ADAPTER',167.83,95,1)
    text(board,'MEGA COMPONENT SIDE DOWN',167.83,100,1.2)
    text(board,'USB END ^',167.83,63,1)
    fp=parts['A1'].Duplicate();fp.SetOrientationDegrees(0);fp.SetPosition(xy(0,0))
    p.PCB_IO_MGR.PluginFind(p.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(ROOT/'Shields.pretty'),fp)
    p.SaveBoard(str(folder/'backplane-placed.kicad_pcb'),board)
    data=json.loads((folder/'circuit.json').read_text())
    next(c for c in data['components'] if c['ref']=='A1')['footprint']='Shields:Mega_Front_Mirrored'
    (folder/'circuit.json').write_text(json.dumps(data,indent=2)+'\n')
    for sch in folder.glob('*.kicad_sch'):
        sch.write_text(sch.read_text().replace('Shields:Arduino_Mega2560_R3_Shield','Shields:Mega_Front_Mirrored'))
    for name in ['Colloquy.kicad_sym','bom.csv']:
        path=folder/name
        path.write_text(path.read_text().replace('Shields:Arduino_Mega2560_R3_Shield','Shields:Mega_Front_Mirrored'))
    project=folder/'backplane.kicad_pro';data=json.loads(project.read_text())
    classes=data['net_settings']['classes'];servo=dict(next(c for c in classes if c['name']=='Power'))
    servo.update(name='Servo12V',track_width=2.0,via_diameter=1.2,via_drill=.6)
    classes[:]=[c for c in classes if c['name']!='Servo12V']+[servo]
    for assignment in data['net_settings']['netclass_patterns']:
        if assignment['pattern']=='+12V':assignment['netclass']='Servo12V'
    project.write_text(json.dumps(data,indent=2)+'\n')
    (folder/'backplane.kicad_dru').write_text('''(version 1)
(rule "Servo12V width" (condition "A.NetName == '+12V'") (constraint track_width (min 2mm)))
(rule "Servo12V outer copper only" (condition "A.NetName == '+12V' && (A.Layer == 'In1.Cu' || A.Layer == 'In2.Cu')") (constraint disallow track))
''')
    print('Front mirrored slot and housing rules staged; route backplane-placed next.')

if __name__=='__main__':main()
