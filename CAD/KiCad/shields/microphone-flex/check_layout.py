"""Finish, fill and independently check the Rev C prototype with KiCad Python."""
from pathlib import Path
import json
import math
import sys

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent/'scripts'))
import pcbnew as p
import planes
import check
import finish
import schematic_support as schematic


def main():
    finish.finish(ROOT)
    path=ROOT/'microphone-flex.kicad_pcb'
    board=p.LoadBoard(str(path))
    for z in list(board.Zones()):
        if not z.GetIsRuleArea():board.Delete(z)
    planes.zone(board,'SH_RETURN','GND',p.B_Cu,[(44.5,50.5),(75.5,50.5),(75.5,111.5),(44.5,111.5)])
    board.BuildConnectivity();p.ZONE_FILLER(board).Fill(board.Zones());p.SaveBoard(str(path),board,True)
    check.run(ROOT)
    drc=json.loads((ROOT/'reports/drc.json').read_text())
    erc=json.loads((ROOT/'reports/erc.json').read_text())
    assert not drc['violations'] and not drc['unconnected_items'],drc['violations']
    assert not [v for sheet in erc['sheets'] for v in sheet['violations']]
    board=p.LoadBoard(str(path));parts={fp.GetReference():fp for fp in board.GetFootprints()}
    circuit=json.loads((ROOT/'circuit.json').read_text())
    expected={(c['ref'],pin):net for c in circuit['components'] for pin,net in c['pins'].items() if net}
    native=schematic.parse((ROOT/'reports/schematic.net').read_text());from_schematic={}
    for net in schematic.children(schematic.children(native,'nets')[0],'net'):
        name=schematic.one(net,'name').replace('{slash}','/')
        if name.startswith('unconnected-'):continue
        for node in schematic.children(net,'node'):
            ref,pin=schematic.one(node,'ref'),schematic.one(node,'pin')
            if not ref.startswith('#'):from_schematic[(ref,pin)]=name
    actual={(fp.GetReference(),pad.GetNumber()):pad.GetNetname() for fp in parts.values() for pad in fp.Pads()
            if pad.GetNumber() and pad.GetNetname()}
    assert from_schematic==expected and actual==expected,'Schematic / PCB pin-net parity'
    shape=p.SHAPE_POLY_SET();assert board.GetBoardPolygonOutlines(shape)
    box=shape.BBox()
    assert abs(p.ToMM(box.GetWidth())-32)<.001 and abs(p.ToMM(box.GetHeight())-62)<.001
    for ref in ('H1','H2'):
        pad=next(iter(parts[ref].Pads()))
        assert pad.GetAttribute()==p.PAD_ATTRIB_NPTH
        assert tuple(round(v,3) for v in p.ToMM(pad.GetDrillSize()))==(12,5.5)
        assert pad.GetDrillShape()==p.PAD_DRILL_SHAPE_OBLONG
    assert p.ToMM(parts['H2'].GetPosition().y-parts['H1'].GetPosition().y)==50
    # Independent source pad geometry and physical socket row comparison.
    meta=json.loads((ROOT/'support-model-validation.json').read_text())
    source=p.LoadBoard(str(ROOT.parent/'max9814-reference/max9814-reference.kicad_pcb'))
    src=next(fp for fp in source.GetFootprints() if fp.GetReference()=='J2')
    labels=['GND','VDD','GAIN','MICOUT','AR']
    max_error=0
    for side,ref in [('left','J2'),('right','J3')]:
        transform=meta[side];rotation=transform['module_rotation'];translation=transform['module_translation_mm']
        targets={pad.GetNumber():pad for pad in parts[ref].Pads()}
        for pad in src.Pads():
            pin=int(pad.GetNumber());x,y=p.ToMM(pad.GetPosition())
            vector=[x-50,-(y-50),0]
            pos=[sum(rotation[i][j]*vector[j] for j in range(3))+translation[i] for i in range(3)]
            target=targets[str(6-pin)];tx,ty=p.ToMM(target.GetPosition())
            # Socket mating axis is X. The purchased library proxy puts it at
            # 1.27 mm above the carrier component face; compare row Y and Z.
            error=math.hypot(pos[1]+ty,pos[2]-1.27);max_error=max(max_error,error)
            assert error<.001,(side,pin,pos,tx,ty)
            assert target.GetNetname()==labels[pin-1],(side,pin,'polarity')
    report={'erc_violations':0,'drc_violations':0,'unconnected_items':0,
            'outline_mm':[32,62],'slots_mm':[12,5.5],'slot_spacing_mm':50,
            'side_socket_contacts_checked':10,'maximum_contact_row_error_mm':max_error,
            'schematic_pcb_connected_pin_parity':len(expected),
            'population':'ONE module only','physical_fit_verified':False}
    (ROOT/'layout-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print('REV C LAYOUT VERIFIED',report)


if __name__=='__main__':main()
