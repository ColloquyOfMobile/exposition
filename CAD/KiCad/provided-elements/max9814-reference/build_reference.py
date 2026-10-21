"""Mechanical MAX9814 reference from Adafruit Eagle geometry; KiCad 9 Python.

The microphone side is F.Cu. Original components are on B.Cu. No routing.
"""
from pathlib import Path
import json
import math
import re
import shutil
import xml.etree.ElementTree as ET
import pcbnew as p

ROOT = Path(__file__).resolve().parent
LIB = Path('C:/Program Files/KiCad/9.0/share/kicad')
xml = ET.parse(ROOT / 'source/Adafruit MAX9814.brd').find('./drawing/board')
b = p.BOARD()
b.GetDesignSettings().SetBoardThickness(p.FromMM(1.6))
WIDTH, HEIGHT = 25.4, 14.097


def xy(x, y):
    return p.VECTOR2I(p.FromMM(float(x)), p.FromMM(float(y)))


def num(e, key, default=0):
    return float(e.get(key, default))


def pos(x, y):
    # Reflect the source so its microphone side faces up, header on the right.
    return 50 + WIDTH - float(x), 50 + HEIGHT - float(y)


def wire(e, transform, layer, parent=None):
    s = p.PCB_SHAPE(parent) if parent else p.PCB_SHAPE()
    a = (num(e, 'x1'), num(e, 'y1'))
    c = (num(e, 'x2'), num(e, 'y2'))
    angle = math.radians(num(e, 'curve'))
    if angle:
        dx, dy = c[0] - a[0], c[1] - a[1]
        cx = (a[0] + c[0]) / 2 - dy / (2 * math.tan(angle / 2))
        cy = (a[1] + c[1]) / 2 + dx / (2 * math.tan(angle / 2))
        vx, vy = a[0] - cx, a[1] - cy
        mid = (cx + vx * math.cos(angle / 2) - vy * math.sin(angle / 2),
               cy + vx * math.sin(angle / 2) + vy * math.cos(angle / 2))
        s.SetShape(p.SHAPE_T_ARC)
        s.SetArcGeometry(xy(*transform(*a)), xy(*transform(*mid)), xy(*transform(*c)))
    else:
        s.SetShape(p.SHAPE_T_SEGMENT)
        s.SetStart(xy(*transform(*a)))
        s.SetEnd(xy(*transform(*c)))
    s.SetLayer(layer)
    s.SetWidth(p.FromMM(max(.05, num(e, 'width'))))
    (parent if parent else b).Add(s)


for e in xml.findall('./plain/wire'):
    if e.get('layer') == '20':
        wire(e, pos, p.Edge_Cuts)

packages = {(lib.get('name'), pkg.get('name')): pkg
            for lib in xml.findall('./libraries/library')
            for pkg in lib.findall('./packages/package')}
