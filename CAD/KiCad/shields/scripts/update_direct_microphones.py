"""One-time migration from the Oct 4 boards to direct microphones (Oct 5).

Run after design.py. Keep fixed geometry and unaffected routes, then reroute
the backplane and adapter. Do not rerun on the completed layouts.
"""
import json
import shutil
import pcbnew as p
from design import ROOT, BASE
from boards import placements, xy, LOCAL


def plain(net):
    return net.replace('{slash}', '/').replace('{space}', ' ')


def main():
    work=ROOT.parents[2]/'tmp/direct-microphone-migration'
    work.mkdir(parents=True,exist_ok=True)
    old=p.LoadBoard(str(BASE/'colloquy-control-v2.kicad_pcb'))
    oldfps={f.GetReference():f for f in old.GetFootprints()}
    for name in ['backplane','teensy-adapter','analyser-msgeq7']:
        folder=ROOT/name
        parts={c['ref']:c for c in json.loads((folder/'circuit.json').read_text())['components']}
        coords=placements(name,oldfps)
        for suffix in ['', '-placed']:
            path=folder/(name+suffix+'.kicad_pcb')
            backup=work/(path.stem+'-before.kicad_pcb')
            if not backup.exists():shutil.copy2(path,backup)
            board=p.LoadBoard(str(path))
            old_zones=list(board.Zones())
            for zone in old_zones:board.Remove(zone)
            # MSGEQ7 wiring is unchanged; only its supply name changes.
            if name=='analyser-msgeq7':board.FindNet('IOREF').SetNetname('MEGA_5V')
            nets={plain(pad.GetNetname()):board.FindNet(pad.GetNetCode()) for fp in board.GetFootprints() for pad in fp.Pads() if pad.GetNetCode()}
            wanted={net for c in parts.values() for net in c['pins'].values() if net}
            for net in wanted:
                if net not in nets:
                    nets[net]=p.NETINFO_ITEM(board,net.replace('/','{slash}'))
                    board.Add(nets[net])
            ripped=set()
            for fp in list(board.GetFootprints()):
                ref=fp.GetReference()
                if ref not in parts:
                    if ref.startswith('H'):continue
                    board.Delete(fp)
                    continue
                c=parts[ref]
                fp.SetValue(c['value'])
                for pad in fp.Pads():
                    net=c['pins'].get(pad.GetNumber())
                    before=plain(pad.GetNetname())
                    if before and before!=net:ripped.add(before)
                    pad.SetNet(nets[net] if net else board.FindNet(0))
            present={f.GetReference() for f in board.GetFootprints()}
            for ref,c in parts.items():
                if ref not in present:
                    fp=p.FootprintLoad(str(LOCAL),c['footprint'].split(':')[1])
                    board.Add(fp);fp.SetReference(ref);fp.SetValue(c['value'])
                    if name=='teensy-adapter' and ref.startswith('CM'):fp.Flip(fp.GetPosition(),True)
                    x,y,a=coords[ref];fp.SetPosition(xy(x,y));fp.SetOrientationDegrees(a)
                    fp.SetFPID(p.LIB_ID('Shields',c['footprint'].split(':')[1]))
                    fp.Value().SetVisible(False)
                    for pad in fp.Pads():
                        net=c['pins'].get(pad.GetNumber())
                        pad.SetNet(nets[net] if net else board.FindNet(0))
            for fp in board.GetFootprints():
                c=parts.get(fp.GetReference())
                if not c:continue
                pathid=p.KIID_PATH()
                for u in (c['sheet_path'].strip('/')+'/'+c['uuid']).split('/'):
                    pathid.push_back(p.KIID(u))
                fp.SetPath(pathid)
            for track in list(board.GetTracks()):
                net=plain(track.GetNetname())
                if net not in wanted or net in ripped:board.Delete(track)
            board.BuildConnectivity()
            staged=work/path.name
            p.SaveBoard(str(staged),board)
            checked=p.LoadBoard(str(staged))
            actual={(f.GetReference(),pad.GetNumber()):plain(pad.GetNetname())
                    for f in checked.GetFootprints() for pad in f.Pads()}
            for ref,c in parts.items():
                for pin,net in c['pins'].items():
                    if net:assert actual.get((ref,pin))==net,(ref,pin,net)
            shutil.copy2(staged,path)
            print(path.name,'ripped',sorted(ripped),flush=True)
        root=(folder/(name+'.kicad_sch')).read_text()
        for sheet in folder.glob('*.kicad_sch'):
            if sheet.name!=name+'.kicad_sch' and sheet.name not in root:sheet.unlink()


if __name__=='__main__':main()
