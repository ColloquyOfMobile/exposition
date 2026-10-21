"""Export checked manufacturer handoffs without modifying source PCBs.

Run with KiCad 9 Python. Each project receives manufacturing/<name>-manufacturing.zip.
"""
from pathlib import Path
import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
import pcbnew as p

ROOT=Path(__file__).resolve().parents[1]
CLI=Path('C:/Program Files/KiCad/9.0/bin/kicad-cli.exe')
NAMES=('backplane','teensy-adapter','voice-thomas','analyser-carrier','microphone')
WORK=ROOT.parents[2]/'tmp'/'manufacturing'
WORK.mkdir(parents=True,exist_ok=True)

def run(args):
    result=subprocess.run([str(CLI)]+list(map(str,args)),capture_output=True,text=True)
    if result.returncode:raise RuntimeError(result.stdout+result.stderr)

def build(name):
    folder=ROOT/name
    source=folder/(name+'.kicad_pcb')
    stage=Path(tempfile.mkdtemp(prefix=name+'-',dir=WORK))
    payload=stage/'package';payload.mkdir()
    assembly=payload/'assembly';assembly.mkdir()
    quality=payload/'checks';quality.mkdir()
    inputs=stage/'input';inputs.mkdir()
    board=p.LoadBoard(str(source))
    smd=[fp for fp in board.GetFootprints() if fp.GetAttributes() & p.FP_SMD]
    assert all(fp.GetLayer()==p.F_Cu for fp in smd),f'{name}: SMD parts must be on the front'
    outsourced=name in ('backplane','teensy-adapter','microphone')
    p.ZONE_FILLER(board).Fill(board.Zones())
    exported=inputs/source.name
    p.SaveBoard(str(exported),board)
    shutil.copy2(source.with_suffix('.kicad_pro'),exported.with_suffix('.kicad_pro'))
    shutil.copy2(folder/'fp-lib-table',inputs/'fp-lib-table')
    # Resolve the relative local footprint library for native DRC in staging.
    table=inputs/'fp-lib-table'
    table.write_text(table.read_text().replace('${KIPRJMOD}/../Shields.pretty',(ROOT/'Shields.pretty').as_posix()))
    run(['pcb','drc','--format','json','-o',quality/'drc.json',exported])
    drc=json.loads((quality/'drc.json').read_text())
    errors=[v for v in drc['violations'] if v['severity']=='error']
    if errors or drc['unconnected_items']:
        raise RuntimeError(f'{name}: DRC has {len(errors)} errors, {len(drc["unconnected_items"])} unconnected; {quality}')
    copper=[board.GetLayerName(layer) for layer in board.GetEnabledLayers().CuStack()]
    layers=copper+['F.Mask','B.Mask','F.SilkS','B.SilkS','Edge.Cuts']
    run(['pcb','export','gerbers','--layers',','.join(layers),'--subtract-soldermask','-o',str(payload)+'/',exported])
    run(['pcb','export','drill','--format','excellon','--drill-origin','absolute',
         '--excellon-units','mm','--excellon-zeros-format','decimal','--excellon-oval-format','route',
         '--excellon-separate-th','--generate-map','--map-format','svg','-o',str(payload)+'/',exported])
    for mapfile in list(payload.glob('*-drl_map.svg')):
        shutil.move(str(mapfile),str(assembly/mapfile.name))
    if outsourced:
        stencil=assembly/'stencil';stencil.mkdir()
        run(['pcb','export','gerbers','--layers','F.Paste','-o',str(stencil)+'/',exported])
    run(['pcb','export','pos','--format','csv','--side','both','--units','mm','--exclude-dnp',
         '-o',assembly/'positions-all.csv',exported])
    if outsourced:
        run(['pcb','export','pos','--format','csv','--side','front','--units','mm','--smd-only','--exclude-dnp',
             '-o',assembly/'positions-smd.csv',exported])
    for side in ('F','B'):
        run(['pcb','export','svg','--layers',f'{side}.Fab,{side}.Silkscreen,Edge.Cuts',
             '--page-size-mode','2','--exclude-drawing-sheet','-o',assembly/f'{side}-assembly.svg',exported])
    shutil.copy2(folder/'bom.csv',assembly/'bom.csv')
    for filename in ('README.md','mechanical.json','socket-assembly.csv','mounting-template.svg','variants.csv'):
        if (folder/filename).exists():shutil.copy2(folder/filename,assembly/filename)
    if (folder/'variants').exists():shutil.copytree(folder/'variants',assembly/'variants')
    shutil.copy2(ROOT/'ASSEMBLY.md',assembly/'system-assembly.md')
    # Native schematic netlist and ERC are useful reference evidence for the assembler.
    if (folder/'reports/schematic.net').exists():
        shutil.copy2(folder/'reports/schematic.net',assembly/'schematic.net')
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    thickness=p.ToMM(board.GetDesignSettings().GetBoardThickness())
    notes=f'''# {name} — manufacturer handoff

Bare-PCB fabrication files are at the ZIP root: Gerber X2 copper, solder mask,
silkscreen and board outline, plus separate PTH and NPTH Excellon drills.
Use Edge.Cuts as the finished outline. Drill slots use routed Excellon commands;
retain them as slots, not round holes. Do not mirror any supplied file.
Gerbers, drills and placement CSVs use the same absolute board origin and mm.

Layer count: {len(copper)}. Top-to-bottom copper: {', '.join(copper)}.
Finished board thickness: {thickness:g} mm. Supply rigid FR-4 boards.
Copper weight, surface finish, mask colour and the manufacturer's dielectric
stack-up are not specified here: confirm these quotation options before ordering.
No controlled-impedance fabrication requirement is declared in this package.
Quantity and panelisation are order choices; one unpanelised board is supplied.

Assembly policy: {'board maker places front SMD only; fit every through-hole part by hand' if outsourced else 'order bare boards; fit every part by hand' }.
{'Voice cards: solder the single 100K 0603 pull-down by hand with the pitch parts. No machine placement file or stencil is supplied.' if name=='voice-thomas' else 'Analyser carrier: no SMD parts to place; fit sockets and modified modules by hand.' if name=='analyser-carrier' else 'Only front SMD placement and front paste files are supplied for outsourced assembly.'}

assembly/ contains BOM, an all-component placement reference, top/bottom
assembly drawings, drill maps, and project assembly notes. Outsourced boards
also include a front SMD placement CSV and front stencil paste Gerber.
These are assembly references, not a fully procurement-qualified PCBA order:
some BOM MPNs are blank or descriptive, and purchased modules/composite socket
footprints require manual interpretation. Confirm exact parts, DNP/variant
population and assembler rotation conventions before machine assembly.
Do not interpret a module-outline footprint as a single pick-and-place part.
For voice-thomas choose ONE intended variant BOM; variants share the same PCB.

This is the current engineering prototype artwork. Read the enclosed project
notes for connector conversion, keying, insulation and fit checks. In particular,
the analyser carrier's module fit remains unverified physically. DRC checks
electrical/layout rules, not purchased-part fit or enclosure clearance.

Source: {source.name}
Source SHA-256: {source_hash}
Freshly refilled export: checked with KiCad {p.GetBuildVersion()}.
DRC errors: {len(errors)}; warnings: {len(drc['violations'])-len(errors)};
unconnected items: {len(drc['unconnected_items'])}. Full report: checks/drc.json.
The source KiCad PCB was not modified by packaging.
'''
    (payload/'README-manufacturing.md').write_text(notes)
    files={f.relative_to(payload).as_posix():{'bytes':f.stat().st_size,'sha256':hashlib.sha256(f.read_bytes()).hexdigest()}
           for f in sorted(payload.rglob('*')) if f.is_file()}
    assert list(payload.glob('*.drl')),name
    expected_ext={'.gtl','.gbl','.gts','.gbs','.gto','.gbo','.gm1'}
    assert expected_ext <= {f.suffix for f in payload.iterdir()}, list(payload.iterdir())
    for layer in range(1,len(copper)-1):
        assert len(list(payload.glob(f'*.g{layer}')))==1
    for suffix in ('PTH','NPTH'):
        drill=payload/(name+'-'+suffix+'.drl')
        assert drill.exists() and 'M30' in drill.read_text()
    manifest={'project':name,'source_sha256':source_hash,'exported_pcb_sha256':hashlib.sha256(exported.read_bytes()).hexdigest(),
              'assembly_policy':'front_smd_only' if outsourced else 'hand_assembled_bare_board',
              'copper_layers_top_to_bottom':copper,'thickness_mm':thickness,'drc_errors':len(errors),
              'drc_warnings':len(drc['violations'])-len(errors),'unconnected':0,'files':files}
    (payload/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    out=folder/'manufacturing';out.mkdir(exist_ok=True)
    archive=out/(name+'-manufacturing.zip')
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED) as z:
        for f in sorted(payload.rglob('*')):
            if f.is_file():z.write(f,f.relative_to(payload).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for filename,details in files.items():
            assert hashlib.sha256(z.read(filename)).hexdigest()==details['sha256']
    (out/'README.md').write_text(f'# Manufacturing package\n\nUpload `{archive.name}` for this PCB. Read the enclosed\n`README-manufacturing.md` before ordering or requesting assembly.\n\nRegenerate all active projects using KiCad Python with\n`scripts/manufacturing.py` from the shields directory.\n')
    print(name,archive.stat().st_size,'bytes;',len(files)+1,'files;',len(copper),'copper layers; DRC errors',len(errors),flush=True)
    return {'project':name,'zip':str(archive.relative_to(ROOT)),'sha256':hashlib.sha256(archive.read_bytes()).hexdigest(),
            'assembly_policy':'front_smd_only' if outsourced else 'hand_assembled_bare_board',
            'files':len(files)+1,'copper_layers':len(copper),'drc_errors':len(errors),'drc_warnings':len(drc['violations'])-len(errors),'unconnected':0}

if __name__=='__main__':
    # The active exporter covers the body boards too and validates exact BOM/CPL parity.
    import runpy
    runpy.run_path(str(ROOT.parents[2]/'export_jlcpcb.py'),run_name='__main__')
