"""Fill local supply-ground copper; audio return stays a separate net."""
from pathlib import Path
import argparse
import pcbnew as p

CAD=Path(__file__).resolve().parents[2]
parser=argparse.ArgumentParser()
parser.add_argument('--only',choices=('female-base-v2','male-static-v2'))
args=parser.parse_args()
for folder,stem,bottom in [('female base v2','female-base-v2',100),('male static v2','male-static-v2',110)]:
    if args.only and stem!=args.only:continue
    path=CAD/folder/(stem+'.kicad_pcb'); board=p.LoadBoard(str(path))
    # Keep removed SWIG wrappers alive while adding the replacement zones.
    old_zones=list(board.Zones())
    for zone in old_zones:
        if not zone.GetIsRuleArea(): board.Remove(zone)
    for layer in (p.F_Cu,p.B_Cu):
        zone=p.ZONE(board); zone.SetZoneName('LOCAL_SUPPLY_GND')
        zone.SetNet(board.FindNet('GND')); zone.SetLayer(layer)
        zone.SetLocalClearance(p.FromMM(.25)); zone.SetMinThickness(p.FromMM(.2))
        zone.SetPadConnection(p.ZONE_CONNECTION_FULL)
        zone.SetIslandRemovalMode(p.ISLAND_REMOVAL_MODE_ALWAYS)
        zone.Outline().NewOutline()
        for x,y in [(25.5,20.5),(74.5,20.5),(74.5,bottom-.5),(25.5,bottom-.5)]:
            zone.Outline().Append(p.FromMM(x),p.FromMM(y))
        board.Add(zone)
    board.BuildConnectivity(); p.ZONE_FILLER(board).Fill(board.Zones()); p.SaveBoard(str(path),board)
    print(stem,'local GND pours filled; AUDIO_RETURN remains separate.')
