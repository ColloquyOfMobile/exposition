"""Move the carrier control sockets to the user's corrected module grid."""
from pathlib import Path
import json
import xml.etree.ElementTree as ET
import pcbnew as p
from boards import xy
from design import ROOT

def move(fp, board=None):
    pads = {q.GetNumber():q for q in fp.Pads() if q.GetNumber()}
    delta = pads['6'].GetPosition().x-pads['7'].GetPosition().x
    if delta == 0:return
    assert abs(abs(p.ToMM(delta))-1.27)<.001
    offset = p.VECTOR2I(delta,0)
    # Only the small 1x2 socket's drawings, not the module or 1x6 outlines.
    a,b = pads['7'].GetPosition(),pads['8'].GetPosition()
    for g in fp.GraphicalItems():
        if not isinstance(g,p.PCB_SHAPE):continue
        centre = g.GetBoundingBox().GetCenter()
        if (min(a.x,b.x)-p.FromMM(1.4) <= centre.x <= max(a.x,b.x)+p.FromMM(1.4)
                and abs(centre.y-a.y)<p.FromMM(1.4)):
            g.Move(offset)
    for number in ('7','8'):
        pad = pads[number]
        old = pad.GetPosition()
        new = old+offset
        if board:
            for track in board.GetTracks():
                if track.GetNetCode()!=pad.GetNetCode():continue
                if abs(track.GetStart().x-old.x)<5 and abs(track.GetStart().y-old.y)<5:track.SetStart(new)
                if abs(track.GetEnd().x-old.x)<5 and abs(track.GetEnd().y-old.y)<5:track.SetEnd(new)
        pad.SetPosition(new)

for filename in ('analyser-carrier.kicad_pcb','analyser-carrier-placed.kicad_pcb'):
    path = ROOT/'analyser-carrier'/filename
    board = p.LoadBoard(str(path))
    for fp in board.GetFootprints():
        if fp.GetReference() in ('M1','M2','M3','M4','M5'):move(fp,board)
    # Keep the reset escape bends clear of the newly shifted strobe pads.
    for base in (0,58):
        for x,y in ((105.7967,85.78),(105.7967,86.1478),(106.6056,86.9567)):
            old,new = xy(x+base,y),xy(x+base-1.27,y)
            for track in board.GetTracks():
                if track.GetNetname()!='analyser{slash}reset':continue
                if abs(track.GetStart().x-old.x)<5 and abs(track.GetStart().y-old.y)<5:track.SetStart(new)
                if abs(track.GetEnd().x-old.x)<5 and abs(track.GetEnd().y-old.y)<5:track.SetEnd(new)
    board.BuildConnectivity()
    p.ZONE_FILLER(board).Fill(board.Zones())
    p.SaveBoard(str(path),board)
fp = p.FootprintLoad(str(ROOT/'Shields.pretty'),'DFR0126_PlugIn_Photo')
move(fp)
p.PCB_IO_MGR.PluginFind(p.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(ROOT/'Shields.pretty'),fp)
path = ROOT/'analyser-carrier'/'mechanical.json'
data = json.loads(path.read_text())
data['socket_grid_mm'][-2:] = [[7,16.51,17.78],[8,19.05,17.78]]
data['control_header_basis'] = 'User module correction 2026-10-08: reset aligned with input pin 6'
path.write_text(json.dumps(data,indent=2)+'\n')
# Refresh the printable contact positions without changing its page scale.
board=p.LoadBoard(str(ROOT/'analyser-carrier'/'analyser-carrier.kicad_pcb'))
modules={f.GetReference():f for f in board.GetFootprints() if f.GetReference().startswith('M')}
svg=ROOT/'analyser-carrier'/'mounting-template.svg'
ET.register_namespace('','http://www.w3.org/2000/svg')
tree=ET.parse(svg);current=None;changed=0
for parent in tree.iter():
    previous=None
    for child in parent:
        if child.tag.endswith('text'):
            value=child.text or ''
            if value.startswith('M') and ': ' in value:current=value.split(':')[0]
            if current in modules and value in ('7','8'):
                pad=next(q for q in modules[current].Pads() if q.GetNumber()==value)
                x=p.ToMM(pad.GetPosition().x)-50
                child.set('x',str(x));previous.set('cx',str(x));changed+=1
        previous=child
assert changed==10,changed
tree.write(svg,encoding='unicode')
# Keep all future generators/checks on the corrected grid.
for filename in ('carrier.py','verify.py'):
    path = Path(__file__).parent/filename
    text = path.read_text().replace('(7,17.78,17.78),(8,20.32,17.78)', '(7,16.51,17.78),(8,19.05,17.78)')
    text = text.replace('[7,17.78,17.78],[8,20.32,17.78]', '[7,16.51,17.78],[8,19.05,17.78]')
    text = text.replace('(17.78,17.78),(20.32,17.78)', '(16.51,17.78),(19.05,17.78)')
    text = text.replace('(16.51,16.51,5.08)', '(15.24,16.51,5.08)')
    path.write_text(text)
print('Moved five two-pin carrier sockets by 1.27 mm; attached tracks followed.')
