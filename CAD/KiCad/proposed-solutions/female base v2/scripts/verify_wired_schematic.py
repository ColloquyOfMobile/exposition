"""Independently validate the reading copy using KiCad's exported connectivity."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
import pcbnew

HERE = Path(__file__).resolve().parents[1]
WIRED = HERE/'wired'
STEM = 'female-base-v2'
CLI = Path(sys.executable).parent/'kicad-cli.exe'


def groups(path):
    return {frozenset((n.get('ref'),n.get('pin')) for n in net.findall('node'))
            for net in ET.parse(path).findall('./nets/net')}


def main():
    expected=defaultdict(set)
    parts=json.loads((HERE/'circuit.json').read_text())['components']
    for p in parts:
        for pin,net in p['pins'].items():
            if net is not None:
                expected[net].add((p['ref'],pin))
    connected={frozenset(v) for v in expected.values()}
    unused={frozenset([(p['ref'],pin)]) for p in parts for pin,net in p['pins'].items() if net is None}
    results=[]
    with tempfile.TemporaryDirectory() as temp:
        for stem,source in [('original',HERE/(STEM+'.kicad_sch')),('wired',WIRED/(STEM+'-wired.kicad_sch'))]:
            target=Path(temp)/(stem+'.xml')
            subprocess.run([str(CLI),'sch','export','netlist','--format','kicadxml','-o',str(target),str(source)],check=True)
            actual=groups(target)
            assert connected <= actual, (stem,'missing or changed nets',connected-actual)
            assert actual-connected <= unused, (stem,'unexpected nets',actual-connected)
            components={n.get('ref'):n.findtext('value') for n in ET.parse(target).findall('./components/comp')}
            assert components == {p['ref']:p['value'] for p in parts}
            footprints={n.get('ref'):n.findtext('footprint') for n in ET.parse(target).findall('./components/comp')}
            assert footprints == {p['ref']:p['footprint'] for p in parts}, (stem,'footprints differ')
            results.append(actual)
        assert results[0]==results[1], 'Source and reading copy differ'
    board=pcbnew.LoadBoard(str(HERE/(STEM+'.kicad_pcb')))
    actual=defaultdict(set)
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            if pad.GetNetname() and not pad.GetNetname().startswith('unconnected-'):
                actual[pad.GetNetname()].add((fp.GetReference(),pad.GetNumber()))
    assert dict(actual)==dict(expected), 'PCB differs from circuit manifest'
    source=WIRED/(STEM+'-wired.kicad_sch')
    raw=source.read_text(encoding='utf-8')
    assert all(token not in raw for token in ['(label ','(global_label ','(hierarchical_label '])
    subprocess.run([str(CLI),'sch','erc','--format','json','--exit-code-violations','-o',str(WIRED/'erc.json'),str(source)],check=True)
    erc=json.loads((WIRED/'erc.json').read_text())
    assert not any(s['violations'] for s in erc['sheets'])
    report=dict(matches_original_v2_schematic=True,matches_pcb=True,matches_circuit_manifest=True,
                components=len(parts),connected_pins=sum(map(len,expected.values())),electrical_nets=len(expected),
                erc_violations=0,electrical_labels=0,
                sha256={str(p.relative_to(HERE)):hashlib.sha256(p.read_bytes()).hexdigest()
                        for p in [source,HERE/(STEM+'.kicad_sch'),HERE/(STEM+'.kicad_pcb'),HERE/'circuit.json']})
    (WIRED/'validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
