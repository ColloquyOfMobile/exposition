"""Apply the 2026-10-22 voice-card and manufacturing-floor corrections once.

Run with KiCad 9 Python. Existing routes are retained; DRC must pass afterwards.
"""
import json
import pcbnew as p
from design import ROOT
from boards import xy


def main():
    for name in ('voice-thomas', 'analyser-carrier'):
        project = ROOT / name / (name + '.kicad_pro')
        data = json.loads(project.read_text())
        data['board']['design_settings']['rules'].update(min_clearance=.15, min_track_width=.15)
        project.write_text(json.dumps(data, indent=2) + '\n')

    folder = ROOT / 'voice-thomas'
    old = 'Shields:R_0603_1608Metric'
    new = 'Shields:R_Axial_DIN0207_L6.3mm_D2.5mm_P7.62mm_Horizontal'
    # Update only the resistor's footprint, preserving schematic UUIDs and wiring.
    for path in [*folder.glob('*.kicad_sch'), folder/'Colloquy.kicad_sym', folder/'circuit.json',
                 folder/'bom.csv', *folder.glob('variants/*/bom.csv')]:
        content = path.read_text(encoding='utf-8')
        if old in content:
            path.write_text(content.replace(old, new), encoding='utf-8')

    path = folder/'voice-thomas.kicad_pcb'
    board = p.LoadBoard(str(path))
    previous = next(f for f in board.GetFootprints() if f.GetReference() == 'R3')
    if previous.GetAttributes() & p.FP_SMD:
        replacement = p.FootprintLoad(str(ROOT/'Shields.pretty'), new.split(':')[1])
        replacement.SetFPID(p.LIB_ID('Shields', new.split(':')[1]))
        replacement.SetReference('R3')
        replacement.SetValue('100K')
        replacement.SetPath(previous.GetPath())
        board.Add(replacement)
        replacement.SetPosition(xy(58.4, 73))
        replacement.SetOrientationDegrees(90)
        old_pads = {pad.GetNumber(): pad for pad in previous.Pads()}
        for pad in replacement.Pads():
            original = old_pads[pad.GetNumber()]
            pad.SetNet(original.GetNet())
            track = p.PCB_TRACK(board)
            track.SetStart(original.GetPosition())
            track.SetEnd(pad.GetPosition())
            track.SetLayer(p.F_Cu)
            track.SetWidth(p.FromMM(.25))
            track.SetNet(original.GetNet())
            board.Add(track)
        replacement.Reference().SetPosition(xy(56, 69))
        replacement.Reference().SetTextSize(xy(.8, .8))
        replacement.Reference().SetTextThickness(p.FromMM(.12))
        replacement.Value().SetVisible(False)
        board.Remove(previous)
        # These existing legends cross the new through-hole mask openings.
        for item in board.GetDrawings():
            if isinstance(item, p.PCB_TEXT) and item.GetText() == 'M1 162 2K2 470n':
                item.SetPosition(xy(57.5, 74.4))
            elif isinstance(item, p.PCB_SHAPE) and item.GetLayer() == p.B_SilkS:
                start, end = (tuple(p.ToMM(pt)) for pt in (item.GetStart(), item.GetEnd()))
                if all(63.59 <= x <= 64.31 and 72.14 <= y <= 72.96 for x, y in (start, end)):
                    item.Move(xy(0, 1.85))
        p.ZONE_FILLER(board).Fill(board.Zones())
        p.SaveBoard(str(path), board)


if __name__ == '__main__':
    main()
