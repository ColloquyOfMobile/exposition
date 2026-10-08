"""Extract manufacturer Eagle mechanical geometry, adding KiCad 3D proxies.

Run with KiCad 9 Python. This deliberately omits electrical connectivity/routing.
"""
from pathlib import Path
import xml.etree.ElementTree as ET
import math
import shutil
import json
import re
import numpy as np
import pcbnew as p

ROOT=Path(__file__).resolve().parent
LIB=Path('C:/Program Files/KiCad/9.0/share/kicad')
SOURCE=ROOT/'source/A000067-cad-files/MEGA2560_Rev3e.brd'
board_xml=ET.parse(SOURCE).find('./drawing/board')
b=p.BOARD()
b.GetDesignSettings().SetBoardThickness(p.FromMM(1.6))
def xy(x,y): return p.VECTOR2I(p.FromMM(float(x)),p.FromMM(float(y)))
def pos(x,y): return (float(x)+50,110-float(y))
def n(e,k,default=0): return float(e.get(k,default))

def wire(e,transform,layer,parent=None):
    a=np.array([n(e,'x1'),n(e,'y1')]); c=np.array([n(e,'x2'),n(e,'y2')])
    s=p.PCB_SHAPE() if parent is None else p.PCB_SHAPE(parent)
    angle=math.radians(n(e,'curve'))
    if abs(angle)>1e-9:
        delta=c-a; centre=(a+c)/2+np.array([-delta[1],delta[0]])/(2*math.tan(angle/2))
        v=a-centre; half=angle/2
        mid=centre+np.array([v[0]*math.cos(half)-v[1]*math.sin(half),v[0]*math.sin(half)+v[1]*math.cos(half)])
        s.SetShape(p.SHAPE_T_ARC); s.SetArcGeometry(xy(*transform(*a)),xy(*transform(*mid)),xy(*transform(*c)))
    else:
        s.SetShape(p.SHAPE_T_SEGMENT); s.SetStart(xy(*transform(*a))); s.SetEnd(xy(*transform(*c)))
    s.SetLayer(layer); s.SetWidth(p.FromMM(max(.05,n(e,'width'))))
    (b if parent is None else parent).Add(s)

for e in board_xml.findall('./plain/wire'):
    if e.get('layer')=='20': wire(e,pos,p.Edge_Cuts)
for i,e in enumerate(board_xml.findall('./plain/hole'),1):
    f=p.FOOTPRINT(b); f.SetReference(f'H{i}'); f.Reference().SetVisible(False); f.Value().SetVisible(False)
    pad=p.PAD(f); pad.SetAttribute(p.PAD_ATTRIB_NPTH); pad.SetShape(p.PAD_SHAPE_CIRCLE)
    pad.SetDrillSize(xy(n(e,'drill'),n(e,'drill'))); pad.SetSize(xy(n(e,'drill'),n(e,'drill')))
    pad.SetLayerSet(p.LSET.AllCuMask()); f.Add(pad); b.Add(f); f.SetPosition(xy(*pos(e.get('x'),e.get('y'))))

