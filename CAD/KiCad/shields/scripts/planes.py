"""Add connected copper pours; the backplane has dedicated supply/return planes.

No AGND/GND short is introduced. JP1 remains their only electrical bond.
Run only after routing; KiCad DRC must be rerun on the filled result.
"""
import json
import pcbnew as p
from design import ROOT
from boards import mm


def zone(board,name,net,layer,points):
    z=p.ZONE(board);z.SetZoneName(name);z.SetNet(board.FindNet(net));z.SetLayer(layer)
    z.SetLocalClearance(mm(.25));z.SetMinThickness(mm(.2));z.SetPadConnection(p.ZONE_CONNECTION_FULL)
    z.SetIslandRemovalMode(p.ISLAND_REMOVAL_MODE_ALWAYS);z.Outline().NewOutline()
    for x,y in points:z.Outline().Append(mm(x),mm(y))
    board.Add(z)


def main():
    for folder in ROOT.iterdir():
        name=folder.name;path=folder/(name+'.kicad_pcb')
        if not path.exists():continue
        board=p.LoadBoard(str(path));old=list(board.Zones())
        for z in old:
            if not z.GetZoneName().startswith('SH_'):raise RuntimeError('Unrecognized zone')
            board.Remove(z)
        bounds=board.GetBoardEdgesBoundingBox()
        left,top,right,bottom=[p.ToMM(v) for v in [bounds.GetLeft(),bounds.GetTop(),bounds.GetRight(),bounds.GetBottom()]]
        points=[(left+.5,top+.5),(right-.5,top+.5),(right-.5,bottom-.5),(left+.5,bottom-.5)]
        if name=='backplane':
            board.SetCopperLayerCount(4)
            zone(board,'SH_POWER_RETURN','GND',p.In1_Cu,points)
            zone(board,'SH_5V_DISTRIBUTION','+5V',p.In2_Cu,points)
            zone(board,'SH_ANALOG_RETURN','AGND',p.B_Cu,[(72,196),(231,196),(231,328),(72,328)])
            layers=4
        elif name=='teensy-adapter':
            board.SetCopperLayerCount(4)
            zone(board,'SH_RETURN','GND',p.In1_Cu,points)
            zone(board,'SH_RETURN_BOTTOM','GND',p.B_Cu,points)
            layers=4
        else:
            zone(board,'SH_RETURN','GND' if name=='teensy-adapter' else 'AGND',p.B_Cu,points)
            layers=2
        board.BuildConnectivity();p.ZONE_FILLER(board).Fill(board.Zones());p.SaveBoard(str(path),board)
        (folder/'reports/planes.json').write_text(json.dumps({'copper_layers':layers,'thickness_mm':1.6,
            'solid_pad_connections':True,'note':'Confirm finished copper weight and load/temperature rise with fabricator; current capacity is not established by DRC.'},indent=2)+'\n')
        print(name,'filled',len(list(board.Zones())),'zones',flush=True)


if __name__=='__main__':main()
