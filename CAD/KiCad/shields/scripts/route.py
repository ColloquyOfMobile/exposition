"""Route staging layouts locally with Freerouting; preserve DSN/SES and logs.

Use --work for intermediates, --jar for the official Freerouting 2.4.1 release.
Only this explicit command replaces a routed PCB.
"""
import argparse
import concurrent.futures
import json
from pathlib import Path
import subprocess
import pcbnew as p
from design import ROOT


def route(folder,args):
    name=folder.name;work=args.work/name;work.mkdir(parents=True,exist_ok=True)
    board=p.LoadBoard(str(folder/(name+('.kicad_pcb' if args.from_routed else '-placed.kicad_pcb'))))
    previous_zones=list(board.Zones())
    for z in previous_zones:board.Remove(z)
    board.SetCopperLayerCount(2)  # Internal planes are re-added after routing.
    violations=set()
    if args.rip_violations:
        report=json.loads((folder/'reports/drc.json').read_text())
        violations={i['uuid'] for v in report['violations'] if v['severity']=='error' for i in v['items']}
    for track in list(board.GetTracks()):
        if track.GetNetname().replace('{slash}','/') in (args.rip_net or []) or track.m_Uuid.AsString() in violations:board.Delete(track)
    ns=board.GetDesignSettings().m_NetSettings
    ns.ClearNetclasses();ns.ClearNetclassPatternAssignments();ns.ClearNetclassLabelAssignments()
    for cls,width in [('Default',.25),('Power',1.5 if name=='backplane' else .5)]:
        nc=p.NETCLASS(cls);nc.SetClearance(p.FromMM(.2));nc.SetTrackWidth(p.FromMM(width))
        nc.SetViaDiameter(p.FromMM(.6));nc.SetViaDrill(p.FromMM(.3))
        if cls=='Default':ns.SetDefaultNetclass(nc)
        else:
            ns.SetNetclass(cls,nc)
            for net in ['+5V','+12V']:ns.SetNetclassPatternAssignment(net,cls)
    ns.ClearAllCaches();board.SynchronizeNetsAndNetClasses(False)
    dsn=work/(name+'.dsn');ses=work/(name+'.ses')
    if not p.ExportSpecctraDSN(board,str(dsn)):raise RuntimeError('DSN export failed: '+name)
    cmd=[str(args.java),'-Xmx2g','-Djava.awt.headless=true','-jar',str(args.jar),
         '--gui.enabled=false','--api_server.enabled=false','--mcp_server.enabled=false','--profile.allow_telemetry=false',
         '--usage_and_diagnostic_data.disable_analytics=true','-da','-l','en',
         '--user_data_path='+str(work/'settings'),'--logging.file.location='+str(work),
         '--router.optimizer.max_passes=2','-mp','40','-mt','1','-de',str(dsn),'-do',str(ses)]
    with (work/'router.log').open('w') as log:
        result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,cwd=work)
    if result.returncode or not ses.exists():raise RuntimeError(f'{name}: routing failed; see {work}/router.log')
    if not p.ImportSpecctraSES(board,str(ses)):raise RuntimeError('SES import failed: '+name)
    p.SaveBoard(str(folder/(name+'.kicad_pcb')),board)
    print(name,'routed',len(list(board.GetTracks())),'tracks/vias',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--jar',type=Path,required=True)
    parser.add_argument('--java',type=Path,default=Path(r'C:\Program Files\Android\Android Studio\jbr\bin\java.exe'))
    parser.add_argument('--work',type=Path,required=True);parser.add_argument('--only',nargs='*')
    parser.add_argument('--from-routed',action='store_true');parser.add_argument('--rip-net',nargs='*')
    parser.add_argument('--rip-violations',action='store_true')
    args=parser.parse_args();args.jar=args.jar.resolve();args.work=args.work.resolve()
    folders=[f for f in ROOT.iterdir() if (f/'circuit.json').exists() and (not args.only or f.name in args.only)]
    # pcbnew serialization is kept sequential; router jobs can be run separately.
    for folder in folders:route(folder,args)

