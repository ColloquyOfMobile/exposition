"""GF1002 module and Thomas perfboard references; run with KiCad 9 Python.

No nets, traces, schematic, or inferred electrical rating. Geometry is estimated.
"""
from pathlib import Path
import json
import re
import shutil
import pcbnew as p

ROOT = Path(__file__).resolve().parent
LIB = Path('C:/Program Files/KiCad/9.0/share/kicad')
ORIGIN = (50, 50)


def xy(x, y):
    return p.VECTOR2I(p.FromMM(x), p.FromMM(y))


def pos(x, y):
    return xy(ORIGIN[0]+x, ORIGIN[1]+y)


def outline(board, width, height):
    board.GetDesignSettings().SetBoardThickness(p.FromMM(1.6))
    points = [(0, 0), (width, 0), (width, height), (0, height)]
    for a, b in zip(points, points[1:]+points[:1]):
        s = p.PCB_SHAPE()
        s.SetShape(p.SHAPE_T_SEGMENT)
        s.SetStart(pos(*a)); s.SetEnd(pos(*b))
        s.SetLayer(p.Edge_Cuts); s.SetWidth(p.FromMM(.05)); board.Add(s)


def label(board, value, x, y, size=.8, layer=p.F_SilkS):
    t = p.PCB_TEXT(board)
    t.SetText(value); t.SetPosition(pos(x, y)); t.SetTextSize(xy(size, size))
    t.SetTextThickness(p.FromMM(.12)); t.SetLayer(layer); board.Add(t)


def custom(board, ref, x, y, model=None, dz=0):
    f = p.FOOTPRINT(board)
    f.SetReference(ref); f.SetValue('PHOTO REFERENCE')
    f.Reference().SetVisible(False); f.Value().SetVisible(False)
    board.Add(f); f.SetPosition(pos(x, y))
    if model:
        m = p.FP_3DMODEL()
        m.m_Filename = '${KIPRJMOD}/3dmodels/' + model + '.wrl'
        m.m_Offset.z = dz
        f.Models().push_back(m)
    return f


def library(board, lib, name, ref, x, y, angle=0):
    f = p.FootprintLoad(str(LIB/'footprints'/(lib+'.pretty')), name)
    assert f is not None, name
    f.SetReference(ref); f.Reference().SetVisible(False); f.Value().SetVisible(False)
    board.Add(f); f.SetPosition(pos(x, y)); f.SetOrientationDegrees(angle)
    for m in f.Models():
        src = LIB/'3dmodels'/m.m_Filename.split('}/')[-1]
        # Include VRML and STEP sibling so previews and CAD use local assets.
        for suffix in ('.wrl', '.step'):
            sibling = src.with_suffix(suffix)
            if sibling.exists():
                shutil.copy2(sibling, ROOT/'3dmodels'/sibling.name)
        m.m_Filename = '${KIPRJMOD}/3dmodels/'+src.name
    return f


def pad(footprint, x, y, number, drill=.9, size=1.7):
    a = p.PAD(footprint); a.SetNumber(str(number))
    a.SetAttribute(p.PAD_ATTRIB_PTH); a.SetShape(p.PAD_SHAPE_CIRCLE)
    a.SetSize(xy(size, size)); a.SetDrillSize(xy(drill, drill))
    layers = p.LSET.AllCuMask()
    layers.AddLayer(p.F_Mask); layers.AddLayer(p.B_Mask)
    a.SetLayerSet(layers)
    a.SetPosition(pos(x, y)); footprint.Add(a)


def save(board, stem):
    label(board, 'PHOTO-DERIVED MECHANICAL STUDY - DO NOT FABRICATE', 20, -5,
          1, p.Cmts_User)
    path = ROOT/(stem+'.kicad_pcb')
    p.SaveBoard(str(path), board)
    path.write_text(re.sub(r'\$\{KICAD9_3DMODEL_DIR\}/[^/]+/([^"\s]+)',
                          r'${KIPRJMOD}/3dmodels/\1', path.read_text()))
    loaded = p.LoadBoard(str(path))
    assert len(list(loaded.GetTracks())) == 0
    assert len(list(loaded.Zones())) == 0
    for f in loaded.GetFootprints():
        for m in f.Models():
            assert (ROOT/m.m_Filename.replace('${KIPRJMOD}/', '')).exists()
    return loaded


