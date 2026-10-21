"""Export the same model choices and visible layers as KiCad's 3D viewer.

Run from KiCad Python. Intermediate VRML lives under ignored tmp/, while GLB
and dependency fingerprints are stored with the assembly exports.
"""
from pathlib import Path
import hashlib
import json
import subprocess

import pcbnew as p

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[2]
CAD = REPO / 'CAD' / 'KiCad'
CLI = Path('C:/Program Files/KiCad/9.0/bin/kicad-cli.exe')
BLENDER = Path('C:/Program Files/Blender Foundation/Blender 5.2/blender.exe')
LIB = CLI.parent.parent / 'share' / 'kicad' / '3dmodels'


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def label(path):
    path = Path(path).resolve()
    for base, prefix in ((CAD, 'CAD/KiCad/'), (LIB, '${KICAD9_3DMODEL_DIR}/')):
        try:
            return prefix + path.relative_to(base).as_posix()
        except ValueError:
            pass
    return path.as_posix()


def prepare(source, destination, original=None):
    source, destination = Path(source).resolve(), Path(destination).resolve()
    original = Path(original or source).resolve()
    board = p.LoadBoard(str(source))
    order = []
    for fp in board.GetFootprints():
        for model in fp.Models():
            if not model.m_Show:
                continue
            filename = model.m_Filename.replace('${KIPRJMOD}', source.parent.as_posix())
            filename = filename.replace('${KICAD9_3DMODEL_DIR}', LIB.as_posix())
            path = Path(filename)
            if not path.is_absolute():
                path = source.parent / path
            if not path.is_file():
                raise FileNotFoundError(f'{source}: {fp.GetReference()} model {path}')
            order.append({'ref': fp.GetReference(), 'file': label(path), 'sha256': digest(path),
                          'offset_mm': [model.m_Offset.x, model.m_Offset.y, model.m_Offset.z],
                          'rotation_deg': [model.m_Rotation.x, model.m_Rotation.y, model.m_Rotation.z],
                          'scale': [model.m_Scale.x, model.m_Scale.y, model.m_Scale.z]})
    work = REPO / 'tmp' / 'kicad-visual-exports'
    work.mkdir(parents=True, exist_ok=True)
    vrml = work / (destination.stem + '.wrl')
    subprocess.run([str(CLI), 'pcb', 'export', 'vrml', '--force', '--user-origin', '0x0mm',
                    '--units', 'mm', '-o', str(vrml), str(source)], check=True)
    entry = {'name': destination.stem, 'vrml': str(vrml), 'output': str(destination),
             'thickness_mm': p.ToMM(board.GetDesignSettings().GetBoardThickness()), 'model_order': order}
    metadata = {'pipeline': 'KiCad native VRML visual layers -> Blender GLB; no STEP substitution',
                'source': label(original), 'source_sha256': digest(original),
                'visual_input_sha256': digest(source), 'native_vrml_sha256': digest(vrml),
                'models': order, 'pcb_underside_z_mm': 0}
    return entry, metadata


def convert(entries):
    manifest = REPO / 'tmp' / 'kicad-visual-exports' / 'manifest.json'
    manifest.write_text(json.dumps(entries, indent=2) + '\n')
    subprocess.run([str(BLENDER), '--background', '--python-exit-code', '1', '--python',
                    str(ROOT / 'scripts/kicad_vrml.py'), '--', str(manifest)], check=True)
    return json.loads(manifest.with_suffix('.results.json').read_text())


def export_visual(source, destination, original=None):
    entry, metadata = prepare(source, destination, original)
    metadata['mesh_counts'] = convert([entry])[entry['name']]
    metadata['glb_sha256'] = digest(destination)
    return metadata
