"""Independent native-netlist/PCB comparison and multi-board interface checks."""
import collections
import json
import hashlib
from pathlib import Path
import pcbnew as p
from design import ROOT,BASE,BODY,V2,OUTPUTS,ANALOG
from mechanical import EAGLE_HOLES
import schematic_support as s


def plain(net):return net.replace('{slash}','/').replace('{space}',' ')
def near(a,b):return abs(a-b)<.00001
def pads(board):return {(fp.GetReference(),x.GetNumber()):x for fp in board.GetFootprints() for x in fp.Pads() if x.GetNumber()}
def position(pad):return tuple(p.ToMM(pad.GetPosition()))


def main():
    loaded={};summary={}
    for folder in ROOT.iterdir():
        if not (folder/'circuit.json').exists():continue
        name=folder.name;data=json.loads((folder/'circuit.json').read_text());board=p.LoadBoard(str(folder/(name+'.kicad_pcb')))
        loaded[name]=board;actual=pads(board)
        expected={(c['ref'],pin):net for c in data['components'] for pin,net in c['pins'].items() if net}
        native=s.parse((folder/'reports/schematic.net').read_text());schematic={}
        for n in s.children(s.children(native,'nets')[0],'net'):
            net=plain(s.one(n,'name'))
            if net.startswith('unconnected-'):continue
            for node in s.children(n,'node'):
                ref,pin=s.one(node,'ref'),s.one(node,'pin')
                if not ref.startswith('#'):schematic[(ref,pin)]=net
        diffs=[]
        for key,net in expected.items():
            if schematic.get(key)!=net:diffs.append(['schematic',key,net,schematic.get(key)])
            got=plain(actual[key].GetNetname()) if key in actual else 'MISSING PAD'
            if got!=net:diffs.append(['pcb',key,net,got])
        for key,net in schematic.items():
            if key not in expected:diffs.append(['unexpected schematic net',key,net])
        for key,pad in actual.items():
            net=plain(pad.GetNetname())
            if net and not net.startswith('unconnected-') and key not in expected:diffs.append(['unexpected pcb net',key,net])
        erc=json.loads((folder/'reports/erc.json').read_text());drc=json.loads((folder/'reports/drc.json').read_text())
        result={'connected_pins':len(expected),'parity_differences':diffs,
                'erc_violations':sum(len(sh['violations']) for sh in erc['sheets']),
                'drc_violations':len(drc['violations']),'unconnected_items':len(drc['unconnected_items']),
                'copper_layers':board.GetCopperLayerCount(),'tracks_and_vias':len(list(board.GetTracks())),
                'sha256':{f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(folder.glob('*.kicad_*')) if f.suffix in ['.kicad_sch','.kicad_pcb','.kicad_pro'] and '-placed' not in f.stem}}
        (folder/'reports/parity.json').write_text(json.dumps(result,indent=2)+'\n');summary[name]=result
    back=pads(loaded['backplane']);old=pads(p.LoadBoard(str(BASE/'colloquy-control-v2.kicad_pcb')))
    fixed=['J1','J5','A-J3','B-J4','J2','J6','J7','Extra1','Extra2','Extra3']
    for (ref,pin),pad in old.items():
        if ref not in fixed:continue
        target=back[(ref,pin)]
        assert plain(target.GetNetname())==plain(pad.GetNetname()),(ref,pin,'harness net')
        assert all(near(a,b) for a,b in zip(position(target),position(pad))),(ref,pin,'harness coordinate')
    for pin,net in V2['A1']['pins'].items():
        if net:assert plain(back[('A1',pin)].GetNetname())==net
    # Slot pairs must mate in world coordinates with a translation only.
    for design in ['voice-thomas','voice-active']:
        card=pads(loaded[design]);c0=position(card[('JV1','1')])
        assert ('JV1','6') not in card
        for i,b in enumerate(BODY,1):
            ref=f'JV{i}';b0=position(back[(ref,'1')]);offset=(b0[0]-c0[0],b0[1]-c0[1])
            for n in range(1,6):
                bp,cp=position(back[(ref,str(n))]),position(card[('JV1',str(n))])
                assert all(near(bp[j],cp[j]+offset[j]) for j in range(2)),(design,n,'mating coordinate')
            bh=next(f for f in loaded['backplane'].GetFootprints() if f.GetReference()==f'HV{i}')
            ch=next(f for f in loaded[design].GetFootprints() if f.GetReference()=='H1')
            assert all(near(position(bh)[j],position(ch)[j]+offset[j]) for j in range(2))
    for design in ['analyser-msgeq7']:
        card=pads(loaded[design]);assert ('JA1','22') not in card
        for n in range(1,22):
            bp,cp=position(back[('JA1',str(n))]),position(card[('JA1',str(n))])
            assert near(bp[0],cp[0]+25) and near(bp[1],cp[1]+215)
    adapter=pads(loaded['teensy-adapter'])
    for (ref,pin),pad in adapter.items():
        if ref!='JM1':continue
        bp,ap=position(back[('A1',pin)]),position(pad)
        assert near(bp[0]+ap[0],335.66) and near(bp[1],ap[1]),(pin,'adapter mirror')
    # Confirm exactly one direct passive GND/AGND bond in the whole backplane.
    backdata=json.loads((ROOT/'backplane/circuit.json').read_text())
    bonds=[c['ref'] for c in backdata['components'] if c['ref'].startswith(('R','JP')) and set(c['pins'].values())=={'AGND','GND'}]
    assert bonds==['JP1'],bonds
    for name,board in loaded.items():
        for fp in board.GetFootprints():
            assert fp.GetReference() not in ['UID1','RID1','CID1','JSID1']
            for pad in fp.Pads():
                assert plain(pad.GetNetname()) not in ['shield/sda','shield/scl','addr0','addr1','addr2','id/wp']
    for i,gpio in enumerate([14,15,16,17,18,19,20,21,22,23,24,25,26,27,38,39]):
        data=json.loads((ROOT/'teensy-adapter/circuit.json').read_text())
        sockets=[c for c in data['components'] if c['ref'] in ['JT1','JT2']]
        pins=[(c['ref'],n) for c in sockets for n,label in c['pin_names'].items() if label==str(gpio)]
        assert len(pins)==1
        net=plain(adapter[pins[0]].GetNetname())
        assert net==(BODY[i]+'/mic direct' if i<5 else f'adc/{gpio}')
    assert set(loaded)=={'backplane','teensy-adapter','analyser-msgeq7','voice-active','voice-thomas'}
    backparts={c['ref']:c for c in backdata['components']}
    adparts={c['ref']:c for c in data['components']}
    for i,body in enumerate(BODY,1):
        direct=body+'/mic direct'
        assert plain(back[('A1',f'D{25+i}')].GetNetname())==direct
        assert plain(adapter[('JM1',f'D{25+i}')].GetNetname())==direct
        assert backparts[f'RM{i}']['pins']=={'1':body+'/microphone','2':direct}
        assert backparts[f'RM{i}']['value']=='4K7'
        assert backparts[f'RMD{i}']['pins']=={'1':direct,'2':'AGND'}
        assert backparts[f'RMD{i}']['value']=='1M'
        assert adparts[f'CM{i}']['pins']=={'1':direct,'2':'GND'}
        assert adparts[f'CM{i}']['value']=='1nF C0G'
        assert plain(back[(f'TPD{i}','1')].GetNetname())==direct
    for pin in ['A0','A1','A2','A3','A4','D3','D4','IORF']:
        assert not adapter[('JM1',pin)].GetNetname(),('Teensy isolation',pin)
    assert not back[('A1','IORF')].GetNetname()
    for pin in [34,35]:assert plain(adapter[(f'TP{pin}','1')].GetNetname())==f'gpio/{pin}'
    analyser=pads(loaded['analyser-msgeq7'])
    for pin,net in [('19','MEGA_5V'),('20','GND'),('21','GND')]:
        assert plain(back[('JA1',pin)].GetNetname())==net
    assert plain(analyser[('JA1','19')].GetNetname())=='MEGA_5V'
    for n in range(1,6):
        assert plain(analyser[(f'U{n}','1')].GetNetname())=='MEGA_5V'
        assert plain(analyser[(f'R{n}13','1')].GetNetname())=='MEGA_5V'
    summary['interfaces']={'fixed_harness_pinout_and_coordinates':'PASS','v2_connected_Mega_pins':'PASS',
        'five_voice_mating_pairs':'PASS','MSGEQ7_mating_pair':'PASS','adapter_mirror':'PASS','single_ground_bond':'PASS','no_identification_hardware':'PASS','revised_Teensy_analogue_mapping':'PASS',
        'direct_microphone_networks':'PASS','MSGEQ7_isolated_from_Teensy':'PASS','MSGEQ7_USB_5V_supply':'PASS'}
    (ROOT/'VALIDATION.json').write_text(json.dumps(summary,indent=2)+'\n')
    for name,result in summary.items():print(name,result)
    assert all(not r['parity_differences'] for n,r in summary.items() if n!='interfaces')
    assert all(r['erc_violations']==r['drc_violations']==r['unconnected_items']==0 for n,r in summary.items() if n!='interfaces')


if __name__=='__main__':main()
