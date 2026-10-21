"""Export the existing v2 body assemblies with KiCad Python, without editing PCBs."""
from pathlib import Path
import argparse
import hashlib
import json

import pcbnew as p
from visual_exports import export_visual

ROOT = Path(__file__).resolve().parent
CAD = ROOT.parent.parent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--only', choices=('female-base-v2', 'male-static-v2'))
    args = parser.parse_args()
    for folder, name in [('female base v2', 'female-base-v2'), ('male static v2', 'male-static-v2')]:
        if args.only and name != args.only:
            continue
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
        data['visual_export'] = export_visual(source, ROOT / 'exports' / (name + '.glb'))
        (ROOT / 'exports' / (name + '.json')).write_text(json.dumps(data, indent=2) + '\n')
        print(name, 'exported with its current components', flush=True)


if __name__ == '__main__':
    main()
