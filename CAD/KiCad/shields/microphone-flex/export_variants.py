"""Export exactly one seated microphone per orientation; run with KiCad Python."""
from pathlib import Path
import hashlib
import json
import sys

import pcbnew as p

ROOT=Path(__file__).resolve().parent
ASSEMBLY=ROOT.parent/'assembly-3d'
sys.path.insert(0,str(ASSEMBLY))
from visual_exports import export_visual
WORK=ROOT/'variants'
WORK.mkdir(parents=True,exist_ok=True)


def attach(fp,path):
    model=p.FP_3DMODEL();model.m_Filename=path.resolve().as_posix();fp.Add3DModel(model)


def main():
    source=ROOT/'microphone-flex.kicad_pcb'
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    reports={}
    for orientation in ('up','left','right'):
        board=p.LoadBoard(str(source));parts={fp.GetReference():fp for fp in board.GetFootprints()}
        for fp in parts.values():
            for model in fp.Models():
                model.m_Filename=model.m_Filename.replace('${KIPRJMOD}',ROOT.as_posix())
        if orientation=='up':
            attach(parts['M1'],ROOT.parent/'microphone/3dmodels/MAX9814_Module_reference.step')
            for ref in ('H3','H4'):attach(parts[ref],ROOT.parent/'microphone/3dmodels/M2_insulating_support_reference.step')
        else:
            dummy=p.FOOTPRINT(board);board.Add(dummy);dummy.SetReference('VISUAL_MODULE_'+orientation.upper())
            dummy.Reference().SetVisible(False);dummy.Value().SetVisible(False)
            attach(dummy,ROOT/'3dmodels'/f'module-{orientation}.step')
            attach(dummy,ROOT/'3dmodels'/f'supports-{orientation}.step')
        staged=WORK/(orientation+'.kicad_pcb');p.SaveBoard(str(staged),board,True)
        dest=ASSEMBLY/'exports'/('microphone-flex-'+orientation+'.glb')
        visual=export_visual(staged,dest,source)
        meta={'source':'microphone-flex/microphone-flex.kicad_pcb','source_sha256':source_hash,
              'orientation':orientation,'module_population':1,'physical_fit_verified':False,'visual_export':visual,
              'footprints':{fp.GetReference():{'xy':list(map(float,p.ToMM(fp.GetPosition()))),
                  'angle':fp.GetOrientationDegrees(),
                  'pads':{q.GetNumber():list(map(float,p.ToMM(q.GetPosition()))) for q in fp.Pads() if q.GetNumber()}}
                  for fp in parts.values()}}
        dest.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n')
        reports[orientation]={'glb_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'one_module_only':True}
    # Variant PCBs are explicit assembled viewing copies, with identical copper.
    (ROOT/'variant-validation.json').write_text(json.dumps({'source_sha256':source_hash,'variants':reports},indent=2)+'\n')


if __name__=='__main__':main()
