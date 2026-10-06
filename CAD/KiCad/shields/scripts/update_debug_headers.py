"""One-time addition of LEDs and Dupont headers; reroute affected boards.

Run after design.py. Original boards are backed up outside the deliverable.
"""
import json
import shutil
import pcbnew as p
from design import ROOT
from boards import LOCAL,xy
from debug_layout import positions,footprints


def main():
    footprints()
    work=ROOT.parents[2]/'tmp/shields-debug-before';work.mkdir(parents=True,exist_ok=True)
    for name in ['backplane','teensy-adapter']:
        folder=ROOT/name;path=folder/(name+'.kicad_pcb')
        if not (work/path.name).exists():shutil.copy2(path,work/path.name)
        parts={c['ref']:c for c in json.loads((folder/'circuit.json').read_text())['components']}
        board=p.LoadBoard(str(work/path.name));old_zones=list(board.Zones())
        original={f.GetReference():(f.GetPosition(),f.GetOrientationDegrees(),f.GetLayer()) for f in board.GetFootprints()}
        for z in old_zones:board.Remove(z)
        for t in list(board.GetTracks()):board.Delete(t)
        nets={n.GetNetname().replace('{slash}','/'):n for n in board.GetNetsByNetcode().values()}
        for net in {net for c in parts.values() for net in c['pins'].values() if net}:
            if net not in nets:
                nets[net]=p.NETINFO_ITEM(board,net.replace('/','{slash}'));board.Add(nets[net])
        coords=positions(name)
        for fp in list(board.GetFootprints()):
            ref=fp.GetReference()
            if ref not in parts:
                if ref.startswith('H'):continue
                board.Delete(fp);continue
            if str(fp.GetFPID().GetLibItemName())!=parts[ref]['footprint'].split(':')[1]:board.Delete(fp)
        fps={f.GetReference():f for f in board.GetFootprints()}
        for ref,c in parts.items():
            if ref not in fps:
                fp=p.FootprintLoad(str(LOCAL),c['footprint'].split(':')[1]);assert fp,ref
                board.Add(fp);fp.SetReference(ref);fps[ref]=fp
                if ref in original:
                    point,angle,layer=original[ref]
                    if fp.GetLayer()!=layer:fp.Flip(fp.GetPosition(),True)
                    fp.SetOrientationDegrees(angle);fp.SetPosition(point)
            fp=fps[ref];fp.SetValue(c['value']);fp.SetFPID(p.LIB_ID('Shields',c['footprint'].split(':')[1]))
            if ref in coords:
                x,y,a=coords[ref];fp.SetPosition(xy(x,y));fp.SetOrientationDegrees(a)
                fp.Reference().SetPosition(xy(x,y-2));fp.Reference().SetLayer(p.F_SilkS)
                fp.Reference().SetTextSize(xy(.8,.8));fp.Reference().SetTextThickness(p.FromMM(.12))
            fp.Value().SetVisible(False)
            for pad in fp.Pads():
                net=c['pins'].get(pad.GetNumber());pad.SetNet(nets[net] if net else board.FindNet(0))
            ids=p.KIID_PATH()
            for u in (c['sheet_path'].strip('/')+'/'+c['uuid']).split('/'):ids.push_back(p.KIID(u))
            fp.SetPath(ids)
        board.BuildConnectivity()
        staged=work/(name+'-new.kicad_pcb');p.SaveBoard(str(staged),board)
        check=p.LoadBoard(str(staged));actual={(f.GetReference(),pad.GetNumber()):pad.GetNetname().replace('{slash}','/') for f in check.GetFootprints() for pad in f.Pads()}
        assert all(actual.get((ref,pin))==net for ref,c in parts.items() for pin,net in c['pins'].items() if net)
        for fp in check.GetFootprints():
            ref=fp.GetReference()
            if ref in original and ref not in coords:
                assert fp.GetPosition()==original[ref][0],(name,ref,'placement changed')
        shutil.copy2(staged,path);shutil.copy2(staged,folder/(name+'-placed.kicad_pcb'))
        print(name,'updated',len(parts),'components',flush=True)


if __name__=='__main__':main()
