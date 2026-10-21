"""Compare independently exported connectivity, components and PCB pads."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import pcbnew

HERE = Path(__file__).resolve().parent
OUT = HERE/'wired'
CLI = Path(sys.executable).resolve().parent/'kicad-cli.exe'
sys.path.insert(0,str(HERE.parent/'scripts'))
from schematic_support import children, one, parse


def export(source, target):
    subprocess.run([str(CLI),'sch','export','netlist','--format','kicadxml',
                    '-o',str(target),str(source)],check=True)
    root=ET.parse(target)
    groups={frozenset((p.get('ref'),p.get('pin')) for p in n.findall('node')
                      if not p.get('ref').startswith('#')) for n in root.findall('./nets/net')}
    components={c.get('ref'):(c.findtext('value'),c.findtext('footprint'))
                for c in root.findall('./components/comp') if not c.get('ref').startswith('#')}
    return groups-{frozenset()},components


def main():
    original, original_parts=export(HERE/'teensy-adapter.kicad_sch',OUT/'original.net.xml')
    wired, wired_parts=export(OUT/'teensy-adapter-wired.kicad_sch',OUT/'wired.net.xml')
    expected=defaultdict(set)
    manifest=json.loads((HERE/'circuit.json').read_text())
    for p in manifest['components']:
        for pin,net in p['pins'].items():
            if net is not None:
                expected[net].add((p['ref'],pin))
    unused={(p['ref'],pin) for p in manifest['components'] for pin,n in p['pins'].items() if n is None}
    for groups in (original,wired):
        assert not any(len(group)>1 and group & unused for group in groups), 'Unused pin was connected'
    # KiCad may include or omit isolated NC contacts in its XML export.
    original={group for group in original if not group <= unused}
    wired={group for group in wired if not group <= unused}
    wanted={frozenset(pins) for pins in expected.values()}
    if original != wired:
        print('Missing groups:',original-wired)
        print('Unexpected groups:',wired-original)
    assert original == wired, 'Original and wired schematic connections differ'
    assert original_parts == wired_parts, 'Component values / footprints differ'
    assert wanted == wired, 'Manifest and wired schematic differ'
    pcb=defaultdict(set)
    board=pcbnew.LoadBoard(str(HERE/'teensy-adapter.kicad_pcb'))
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname():
                pcb[pad.GetNetname().replace('{slash}','/')].add((fp.GetReference(),pad.GetNumber()))
    assert dict(pcb) == dict(expected), 'PCB and manifest differ'
    subprocess.run([str(CLI),'sch','erc','--format','json','-o',str(OUT/'erc.json'),
                    str(OUT/'teensy-adapter-wired.kicad_sch')],check=True)
    erc=json.loads((OUT/'erc.json').read_text())
    violations=[v for sheet in erc['sheets'] for v in sheet['violations']]
    text=(OUT/'teensy-adapter-wired.kicad_sch').read_text(encoding='utf-8')
    assert all('('+k+' ' not in text for k in ('global_label','label','hierarchical_label'))
    drawing=parse(text)
    symbols=children(drawing,'symbol')
    embedded=children(drawing,'lib_symbols')[0]
    for ref in ('U1','U2','U3','U4'):
        instances=[symbol for symbol in symbols if any(
            prop[1:3]==['Reference',ref] for prop in children(symbol,'property'))]
        assert len(instances)==1 and one(instances[0],'unit')=='1', ref+' must have one complete block'
        name='Colloquy:3to5V_Shifter_'+ref
        assert one(instances[0],'lib_id')==name, ref+' must have a descriptive shifter basename'
        definition=next(symbol for symbol in children(embedded,'symbol') if symbol[1]==name)
        units=children(definition,'symbol')
        assert len(units)==1
        assert {one(pin,'number') for pin in children(units[0],'pin')}=={str(i) for i in range(1,15)}
    report=dict(components=len(original_parts),connected_pins=sum(map(len,expected.values())),
                electrical_nets=len(expected),matches_original_schematic=True,
                matches_original_components_values_footprints=True,matches_pcb=True,
                matches_manifest=True,electrical_labels=0,shifter_blocks=4,
                each_shifter_has_all_14_pins=True,erc_violations=len(violations),
                erc_types=sorted({v['type'] for v in violations}),
                sha256={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in [HERE/'circuit.json',HERE/'teensy-adapter.kicad_pcb',
                                  OUT/'teensy-adapter-wired.kicad_sch',
                                  *sorted(HERE.glob('*.kicad_sch'))]})
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='sha256'},indent=2))
    assert not violations, 'Resolve ERC diagnostics before delivery'


if __name__=='__main__':
    main()
