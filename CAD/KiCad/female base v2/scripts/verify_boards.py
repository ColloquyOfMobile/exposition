"""Verify the changed interfaces, original geometry, CAD checks and model paths."""
from pathlib import Path
import json
import pcbnew as p

CAD=Path(__file__).resolve().parents[2]
for original,stem in [('female base','female-base-v2'),('male static','male-static-v2')]:
    root=CAD/(original+' v2')
    b=p.LoadBoard(str(root/(stem+'.kicad_pcb')))
    old=p.LoadBoard(str(CAD/original/(original+'.kicad_pcb')))
    def edges(board):
        return sorted((str(d.GetShapeStr()),d.GetStart().x,d.GetStart().y,d.GetEnd().x,d.GetEnd().y,
                       d.GetArcMid().x if d.GetShape()==p.SHAPE_T_ARC else 0,
                       d.GetArcMid().y if d.GetShape()==p.SHAPE_T_ARC else 0) for d in board.GetDrawings()
                      if isinstance(d,p.PCB_SHAPE) and d.GetLayer()==p.Edge_Cuts)
    assert edges(b)==edges(old), 'Artwork outline/cutouts changed'
    footprints={f.GetReference():f for f in b.GetFootprints()}
    for f in old.GetFootprints():
        new=footprints[f.GetReference()]
        if f.GetReference()=='J7':
            def locations(fp):
                return sorted((a.GetNumber(),a.GetPosition().x,a.GetPosition().y,
                               a.GetDrillSize().x,a.GetDrillSize().y) for a in fp.Pads())
            assert locations(new)==locations(f), 'DSUB geometry changed'
        oldpads={a.GetNumber():a for a in f.Pads()}
        for pad in new.Pads():
            source=oldpads[pad.GetNumber()]
            assert pad.GetDrillSize()==source.GetDrillSize()
            net=source.GetNetname().lstrip('/')
            if net.startswith('unconnected-'): continue
            if 'speaker' in net: net='LINE_IN' if '+' in net else 'AUDIO_RETURN'
            if f.GetReference()=='J6': net='AMP_OUT_P' if pad.GetNumber()=='1' else 'AMP_OUT_N'
            assert pad.GetNetname()==net,(original,f.GetReference(),pad.GetNumber(),pad.GetNetname(),net)
    amp={a.GetNumber():a.GetNetname() for a in footprints['JA1'].Pads()}
    assert amp=={'1':'5V','2':'GND','3':'AMP_INPUT','4':'AUDIO_RETURN','5':'AMP_OUT_P','6':'AMP_OUT_N'}
    assert not list(footprints['M1'].Pads()), 'Reference is not a verified solder footprint'
    assert abs(footprints['M1'].Models()[0].m_Offset.z-4.6)<.001
    for f in footprints.values():
        for model in f.Models():
            filename=Path(model.m_Filename.replace('${KIPRJMOD}',str(root)))
            assert filename.exists(), filename
    drc=json.loads((root/'reports/drc.json').read_text())
    assert not drc['violations'], drc['violations']
    assert not drc['unconnected_items'], drc['unconnected_items']
    assert not drc['schematic_parity'], drc['schematic_parity']
    erc=json.loads((root/'reports/erc.json').read_text())
    assert all(not sheet['violations'] for sheet in erc['sheets'])
    print(stem+': outline/fixings/DSUB geometry and harness nets verified; 5V amplifier supply; ERC/DRC/parity clean; local models resolve.')
