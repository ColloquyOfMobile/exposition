"""Build the socketed MAX9814 holder, preserving the artwork's M5 interface.

Run with KiCad 9 Python. Writes schematic and unrouted placement only;
route.py, finish.py, planes.py, check.py and verify.py finish/check the PCB.
"""
import json
import math
import shutil
import pcbnew as p
from design import ROOT, Circuit, emit
from boards import LOCAL, LIB, xy, rect, text, project

MODULE_GAP = 11.04  # Socket body 8.5 + module header collar 2.54; confirm sample.
MOUNT_CENTRES = ((65.0165, 69.032), (54.9835, 69.032))
HEADER_CENTRES = [(64.8895 - i * 2.54, 91.003) for i in range(5)]


def circuit():
    d = Circuit('microphone')
    d.add('M1', 'MAX9814 MODULE / 1x05 SOCKET',
          'Shields:MAX9814_Module_Socket_1x05',
          {1: 'GND', 2: 'VDD', 3: 'GAIN', 4: 'MICOUT', 5: 'AR'}, 'module',
          names={'1': 'GND', '2': 'Vdd', '3': 'Gain', '4': 'Out', '5': 'AR'},
          types={'1': 'power_in', '2': 'power_in', '3': 'input', '4': 'output', '5': 'input'},
          description='Existing violet MAX9814 module on female 2.54mm socket. Insulating M2 spacers must match the seated header height. Verify physical sample.',
          mpn='Existing MAX9814 module + 1x05 2.54mm female socket')
    d.r('R1', '0R / GAIN VDD 40dB', 'GAIN', 'VDD', 'module')
    d.r('R2', '0R / AR GND 1:500', 'AR', 'GND', 'module')
    d.r('R4', '33R', '+5V', 'VDD', 'power')
    d.c('C7', '22uF X5R 10V', 'VDD', 'GND', 'power', 'Capacitor_SMD:C_0805_2012Metric')
    d.c('C6', '100nF', 'VDD', 'GND', 'power')
    d.led('D1', 'R6', '2K2', '+5V', 'GREEN', 'power')
    d.r('R5', '470R', 'MICOUT', 'OUT', 'interface')
    d.add('J1', 'GND / +5V / OUT', 'Shields:JST_EH_B3B-EH-A_1x03_P2.50mm_Vertical',
          {1: 'GND', 2: '+5V', 3: 'OUT'}, 'interface', mpn='B3B-EH-A')
    d.testpin('TP1', 'MICOUT', 'interface')
    d.testpin('TP2', 'GND', 'interface')
    for i in (1, 2):
        d.add(f'H{i}', 'M5 / 12mm copper keepout',
              'Shields:MountingHole_5.5mm_Keepout12', {}, 'mechanical')
    for i in (3, 4):
        d.add(f'H{i}', 'M2 MODULE / INSULATING SPACER',
              'Shields:MountingHole_2.2mm_M2_Keepout6', {}, 'mechanical')
    return d


def keepout(fp, x, y, radius):
    for layer in (p.F_Cu, p.B_Cu):
        zone = p.ZONE(fp)
        zone.SetIsRuleArea(True)
        zone.SetLayer(layer)
        zone.SetDoNotAllowTracks(True)
        zone.SetDoNotAllowVias(True)
        zone.SetDoNotAllowPads(False)  # Own NPTH is inside; verify.py checks every other pad.
        zone.SetDoNotAllowCopperPour(True)
        zone.SetDoNotAllowFootprints(True)
        zone.Outline().NewOutline()
        for i in range(96):
            angle = i * math.tau / 96
            zone.Outline().Append(p.FromMM(x + radius * math.cos(angle)),
                                  p.FromMM(y + radius * math.sin(angle)))
        fp.Add(zone)


