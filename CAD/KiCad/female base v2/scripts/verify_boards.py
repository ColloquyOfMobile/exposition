"""Verify the changed interfaces, original geometry, CAD checks and model paths."""
from pathlib import Path
import hashlib
import json
import pcbnew as p
from routing_checks import check as check_routing

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
    assert 'JA1' not in footprints
    metadata=json.loads((root/'circuit.json').read_text())
    assert metadata['revision']=='D' and not metadata['module_pins_must_be_flush']
    assert metadata['module_underside_gap_mm']==11 and not metadata['stack_height_verified']
    module=footprints['M1']; mx,my=metadata['module_origin_mm']
    socket={a.GetNumber():a for a in module.Pads()}
    assert len(socket)==11
    expected={1:'AMP_INPUT',2:'AUDIO_RETURN',5:'5V',6:'GND',10:'AMP_OUT_P',11:'AMP_OUT_N'}
    reference=p.LoadBoard(str(CAD/'shields/gf1002-reference/gf1002-reference.kicad_pcb'))
    contacts={a.GetNumber():a for f in reference.GetFootprints() if f.GetReference()=='CONTACTS' for a in f.Pads()}
    for number in range(1,12):
        pad=socket[str(number)]; x,y=p.ToMM(pad.GetPosition())
        assert abs(x-(mx+18.55))<.001 and abs(y-(my+1.2+2.54*(number-1)))<.001
        if str(number) in contacts:
            rx,ry=p.ToMM(contacts[str(number)].GetPosition())
            assert abs(x-(mx+rx-50))<.001 and abs(y-(my+ry-50))<.001
        if number in expected:assert pad.GetNetname()==expected[number]
        else:
            assert not pad.GetNetname() or pad.GetNetname().startswith('unconnected-')
            assert not any(t.GetNetCode()==pad.GetNetCode() for t in b.GetTracks())
    module_model=next(m for m in module.Models() if m.m_Filename.endswith('module_assembly.wrl'))
    assert abs(module_model.m_Offset.z-12.6)<.001
    assert abs(module_model.m_Offset.x+18.55)<.001 and abs(module_model.m_Offset.y-1.2)<.001
    assert len(list(module.Models()))==5  # socket, module and three male header groups
    strip=(mx+16.5,my,mx+20.2,my+30)
    def overlaps(a,b):
        return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
    assert p.ToMM(footprints['H1'].GetPosition())==(mx-2.5,my+19.5)
    hx,hy=p.ToMM(footprints['H2'].GetPosition())
    assert abs(hx-(mx+10.1))<.001 and abs(hy-(my+32.5))<.001
    assert footprints['H2'].GetOrientationDegrees()==90
    # H1 lip extends +X; H2 is the same clamp rotated towards -Y.
    assert not overlaps((mx-1,my+18.25,mx+2,my+20.75),strip)
    assert not overlaps((hx-1.25,hy-4.5,hx+1.25,hy-1.5),strip)
    for ref,fp in footprints.items():
        if ref=='M1':continue
        for pad in fp.Pads():
            x,y=p.ToMM(pad.GetPosition()); sx,sy=p.ToMM(pad.GetSize())
            assert not overlaps((x-sx/2,y-sy/2,x+sx/2,y+sy/2),strip),(original,ref,'contact strip')
        if ref not in ('H1','H2'):
            box=fp.GetBoundingBox(False,False)
            bounds=tuple(p.ToMM(v) for v in (box.GetLeft(),box.GetTop(),box.GetRight(),box.GetBottom()))
            assert not overlaps(bounds,strip),(original,ref,'component over contact strip')
    for via in (t for t in b.GetTracks() if isinstance(t,p.PCB_VIA)):
        x,y=p.ToMM(via.GetPosition())
        assert not overlaps((x-.001,y-.001,x+.001,y+.001),strip),'Via in module contact strip'
    def pad_at(ref,pin):
        return next(a for a in footprints[ref].Pads() if a.GetNumber()==str(pin))
    def distance(a,b):
        ax,ay=p.ToMM(a.GetPosition()); bx,by=p.ToMM(b.GetPosition())
        return ((ax-bx)**2+(ay-by)**2)**.5
    c2_distances=[distance(pad_at('C2',n),socket[str(s)]) for n,s in ((1,5),(2,6))]
    assert max(c2_distances)<5,c2_distances
    c1_distance=distance(pad_at('C1',1),socket['5'])
    assert c1_distance<9,c1_distance
    for number in (5,6):
        pos=socket[str(number)].GetPosition()
        assert any(not isinstance(t,p.PCB_VIA) and (t.GetStart()==pos or t.GetEnd()==pos)
                   and p.ToMM(t.GetWidth())>=.799 for t in b.GetTracks())
    assert not metadata['module_dimensions_verified']
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
    routing=check_routing(b)
    result={'source_sha256':hashlib.sha256((root/(stem+'.kicad_pcb')).read_bytes()).hexdigest(),
            'original_outline_and_dsub_geometry':'PASS','harness_nets_and_pad_drills':'PASS',
            'revision':'D','socket_pinout_and_reference_alignment':'PASS',
            'contact_strip_clearance':'PASS','adjustable_support_positions':'PASS',
            'module_underside_gap_mm_nominal':11,'c2_distance_to_supply_pins_mm':[round(d,3) for d in c2_distances],
            'c1_distance_to_supply_pin_mm':round(c1_distance,3),'routing':routing,
            'erc_violations':0,'drc_violations':0,
            'unconnected_items':0,'schematic_parity_differences':0,
            'physical_module_fit_verified':False,'stack_height_verified':False,'output_polarity_verified':False}
    (root/'reports/validation.json').write_text(json.dumps(result,indent=2)+'\n')
    print(stem+': Rev D socket, supports, decoupling and routing verified; ERC/DRC/parity clean.',routing)
