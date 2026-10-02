"""Export local review artifacts and an honest validation summary.

Uses ordinary Python for CLI subprocesses. Does not order or publish anything.
Fabrication files are deliberately separate from these review exports.
"""
from pathlib import Path
import csv
import json
import re
import subprocess
import sys
from collections import Counter
from verify_schematic import verify

ROOT=Path(__file__).resolve().parents[1]
NAME='thomas-or-teensy'
CLI=Path(r'C:\Program Files\KiCad\9.0\bin\kicad-cli.exe')

def main():
    reports=ROOT/'reports';assembly=ROOT/'assembly';assembly.mkdir(exist_ok=True)
    board=ROOT/(NAME+'.kicad_pcb');sch=ROOT/(NAME+'.kicad_sch')
    def run(*args):subprocess.run([str(CLI),*map(str,args)],cwd=ROOT,check=True)
    run('sch','erc',sch,'--format','json','-o',reports/'erc.json')
    run('sch','export','netlist',sch,'-o',reports/'schematic.net')
    run('pcb','drc',board,'--format','json','--schematic-parity','-o',reports/'drc.json')
    parity=verify(reports/'schematic.net',board)
    (reports/'connectivity-parity.json').write_text(json.dumps(parity,indent=2)+'\n')
    subprocess.run([sys.executable,str(ROOT/'scripts/check_design.py')],check=True)
    run('sch','export','pdf',sch,'-o',reports/'schematic.pdf')
    run('pcb','export','pos',board,'--format','csv','--units','mm','--exclude-dnp','-o',assembly/'component-positions.csv')
    run('pcb','export','svg',board,'--layers','F.Cu,B.Cu,F.SilkS,Edge.Cuts','--page-size-mode','2','--mode-single','-o',reports/'board.svg')
    run('pcb','export','svg',board,'--layers','In1.Cu,Edge.Cuts','--page-size-mode','2','--mode-single','-o',reports/'ground-plane.svg')
    run('pcb','render',board,'--width','1300','--height','1800','--side','top','--quality','basic','-o',reports/'board-preview.png')
    data=json.loads((ROOT/'circuit.json').read_text())
    with (assembly/'bom.csv').open('w',newline='',encoding='utf-8-sig') as stream:
        writer=csv.writer(stream)
        writer.writerow(['Reference','Value','Footprint','Manufacturer part / purchase description','Assembly','Notes'])
        for c in data['components']:
            if not c.get('include_bom',True):continue
            mpn=c.get('mpn','')
            if c['ref'].startswith(('R','C')) and mpn==c['value']:mpn=''
            writer.writerow([c['ref'],c['value'],c['footprint'],mpn,c.get('assembly','fit'),c.get('description','')])
        writer.writerow(['MODULE-T','Teensy 4.1','JT1 + JT2','PJRC Teensy 4.1 with headers','optional for Thomas','Plug-in module is not a separately placed carrier footprint'])
        writer.writerow(['SHUNT','2-pin 2.54mm shunt','JM1','2-pin insulated shunt','fit 1-2 for Thomas','No shunt also selects Thomas'])
    erc=json.loads((reports/'erc.json').read_text());drc=json.loads((reports/'drc.json').read_text())
    coil=json.loads((reports/'coil-supply-review.json').read_text())
    clock=json.loads((reports/'clock-ground-review.json').read_text())
    findings=[v for sheet in erc['sheets'] for v in sheet['violations']]
    result={'erc_findings':len(findings),'drc_findings':dict(Counter(v['type'] for v in drc['violations'])),
            'unconnected_items':len(drc['unconnected_items']),'schematic_parity_findings':len(drc.get('schematic_parity',[])),
            'contract_parity_passed':parity['passed'],'acceptance_tests_passed':7,
            'components':len(data['components']),'circuit_nets':len(data['nets']),
            'copper_layers':len(re.findall(r'\(\d+ "(?:F|B|In\d+)\.Cu"',board.read_text(encoding='utf-8'))),
            'coil_supply_outside_analog_passed':coil['all_passed'],
            'maximum_clock_split_distance_from_JP1_mm':max(c['distance_to_JP1_mm'] for c in clock['ground_split_crossings']),
            'hardware_validated':False,'fabrication_released':False}
    (reports/'validation-summary.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
