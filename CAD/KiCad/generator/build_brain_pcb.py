"""Place, pre-route power, autoroute and finish the TJ Brain PCB."""
import json
import math
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcbnew
from pcbgen import Builder, mm, V
from brain import D, REV

OUT = os.path.join(HERE, '..', 'tj_brain')
SCR = os.environ.get('TJ_BUILD', os.path.join(HERE, '_build'))
os.makedirs(SCR, exist_ok=True)
W, H = 180.0, 136.0
DY = 6.0   # extra room between the Teensy and the lower half
uuids = json.load(open(os.path.join(HERE, 'brain_uuids.json')))

P = {}          # ref -> (x, y, rot)
LABELS = []     # (text, x, y, size)


def grp(name):
    return [p.ref for p in D.parts if p.group == name and not p.ref.startswith('#')]


def put(ref, x, y, r=0):
    P[ref] = (x, y, r)


# ------------------------------------------------------------------ placement
# Teensy, USB at the left board edge
put('U1', 3.0, 60.0, 90)
TX = lambda k: 3.0 + 2.54 * k  # x of pin index k along a row

# Power input (cable from the left edge, like USB)
put('J1', 14.2, 100.0, 90)
put('C3', 27, 92); put('C1', 27, 104)
put('D2', 40, 89); put('C4', 40, 93.5)
put('D1', 40, 103); put('C2', 40, 107.5)
put('D3', 5, 38); put('C5', 5, 35); put('C6', 10, 40.5)
r = grp('Rail LEDs')   # R1 D4 R2 D5 R3 D6 R4 D7 R5 D8
for i, lab in enumerate(['12V', '5V', '3V3']):
    put(r[2 * i], 27 + 6 * i, 80.5); put(r[2 * i + 1], 27 + 6 * i, 83.6)
    LABELS.append((lab, 27 + 6 * i, 85.7, 0.8))
# body supply PTCs + LEDs (bottom right, near the body connector)
put('F1', 152, 100); put('F2', 152, 106)
put(r[6], 158, 88); put(r[7], 163, 88)     # R4 D7 BODY 12V
put(r[8], 158, 91.5); put(r[9], 163, 91.5)  # R5 D8 BODY 5V
LABELS.append(('BODY12', 168.0, 88, 0.8)); LABELS.append(('BODY5', 168.0, 91.5, 0.8))
tp = grp('Test points & mounting')  # TP1..TP5 H1..H4
put(tp[0], 5, 84)                  # GND loop near power input
put(tp[1], 152, 117.5)            # GND loop bottom right
put(tp[2], 157, 117.5); put(tp[3], 161, 117.5); put(tp[4], 165, 117.5)
put(tp[5], 4, 4); put(tp[6], 176, 4); put(tp[7], 4, 126); put(tp[8], 176, 126)

# ID switch, status LEDs, expansion
put('SW1', 30, 67, 270)
s = grp('Firmware status LEDs')
for i, lab in enumerate(['HB', 'HOST', 'ERR', 'USER']):
    put(s[2 * i], 75, 32 + 3.6 * i); put(s[2 * i + 1], 80, 32 + 3.6 * i)
    LABELS.append((lab, 82.3, 32 + 3.6 * i, 0.8, -1))
put('J2', 128, 7, 90)
put('R10', 130.5, 12.5); put('R11', 135.5, 12.5)

# Dynamixel buffers next to Teensy D0..D2
put('U2', 8, 70); put('C7', 13.5, 70)
put('U3', 8, 76); put('C8', 13.5, 76)
put('R12', 8, 81); put('R13', 13.5, 81); put('R14', 13.5, 65.5)
for i, ref in enumerate(['J3', 'J4', 'J5']):
    put(ref, 112 + 12 * i, 126)
put('TP6', 169, 117.5)

