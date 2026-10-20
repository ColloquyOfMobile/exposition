"""Route the manually edited 2026-10-20 placement with KiCad 9 Python.

Keep the placement checkpoint intact. The protected speaker paths and sensor
corridors below are specific to this placement; native DRC checks the result.
"""
from pathlib import Path
import hashlib
import json
import subprocess
import pcbnew as p

ROOT = Path(__file__).resolve().parents[4]
FOLDER = ROOT / 'CAD/KiCad/male static v2'
WORK = ROOT / 'tmp/male-placement-reroute'
WORK.mkdir(exist_ok=True)
board = p.LoadBoard(str(FOLDER / 'male-static-v2-placed.kicad_pcb'))
p.SaveBoard(str(WORK / 'placement-before.kicad_pcb'), board)
removed = list(board.GetTracks())
for item in removed:
    board.Remove(item)
pads = {(f.GetReference(), a.GetNumber()): a for f in board.GetFootprints() for a in f.Pads()}
def at(ref, pin):
    return tuple(p.ToMM(pads[ref, str(pin)].GetPosition()))
def xy(pt):
    return p.VECTOR2I(*(p.FromMM(v) for v in pt))

assert at('M1', 1) == (56.88, 65.08), 'Adapt protected routes to the new socket placement'
assert at('J6', 1) == (48.5, 89.0), 'Adapt protected routes to the new speaker placement'

def path(net, points, layer=p.F_Cu, width=.25):
    for a, b in zip(points, points[1:]):
        t = p.PCB_TRACK(board)
        t.SetStart(xy(a)); t.SetEnd(xy(b)); t.SetLayer(layer)
        t.SetWidth(p.FromMM(width)); t.SetNet(board.FindNet(net)); t.SetLocked(True)
        board.Add(t)

old_zones = list(board.Zones())
for zone in old_zones:
    if not zone.GetIsRuleArea():
        board.Remove(zone)

# Keep the bridge output pair together, below the rotated contact row.
path('AMP_OUT_P', [at('M1',10), (36,67.06), (36,68), (42.5,74.5), (42.5,79), (48.5,85), at('J6',1)], width=.8)
path('AMP_OUT_N', [at('M1',11), (33.5,67.1), (33.5,67.5), (40.5,74.5), (40.5,79.5), (45,84), (45,89), (48,92), (51,92), at('J6',2)], width=.8)
# Reserve the left-hand sensor corridor before routing the remaining nets.
path('photo sensor male output c', [at('J7',5), (51.385,37), (29.7,58.685), (29.7,68.5), (28.7,69.5), (28.7,94.5), (33.5,94.5), at('J1',3)], p.B_Cu)
path('photo sensor male output d', [at('J7',13), (52.77,30.1), (40,30.1), (27.5,42.6), (27.5,104.5), (33.5,104.5), at('J4',3)], p.B_Cu)
board.BuildConnectivity()
dsn = WORK / 'male-static-v2.dsn'
ses = WORK / 'male-static-v2.ses'
assert p.ExportSpecctraDSN(board, str(dsn))
java = 'C:/Program Files/Android/Android Studio/jbr/bin/java.exe'
jar = ROOT / 'tmp/shields-tools/freerouting-2.4.1.jar'
cmd = [java, '-Xmx2g', '-Djava.awt.headless=true', '-jar', str(jar),
       '--gui.enabled=false', '--api_server.enabled=false', '--mcp_server.enabled=false',
       '--profile.allow_telemetry=false', '--usage_and_diagnostic_data.disable_analytics=true',
       '--user_data_path='+str(WORK/'settings'), '--logging.file.location='+str(WORK),
       '--router.optimizer.max_passes=2', '-mp','30','-mt','1','-da','-l','en',
       '-de',str(dsn),'-do',str(ses)]
with (WORK/'router.log').open('w') as log:
    subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=WORK, check=True)
assert p.ImportSpecctraSES(board, str(ses))
for layer in (p.F_Cu, p.B_Cu):
    zone = p.ZONE(board); zone.SetZoneName('LOCAL_SUPPLY_GND')
    zone.SetNet(board.FindNet('GND')); zone.SetLayer(layer)
    zone.SetLocalClearance(p.FromMM(.25)); zone.SetMinThickness(p.FromMM(.2))
    zone.SetPadConnection(p.ZONE_CONNECTION_FULL)
    zone.SetIslandRemovalMode(p.ISLAND_REMOVAL_MODE_ALWAYS)
    zone.Outline().NewOutline()
    for pt in [(25.5,20.5),(74.5,20.5),(74.5,109.5),(25.5,109.5)]:
        zone.Outline().Append(*xy(pt))
    board.Add(zone)
board.BuildConnectivity()
p.ZONE_FILLER(board).Fill(board.Zones())
p.SaveBoard(str(FOLDER/'male-static-v2.kicad_pcb'), board)
print('Saved routed board:', len(list(board.GetTracks())), 'tracks/vias')

cli = 'C:/Program Files/KiCad/9.0/bin/kicad-cli.exe'
report = FOLDER / 'reports/drc.json'
subprocess.run([cli, 'pcb', 'drc', '--schematic-parity', '--format', 'json',
                '-o', str(report), str(FOLDER/'male-static-v2.kicad_pcb')], check=True)
drc = json.loads(report.read_text())
assert not drc['violations'] and not drc['unconnected_items'], 'Inspect reports/drc.json'

def placement(b):
    return sorted((f.GetReference(), tuple(p.ToMM(f.GetPosition())), f.GetOrientationDegrees(),
                   sorted((a.GetNumber(), tuple(p.ToMM(a.GetPosition())), a.GetNetname(),
                           tuple(p.ToMM(a.GetDrillSize()))) for a in f.Pads()))
                  for f in b.GetFootprints())

source = p.LoadBoard(str(FOLDER/'male-static-v2-placed.kicad_pcb'))
assert placement(source) == placement(board), 'Routing changed component placement or pad nets'
assert {v['type'] for v in drc['schematic_parity']} <= {'missing_footprint'}
assert all('H1 ' in v['description'] or 'H2 ' in v['description'] for v in drc['schematic_parity'])
tracks = [t for t in board.GetTracks() if not isinstance(t, p.PCB_VIA)]
def digest(path):
    return hashlib.sha256(path.read_bytes().replace(b'\r\n', b'\n')).hexdigest()
validation = {
    'source_sha256': digest(FOLDER/'male-static-v2.kicad_pcb'),
    'placement_sha256': digest(FOLDER/'male-static-v2-placed.kicad_pcb'),
    'placement_and_pad_nets_preserved': 'PASS',
    'drc_violations': len(drc['violations']),
    'unconnected_items': len(drc['unconnected_items']),
    'schematic_parity': drc['schematic_parity'],
    'routing_lengths_mm': {net: round(sum(p.ToMM(t.GetLength()) for t in tracks if t.GetNetname()==net), 3)
                           for net in ('AMP_OUT_P','AMP_OUT_N','AMP_INPUT','LINE_IN','AUDIO_RETURN')},
    'speaker_layer': 'F.Cu',
    'speaker_minimum_width_mm': min(p.ToMM(t.GetWidth()) for t in tracks if t.GetNetname() in ('AMP_OUT_P','AMP_OUT_N')),
    'ground_pours': 'F.Cu and B.Cu, supply GND only',
    'hardware_validation': 'Not performed',
    'previous_revision_D_routing_geometry_checks': 'Superseded by manual placement; not asserted',
}
(FOLDER/'reports/validation.json').write_text(json.dumps(validation, indent=2)+'\n')
