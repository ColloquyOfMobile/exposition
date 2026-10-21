"""Migrate the initial boards to the 2026-10-04 simplified specification.

Run once against the original routed/placed boards after design.py. Preserves
mechanical positions and unaffected copper; rip changed nets for re-routing.
"""
import json
import pcbnew as p
from design import ROOT,BASE
from boards import make_slots,placements,xy,LOCAL

def plain(s):return s.replace('{slash}','/').replace('{space}',' ')
def encoded(s):return s.replace('/','{slash}')

make_slots()
old=p.LoadBoard(str(BASE/'colloquy-control-v2.kicad_pcb'))
oldfps={f.GetReference():f for f in old.GetFootprints()}
for folder in ROOT.iterdir():
    if not (folder/'circuit.json').exists():continue
    name=folder.name;data=json.loads((folder/'circuit.json').read_text());parts={c['ref']:c for c in data['components']}
    coords=placements(name,oldfps)
    for path in [folder/(name+'.kicad_pcb'),folder/(name+'-placed.kicad_pcb')]:
        board=p.LoadBoard(str(path));old_zones=list(board.Zones())
        for z in old_zones:board.Remove(z)
        if name=='teensy-adapter':
            renames={26:24,27:25,38:26,39:27,40:38,41:39}
            for fp in board.GetFootprints():
                ref=fp.GetReference()
                for prefix in ['RA','RB','CA']:
                    if ref.startswith(prefix) and int(ref[len(prefix):]) in renames:fp.SetReference(prefix+str(renames[int(ref[len(prefix):])]))
        nets={plain(n.GetNetname()):n for n in board.GetNetsByNetcode().values()}
        wanted={net for c in parts.values() for net in c['pins'].values() if net}
        for net in wanted:
            if net not in nets:
                n=p.NETINFO_ITEM(board,encoded(net));board.Add(n);nets[net]=n
        changed=set()
        # Entire affected analogue networks are rebuilt, including the local dividers.
        if name=='teensy-adapter':changed.update('adc/'+str(n) for n in [24,25,26,27,38,39,40,41])
        for fp in list(board.GetFootprints()):
            ref=fp.GetReference()
            if ref.startswith('HM'):continue
            if ref not in parts:
                board.Remove(fp);continue
            c=parts[ref]
            if ref.startswith('JV') or ref=='JA1':
                position=fp.GetPosition();angle=fp.GetOrientationDegrees();bottom=fp.GetLayer()==p.B_Cu
                board.Remove(fp);fp=p.FootprintLoad(str(LOCAL),c['footprint'].split(':')[1]);board.Add(fp)
                if bottom:fp.Flip(fp.GetPosition(),True)
                fp.SetPosition(position);fp.SetOrientationDegrees(angle);fp.SetReference(ref)
            fp.SetValue(c['value']);fp.SetFPID(p.LIB_ID('Shields',c['footprint'].split(':')[1]))
            for pad in fp.Pads():
                pin=pad.GetNumber();net=c['pins'].get(pin);before=plain(pad.GetNetname())
                if before and before!=net:changed.add(before)
                if net and before!=net:changed.add(net)
                pad.SetNet(nets[net] if net else board.FindNet(0))
        present={f.GetReference() for f in board.GetFootprints()}
        for ref,c in parts.items():
            if ref in present:continue
            fp=p.FootprintLoad(str(LOCAL),c['footprint'].split(':')[1]);board.Add(fp)
            fp.SetReference(ref);fp.SetValue(c['value']);x,y,a=coords[ref];fp.SetPosition(xy(x,y));fp.SetOrientationDegrees(a)
            fp.SetFPID(p.LIB_ID('Shields',c['footprint'].split(':')[1]))
            for pad in fp.Pads():
                net=c['pins'].get(pad.GetNumber());pad.SetNet(nets[net] if net else board.FindNet(0))
        for t in list(board.GetTracks()):
            net=plain(t.GetNetname())
            if net not in wanted or net in changed:board.Delete(t)
        board.BuildConnectivity();p.SaveBoard(str(path),board)
        print(path.name,'ripped',sorted(changed),flush=True)
    # Remove sheets no longer referenced by the regenerated root.
    root=(folder/(name+'.kicad_sch')).read_text()
    for f in folder.glob('*.kicad_sch'):
        if f.name!=name+'.kicad_sch' and f.name not in root:f.unlink()