mapping = {
    'C0805K': ('Capacitor_SMD', 'C_0805_2012Metric'),
    'R0805': ('Resistor_SMD', 'R_0805_2012Metric'),
    '0805': ('Inductor_SMD', 'L_0805_2012Metric'),
    'TDFN14_3X3MM': ('Package_DFN_QFN', 'TDFN-14-1EP_3x3mm_P0.4mm_EP1.78x2.35mm'),
}
report = []
retained = []
for e in xml.findall('./elements/element'):
    package, ref = e.get('package'), e.get('name')
    if package == 'ADAFRUIT_3.5MM':
        continue
    pkg = packages[(e.get('library'), package)]
    rot = e.get('rot', 'R0')
    degrees = float(rot.replace('M', '').replace('R', ''))
    angle = math.radians(degrees)
    mirror = 'M' in rot

    def transform(x, y):
        x = -x if mirror else x
        return pos(num(e, 'x') + x * math.cos(angle) - y * math.sin(angle),
                   num(e, 'y') + x * math.sin(angle) + y * math.cos(angle))

    layer = p.F_Cu if mirror else p.B_Cu
    f = p.FOOTPRINT(b)
    f.SetLayer(layer)
    f.SetReference(ref)
    f.SetValue(e.get('value', ''))
    f.Reference().SetVisible(False)
    f.Value().SetVisible(False)
    b.Add(f)
    for item in list(pkg.findall('pad')) + list(pkg.findall('smd')):
        pad = p.PAD(f)
        pad.SetNumber(item.get('name'))
        pad.SetPosition(xy(*transform(num(item, 'x'), num(item, 'y'))))
        if item.tag == 'pad':
            drill = num(item, 'drill')
            diameter = num(item, 'diameter', drill * 1.6)
            pad.SetAttribute(p.PAD_ATTRIB_PTH)
            pad.SetDrillSize(xy(drill, drill))
            pad.SetSize(xy(diameter, diameter))
            pad.SetShape(p.PAD_SHAPE_CIRCLE)
            layers = p.LSET.AllCuMask()
            layers.AddLayer(p.F_Mask)
            layers.AddLayer(p.B_Mask)
        else:
            pad.SetAttribute(p.PAD_ATTRIB_SMD)
            pad.SetShape(p.PAD_SHAPE_RECT)
            pad.SetSize(xy(num(item, 'dx'), num(item, 'dy')))
            layers = p.LSET()
            for side in (layer, p.F_Mask if mirror else p.B_Mask,
                         p.F_Paste if mirror else p.B_Paste):
                layers.AddLayer(side)
            pad.SetOrientationDegrees(-degrees - float(item.get('rot', 'R0').replace('R', '')))
        pad.SetLayerSet(layers)
        f.Add(pad)
    for w in pkg.findall('wire'):
        if w.get('layer') == '21':
            wire(w, transform, p.F_SilkS if mirror else p.B_SilkS, f)
    if package in mapping:
        lib, name = mapping[package]
        model_fp = p.FootprintLoad(str(LIB / 'footprints' / f'{lib}.pretty'), name)
        if model_fp is None:
            raise RuntimeError(f'Missing KiCad footprint {lib}:{name}')
        for item in list(model_fp.Pads()) + list(model_fp.GraphicalItems()):
            retained.append(item)
            model_fp.Remove(item)
        b.Add(model_fp)
        model_fp.SetPosition(xy(*transform(0, 0)))
        if layer == p.B_Cu:
            model_fp.Flip(model_fp.GetPosition(), False)
        model_fp.SetOrientationDegrees(-degrees)
        for model in model_fp.Models():
            source = LIB / '3dmodels' / model.m_Filename.split('}/')[-1]
            if not source.exists():
                if not (ROOT / '3dmodels' / source.name).exists():
                    raise FileNotFoundError(source)
            else:
                shutil.copy2(source, ROOT / '3dmodels' / source.name)
        model_fp.SetReference(ref + '_3D')
        model_fp.Reference().SetVisible(False)
        model_fp.Value().SetVisible(False)
        report.append({'reference': ref, 'model': name, 'side': 'underside',
                       'basis': ('simplified 3x3x0.8 mm IC envelope' if package == 'TDFN14_3X3MM'
                                 else 'representative KiCad library body; original Eagle pads retained')})
    elif package in ('9.7ELECTRET', '1X05_ROUND_76'):
        model_fp = p.FOOTPRINT(b)
        model_fp.SetPosition(xy(*pos(num(e, 'x'), num(e, 'y'))))
        if package == '1X05_ROUND_76':
            # Local +Y corresponds to GND -> AR in the source connector.
            first = next(item for item in pkg.findall('pad') if item.get('name') == '1')
            model_fp.SetPosition(xy(*transform(num(first, 'x'), num(first, 'y'))))
            filename = 'header_down_reference.wrl'
        else:
            filename = 'electret_reference.wrl'
        model_fp.SetReference(ref + '_3D')
        model_fp.Reference().SetVisible(False)
        model_fp.Value().SetVisible(False)
        model = p.FP_3DMODEL()
        model.m_Filename = '${KIPRJMOD}/3dmodels/' + filename
        model_fp.Add3DModel(model)
        b.Add(model_fp)
        report.append({'reference': ref, 'model': filename,
                       'basis': 'source planar dimensions; approximate height and pin lengths'})

# Reproduce the visible microphone-side labels in a readable arrangement.
def text(label, x, y, size=.65, angle=0, layer=p.F_SilkS):
    t = p.PCB_TEXT(b)
    t.SetText(label)
    t.SetPosition(xy(50 + x, 50 + y))
    t.SetTextSize(xy(size, size))
    t.SetTextThickness(p.FromMM(.1))
    t.SetTextAngle(p.EDA_ANGLE(angle, p.DEGREES_T))
    t.SetLayer(layer)
    b.Add(t)

for label, y in zip(('GND', 'Vdd', 'Gain', 'Out', 'AR'), (2.159, 4.699, 7.239, 9.779, 12.319)):
    text(label, 21.2, y)
for label, x in zip(('Gain float -> 60dB', 'G=Gnd -> 50dB', 'G=Vdd -> 40dB',
                     'Output 2Vpp max', 'DC Offset: 1.25V'), (13.3, 14.7, 16.1, 17.5, 18.9)):
    text(label, x, 7.05, .65, 90)
text('MAX9814 mechanical reference - verify sample dimensions', 12.7, 18, .8,
     layer=p.Cmts_User)
out = ROOT / 'max9814-reference.kicad_pcb'
p.SaveBoard(str(out), b)
stackup = '''(stackup
 (layer "F.SilkS" (type "Top Silk Screen") (color "White"))
 (layer "F.Mask" (type "Top Solder Mask") (color "#643B89") (thickness 0.01))
 (layer "F.Cu" (type "copper") (thickness 0.035))
 (layer "dielectric 1" (type "core") (thickness 1.51) (material "FR4") (epsilon_r 4.5) (loss_tangent 0.02))
 (layer "B.Cu" (type "copper") (thickness 0.035))
 (layer "B.Mask" (type "Bottom Solder Mask") (color "#643B89") (thickness 0.01))
 (layer "B.SilkS" (type "Bottom Silk Screen") (color "White")))'''
content = out.read_text().replace('(setup', '(setup\n' + stackup, 1)
content = re.sub(r'\$\{KICAD9_3DMODEL_DIR\}/[^/\"]+/([^\"]+)',
                 r'${KIPRJMOD}/3dmodels/\1', content)
out.write_text(content)
(ROOT / 'model-mapping.json').write_text(json.dumps(report, indent=2) + '\n')
print(f'Saved {out.name}: {len(report)} component models')
