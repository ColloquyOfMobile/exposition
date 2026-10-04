"""Apply the simplified specification's operating labels and variant tables."""
import json
import pcbnew as p
from design import ROOT,BODY,CHANNEL
from boards import text,rect,line,xy,mm
from variants import math

def label(board,value,x,y,size=.8,back=False):
    t=text(board,value,x,y,size,p.B_SilkS if back else p.F_SilkS)
    t.SetMirrored(back);return t

def main(only=None):
    for folder in ROOT.iterdir():
        if only and folder.name not in only:continue
        path=folder/(folder.name+'.kicad_pcb')
        if not path.exists():continue
        b=p.LoadBoard(str(path));name=folder.name
        for item in list(b.GetDrawings()):
            if item.GetLayer() in [p.F_SilkS,p.B_SilkS] or isinstance(item,p.PCB_TEXT):b.Delete(item)
        refs={f.GetReference():f for f in b.GetFootprints()};named=set()
        def at(ref,value,dx=0,dy=-2,size=None):
            named.add(ref)
            f=refs[ref];x,y=p.ToMM(f.GetPosition());label(b,value,x+dx,y+dy,size or (1 if name in ['backplane','teensy-adapter'] else .8))
        if name=='backplane':
            label(b,'COLLOQUY - SHIELD BACKPLANE - REV A',145,57,1.4)
            label(b,'POWER RACK AND COMPUTING USB TOGETHER',144,190,1.2)
            label(b,'CHANGE A SHIELD ONLY WITH BOTH UNPLUGGED',144,194,1.1)
            rect(b,110,187,68,10,p.F_SilkS)
            label(b,'SLOT N = BODY N',145,200,1.2)
            for i,(body,mega,gpio) in enumerate(zip(BODY,[6,46,10,11,5],[2,4,5,6,28]),1):
                x=93+(i-1)*32
                label(b,f'JV{i} - {body.upper()}\nMEGA D{mega} - TEENSY {gpio}',x,207,1)
                label(b,'CARD        PITCH       Hz',x,234,1)
                rect(b,x-10,236,8,3,p.F_SilkS);rect(b,x+2,236,8,3,p.F_SilkS)
                at(f'TPV{i}',f'TONE {i}');at(f'TPL{i}',f'LINE {i}')
                at(f'TPM{i}',f'MIC {i}');at(f'TPA{i}',f'ANA {i}')
                at(f'JV{i}','1',-1.4,-2)
                at(f'JV{i}','KEY <-',7,5.08)
                n=CHANNEL[body];at(f'R{n}03','LINE OUT',0,3);at(f'JP{n+1}','AUDIO RTN',0,3)
            label(b,'JA1 - ANALYSER - MSGEQ7 OR DIRECT',151,273,1.2)
            label(b,'MIC ORDER F1 F2 F3 M1 M2 - MODULE N = BODY N',151,278,1)
            at('JA1','1',-1.5,-2);at('JA1','KEY <-',7,25.4)
            at('TPI1','IOREF: 5 V = MEGA / 3.3 V = TEENSY',-2,4)
            label(b,'U2D2',76,70,1.5);at('J7','SERVO BUS - 12 V',8,-5)
            at('JP1','JP1 - ONLY AGND-GND BOND',0,6)
            label(b,'B-J4 - NO POWER',193,329,1.2)
            label(b,'COMPUTING SLOT\nMEGA 2560 OR TEENSY ADAPTER',167,100,1.2,True)
            label(b,'USB END ^',168,62,1.2,True)
            for ref in refs:
                if ref.startswith('HM'):at(ref,'M3',0,-3)
        elif name=='teensy-adapter':
            label(b,'TEENSY 4.1 ADAPTER\nIN PLACE OF THE MEGA\nFIRMWARE 5',168,68,1)
            label(b,'3.3 V\nNOT 5 V TOLERANT',168,112,1)
            label(b,'USB ^',168,55,1);at('JT1','PIN 0',4,4);at('JT2','VIN',-3,0)
            label(b,'POWERED BY TEENSY USB',169,152,1)
            for pin in [0,1,3,33,36,37,40,41]:at(f'TP{pin}',str(pin),0,-2)
            at('TPV','VIN');at('TPI','3V3');at('TPG','GND',0,2)
        elif name.startswith('analyser'):
            label(b,'ANALYSER - '+('5 x MSGEQ7 - BANDS' if name.endswith('msgeq7') else 'DIRECT TO TEENSY - RAW SAMPLES'),123,52,1.2)
            for i,body in enumerate(BODY):
                x=69+i*24 if name.endswith('msgeq7') else 68+i*22
                label(b,f'CH{i} '+['F1','F2','F3','M1','M2'][i],x,59 if name.endswith('msgeq7') else 81,.9)
                if name.endswith('msgeq7'):
                    n=CHANNEL[body];at(f'JS{n}','OPEN UNLESS\nMEASURED',0,5)
                    at(f'C{n}16','REF - NEVER\nGROUND',4,3)
                    at(f'TP{n+10}',f'ANA {i}',0,2)
                else:at(f'TP{i+1}',f'ANA {i}',0,2)
            at('TPG','AGND',0,2);at('TPI' if name.endswith('msgeq7') else 'TPR','IOREF',0,2)
            if name.endswith('direct'):
                at('JSRC1','HARNESS < CH0 > BENCH',0,-4)
                at('JB1','BENCH MIC - GND 5V SIG',0,4)
                label(b,'UNPLUGGED MIC = 0 V',123,99,1)
            else:at('TPS','STROBE',0,2);at('TPR','RESET',5,2)
            at('JA1','1',-1,-2);at('JA1','KEY <-',7,25.4)
        else:
            active=name=='voice-active'
            label(b,'ACTIVE VOICE CARD' if active else 'THOMAS VOICE CARD',65,76,.9)
            if not active:label(b,'FIXED PITCH',66,79,.8)
            label(b,'CORNER        Hz' if active else 'BODY',67,82,.8)
            rect(b,61,83,10,2.5,p.F_SilkS)
            if active:label(b,'PLAY 0.5-1 x CORNER\nBEST 0.6-0.85 x CORNER',65,51.8,.8,True)
            at('TP1','TONE',0,-2);at('TP4','LINE',0,1.8);at('TP5','AGND',4,1.8)
            at('JV1','1',-1,-2);at('JV1','KEY <-',7,5.08)
            for x,v in zip([70,63,56,78],['CORNER' if active else 'BODY/Hz','Ra' if active else 'R1=R2','Rb' if active else 'C1=C2','FIT']):label(b,v,x,63.4,.8,True)
            rows=[]
            if active:
                for c in math.CARD_CORNERS:
                    a,r=math.card_resistors(c)
                    rows.append((str(round(c)),f'{a/1000:g}K',f'{r/1000:g}K'))
            else:
                for body in BODY:
                    r,c=math.THOMAS_CHANNELS[body]
                    rows.append((body.replace('female','F').replace('male','M')+' '+str(int(math.MEGA_PITCHES[body])),f'{r/1000:g}K',f'{c*1e9:g}n'))
            for i,row in enumerate(rows):
                y=65+i*(1.6 if active else 3)
                for x,v in zip([70,63,56],row):label(b,v,x,y,.8,True)
                rect(b,77.5,y-.5,1,1,p.B_SilkS)
        # All otherwise unnamed test pads carry their actual net.
        for ref,fp in refs.items():
            if not ref.startswith('TP'):continue
            # Retain reference but give assembly readers its signal name too.
            fp.SetValue(next(iter(fp.Pads())).GetNetname().replace('{slash}','/'))
            if ref not in named:
                value=fp.GetValue().upper().replace('MEGA_5V','MEGA 5V (COMPUTING USB)').replace('+5V','BOARD +5V')
                for i,body in enumerate(BODY,1):value=value.replace(body.upper()+'/',str(i)+' ')
                at(ref,value.replace('/',' ').replace('ANALYSER OUT','ANA').replace('FILTER OUT','LINE').replace('MICROPHONE','MIC'))
        p.SaveBoard(str(path),b)

if __name__=='__main__':
    import sys
    main(sys.argv[1:])

