"""Export visual board copies. Run with KiCad Python; never edits source PCBs."""
from pathlib import Path
import json, math, re, shutil, subprocess, sys
import numpy as np
import pcbnew as p
ROOT=Path(__file__).resolve().parent
SHIELDS=ROOT.parent
LIB=Path('C:/Program Files/KiCad/9.0/share/kicad')
CLI=LIB.parents[1]/'bin/kicad-cli.exe'
NAMES=['backplane','teensy-adapter','voice-thomas','microphone','analyser-carrier','dfrobot-module','arduino-mega-reference','teensy41-reference']
for folder in ['exports','inputs','logs']:(ROOT/folder).mkdir(parents=True,exist_ok=True)
def xy(x,y):return p.VECTOR2I(p.FromMM(float(x)),p.FromMM(float(y)))
def points(fp):return [np.array([p.ToMM(q.GetPosition().x),p.ToMM(q.GetPosition().y)]) for q in fp.Pads() if q.GetAttribute()!=p.PAD_ATTRIB_NPTH]

def main(name):
    source=SHIELDS/name/(name+'.kicad_pcb');b=p.LoadBoard(str(source));retained=[];added=[];missing=[]
    def header(ref,targets,rows,count,bottom=False):
        kind='PinSocket' if bottom or ref.startswith('DFR') else 'PinHeader'
        lib='Connector_'+kind+'_2.54mm';part=f'{kind}_{rows}x{count:02d}_P2.54mm_Vertical'
        f=p.FootprintLoad(str(LIB/'footprints'/f'{lib}.pretty'),part)
        if f is None:raise RuntimeError(part)
        b.Add(f)
        if bottom:f.Flip(xy(0,0),p.FLIP_DIRECTION_TOP_BOTTOM)
        best=None;target=np.array(targets)
        for angle in [0,90,180,270]:
            f.SetOrientationDegrees(angle);f.SetPosition(xy(0,0));src=np.array(points(f))
            # Include keyed missing pad by bounding-box alignment, not mean.
            offset=(target.min(0)+target.max(0)-src.min(0)-src.max(0))/2
            distances=np.sqrt(((target[:,None,:]-(src+offset)[None,:,:])**2).sum(2))
            error=distances.min(1).max()
            if best is None or error<best[0]:best=(error,angle,offset)
        assert best[0]<.01,(ref,best)
        f.SetOrientationDegrees(best[1]);f.SetPosition(xy(*best[2]));f.SetReference(ref+'_VISUAL')
        f.Reference().SetVisible(False);f.Value().SetVisible(False)
        for item in list(f.Pads())+list(f.GraphicalItems()):retained.append(item);f.Remove(item)
        added.append(ref+': '+part)
    original=list(b.GetFootprints())
    for f in original:
        ref=f.GetReference();part=str(f.GetFPID().GetLibItemName())
        if part.startswith(('Header_2x','Socket_2x')):
            count=11 if '2x11' in part else 3
            header(ref,points(f),2,count,f.GetLayer()==p.B_Cu)
        elif ref in ('A1','JM1') and name in ('backplane','teensy-adapter'):
            todo=points(f)
            while todo:
                group=[todo.pop()];changed=True
                while changed:
                    changed=False
                    for q in todo[:]:
                        if any(np.linalg.norm(q-other)<2.55 for other in group):
                            todo=[t for t in todo if t is not q];group.append(q);changed=True
                spans=np.ptp(np.array(group),axis=0);rows=2 if min(spans)>1 else 1
                header(ref+'_'+str(len(added)),group,rows,round(max(spans)/2.54)+1,ref=='JM1')
        elif name=='analyser-carrier' and ref in ['M1','M2','M3','M4','M5']:
            pads={q.GetNumber():np.array([p.ToMM(q.GetPosition().x),p.ToMM(q.GetPosition().y)]) for q in f.Pads()}
            header('DFR_'+ref+'_input',[pads[str(i)] for i in range(1,7)],1,6)
            header('DFR_'+ref+'_control',[pads[str(i)] for i in (7,8)],1,2)
        elif not list(f.Models()) and ref in ('MK1','J2','J6'):
            missing.append({'ref':ref,'footprint':part,'position_mm':list(map(float,p.ToMM(f.GetPosition()))),'kind':'unmodelled body; see Blender proxy'})
    # Resolve models before moving visual input copies to a different directory.
    dest=ROOT/'inputs'/(name+'.kicad_pcb');p.SaveBoard(str(dest),b)
    content=dest.read_text()
    content=content.replace('${KIPRJMOD}',source.parent.as_posix()).replace('${KICAD9_3DMODEL_DIR}',(LIB/'3dmodels').as_posix())
    dest.write_text(content)
    meta={'source':str(source.relative_to(SHIELDS)),'extra_header_models':added,'unmodelled_bodies':missing,
          'footprints':{f.GetReference():{'xy':list(map(float,p.ToMM(f.GetPosition()))),'angle':f.GetOrientationDegrees(),
          'pads':{q.GetNumber():list(map(float,p.ToMM(q.GetPosition()))) for q in f.Pads() if q.GetNumber()}} for f in original}}
    (ROOT/'exports'/(name+'.json')).write_text(json.dumps(meta,indent=2))
    for fmt in ['step','glb']:
        cmd=[str(CLI),'pcb','export',fmt,'--force','--subst-models','--user-origin','0x0mm','-o',str(ROOT/'exports'/(name+'.'+fmt))]
        if fmt=='glb':cmd+=['--include-pads','--include-silkscreen']
        with (ROOT/'logs'/(name+'-'+fmt+'.log')).open('w') as log:
            subprocess.run(cmd+[str(dest)],stdout=log,stderr=subprocess.STDOUT,check=True)
    print(name,'STEP/GLB exported;',len(added),'added connector bodies;',len(missing),'body proxies pending',flush=True)

if __name__=='__main__':
    if len(sys.argv)>1:main(sys.argv[1])
    else:
        for name in NAMES:subprocess.run([sys.executable,__file__,name],check=True)
