"""Export complete assembly BOMs and silkscreen tables for all specified voice cards."""
import copy
import csv
import importlib.util
import json
from pathlib import Path
from design import ROOT, BODY

source=ROOT.parents[2]/'Source code/Python/colloquy/hardware/electronics/shields.py'
spec=importlib.util.spec_from_file_location('shield_math',source)
math=importlib.util.module_from_spec(spec);spec.loader.exec_module(math)


def save(kind,name,changes,identity):
    folder=ROOT/kind/'variants'/name;folder.mkdir(parents=True,exist_ok=True)
    parts=copy.deepcopy(json.loads((ROOT/kind/'circuit.json').read_text())['components'])
    for p in parts:
        if p['ref'] in changes:p.update(changes[p['ref']])
    with (folder/'bom.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['Reference','Value','Footprint','MPN','Assembly'])
        for p in parts:
            if p.get('include_bom',True):w.writerow([p['ref'],p['value'],p['footprint'],p.get('mpn',''),p['assembly']])
    (folder/'population.json').write_text(json.dumps(identity,indent=2)+'\n')



def main():
    for b in BODY:
        r,c=math.THOMAS_CHANNELS[b];values={f'R{i}':dict(value=f'{r:g} ohm 1%') for i in [1,2]}
        for i in [1,2]:
            values[f'C{i}']=dict(value='DNP PPS',assembly='DNP',mpn='')
            values[f'CX{i}']=dict(value='DNP PPS',assembly='DNP',mpn='')
            values[f'CY{i}']=dict(value='DNP C0G',assembly='DNP',mpn='')
            if c>=100e-9:
                nf=150 if b=='female1' else 220
                values[f'C{i}']=dict(value=f'{nf}nF PPS 5%',assembly='fit',mpn='ECHU1H154JX9' if nf==150 else 'ECHU1H224JX9')
                if b=='male1':
                    values[f'CX{i}']=dict(value='220nF PPS 5%',assembly='fit',mpn='ECHU1H224JX9')
                    values[f'CY{i}']=dict(value='30nF C0G 5% >=25V',assembly='fit',mpn='')
            else:values[f'CY{i}']=dict(value=f'{c*1e9:g}nF C0G 5% >=25V',assembly='fit',mpn='')
        save('voice-thomas',b,values,dict(kind='voice thomas',body=b,hz=int(math.MEGA_PITCHES[b])))
    rows=[]
    for corner in math.CARD_CORNERS:
        ra,rb=math.card_resistors(corner);label=str(round(corner))
        changes={ref:dict(value=f'{val:g} ohm 1%') for ref,val in [('R3',ra),('R4',ra),('R5',rb),('R6',rb)]}
        sweet=[round(corner*x) for x in math.SWEET];allowed=[round(corner*x) for x in math.ALLOWED]
        save('voice-active',label,changes,dict(kind='voice active',corner=round(corner),sweet=sweet,allowed=allowed))
        rows.append([label,ra,rb,*sweet,*allowed])
    with (ROOT/'voice-active/variants.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['Card','R3=R4 ohm','R5=R6 ohm','Sweet min Hz','Sweet max Hz','Allowed min Hz','Allowed max Hz']);w.writerows(rows)
    (ROOT/'ASSEMBLY.md').write_text('''# Assembly and variants

The default native voice layouts are female1 Thomas (1012Hz) and active 1414.
All five Thomas populations and all thirteen active populations use their own
complete BOM under `variants/`. A BOM changes population, never connector order.
Mark the fitted body or corner in the front white box and tick its row in the
back silkscreen table. The same artwork supports every population. The
population.json files describe assembly choices; no memory chip is fitted.

Build in this order: (1) backplane, five Thomas cards and MSGEQ7 analyser with
Mega/firmware 4; (2) Teensy adapter; (3) direct analyser; (4) active cards
1414, 4000, 8000, 250, 500 in body order. Other corners come later as needed.

Fit gold-plated contacts on both halves. Remove male pin 6/22 and block the
matching socket cavity. Sockets are on B.Cu; all small parts are on F.Cu.
Use insulated M3 standoffs. Do not hot-plug any card. Verify contact numbering
with a meter before fitting silicon. Direct analyser JSRC1 defaults to pins
1-2 (HARNESS); pins 2-3 select the bench JST. All attenuation bypasses are OPEN.

The 5V backplane rail, USB-derived MEGA_5V and IOREF are distinct supplies.
Follow REVIEW.md and SHIELDS.md section 10 for continuity and power-up checks.
Hardware performance, enclosure fit and a fabrication release remain unverified.
''')


if __name__=='__main__':main()
