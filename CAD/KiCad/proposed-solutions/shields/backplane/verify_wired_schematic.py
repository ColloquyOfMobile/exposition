"""Compare independently exported connectivity, components and PCB pads."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

import pcbnew

sys.path.insert(0,str(Path(__file__).resolve().parent.parent/'scripts'))
import schematic_support as s

HERE = Path(__file__).resolve().parent
OUT = HERE/'wired'
CLI = Path(sys.executable).resolve().parent/'kicad-cli.exe'


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
    original, original_parts=export(HERE/'backplane.kicad_sch',OUT/'original.net.xml')
    wired, wired_parts=export(OUT/'backplane-wired.kicad_sch',OUT/'wired.net.xml')
    expected=defaultdict(set)
    manifest=json.loads((HERE/'circuit.json').read_text())
    omitted={p['ref'] for p in manifest['components'] if p['ref'].startswith('TP')}
    original_parts={ref:value for ref,value in original_parts.items() if ref not in omitted}
    original={frozenset((ref,pin) for ref,pin in group if ref not in omitted) for group in original}
    original.discard(frozenset())
    for p in manifest['components']:
        if p['ref'] in omitted:
            continue
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
    board=pcbnew.LoadBoard(str(HERE/'backplane.kicad_pcb'))
    for fp in board.GetFootprints():
        if fp.GetReference() in omitted:
            continue
        for pad in fp.Pads():
            if pad.GetNetname():
                pcb[pad.GetNetname().replace('{slash}','/')].add((fp.GetReference(),pad.GetNumber()))
    assert dict(pcb) == dict(expected), 'PCB and manifest differ'
    subprocess.run([str(CLI),'sch','erc','--format','json','-o',str(OUT/'erc.json'),
                    str(OUT/'backplane-wired.kicad_sch')],check=True)
    erc=json.loads((OUT/'erc.json').read_text())
    violations=[v for sheet in erc['sheets'] for v in sheet['violations']]
    text=(OUT/'backplane-wired.kicad_sch').read_text(encoding='utf-8')
    assert all('('+k+' ' not in text for k in ('global_label','label','hierarchical_label'))
    native=s.parse(text)
    stock_name='Connector:DA15_Pins_MountingHoles'
    embedded=next(sym for sym in s.children(s.children(native,'lib_symbols')[0],'symbol') if sym[1]==stock_name)
    stock_library=s.parse((CLI.parent.parent/'share/kicad/symbols/Connector.kicad_sym').read_text(encoding='utf-8'))
    stock=next(sym for sym in s.children(stock_library,'symbol') if sym[1]=='DA15_Pins_MountingHoles')
    stock[1]=stock_name
    assert embedded==stock,'The D-sub artwork must remain the unmodified KiCad default'
    instances=s.children(native,'symbol')
    for ref in ['A1','JA1','JV1','JV2','JV3','JV4','JV5','J1','J5','A-J3','B-J4']:
        matching=[obj for obj in instances if any(p[1:3]==['Reference',ref] for p in s.children(obj,'property'))]
        assert len(matching)==1 and s.one(matching[0],'unit')=='1',('Interface split into multiple symbols',ref)
    report=dict(components=len(original_parts),connected_pins=sum(map(len,expected.values())),
                electrical_nets=len(expected),matches_original_schematic_except_omitted_testpoints=True,
                omitted_testpoints=sorted(omitted),
                matches_original_components_values_footprints=True,matches_pcb=True,
                matches_manifest=True,electrical_labels=0,erc_violations=len(violations),
                stock_dsub_symbols_unmodified=True,interfaces_drawn_as_single_blocks=True,
                erc_types=sorted({v['type'] for v in violations}),
                sha256={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in [HERE/'circuit.json',HERE/'backplane.kicad_pcb',
                                  OUT/'backplane-wired.kicad_sch',
                                  *sorted(HERE.glob('*.kicad_sch'))]})
    (OUT/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='sha256'},indent=2))
    assert not violations, 'Resolve ERC diagnostics before delivery'


if __name__=='__main__':
    main()
