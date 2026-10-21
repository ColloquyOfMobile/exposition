"""Move the five adapter reservoirs to the assembly face, preserving other parts.

Run once with KiCad Python, then check native DRC and regenerate exports.
"""
import pcbnew as p
from design import ROOT
from boards import xy


def main():
    folder = ROOT / 'teensy-adapter'
    for suffix in ('', '-placed'):
        path = folder / ('teensy-adapter' + suffix + '.kicad_pcb')
        board = p.LoadBoard(str(path))
        caps = [fp for fp in board.GetFootprints() if fp.GetReference() in {f'CM{i}' for i in range(1, 6)}]
        assert len(caps) == 5
        if all(fp.GetLayer() == p.F_Cu for fp in caps):
            continue
        if not suffix:
            for track in list(board.GetTracks()):
                if 'mic direct' in track.GetNetname() or (track.GetNetname() == 'GND' and not isinstance(track, p.PCB_VIA) and (abs(p.ToMM(track.GetStart().x) - 179.175) < .001 or abs(p.ToMM(track.GetEnd().x) - 179.175) < .001)):
                    board.Delete(track)
        for fp in board.GetFootprints():
            if fp.GetReference() not in {f'CM{i}' for i in range(1, 6)}:
                continue
            if fp.GetLayer() == p.F_Cu:
                continue
            fp.Flip(fp.GetPosition(), True)
            i = int(fp.GetReference()[2:])
            fp.SetOrientationDegrees(90)
            fp.SetPosition(xy(172.4, 90 - (i - 1) * 3.5))
        board.BuildConnectivity()
        p.ZONE_FILLER(board).Fill(board.Zones())
        p.SaveBoard(str(path), board)


if __name__ == '__main__':
    main()
