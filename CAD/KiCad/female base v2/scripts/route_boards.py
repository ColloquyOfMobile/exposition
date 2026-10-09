"""Route both v2 boards with local Freerouting; KiCad 9 Python."""
from pathlib import Path
import subprocess
import pcbnew as p

CAD=Path(__file__).resolve().parents[2]
REPO=CAD.parents[1]
JAVA=Path('C:/Program Files/Android/Android Studio/jbr/bin/java.exe')
JAR=REPO/'tmp/shields-tools/freerouting-2.4.1.jar'
for folder,stem in [('female base v2','female-base-v2'),('male static v2','male-static-v2')]:
    root=CAD/folder
    work=REPO/'tmp/body-amplifier-route'/stem; work.mkdir(parents=True,exist_ok=True)
    board=p.LoadBoard(str(root/(stem+'-placed.kicad_pcb')))
    dsn=work/(stem+'.dsn'); ses=work/(stem+'.ses')
    assert p.ExportSpecctraDSN(board,str(dsn))
    cmd=[str(JAVA),'-Xmx2g','-Djava.awt.headless=true','-jar',str(JAR),
         '--gui.enabled=false','--api_server.enabled=false','--mcp_server.enabled=false',
         '--profile.allow_telemetry=false','--usage_and_diagnostic_data.disable_analytics=true',
         '--user_data_path='+str(work/'settings'),'--logging.file.location='+str(work),
         '--router.optimizer.max_passes=2','-mp','30','-mt','1','-da','-l','en','-de',str(dsn),'-do',str(ses)]
    print('Routing',stem,flush=True)
    with (work/'router.log').open('w') as log:
        subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT,cwd=work,check=True)
    assert p.ImportSpecctraSES(board,str(ses))
    p.SaveBoard(str(root/(stem+'.kicad_pcb')),board)
    print('Saved',stem,len(list(board.GetTracks())),'tracks/vias',flush=True)
