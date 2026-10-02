"""Independent acceptance assertions against the v2 interface and part pinouts."""
from pathlib import Path
import json
import math
import unittest
from schematic_support import parse, children, one

ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT.parent/'electronic box v2'/'colloquy-control-v2'

class CircuitChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.new={c['ref']:c for c in json.loads((ROOT/'circuit.json').read_text())['components']}
        cls.old={c['ref']:c for c in json.loads((BASE/'circuit.json').read_text())['components']}

    def test_harness_and_mega_compatibility(self):
        for ref in ['J5','J1','A-J3','B-J4','J2','J6','J7','Extra1','Extra2','Extra3']:
            self.assertEqual(self.old[ref]['pins'],self.new[ref]['pins'],ref)
        changed={pin for pin in self.old['A1']['pins'] if self.old['A1']['pins'][pin]!=self.new['A1']['pins'][pin]}
        self.assertEqual(changed,{'D18','D19','D30'})
        for ref in ['JP1','JP2','JP3','JP4','JP5','JP6']:
            self.assertEqual(self.old[ref]['pins'],self.new[ref]['pins'])

    def test_released_relays_and_shared_buildouts(self):
        bodies=['female1','female2','female3','male1','male2']
        chan={'male1':1,'male2':2,'female1':3,'female2':4,'female3':5}
        for i,b in enumerate(bodies):
            relay=self.new[f'K{i//2+1}']['pins']
            nc,com,no=('2','3','4') if i%2==0 else ('7','6','5')
            self.assertEqual((relay[nc],relay[com],relay[no]),(b+'/filter out',b+'/selected',b+'/dac'))
            self.assertEqual(self.new[f'R{chan[b]}03']['pins'],{'1':b+'/selected','2':b+'/line out'})
        self.assertEqual([self.new['K3']['pins'][p] for p in ['7','6','5']],[None]*3)
        for n in range(1,4):
            self.assertEqual([self.new[f'K{n}']['pins'][p] for p in ['1','8']],['+5V','COIL_LOW'])
        self.assertEqual(self.new['JM1']['pins'],{'1':'GND','2':'MODE','3':'+5V'})

    def test_dac_pinouts_and_power_isolation(self):
        for n in range(1,4):
            pins=self.new[f'UD{n}']['pins']
            for pin in ['1','8','20']:self.assertEqual(pins[pin],'DAC_3V3')
            for pin in ['3','9','19','10','11','12','16']:self.assertEqual(pins[pin],'AGND')
            self.assertEqual(pins['17'],'DAC_XSMT')
            self.assertEqual(self.new[f'CD{n}9']['pins'],{'1':f'DAC_{"ABC"[n-1]}/LDOO','2':'AGND'})
        self.assertEqual(self.new['UL1']['pins'],{'1':'TEENSY_VIN','2':'AGND','3':'TEENSY_VIN','4':None,'5':'DAC_3V3'})
        for n in range(1,5):
            b=self.new[f'UB{n}'];self.assertEqual(b['value'],'SN74LVC1T45DBVR')
            self.assertEqual(b['pins']['1'],b['pins']['5'])
        # No wire or 0R ties the independently powered rails together.
        rails={'+5V','MEGA_5V','TEENSY_VIN','TEENSY_3V3','DAC_3V3'}
        for c in self.new.values():
            if c['value'] in ('0R','0 R'):
                self.assertLessEqual(len(set(c['pins'].values()) & rails),1)

    def test_teensy_physical_socket_mapping(self):
        self.assertEqual(len(self.new['JT1']['pins']),24)
        self.assertEqual(len(self.new['JT2']['pins']),24)
        for name in ['6','13','23']:
            for ref in ['JT1','JT2']:
                for pad,pin in self.new[ref]['pin_names'].items():
                    if pin==name:self.assertIsNone(self.new[ref]['pins'][pad])
        for i,b in enumerate(['female1','female2','female3','male1','male2','bench']):
            socket=self.new['JT2'];pad=next(p for p,n in socket['pin_names'].items() if n==str(14+i))
            self.assertEqual(socket['pins'][pad],b+'/adc')

    def test_ear_isolation_and_filter_values(self):
        for n,b in enumerate(['female1','female2','female3','male1','male2','bench'],1):
            self.assertEqual(self.new[f'RE{n}1']['pins'],{'1':b+'/microphone','2':b+'/isolator in'})
            self.assertEqual(self.new[f'CE{n}1']['pins'],{'1':b+'/mid','2':b+'/buffer'})
            mux=self.new[f'UX{1+(n-1)//3}']['pins'];local=(n-1)%3
            a,d=[('2','3'),('5','6'),('9','8')][local]
            self.assertEqual((mux[a],mux[d]),(b+'/isolator in',b+'/mid'))
        self.assertAlmostEqual(1/(2*math.pi*10000*math.sqrt(2.2e-9*1e-9)),10730.224,places=2)

    def test_thomas_filter_equivalence(self):
        for n in range(1,6):
            for stage in [1,2]:
                r=f'R{n}0{stage}';self.assertEqual(self.old[r]['pins'],self.new[r]['pins']);self.assertEqual(self.old[r]['value'],self.new[r]['value'])
                c=f'C{n}0{stage}';self.assertEqual(self.old[c]['pins'],self.new[c]['pins'])
                if n==1:
                    extras=[f'CF10{stage}',f'CF11{stage}']
                    for extra in extras:self.assertEqual(self.new[c]['pins'],self.new[extra]['pins'])
                    self.assertEqual(sum(float(self.new[x]['value'].split('nF')[0]) for x in [c,*extras]),470)

    def test_fixed_geometry(self):
        def fps(path):
            board=parse(path.read_text(encoding='utf-8'))
            return board,{next(x[2] for x in children(fp,'property') if x[1]=='Reference'):fp for fp in children(board,'footprint')}
        b_old,f_old=fps(BASE/'colloquy-control-v2.kicad_pcb')
        target=ROOT/'thomas-or-teensy.kicad_pcb'
        if not target.exists():target=ROOT/'thomas-or-teensy-placed.kicad_pcb'
        b_new,f_new=fps(target)
        for ref in ['A1','M1','J2','J6','J7','J5','J1','A-J3','B-J4','Extra1','Extra2','Extra3','H1','H2','H3','H4']:
            self.assertEqual(children(f_old[ref],'at'),children(f_new[ref],'at'),ref)
            # Pad centres, size, drill, layer and physical numbering, independent of net IDs.
            def signature(fp):
                return [(p[1:4],*[children(p,k) for k in ['at','size','drill','layers']]) for p in children(fp,'pad')]
            self.assertEqual(signature(f_old[ref]),signature(f_new[ref]),ref)

if __name__=='__main__':
    unittest.main(verbosity=2)