def footprints():
    io = p.PCB_IO_MGR.PluginFind(p.PCB_IO_MGR.KICAD_SEXP)
    fp = p.FootprintLoad(str(LIB / 'Connector_PinSocket_2.54mm.pretty'),
                         'PinSocket_1x05_P2.54mm_Vertical')
    fp.SetFPID(p.LIB_ID('Shields', 'MAX9814_Module_Socket_1x05'))
    fp.SetLibDescription('Five-pin female socket for violet MAX9814, pins GND/Vdd/Gain/Out/AR. Separate insulating M2 supports. Source Adafruit geometry; physical sample unverified.')
    model = p.FP_3DMODEL()
    model.m_Filename = '${KIPRJMOD}/3dmodels/MAX9814_Module_reference.wrl'
    fp.Add3DModel(model)
    io.FootprintSave(str(LOCAL), fp)
    temporary = p.BOARD()
    fp = p.FOOTPRINT(temporary)
    temporary.Add(fp)
    fp.SetFPID(p.LIB_ID('Shields', 'MountingHole_2.2mm_M2_Keepout6'))
    fp.SetAttributes(p.FP_EXCLUDE_FROM_BOM | p.FP_EXCLUDE_FROM_POS_FILES)
    pad = p.PAD(fp)
    pad.SetAttribute(p.PAD_ATTRIB_NPTH)
    pad.SetShape(p.PAD_SHAPE_CIRCLE)
    pad.SetDrillSize(xy(2.2, 2.2))
    pad.SetSize(xy(2.2, 2.2))
    pad.SetLayerSet(p.LSET.AllCuMask())
    fp.Add(pad)
    for layer in (p.F_CrtYd, p.B_CrtYd):
        g = p.PCB_SHAPE(fp)
        g.SetShape(p.SHAPE_T_CIRCLE)
        g.SetCenter(xy(0, 0))
        g.SetEnd(xy(3, 0))
        g.SetWidth(p.FromMM(.05))
        g.SetLayer(layer)
        fp.Add(g)
    keepout(fp, 0, 0, 3)
    model = p.FP_3DMODEL()
    model.m_Filename = '${KIPRJMOD}/3dmodels/M2_insulating_support_reference.step'
    fp.Add3DModel(model)
    io.FootprintSave(str(LOCAL), fp)


def positions():
    return {'H1': (60, 56, 0), 'H2': (60, 106, 0),
            'H3': (*MOUNT_CENTRES[0], 0), 'H4': (*MOUNT_CENTRES[1], 0),
            'M1': (*HEADER_CENTRES[0], 270),
            'R1': (64, 84, 0), 'R2': (55.5, 84, 0),
            'R4': (64, 80, 0), 'C7': (60.5, 85, 90), 'C6': (64, 86.4, 0),
            'R5': (57.2695, 87.5, 90), 'J1': (57.5, 96.8, 0),
            'D1': (60, 64, 0), 'R6': (60, 74, 0),
            'TP1': (65.5, 64, 0), 'TP2': (54.5, 64, 0)}


def operating_labels(board):
    text(board, 'COLLOQUY MIC B', 60, 52, .8)
    text(board, 'OUT', 65.5, 61.8, .8)
    text(board, 'GND', 54.5, 61.8, .8)
    text(board, '5V', 60, 65.6, .8)
    text(board, 'M2', 65, 72.8, .8)
    text(board, 'M2', 55, 72.8, .8)
    text(board, 'MAX9814 MODULE', 60, 77.5, .8)
    text(board, 'G40 / AR500', 60, 82, .8)
    text(board, 'GND +5V OUT', 60, 101, .8)
    for label, y in [('VIOLET MODULE', 67), ('GND VDD GAIN', 74),
                     ('OUT AR / 1x5', 77), ('M2 NYLON POSTS', 82),
                     ('MATCH SOCKET HEIGHT', 85), ('M5 / INSULATE FRAME', 95)]:
        t = text(board, label, 60, y, .8, p.B_SilkS)
        t.SetMirrored(True)