module = p.BOARD(); outline(module, 20.2, 30)
custom(module, 'RV1', 0, 0, 'volume_control')
custom(module, 'C1', 12, 13, 'capacitor')
custom(module, 'U1', 11, 23, 'unknown_16pin_ic')
for i, (x, y) in enumerate([(3, 13), (3, 18), (3, 23), (3, 28), (11, 28), (17, 28)], 1):
    library(module, 'Resistor_SMD', 'R_0805_2012Metric', 'P'+str(i), x, y)
# Photo-derived nine contacts on an eleven-position perfboard grid.
# Pair polarity is unreadable: retain neutral A/B labels, with no inferred nets.
contacts = custom(module, 'CONTACTS', 0, 0)
contact_names = {1:'R IN',2:'G IN',3:'L IN',5:'V+',6:'V-',
                 8:'LOUT A',9:'LOUT B',10:'ROUT A',11:'ROUT B'}
for number, name in contact_names.items():
    y = 1.2 + 2.54*(number-1)
    pad(contacts, 18.55, y, number, .8, 1.3)
    label(module, name, 22.8, y, .55, p.Dwgs_User)
label(module, 'GF1002 REF', 10, 17, .7)
save(module, 'gf1002-reference')

carrier = p.BOARD(); outline(carrier, 40, 60)
grid = custom(carrier, 'PERFBOARD', 0, 0)
for row in range(23):
    for col in range(16):
        x, y = 2.22+2.54*col, 2.06+2.54*row
        if any((x-hx)**2+(y-hy)**2 < 2.5**2
               for hx, hy in [(2.5, 2.5), (37.5, 2.5), (2.5, 57.5), (37.5, 57.5)]):
            continue
        pad(grid, x, y, row*16+col+1, 1, 1.8)
for ref, x, y in [('H1', 2.5, 2.5), ('H2', 37.5, 2.5),
                  ('H3', 2.5, 57.5), ('H4', 37.5, 57.5)]:
    library(carrier, 'MountingHole', 'MountingHole_3.2mm_M3', ref, x, y)
custom(carrier, 'AMPLIFIER', -5, 9, 'module_assembly', 5)
for ref, count, x, y in [('J1', 2, 35, 10), ('J2', 3, 35, 22),
                          ('J3', 2, 26, 18), ('J4', 2, 35, 35)]:
    library(carrier, 'Connector_JST',
            f'JST_XH_B{count}B-XH-A_1x0{count}_P2.50mm_Vertical', ref, x, y, 90)
terminal = library(carrier, 'TerminalBlock', 'TerminalBlock_bornier-2_P5.08mm', 'J5', 24, 49)
terminal.Models().clear()
model = p.FP_3DMODEL()
model.m_Filename = '${KIPRJMOD}/3dmodels/speaker_terminal.wrl'
terminal.Models().push_back(model)
for i, (x, y, angle) in enumerate([(20, 9, 0), (18, 13, 90), (18, 22, 90)], 1):
    library(carrier, 'Resistor_THT', 'R_Axial_DIN0207_L6.3mm_D2.5mm_P10.16mm_Horizontal',
            'R'+str(i), x, y, angle)
label(carrier, 'Audio / GND', 31, 6, .75)
label(carrier, 'Audio / VDD / GND', 29, 29, .65)
label(carrier, 'VDD / GND', 25, 15, .65)
label(carrier, 'ROUT+ / ROUT-', 29, 41, .7)
label(carrier, 'ROUT+ / ROUT-', 27, 55, .7)
label(carrier, 'THOMAS - REF ONLY', 20, 58.5, .65)
save(carrier, 'thomas-amplifier-carrier-reference')
(ROOT/'mechanical.json').write_text(json.dumps({
    'basis': 'Thomas PDF Figure 6; photo scale assumes 2.54 mm perfboard pitch',
    'module_outline_mm': [20.2, 30], 'carrier_outline_mm': [40, 60],
    'module_length_basis': 'Conservative 30mm envelope; seller lists 29.5mm; unmeasured',
    'contact_row_x_mm':18.55, 'contact_first_y_mm':1.2, 'contact_pitch_mm':2.54,
    'contacts':contact_names, 'contact_position_uncertainty_mm':.5,
    'output_pair_polarity_verified':False, 'pot_overhang_mm':3,
    'pcb_thickness_mm': 1.6, 'carrier_module_top_offset_mm': 5,
    'module_carrier_xy_mm': [-5, 9],
    'confirmed_dimensions': [], 'electrical_connectivity': 'not reconstructed',
    'connector_identity': 'JST XH and 5.08 mm terminal proxies; unconfirmed',
}, indent=2)+'\n')
print('Saved and reloaded two references; local models resolve; no tracks or zones.')
