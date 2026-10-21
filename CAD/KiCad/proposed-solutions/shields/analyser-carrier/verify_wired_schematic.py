"""Independently compare KiCad-exported connectivity with the source and PCB."""
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import pcbnew

HERE = Path(__file__).resolve().parent
WIRED = HERE/'wired'
CLI = Path(sys.executable).resolve().parent/'kicad-cli.exe'


def groups_from_netlist(path):
    root = ET.parse(path)
    return {
        frozenset((p.get('ref'), p.get('pin')) for p in net.findall('node') if not p.get('ref').startswith('#'))
        for net in root.findall('./nets/net') if not net.get('name', '').startswith('unconnected-')
    } - {frozenset()}


def main():
    with tempfile.TemporaryDirectory(prefix='analyser-wired-') as temp:
        netlists = []
        for stem, source in [('original', HERE/'analyser-carrier.kicad_sch'),
                             ('wired', WIRED/'analyser-carrier-wired.kicad_sch')]:
            target = Path(temp)/(stem+'.xml')
            subprocess.run([str(CLI), 'sch', 'export', 'netlist', '--format', 'kicadxml',
                            '-o', str(target), str(source)], check=True)
            netlists.append(groups_from_netlist(target))
        assert netlists[0] == netlists[1], 'Original and wired schematic connections differ'
        original = ET.parse(Path(temp)/'original.xml')
        wired = ET.parse(Path(temp)/'wired.xml')
        def component_table(tree):
            return {p.get('ref'): (p.findtext('value'), p.findtext('footprint'))
                    for p in tree.findall('./components/comp')}
        assert component_table(original) == component_table(wired), 'Components changed'
        for tree in (original, wired):
            nc = {frozenset((p.get('ref'),p.get('pin')) for p in net.findall('node'))
                  for net in tree.findall('./nets/net') if net.get('name','').startswith('unconnected-')}
            assert nc == {frozenset({('JA1','20')}), frozenset({('JA1','21')})}
        expected = defaultdict(set)
        manifest = json.loads((HERE/'circuit.json').read_text())
        for part in manifest['components']:
            for pin, net in part['pins'].items():
                if net is not None: expected[net].add((part['ref'], pin))
        assert netlists[1] == {frozenset(pins) for pins in expected.values()}
        board = pcbnew.LoadBoard(str(HERE/'analyser-carrier.kicad_pcb'))
        actual = defaultdict(set)
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                if pad.GetNetname():
                    actual[pad.GetNetname().replace('{slash}', '/')].add((fp.GetReference(), pad.GetNumber()))
        assert dict(actual) == dict(expected), 'PCB and circuit manifest differ'
        subprocess.run([str(CLI), 'sch', 'erc', '--format', 'json', '--exit-code-violations',
                        '-o', str(Path(temp)/'erc.json'),
                        str(WIRED/'analyser-carrier-wired.kicad_sch')], check=True)
        erc = json.loads((Path(temp)/'erc.json').read_text())
        assert not any(sheet['violations'] for sheet in erc['sheets'])
        (WIRED/'erc.json').write_text(json.dumps(erc,indent=2)+'\n')
    schematic = WIRED/'analyser-carrier-wired.kicad_sch'
    text = schematic.read_text(encoding='utf-8')
    assert '(global_label ' not in text and '(label ' not in text and '(hierarchical_label ' not in text
    report = {
        'connected_pins': sum(map(len, expected.values())),
        'electrical_nets': len(expected),
        'matches_original_schematic': True,
        'matches_circuit_manifest': True,
        'matches_pcb': True,
        'erc_violations': 0,
        'electrical_labels': 0,
        'components_unchanged': True,
        'unused_pins_unchanged': ['JA1.20', 'JA1.21'],
        'sha256': {str(p.relative_to(HERE)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in [HERE/'analyser-carrier.kicad_pcb', HERE/'circuit.json', schematic,
                             *sorted(HERE.glob('*.kicad_sch'))]},
    }
    (WIRED/'validation.json').write_text(json.dumps(report, indent=2)+'\n')
    print(f'PASS: {report["connected_pins"]} connected pins / {report["electrical_nets"]} nets; original schematic, manifest and PCB agree; ERC clean.')


if __name__ == '__main__':
    main()