packages={(lib.get('name'),pkg.get('name')):pkg for lib in board_xml.findall('./libraries/library') for pkg in lib.findall('./packages/package')}
mapping={
 '1X08':('Connector_PinSocket_2.54mm','PinSocket_1x08_P2.54mm_Vertical'),
 '1X10':('Connector_PinSocket_2.54mm','PinSocket_1x10_P2.54mm_Vertical'),
 '2X18':('Connector_PinSocket_2.54mm','PinSocket_2x18_P2.54mm_Vertical'),
 '2X03':('Connector_PinHeader_2.54mm','PinHeader_2x03_P2.54mm_Vertical'),
 'TQFP100':('Package_QFP','TQFP-100_14x14mm_P0.5mm'),
 'MLF32':('Package_DFN_QFN','QFN-32-1EP_5x5mm_P0.5mm_EP3.1x3.1mm'),
 'C0603-ROUND':('Capacitor_SMD','C_0603_1608Metric'),
 'R0603-ROUND':('Resistor_SMD','R_0603_1608Metric'),
 'CT/CN0603':('Resistor_SMD','R_0603_1608Metric'),
 'CHIPLED_0805':('LED_SMD','LED_0805_2012Metric'),
 '0805':('Inductor_SMD','L_0805_2012Metric'),
 'CAY16':('Resistor_SMD','R_Array_Convex_4x0603'),
 'LINEAR_SOT223':('Package_TO_SOT_SMD','SOT-223-3_TabPin2'),
 'SOT-23':('Package_TO_SOT_SMD','SOT-23'),
 'SOT23-DBV':('Package_TO_SOT_SMD','SOT-23-5'),
 'MSOP08':('Package_SO','MSOP-8_3x3mm_P0.65mm'),
 'SMB':('Diode_SMD','D_SMB'),
 'MINIMELF':('Diode_SMD','D_MiniMELF'),
 'L1812':('Fuse','Fuse_1812_4532Metric'),
 'PANASONIC_D':('Capacitor_SMD','CP_Elec_6.3x5.8'),
 'PN61729':('Connector_USB','USB_B_Lumberg_2411_02_Horizontal'),
 'POWERSUPPLY_DC-21MM':('Connector_BarrelJack','BarrelJack_Horizontal'),
 'TS42':('Button_Switch_SMD','SW_Push_1TS009xxxx-xxxx-xxxx_6x6x5mm'),
 'QS':('Crystal','Crystal_SMD_HC49-SD'),
 'RESONATOR':('Crystal','Resonator_SMD_Murata_CSTCE-3Pin_3.2x1.3mm'),
}
retained=[]
report=[]
for e in board_xml.findall('./elements/element'):
    package=e.get('package'); ref=e.get('name')
    if package=='FRAME': continue
    pkg=packages[(e.get('library'),package)]
    rotation=e.get('rot','R0'); angle=math.radians(float(rotation.replace('M','').replace('R','')))
    def transform(x,y):
        if 'M' in rotation: x=-x
        return pos(n(e,'x')+x*math.cos(angle)-y*math.sin(angle),n(e,'y')+x*math.sin(angle)+y*math.cos(angle))
    f=p.FOOTPRINT(b); f.SetReference(ref); f.SetValue(e.get('value',''))
    f.Reference().SetVisible(False); f.Value().SetVisible(False); b.Add(f)
    points={}
    for item in list(pkg.findall('pad'))+list(pkg.findall('smd')):
        pad=p.PAD(f); pad.SetNumber(item.get('name')); loc=transform(n(item,'x'),n(item,'y')); points[item.get('name')]=loc
        pad.SetPosition(xy(*loc))
        if item.tag=='pad':
            drill=n(item,'drill'); diameter=n(item,'diameter',drill*1.6)
            pad.SetAttribute(p.PAD_ATTRIB_PTH); pad.SetDrillSize(xy(drill,drill)); pad.SetSize(xy(diameter,diameter))
            pad.SetShape(p.PAD_SHAPE_RECT if item.get('shape')=='square' else p.PAD_SHAPE_CIRCLE)
            layers=p.LSET.AllCuMask(); layers.AddLayer(p.F_Mask); layers.AddLayer(p.B_Mask); pad.SetLayerSet(layers)
        else:
            pad.SetAttribute(p.PAD_ATTRIB_SMD); pad.SetShape(p.PAD_SHAPE_RECT); pad.SetSize(xy(n(item,'dx'),n(item,'dy')))
            layers=p.LSET(); layers.AddLayer(p.F_Cu); layers.AddLayer(p.F_Mask); layers.AddLayer(p.F_Paste); pad.SetLayerSet(layers)
            pad.SetOrientationDegrees(math.degrees(angle)+float(item.get('rot','R0').replace('R','')))
        f.Add(pad)
    for w in pkg.findall('wire'):
        if w.get('layer')=='21': wire(w,transform,p.F_SilkS,f)
    if package in ('PN61729','RESONATOR','QS','TS42','MLF32','L1812'):
        model_fp=p.FOOTPRINT(b); model_fp.SetReference(ref+'_3D')
        model_fp.Reference().SetVisible(False); model_fp.Value().SetVisible(False)
        model_fp.SetPosition(xy(*transform(0,0))); model_fp.SetOrientationDegrees(math.degrees(angle))
        model=p.FP_3DMODEL(); model.m_Filename='${KIPRJMOD}/3dmodels/'+package+'_envelope.step'
        model_fp.Add3DModel(model); b.Add(model_fp)
        report.append({'ref':ref,'source_package':package,'proxy':package+'_envelope','pad_fit_rms_mm':None})
        continue
    if package not in mapping: continue
    lib,name=mapping[package]
    model_fp=p.FootprintLoad(str(LIB/'footprints'/f'{lib}.pretty'),name)
    if not model_fp:
        print('Missing proxy',package,name); continue
    srcpoints={pad.GetNumber():np.array([p.ToMM(pad.GetPosition().x),p.ToMM(pad.GetPosition().y)]) for pad in model_fp.Pads() if pad.GetNumber()}
    common=[key for key in srcpoints if key in points]
    # Package pad numbers align orientation where available; otherwise use body centre.
    if len(common)>=2:
        src=np.array([srcpoints[k] for k in common]); dst=np.array([points[k] for k in common])
        choices=[]
        for degrees in (0,90,180,270):
            rad=math.radians(degrees); rot=np.array([[math.cos(rad),math.sin(rad)],[-math.sin(rad),math.cos(rad)]])
            offset=dst.mean(0)-(src@rot.T).mean(0); error=np.mean(np.sum((src@rot.T+offset-dst)**2,axis=1))
            choices.append((error,degrees,offset))
        error,degrees,offset=min(choices,key=lambda c:c[0])
    else:
        degrees=math.degrees(angle); offset=np.array(transform(0,0)); error=None
    if ref=='X1':
        # Eagle jack numbering differs from the KiCad proxy: rear centre is 2.
        degrees=0; offset=np.array(points['2']); error=None
    if ref in ('IC1','T1'):
        # Different pin naming in these library variants; centre the body instead.
        degrees=math.degrees(angle); offset=np.array(transform(0,0)); error=None
    model_fp.SetOrientationDegrees(degrees); model_fp.SetPosition(xy(*offset))
    model_fp.SetReference(ref+'_3D'); model_fp.Reference().SetVisible(False); model_fp.Value().SetVisible(False)
    for item in list(model_fp.Pads())+list(model_fp.GraphicalItems()):
        retained.append(item); model_fp.Remove(item)
    for model in model_fp.Models():
        source=LIB/'3dmodels'/model.m_Filename.split('}/')[-1]
        out=ROOT/'3dmodels'/source.name; out.parent.mkdir(exist_ok=True)
        if not source.exists():
            print('Missing STEP',source); continue
        shutil.copy2(source,out)
        model.m_Filename='${KIPRJMOD}/3dmodels/'+source.name
    b.Add(model_fp)
    report.append({'ref':ref,'source_package':package,'proxy':name,'pad_fit_rms_mm':None if error is None else round(math.sqrt(error),4)})

