"""Export exactly one seated microphone per orientation; run with KiCad Python."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

import pcbnew as p

ROOT=Path(__file__).resolve().parent
ASSEMBLY=ROOT.parents[4]/'CAD/Blender/pcb-assemblies'
sys.path.insert(0,str(ASSEMBLY/'scripts'))
from visual_exports import CLI, export_visual
WORK=ROOT/'variants'
WORK.mkdir(parents=True,exist_ok=True)


def attach(fp,path):
    model=p.FP_3DMODEL();model.m_Filename=path.resolve().as_posix();fp.Add3DModel(model)


def preview():
    """Refresh the orientation comparison from the same saved variant PCBs."""
    from PIL import Image, ImageDraw, ImageFont
    canvas=Image.new('RGB',(1800,900),'white')
    draw=ImageDraw.Draw(canvas)
    font=ImageFont.truetype('C:/Windows/Fonts/arial.ttf',24)
    heading=ImageFont.truetype('C:/Windows/Fonts/arialbd.ttf',30)
    draw.text((30,15),'MICROPHONE FLEX / REMOVABLE GAIN AND A/R SELECTORS',font=heading,fill='black')
    draw.text((30,55),'Initial shunts: JP1 2-3 = 40 dB; JP2 1-2 = 1:500. Fit one module only.',font=font,fill='black')
    hashes={}
    for i,orientation in enumerate(('left','right','up')):
        image=WORK/(orientation+'.png')
        subprocess.run([str(CLI),'pcb','render','--width','800','--height','960',
                        '--background','opaque','--side','top','--rotate','335,0,20','--zoom','0.7',
                        '-o',str(image),str(WORK/(orientation+'.kicad_pcb'))],
                       check=True,stdout=subprocess.DEVNULL)
        with Image.open(image) as rendered:
            canvas.paste(rendered.convert('RGB').resize((600,720)),(600*i,140))
        draw.text((600*i+30,105),orientation.upper()+(' / DOWN' if orientation!='up' else ''),font=heading,fill='black')
        hashes[orientation]=hashlib.sha256(image.read_bytes()).hexdigest()
    draw.text((30,865),'Generic header/shunt proxies. Physical dimensions and adjustment access require checking.',font=font,fill='black')
    path=ASSEMBLY/'previews/microphone-positions-preview.png'
    staged=path.with_name(path.stem+'-staged.png')
    canvas.save(staged)
    staged.replace(path)
    hashes['comparison']=hashlib.sha256(path.read_bytes()).hexdigest()
    return hashes


def main():
    source=ROOT/'microphone-flex.kicad_pcb'
    source_hash=hashlib.sha256(source.read_bytes()).hexdigest()
    reports={}
    for orientation in ('up','left','right'):
        board=p.LoadBoard(str(source));parts={fp.GetReference():fp for fp in board.GetFootprints()}
        for fp in parts.values():
            models=list(fp.Models())
            fp.Models().clear()
            for model in models:
                model.m_Filename=model.m_Filename.replace('${KIPRJMOD}',ROOT.as_posix())
                fp.Add3DModel(model)
        if orientation=='up':
            attach(parts['M1'],ROOT.parents[2]/'old-reference/microphone-rev-b/3dmodels/MAX9814_Module_reference.step')
            for ref in ('H3','H4'):
                if ref in parts:
                    attach(parts[ref],ROOT.parents[2]/'old-reference/microphone-rev-b/3dmodels/M2_insulating_support_reference.step')
        else:
            dummy=p.FOOTPRINT(board);board.Add(dummy);dummy.SetReference('VISUAL_MODULE_'+orientation.upper())
            dummy.Reference().SetVisible(False);dummy.Value().SetVisible(False)
            # These models include the current socket translation and the
            # 180-degree turn around its horizontal insertion axis.
            attach(dummy,ROOT/'3dmodels'/f'module-{orientation}-down.step')
        staged=WORK/(orientation+'.kicad_pcb');p.SaveBoard(str(staged),board,True)
        dest=ASSEMBLY/'exports'/('microphone-flex-'+orientation+'.glb')
        visual=export_visual(staged,dest,source)
        meta={'source':'microphone-flex/microphone-flex.kicad_pcb','source_sha256':source_hash,
              'orientation':orientation,'module_population':1,'physical_fit_verified':False,'visual_export':visual,
              'side_module_direction':'downward' if orientation!='up' else 'upward',
              'module_support_holes':[ref for ref in ('H3','H4','H5','H6','H7','H8') if ref in parts],
              'footprints':{fp.GetReference():{'xy':list(map(float,p.ToMM(fp.GetPosition()))),
                  'angle':fp.GetOrientationDegrees(),
                  'pads':{q.GetNumber():list(map(float,p.ToMM(q.GetPosition()))) for q in fp.Pads() if q.GetNumber()}}
                  for fp in parts.values()}}
        dest.with_suffix('.json').write_text(json.dumps(meta,indent=2)+'\n')
        reports[orientation]={'glb_sha256':hashlib.sha256(dest.read_bytes()).hexdigest(),'one_module_only':True}
    # Variant PCBs are explicit assembled viewing copies, with identical copper.
    (ROOT/'variant-validation.json').write_text(json.dumps({
        'source_sha256':source_hash,'variants':reports,'preview_sha256':preview()},indent=2)+'\n')


if __name__=='__main__':main()
