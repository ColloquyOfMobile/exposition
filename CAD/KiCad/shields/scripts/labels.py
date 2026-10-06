"""Apply the simplified specification's operating labels and variant tables."""
import json
import pcbnew as p
from design import ROOT,BODY,CHANNEL
from boards import text,rect,line,xy,mm
from variants import math

def label(board,value,x,y,size=.8,back=False):
    t=text(board,value,x,y,size,p.B_SilkS if back else p.F_SilkS)
    t.SetMirrored(back);return t

def writebox(board,x,y,w,h):
    shape=p.PCB_SHAPE(board);shape.SetShape(p.SHAPE_T_RECT)
    shape.SetStart(xy(x,y));shape.SetEnd(xy(x+w,y+h));shape.SetLayer(p.F_SilkS)
    shape.SetFilled(True);shape.SetWidth(mm(.1));board.Add(shape)

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
            rect(b,110,187,68,9,p.F_SilkS)
            label(b,'T = TONE / L = LINE',145,199,1)
            for i,(body,mega,gpio) in enumerate(zip(BODY,[6,46,10,11,5],[2,4,5,6,28]),1):
                x=93+(i-1)*32
                label(b,f'JV{i} - {body.upper()}\nMEGA D{mega} - TEENSY {gpio}',x,207,1)
                label(b,'CARD        PITCH       Hz',x,234,1)
                writebox(b,x-10,236,8,3);writebox(b,x+2,236,8,3)
                at(f'TPV{i}',f'T{i}',0,-2);at(f'TPL{i}',f'L{i}',0,2)
                at(f'TPM{i}',f'MIC {i}');at(f'TPA{i}',f'A{i}',0,2)
                at(f'TPD{i}',f'M{i}',0,-2)
                at(f'JV{i}','1',-1.4,-2)
                at(f'JV{i}','KEY <-',7,5.08)
                n=CHANNEL[body];at(f'R{n}03','LINE OUT',0,3);at(f'JP{n+1}','AUDIO RTN',0,3)
            label(b,'JA1 - MSGEQ7 ANALYSER - MEGA ONLY - EMPTY WITH TEENSY',151,273,1.2)
            label(b,'MIC ORDER F1 F2 F3 M1 M2 - MODULE N = BODY N',151,278,1)
            at('JA1','1',-1.5,-2);at('JA1','KEY <-',7,25.4)
            label(b,'MIC DIRECT - 4.7 K - TO TEENSY A0-A4',151,284,1)
            for ref,val in [('DP5','BOARD 5V'),('DP12','12V'),('DPUSB','MEGA 5V')]:at(ref,val,0,-2)
            for i in range(1,6):at(f'DT{i}',f'TONE {i}',0,-2)
            for ref,val,dy in [('TP31','5V',2),('TP33','12V',2),('TPUSB','USB',-2),('TP34','GND',2),('TPVG','AGND',2),('TPEG','AGND',2)]:at(ref,val,0,dy)
            label(b,'U2D2',76,106,1.5);at('J7','SERVO BUS - 12 V',8,-5)
            at('JP1','JP1 - ONLY AGND-GND BOND',0,6)
            at('TP20','STROBE',8,0);at('TP21','RESET',8,0)
            label(b,'B-J4 - NO POWER',193,329,1.2)
            label(b,'COMPUTING SLOT\nMEGA 2560 OR TEENSY ADAPTER',167,100,1.2,True)
            label(b,'USB END ^',168,62,1.2,True)
            for ref in refs:
                if ref.startswith('HM'):at(ref,'M3',0,-3)
        elif name=='teensy-adapter':
            label(b,'TEENSY 4.1\nADAPTER\nIN PLACE OF\nTHE MEGA\nFIRMWARE 5',167.5,65.5,1)
            label(b,'3.3 V\nNOT 5 V\nTOLERANT',167.5,111,1)
            label(b,'USB ^',168,55,1);at('JT1','PIN 0',4,4);at('JT2','VIN',-3,0)
            label(b,'POWERED BY TEENSY USB',169,152,1)
            for pin in [0,1,3,33,34,35,36,37,40,41]:at(f'TP{pin}',str(pin),0,-2)
            at('TPV','VIN');at('TPI','3V3');at('TPG','GND',0,2)
        elif name=='analyser-msgeq7':
            label(b,'MSGEQ7 ANALYSER - MEGA ONLY',123,52,1.2)
            for i,body in enumerate(BODY):
                x=69+i*24
                label(b,f'CH{i} '+['F1','F2','F3','M1','M2'][i],x,59,.9)
                n=CHANNEL[body];at(f'JS{n}','OPEN UNLESS\nMEASURED',0,5)
                at(f'C{n}16','REF - NEVER\nGROUND',4,3)
                at(f'TP{n+10}',f'ANA {i}',0,2)
            at('TPG','AGND',0,2);at('TPI','MEGA 5V',0,2)
            at('TPS','STROBE',0,2);at('TPR','RESET',5,2)
            at('JA1','1',-1,-2);at('JA1','KEY <-',7,25.4)
        elif name=='microphone':
            label(b,'COLLOQUY MIC',60,52,1)
            label(b,'MAX9814',60,61.8,.8)
            label(b,'GND  GAIN  VDD',57,88.5,.8)
            label(b,'A/R',52,91,.8)
            label(b,'GND +5V OUT',60,99,.8)
            label(b,'MIC GND',66,94,.8)
            label(b,'40dB: GAIN-VDD\n50dB: GAIN-GND\n60dB: OPEN\nA/R: GND = 1:500\nVDD = 1:2000\nOPEN = 1:4000',60,77,.8,True)
            label(b,'M5 / NYLON\nINSULATE FRAME',60,96,.8,True)
            named.update(['TP1','TP2'])
        elif name=='voice-thomas':
            label(b,'VOICE CARD - THOMAS RC',65,51.5,.8)
            label(b,'PITCH             Hz',65,81,.8);writebox(b,61,82,7,1.6)
            label(b,'BODY',57,84.5,.8);writebox(b,60,84,8,1.6)
            label(b,'R1 R2 C1 C2\nSET THE PITCH',74,69,.8)
            at('TP1','TONE',0,-2);at('TP4','LINE',-1,2);at('TP5','AGND',6,2)
            at('JV1','1',-1,-2);at('JV1','KEY',5,5.08)
            label(b,'R x C = 0.179 / f',65,51.6,.8,True)
            rows=[]
            for body in BODY:
                rr,cc=math.THOMAS_CHANNELS[body]
                rows.append((body.replace('female','F').replace('male','M')+' '+str(int(math.MEGA_PITCHES[body])),rr,cc))
            for pitch in math.CARD_PITCHES:
                rr,cc=math.card_values(pitch);rows.append((str(round(pitch)),rr,cc))
            from finish import box,intersects
            obstacles=[]
            for fp in b.GetFootprints():
                obstacles += [box(pad,.25) for pad in fp.Pads() if pad.IsOnLayer(p.B_Mask)]
                obstacles += [box(g,.15) for g in fp.GraphicalItems() if g.GetLayer()==p.B_SilkS]
            for col in range(2):
                last=52.5
                for pitch,rr,cc in rows[col*9:(col+1)*9]:
                    rv=f'{rr/1000:g}'.replace('.','K')
                    if 'K' not in rv:rv+='K'
                    t=label(b,f'{pitch} {rv} {cc*1e9:g}n',57.5+col*15,54,.8,True)
                    for step in range(150):
                        y=last+1.7+step*.25;t.SetPosition(xy(57.5+col*15,y))
                        bounds=box(t,.12)
                        if y>90:raise RuntimeError('Voice table does not fit')
                        if not any(intersects(bounds,o) for o in obstacles):
                            mark=rect(b,63.6+col*15,y-.4,.7,.8,p.B_SilkS)
                            obstacles.append(bounds);last=y;break
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
    if len(sys.argv)>1:main(sys.argv[1:])
    else:
        import subprocess
        for f in ROOT.iterdir():
            if (f/'circuit.json').exists():subprocess.run([sys.executable,__file__,f.name],check=True)