# Keep useful top-side manufacturer legends with their source locations.
for e in board_xml.findall('./plain/text'):
    if e.get('layer') not in ('21','25') or not e.text: continue
    t=p.PCB_TEXT(b); t.SetText(e.text); t.SetPosition(xy(*pos(n(e,'x'),n(e,'y')))); t.SetLayer(p.F_SilkS)
    size=n(e,'size',1); t.SetTextSize(xy(size,size)); t.SetTextThickness(p.FromMM(max(.1,size*.12)))
    t.SetTextAngle(p.EDA_ANGLE(float(e.get('rot','R0').replace('R','')),p.DEGREES_T)); b.Add(t)
    t.SetHorizJustify(p.GR_TEXT_H_ALIGN_LEFT); t.SetVertJustify(p.GR_TEXT_V_ALIGN_BOTTOM)

out=ROOT/'arduino-mega-reference.kicad_pcb'
p.SaveBoard(str(out),b)
# Mechanical reference colour; source board soldermask is blue.
stackup='''(stackup
 (layer "F.SilkS" (type "Top Silk Screen") (color "White"))
 (layer "F.Mask" (type "Top Solder Mask") (color "Blue") (thickness 0.01))
 (layer "F.Cu" (type "copper") (thickness 0.035))
 (layer "dielectric 1" (type "core") (thickness 1.51) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
 (layer "B.Cu" (type "copper") (thickness 0.035))
 (layer "B.Mask" (type "Bottom Solder Mask") (color "Blue") (thickness 0.01))
 (layer "B.SilkS" (type "Bottom Silk Screen") (color "White")))'''
content=out.read_text().replace('(setup','(setup\n'+stackup,1)
# SWIG Models() iteration returns value copies; rewrite saved library paths.
content=re.sub(r'\$\{KICAD9_3DMODEL_DIR\}/[^/\"]+/([^\"]+)',r'${KIPRJMOD}/3dmodels/\1',content)
out.write_text(content)
report_path=ROOT/'model-mapping.json'; report_path.write_text(json.dumps(report,indent=2)+'\n')
print(f'Saved {len(report)} component models; 6 original mounting holes.')
print('Approximate fits:',[(r['ref'],r['pad_fit_rms_mm']) for r in report if (r['pad_fit_rms_mm'] or 0)>.3])


