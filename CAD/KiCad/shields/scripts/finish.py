"""Finish readable silkscreen and normalize local library mounting sides.

Does not change copper, pad placement, or the electrical circuit.
"""
import json
import pcbnew as p
from design import ROOT
from boards import xy,mm


def box(item,gap=0):
    b=item.GetBoundingBox();g=mm(gap)
    return (b.GetLeft()-g,b.GetTop()-g,b.GetRight()+g,b.GetBottom()+g)
def intersects(a,b):return a[0]<b[2] and b[0]<a[2] and a[1]<b[3] and b[1]<a[3]
def inside(a,b):return b[0]<=a[0] and b[1]<=a[1] and b[2]>=a[2] and b[3]>=a[3]


def finish(folder):
    name=folder.name;path=folder/(name+'.kicad_pcb')
    if not path.exists():return
    board=p.LoadBoard(str(path));bounds=board.GetBoardEdgesBoundingBox()
    limit=(bounds.GetLeft()+mm(.3),bounds.GetTop()+mm(.3),bounds.GetRight()-mm(.3),bounds.GetBottom()-mm(.3))
    obstacles={p.F_SilkS:[],p.B_SilkS:[]};accepted={p.F_SilkS:[],p.B_SilkS:[]}
    fields=[]
    for fp in board.GetFootprints():
        if fp.GetReference().startswith('H') and fp.GetFPID().GetLibNickname()!='Shields':
            fp.SetFPID(p.LIB_ID('Shields','MountingHole_3.2mm_M3'))
        for pad in fp.Pads():
            for silk,mask in [(p.F_SilkS,p.F_Mask),(p.B_SilkS,p.B_Mask)]:
                if pad.IsOnLayer(mask):obstacles[silk].append(box(pad,.2))
        for item in fp.GraphicalItems():
            if item.GetLayer() in obstacles:obstacles[item.GetLayer()].append(box(item,.1))
        if fp.Reference().IsVisible():fields.append(fp.Reference())
    # Titles have priority over the movable references.
    texts=[x for x in board.GetDrawings() if isinstance(x,p.PCB_TEXT) and x.GetLayer() in obstacles]
    moved=[]
    for field in texts+fields:
        layer=field.GetLayer()
        if layer not in obstacles:continue
        field.SetTextSize(xy(max(.8,p.ToMM(field.GetTextSize().x)),max(.8,p.ToMM(field.GetTextSize().y))))
        field.SetTextThickness(mm(.12));field.SetMirrored(layer==p.B_SilkS)
        field.SetTextAngle(p.EDA_ANGLE(0,p.DEGREES_T))
        if name.startswith('voice') and layer==p.B_SilkS and field in texts:
            accepted[layer].append(box(field,.05));continue  # Fixed table rows must not drift.
        origin=field.GetPosition();found=False
        # Reference text stays close to its part; top/bottom offsets first.
        candidates=[(0,0)]
        for dist in [1.5,3,4.5,6]:
            candidates += [(0,dist),(0,-dist),(dist,0),(-dist,0),(dist,dist),(-dist,dist),(dist,-dist),(-dist,-dist)]
        for dx,dy in candidates:
            field.SetPosition(origin+xy(dx,dy));b=box(field,.1)
            if inside(b,limit) and not any(intersects(b,o) for o in obstacles[layer]+accepted[layer]):
                accepted[layer].append(b);found=True;break
        if not found:
            field.SetPosition(origin);field.SetLayer(p.B_Fab if layer==p.B_SilkS else p.F_Fab)
            moved.append(field.GetText())
    # Save bottom-mounted footprints in the canonical front-side library view.
    # This resolves library mismatches without changing any physical pad position.
    io=p.PCB_IO_MGR.PluginFind(p.PCB_IO_MGR.KICAD_SEXP)
    for fp in board.GetFootprints():
        if fp.GetLayer()!=p.B_Cu:continue
        lib=fp.Duplicate();lib.Flip(lib.GetPosition(),True);lib.SetOrientationDegrees(0);lib.SetPosition(xy(0,0))
        lib.Reference().SetVisible(True);lib.Reference().SetLayer(p.F_SilkS);lib.Reference().SetMirrored(False)
        io.FootprintSave(str(ROOT/'Shields.pretty'),lib)
    p.SaveBoard(str(path),board)
    reports=folder/'reports';reports.mkdir(exist_ok=True)
    assembly_refs=sorted(fp.GetReference() for fp in board.GetFootprints() if fp.Reference().GetLayer() in [p.F_Fab,p.B_Fab])
    (reports/'silkscreen.json').write_text(json.dumps({'references_on_assembly_layer_due_to_space':assembly_refs},indent=2)+'\n')
    print(name,'finished;',len(moved),'labels moved to assembly layer',flush=True)


if __name__=='__main__':
    for f in ROOT.iterdir():
        if (f/'circuit.json').exists():finish(f)