def main(schematic_only=False):
    footprints()
    emit(circuit())
    folder = ROOT / 'microphone'
    # These sheets belonged only to the replaced bare-chip circuit.
    for name in ('amplifier.kicad_sch', 'amplifier_2.kicad_sch', 'interface_2.kicad_sch'):
        (folder / name).unlink(missing_ok=True)
    for name in ('microphone', 'module', 'power', 'interface', 'mechanical', 'supplies'):
        path = folder / (name + '.kicad_sch')
        value = path.read_text(encoding='utf-8')
        value = value.replace('2026-10-05', '2026-10-08').replace('A-prototype', 'B-module-holder')
        value = value.replace('Rev A', 'Rev B').replace('SHIELDS.md direct microphones 2026-10-08', 'MAX9814 module holder 2026-10-08')
        path.write_text(value, encoding='utf-8')
    if schematic_only:
        return
    data = json.loads((folder / 'circuit.json').read_text())
    previous = p.LoadBoard(str(folder / 'microphone.kicad_pcb'))
    board = p.BOARD()
    board.GetDesignSettings().SetBoardThickness(p.FromMM(1.6))
    # Retain the proven rounded outline in a fresh board.
    for item in previous.GetDrawings():
        if item.GetLayer() == p.Edge_Cuts:
            board.Add(item.Duplicate())
    board.SetCopperLayerCount(2)
    nets = {}
    for name in sorted({n for part in data['components'] for n in part['pins'].values() if n}):
        existing = board.FindNet(name)
        if existing is None:
            existing = p.NETINFO_ITEM(board, name)
            board.Add(existing)
        nets[name] = existing
    placements = positions()
    for part in data['components']:
        fp = p.FootprintLoad(str(LOCAL), part['footprint'].split(':')[1])
        assert fp is not None, part['footprint']
        board.Add(fp)
        fp.SetFPID(p.LIB_ID('Shields', part['footprint'].split(':')[1]))
        fp.SetReference(part['ref'])
        fp.SetValue(part['value'])
        x, y, angle = placements[part['ref']]
        fp.SetOrientationDegrees(angle)
        fp.SetPosition(xy(x, y))
        fp.Value().SetVisible(False)
        fp.Reference().SetPosition(xy(x, y - 2))
        fp.Reference().SetTextSize(xy(.8, .8))
        fp.Reference().SetTextThickness(p.FromMM(.12))
        ids = p.KIID_PATH()
        for uid in (part['sheet_path'].strip('/') + '/' + part['uuid']).split('/'):
            ids.push_back(p.KIID(uid))
        fp.SetPath(ids)
        for pad in fp.Pads():
            net = part['pins'].get(pad.GetNumber())
            pad.SetNet(nets[net] if net else board.FindNet(0))
    rect(board, 52.9515, 67, 14.097, 25.4, p.Dwgs_User)
    text(board, 'MODULE ABOVE / FACE ROOM', 60, 75, .8, p.Dwgs_User)
    operating_labels(board)
    # Fix the long test lead through the narrow channel beside the M2 post.
    # Both ends are PTH, so this underside path needs no vias.
    path = [(65.5, 64), (68.9, 64), (68.9, 92.9), (59.1665, 92.9), (57.2695, 91.003)]
    for a, c in zip(path, path[1:]):
        track = p.PCB_TRACK(board)
        track.SetStart(xy(*a))
        track.SetEnd(xy(*c))
        track.SetLayer(p.B_Cu)
        track.SetWidth(p.FromMM(.25))
        track.SetNet(nets['MICOUT'])
        board.Add(track)
    board.BuildConnectivity()
    p.SaveBoard(str(folder / 'microphone-placed.kicad_pcb'), board, True)
    if not (folder / 'microphone.kicad_pro').exists():
        project(folder, 'microphone')
    shutil.copy2(folder / 'microphone.kicad_pro', folder / 'microphone-placed.kicad_pro')
    mechanical = {'board_mm': [20, 62], 'artwork_holes_mm': [[10, 6], [10, 56]],
                  'artwork_drill_mm': 5.5, 'module_holes_mm': [[x-50, y-50] for x, y in MOUNT_CENTRES],
                  'module_drill_mm': 2.2, 'header_centres_mm': [[x-50, y-50] for x, y in HEADER_CENTRES],
                  'module_underside_gap_mm': MODULE_GAP, 'module_head_max_diameter_mm': 4,
                  'basis': 'Adafruit MAX9814 source geometry; socket/header height proxies',
                  'physical_fit_verified': False}
    (folder / 'mechanical.json').write_text(json.dumps(mechanical, indent=2) + '\n')
    print('microphone: generated socketed module holder', len(data['components']), 'parts')


if __name__ == '__main__':
    import sys
    main('--schematic-only' in sys.argv)
