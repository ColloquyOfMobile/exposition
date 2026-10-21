"""Route both v2 boards with local Freerouting; KiCad 9 Python."""
from pathlib import Path
import argparse
import subprocess
import pcbnew as p

CAD=Path(__file__).resolve().parents[2]
REPO=CAD.parents[2]
JAVA=Path('C:/Program Files/Android/Android Studio/jbr/bin/java.exe')
JAR=REPO/'tmp/shields-tools/freerouting-2.4.1.jar'
parser=argparse.ArgumentParser()
parser.add_argument('--only',choices=('female-base-v2','male-static-v2'))
parser.add_argument('--from-routed',action='store_true')
parser.add_argument('--max-passes',type=int,default=30)
args=parser.parse_args()
for folder,stem in [('female base v2','female-base-v2'),('male static v2','male-static-v2')]:
    if args.only and stem!=args.only:continue
    root=CAD/folder
    work=REPO/'tmp/body-amplifier-route'/stem; work.mkdir(parents=True,exist_ok=True)
    board=p.LoadBoard(str(root/(stem+('' if args.from_routed else '-placed')+'.kicad_pcb')))
    if not args.from_routed:
        from analogue_routes import prepare
        prepare(board,stem)
    # Keep removed SWIG wrappers alive through DSN/SES import and serialization.
    old_zones=list(board.Zones())
    for zone in old_zones:
        if not zone.GetIsRuleArea():board.Remove(zone)
    dsn=work/(stem+'.dsn'); ses=work/(stem+'.ses')
    assert p.ExportSpecctraDSN(board,str(dsn))
    cmd=[str(JAVA),'-Xmx2g','-Djava.awt.headless=true','-jar',str(JAR),
         '--gui.enabled=false','--api_server.enabled=false','--mcp_server.enabled=false',
         '--profile.allow_telemetry=false','--usage_and_diagnostic_data.disable_analytics=true',
         '--user_data_path='+str(work/'settings'),'--logging.file.location='+str(work),
         '--router.optimizer.max_passes=2','-mp',str(args.max_passes),'-mt','1','-da','-l','en','-de',str(dsn),'-do',str(ses)]
    print('Routing',stem,flush=True)
    with (work/'router.log').open('w') as log:
        subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,cwd=work,check=True)
    assert p.ImportSpecctraSES(board,str(ses))
    p.SaveBoard(str(root/(stem+'.kicad_pcb')),board)
    print('Saved',stem,len(list(board.GetTracks())),'tracks/vias',flush=True)
