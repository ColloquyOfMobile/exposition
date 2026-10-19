"""Apply the 2026-10-19 microphone-on-L specification, preserving placement.

Run with KiCad Python, then route the placed board and run finish/planes/check.
The routed board is deliberately left untouched until routing succeeds.
"""
import json
import pcbnew as p
from carrier import circuit
from design import ROOT, emit


def main():
    folder = ROOT / 'analyser-carrier'
    design = circuit()
    board = p.LoadBoard(str(folder / 'analyser-carrier-placed.kicad_pcb'))
    before = {(f.GetReference(), pad.GetNumber()): tuple(pad.GetPosition())
              for f in board.GetFootprints() for pad in f.Pads()}
    for track in list(board.GetTracks()):
        board.Delete(track)
    for zone in list(board.Zones()):
        if not zone.GetIsRuleArea():
            board.Remove(zone)
    for fp in board.GetFootprints():
        pins = design.parts[fp.GetReference()]['pins']
        for pad in fp.Pads():
            net = pins.get(pad.GetNumber())
            pad.SetNet(board.FindNet(net.replace('/', '{slash}')) if net else board.FindNet(0))
    replacements = {'MODULE: REMOVE R4 / LINK L TO OUT': 'MODULE: REMOVE R3 / LINK R TO OUT',
                    'OUT + - MIC + -': 'MIC + - OUT + -',
                    '- + MIC - + OUT': '- + OUT - + MIC'}
    for item in board.GetDrawings():
        if isinstance(item, p.PCB_TEXT) and item.GetText() in replacements:
            item.SetText(replacements[item.GetText()])
    assert before == {(f.GetReference(), pad.GetNumber()): tuple(pad.GetPosition())
                      for f in board.GetFootprints() for pad in f.Pads()}
    emit(design)
    board.BuildConnectivity()
    p.SaveBoard(str(folder / 'analyser-carrier-placed.kicad_pcb'), board)
    path = folder / 'mechanical.json'
    data = json.loads(path.read_text())
    data['module_modification'] = 'Remove R3; link isolated R to OUT; microphone on L; downward headers'
    path.write_text(json.dumps(data, indent=2) + '\n')
    path = folder / 'mounting-template.svg'
    path.write_text(path.read_text().replace('Remove R4', 'Remove R3').replace('remove R4', 'remove R3')
                    .replace('L to OUT', 'R to OUT').replace('L=OUT', 'R=OUT')
                    .replace('1 OUT*', '1 MIC (L)').replace('4 MIC', '4 OUT* (R)'))
    print('Carrier placed board and schematic: microphone on L, OUT on converted R; geometry preserved.')


if __name__ == '__main__':
    main()
