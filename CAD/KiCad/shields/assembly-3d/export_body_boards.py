"""Export the existing v2 body assemblies with KiCad Python, without editing PCBs."""
from pathlib import Path
import hashlib
import json
import subprocess

import pcbnew as p

ROOT = Path(__file__).resolve().parent
CAD = ROOT.parent.parent
CLI = Path('C:/Program Files/KiCad/9.0/bin/kicad-cli.exe')


def main():
    for folder, name in [('female base v2', 'female-base-v2'), ('male static v2', 'male-static-v2')]:
        source = CAD / folder / (name + '.kicad_pcb')
        board = p.LoadBoard(str(source))
        missing = []
        for fp in board.GetFootprints():
            for model in fp.Models():
                resolved = Path(model.m_Filename.replace('${KIPRJMOD}', source.parent.as_posix()))
                if not resolved.is_file():
                    missing.append(str(resolved))
        assert not missing, missing
        outline = p.SHAPE_POLY_SET()
        assert board.GetBoardPolygonOutlines(outline)
        box = outline.BBox()
        data = {
            'source': source.relative_to(CAD).as_posix(),
            'sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'outline_mm': [p.ToMM(box.GetX()), p.ToMM(box.GetY()), p.ToMM(box.GetWidth()), p.ToMM(box.GetHeight())],
            'footprints': {
                fp.GetReference(): {
                    'xy': list(map(float, p.ToMM(fp.GetPosition()))),
                    'angle': fp.GetOrientationDegrees(),
                    'models': [model.m_Filename for model in fp.Models()],
                }
                for fp in board.GetFootprints()
            },
        }
        subprocess.run([
            str(CLI), 'pcb', 'export', 'glb', '--force', '--subst-models',
            '--user-origin', '0x0mm', '--include-pads', '--include-silkscreen',
            '-o', str(ROOT / 'exports' / (name + '.glb')), str(source),
        ], check=True)
        (ROOT / 'exports' / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')
        print(name, 'exported with existing amplifier and both clamps', flush=True)


if __name__ == '__main__':
    main()
