"""Native KiCad ERC, DRC and schematic-to-PCB pin/net parity reports."""
from pathlib import Path
import collections
import concurrent.futures
import json
import subprocess
import shutil
import pcbnew as p
from design import ROOT
import schematic_support as s

CLI=Path(r'C:\Program Files\KiCad\9.0\bin\kicad-cli.exe')


def run(folder):
    name=folder.name;reports=folder/'reports';reports.mkdir(exist_ok=True)
    sch=folder/(name+'.kicad_sch')
    expected_svg={name+'.svg'}|{name+'-'+s.stem+'.svg' for s in folder.glob('*.kicad_sch') if s!=sch}
    for old_svg in (reports/'schematic').glob('*.svg'):
        if old_svg.name not in expected_svg:old_svg.unlink()
    board=folder/(name+'.kicad_pcb')
    if not board.exists():board=folder/(name+'-placed.kicad_pcb')
    if board.stem.endswith('-placed'):shutil.copy2(folder/(name+'.kicad_pro'),board.with_suffix('.kicad_pro'))
    commands=[['sch','erc','--format','json','-o',str(reports/'erc.json'),str(sch)],
              ['sch','export','netlist','-o',str(reports/'schematic.net'),str(sch)],
              ['pcb','drc','--format','json','-o',str(reports/'drc.json'),str(board)],
              ['pcb','export','pos','--format','csv','--side','both','--units','mm','--smd-only','-o',str(folder/'positions.csv'),str(board)],
              ['sch','export','svg','-o',str(reports/'schematic'),str(sch)],
              ['pcb','export','svg','--layers','F.Cu,F.Silkscreen,Edge.Cuts','--page-size-mode','2','--exclude-drawing-sheet','-o',str(reports/'board.svg'),str(board)],
              ['pcb','export','svg','--layers','F.Fab,F.Silkscreen,Edge.Cuts,Dwgs.User','--page-size-mode','2','--exclude-drawing-sheet','-o',str(reports/'assembly-front.svg'),str(board)],
              ['pcb','export','svg','--layers','B.Fab,B.Silkscreen,Edge.Cuts','--page-size-mode','2','--exclude-drawing-sheet','-o',str(reports/'assembly-back.svg'),str(board)]]
    logs=[]
    for cmd in commands:
        result=subprocess.run([str(CLI)]+cmd,capture_output=True,text=True)
        logs.append(' '.join(cmd)+'\n'+result.stdout+result.stderr)
        if result.returncode:raise RuntimeError(logs[-1])
    (reports/'commands.log').write_text('\n'.join(logs))
    erc=json.loads((reports/'erc.json').read_text());drc=json.loads((reports/'drc.json').read_text())
    print(name,'ERC',dict(collections.Counter(v['type'] for sh in erc['sheets'] for v in sh['violations'])),
          'DRC',dict(collections.Counter(v['type'] for v in drc['violations'])),'unconnected',len(drc['unconnected_items']),flush=True)


if __name__=='__main__':
    folders=[f for f in ROOT.iterdir() if (f/'circuit.json').exists()]
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:list(pool.map(run,folders))
