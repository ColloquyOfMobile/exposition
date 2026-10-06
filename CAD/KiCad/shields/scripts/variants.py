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
    rows=[]
    for body in BODY:
        ohms,farads=math.THOMAS_CHANNELS[body]
        hz=int(math.MEGA_PITCHES[body]);rows.append([body,hz,ohms,farads*1e9,hz,hz])
    for pitch in math.CARD_PITCHES:
        ohms,farads=math.card_values(pitch)
        rows.append(['pitch-'+str(round(pitch)),round(pitch),ohms,farads*1e9,round(pitch*2**-.25),round(pitch*2**.25)])
    for name,hz,ohms,nf,low,high in rows:
        changes={f'R{i}':dict(value=f'{ohms:g} ohm metal film 1% 0.25W') for i in [1,2]}
        changes.update({f'C{i}':dict(value=f'{nf:g}nF film 5% >=50V') for i in [1,2]})
        save('voice-thomas',name,changes,dict(kind='Thomas RC',body=name if name in BODY else None,pitch_hz=hz,window_hz=[low,high]))
    with (ROOT/'voice-thomas/variants.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['Population','Pitch Hz','R1=R2 ohm','C1=C2 nF film','Low Hz','High Hz']);w.writerows(rows)


if __name__=='__main__':main()