# NeoPixel shifter + outputs
put('U4', 45, 72); put('C9', 45, 65.5)
for i, (pd, ser) in enumerate([('R15', 'R16'), ('R17', 'R18'), ('R19', 'R20'), ('R21', 'R22')]):
    x = 53 + 5.5 * (i // 2)
    y = 67 + 6 * (i % 2)
    put(pd, x, y); put(ser, x, y + 3)
for i, ref in enumerate(['J6', 'J7', 'J8', 'J9']):
    put(ref, 12 + 20 * i, 120)
put('J11', 92, 120)

# Audio: filter, amp, ext amp
f = grp('2nd order low-pass (fit R/C for the unit band)') + grp('Divider + coupling')  # R23 C10 R24 C11 R25 R26 C12 TP7
for i, ref in enumerate(f[:4]):
    put(ref, 84, 64 + 3.5 * i)
for i, ref in enumerate(f[4:7]):
    put(ref, 90, 64 + 3.5 * i)
put(f[7], 90, 75.5)
put('U5', 102, 78)
put('RV1', 132, 66)
put('R27', 96.5, 79.5); put('C13', 96.5, 75.5)
put('J10', 138, 66); put('JP1', 143, 66); put('JP2', 143, 70)
# microphone + MSGEQ7
put('J12', 68, 5)
put('JP3', 80, 6)
put('R28', 69.5, 12); put('D13', 75, 13); put('C14', 69.5, 15); put('TP8', 69.5, 18.5)
put('U6', 47, 30)
eq = grp('MSGEQ7 7-band analyser (optional, socketed)')  # U6 C15 C16 C17 R29 R30 C18
put(eq[1], 60, 30); put(eq[2], 60, 33.5); put(eq[3], 60, 37); put(eq[4], 65, 37); put(eq[5], 65, 30); put(eq[6], 65, 33.5)

# Light sensors
put('JP4', 66, 12.5)
put('U7', 33, 33, 90); put('C19', 40, 33, 90)
for n in range(4):
    j, rin, rpd, c, rv, rl, led = grp('Light sensor %d' % (n + 1))
    x0 = 10 + 14 * n
    put(j, x0, 5)
    put(rin, x0 + 1.5, 12); put(rpd, x0 + 1.5, 15); put(c, x0 + 1.5, 18)
    put(rl, x0 + 8, 12); put(led, x0 + 8, 15)
    put(rv, x0 + 9.5, 24.5)
    LABELS.append(('LIGHT%d' % (n + 1), x0 + 8, 17.3, 0.7))
a = grp('AUX analog input (D-sub pin 11)')  # R43 D18 C24 TP9
put(a[0], 15, 38); put(a[1], 20.5, 38); put(a[2], 15, 35); put(a[3], 24.5, 35)

# State drivers under their connectors
for n, bx in ((1, 88), (2, 110)):
    rg, rpd, qn, rpu, qp, rlim, rl, led, j = grp('State output %d' % n)
    put(j, bx, 5)
    put(rg, bx, 11); put(rpd, bx + 5, 11)
    put(qn, bx, 15); put(rpu, bx + 5, 14.5)
    put(qp, bx, 19.5); put(rlim, bx + 6, 19.5)
    put(rl, bx, 24); put(led, bx + 5, 24)
    LABELS.append(('STATE%d' % n, bx + 5, 26.3, 0.7))

# Indicator panel
put('U8', 79, 83.5, 90); put('U9', 128, 83.5, 90)
put('C25', 86, 80.5); put('C26', 135, 80.5)
put('J19', 144, 106.5); put('R54', 139, 106.5)
names = ['NP1', 'NP2', 'NP3', 'NP4', 'DXL TX', 'DXL BUS', 'TONE', 'PROBE']
for i, nm in enumerate(names):
    rs, d, rdis, c, rl, led = grp('Indicator %s' % nm)
    bx = 68 + 11 * i
    put(rs, bx - 2.6, 89); put(d, bx - 2.6, 92.2); put(c, bx - 2.6, 95.4)
    put(rdis, bx + 2.6, 89); put(rl, bx + 2.6, 92.2)
    put(led, bx, 100)
    LABELS.append((nm, bx, 102.4, 0.8))

# Body connector on the right edge
put('J20', W - 7.78, 70, 90)

for ref, (x, y, rr) in list(P.items()):
    if y > 62.5:
        P[ref] = (x, y + DY, rr)
LABELS = [(l[0], l[1], l[2] + DY if l[2] > 62.5 else l[2]) + tuple(l[3:]) for l in LABELS]

missing = [p.ref for p in D.parts if not p.ref.startswith('#') and p.footprint and p.ref not in P]
assert not missing, missing

# ------------------------------------------------------------------ build
b = Builder(D, uuids, W, H)
b.outline()
b.add_parts(P)

# pre-routed power trunks (locked)
# +5V: top layer bus along y=112 (signals cross underneath on B.Cu)
# +12V: bottom layer bus along y=123.3, *below* the terminal pins so they stay reachable
p12 = b.pad_pos('J1', 1); p5 = b.pad_pos('J1', 2)
Y5, Y12 = 112.0 + DY, 123.3 + DY
b.track([p5, (6.5, p5[1]), (6.5, Y5), (160, Y5)], 3.0, pcbnew.F_Cu, '+5V')
for j in ('J6', 'J7', 'J8', 'J9'):
    q = b.pad_pos(j, 1)
    b.track([(q[0], Y5), q], 2.5, pcbnew.F_Cu, '+5V')
c3 = b.pad_pos('C3', 1)
b.track([p5, (p5[0], c3[1]), c3], 2.0, pcbnew.F_Cu, '+5V')
f2a = b.pad_pos('F2', 1)
b.track([(f2a[0], Y5), f2a], 2.5, pcbnew.F_Cu, '+5V')
b.track([p12, (p12[0], Y12), (147, Y12)], 1.5, pcbnew.B_Cu, '+12V')
for j in ('J3', 'J4', 'J5'):
    q = b.pad_pos(j, 2)
    b.track([(q[0], Y12), q], 1.5, pcbnew.B_Cu, '+12V')
f1a = b.pad_pos('F1', 1)
b.track([(147, Y12), (147, f1a[1]), f1a], 1.5, pcbnew.B_Cu, '+12V')
c1 = b.pad_pos('C1', 1)
b.track([p12, (p12[0] + 3, p12[1] + 3), (c1[0], p12[1] + 3), c1], 1.5, pcbnew.B_Cu, '+12V')
# body supply to DA-15 pins 15 (+5V_BODY) and 7 (+12V_BODY)
f2b = b.pad_pos('F2', 2); d15 = b.pad_pos('J20', 15); d7 = b.pad_pos('J20', 7)
b.track([f2b, (177.3, f2b[1]), (177.3, d15[1]), d15], 1.5, pcbnew.F_Cu, '+5V_BODY')
f1b = b.pad_pos('F1', 2)
b.track([f1b, (160.5, f1b[1]), (160.5, d7[1]), d7], 1.2, pcbnew.B_Cu, '+12V_BODY')

nvias = b.gnd_fanout()
print('GND fanout vias:', nvias)

# ------------------------------------------------------------------ silkscreen
for p in D.parts:
    if p.silk and p.ref in b.fps and not p.ref.startswith(('D', 'H')):
        fp = b.fps[p.ref]
        bb = fp.GetCourtyard(pcbnew.F_CrtYd).BBox() if fp.GetCourtyard(pcbnew.F_CrtYd).OutlineCount() else fp.GetBoundingBox(False, False)
        x = pcbnew.ToMM(bb.GetCenter().x)
        y0, y1 = pcbnew.ToMM(bb.GetTop()), pcbnew.ToMM(bb.GetBottom())
        if y1 > H - 15:                 # bottom-edge connectors: label above
            b.text(p.silk, x, y0 - 1.2, 1.0, bold=True)
        elif y0 < 12:                   # top-edge connectors: label below
            b.text(p.silk, x, y1 + 1.1, 1.0, bold=True)
for lab in LABELS:
    b.text(lab[0], lab[1], lab[2], lab[3], just=lab[4] if len(lab) > 4 else 0)
# keep silkscreen readable: hide reference designators of small parts (they stay on F.Fab)
for ref, fp in b.fps.items():
    if ref.startswith(('R', 'C', 'D', 'Q', 'TP', 'JP', 'H')) and not ref.startswith('RV'):
        fp.Reference().SetVisible(False)
b.text('TJ BRAIN  rev %s' % REV, 158, 8, 2.0, bold=True)
b.text('Colloquy of Mobiles - one brain per unit', 158, 11.5, 1.0)
b.text('Teensy 4.1 / USB to backplane hub', 158, 14, 1.0)
b.text('UNIT ID: SW1 ON=1, sw1=bit0', 26, 77.3 + DY, 0.7)
b.text('1 F1 2 F2 3 F3 4 M1 5 M2 6 BAR', 26, 78.6 + DY, 0.7)
b.text('USB', 1.5, 52.4, 1.2, bold=True, angle=90)
b.text('12V 5V', 3.5, 98 + DY, 0.8, angle=90)
dsub = ['BODY DA-15', '1 LS2   9 NP2', '2 LS3  10 STATE1', '3 LS4  11 AUX', '4 SPK- 12 SPK+',
        '5 LS1  13 NP1', '6 MIC  14 DXL', '7 12V  15 5V', '8 GND']
for i, line in enumerate(dsub):
    b.text(line, 147.5, 50 + 2.0 * i, 1.0 if i == 0 else 0.9, bold=(i == 0), just=-1)

# ------------------------------------------------------------------ zones
inset = 0.5
poly = [(inset, inset), (W - inset, inset), (W - inset, H - inset), (inset, H - inset)]
b.zone('GND', pcbnew.B_Cu, poly, priority=0)
b.zone('GND', pcbnew.F_Cu, poly, priority=0)

pre = os.path.join(SCR, 'tj_brain_placed.kicad_pcb')
b.save(pre)
print('placed board saved', pre)
