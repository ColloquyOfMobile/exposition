"""Verify the changed interfaces, original geometry, CAD checks and model paths."""
from pathlib import Path
import hashlib
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
    module=footprints['M1']; mx,my=p.ToMM(module.GetPosition())
    # Reserve the full contact-side strip, including the conservative 0.2mm width.
    strip=(mx+16.5,my,mx+20.2,my+30)
    def overlaps(a,b):
        return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
    assert p.ToMM(footprints['H1'].GetPosition())==(mx-2.5,my+19.5)
    hx,hy=p.ToMM(footprints['H2'].GetPosition())
    assert abs(hx-(mx+10.1))<.001 and abs(hy-(my+32.5))<.001
    assert footprints['H2'].GetOrientationDegrees()==90
    # H1 lip extends +X; H2 is the same clamp rotated towards -Y.
    assert not overlaps((mx-1,my+18.75,mx+1.5,my+20.25),strip)
    assert not overlaps((hx-.75,hy-4,hx+.75,hy-1.5),strip)
    for ref,fp in footprints.items():
        if ref=='M1':continue
        for pad in fp.Pads():
            x,y=p.ToMM(pad.GetPosition()); sx,sy=p.ToMM(pad.GetSize())
            assert not overlaps((x-sx/2,y-sy/2,x+sx/2,y+sy/2),strip),(original,ref,'contact strip')
        if ref not in ('H1','H2'):
            box=fp.GetBoundingBox(False,False)
            bounds=tuple(p.ToMM(v) for v in (box.GetLeft(),box.GetTop(),box.GetRight(),box.GetBottom()))
            assert not overlaps(bounds,strip),(original,ref,'component over contact strip')
    ja=footprints['JA1'].GetPosition()
    assert mx+20.2<p.ToMM(ja.x)<mx+25 and my<p.ToMM(ja.y)<my+30
    metadata=json.loads((root/'circuit.json').read_text())
    assert metadata['module_pins_must_be_flush'] and not metadata['module_dimensions_verified']
    assert metadata['amplifier_input']=='R' and metadata['speaker_output']=='ROUT'
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
    result={'source_sha256':hashlib.sha256((root/(stem+'.kicad_pcb')).read_bytes()).hexdigest(),
            'original_outline_and_dsub_geometry':'PASS','harness_nets_and_pad_drills':'PASS',
            'contact_strip_clearance':'PASS','shaft_and_short_edge_clamps':'PASS',
            'wire_pads_on_contact_side':'PASS','erc_violations':0,'drc_violations':0,
            'unconnected_items':0,'schematic_parity_differences':0,
            'physical_module_fit_verified':False,'module_pins_must_be_flush':True}
    (root/'reports/validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(stem+': outline/fixings/DSUB geometry and harness nets verified; 5V amplifier supply; ERC/DRC/parity clean; local models resolve.')
