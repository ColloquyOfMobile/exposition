"""Build both body boards with directly clamped, wire-connected GF1002 modules.

Run with KiCad 9 Python. Original artwork outlines and DSUB geometry are retained.
Outputs are engineering prototypes; module dimensions are photo estimates.
"""
from pathlib import Path
import csv
import importlib.util
import json
import math
import re
import shutil
import subprocess
import uuid
import xml.etree.ElementTree as ET
import pcbnew as p

CAD = Path(__file__).resolve().parents[2]
LIB = Path('C:/Program Files/KiCad/9.0/share/kicad')
CLI = Path('C:/Program Files/KiCad/9.0/bin/kicad-cli.exe')
spec = importlib.util.spec_from_file_location('support', CAD/'shields/scripts/schematic_support.py')
s = importlib.util.module_from_spec(spec); spec.loader.exec_module(s)


def xy(x, y):
    return p.VECTOR2I(p.FromMM(x), p.FromMM(y))


def graphic(owner, a, b, layer, width=.1):
    g = p.PCB_SHAPE(owner); g.SetShape(p.SHAPE_T_SEGMENT)
    g.SetStart(xy(*a)); g.SetEnd(xy(*b)); g.SetLayer(layer)
    g.SetWidth(p.FromMM(width)); owner.Add(g)


def text(board, value, x, y, size=.8, layer=p.F_SilkS):
    t = p.PCB_TEXT(board); t.SetText(value); t.SetPosition(xy(x, y))
    t.SetTextSize(xy(size, size)); t.SetTextThickness(p.FromMM(.12))
    if layer==p.B_SilkS: t.SetMirrored(True)
    t.SetLayer(layer); board.Add(t)


def keepout(fp, centre, radius):
    for layer in (p.F_Cu, p.B_Cu):
        z = p.ZONE(fp); z.SetIsRuleArea(True); z.SetLayer(layer)
        z.SetDoNotAllowTracks(True); z.SetDoNotAllowVias(True)
        z.SetDoNotAllowPads(False); z.SetDoNotAllowCopperPour(True)
        z.SetDoNotAllowFootprints(False); z.Outline().NewOutline()
        for i in range(64):
            a = i*math.tau/64
            z.Outline().Append(p.FromMM(centre[0]+radius*math.cos(a)),
                               p.FromMM(centre[1]+radius*math.sin(a)))
        fp.Add(z)


def local_footprints(folder, original):
    local = folder/'Body.pretty'; local.mkdir(exist_ok=True)
    io = p.PCB_IO_MGR.PluginFind(p.PCB_IO_MGR.KICAD_SEXP)
    # Preserve exact original connector copper, fixing geometry and pin order.
    for old in original.GetFootprints():
        f = old.Duplicate()
        f.SetOrientationDegrees(0); f.SetPosition(xy(0, 0))
        f.SetFPID(p.LIB_ID('Body', old.GetReference()+'_original'))
        f.SetReference('REF**')
        for pad in f.Pads(): pad.SetNetCode(0)
        # Match canonical local library models after board serialization.
        f.Models().clear()
        name = str(old.GetFPID().GetLibItemName())
        if old.GetReference() == 'J7':
            name = name.replace('Female', 'Socket')
        source = p.FootprintLoad(str(LIB/'footprints'/('Connector_Dsub.pretty' if old.GetReference() == 'J7' else 'Connector_JST.pretty')), name)
        if source:
            for model in source.Models(): f.Add3DModel(model)
        io.FootprintSave(str(local), f)
    # Six separate labelled hookup pads, not a presumed module header pinout.
    board = p.BOARD(); f = p.FOOTPRINT(board); board.Add(f)
    f.SetFPID(p.LIB_ID('Body', 'GF1002_WirePads_2x03'))
    for i in range(6):
        pad = p.PAD(f); pad.SetNumber(str(i+1)); pad.SetAttribute(p.PAD_ATTRIB_PTH)
        pad.SetShape(p.PAD_SHAPE_CIRCLE); pad.SetSize(xy(2, 2)); pad.SetDrillSize(xy(1, 1))
        layers = p.LSET.AllCuMask(); layers.AddLayer(p.F_Mask); layers.AddLayer(p.B_Mask)
        pad.SetLayerSet(layers); pad.SetPosition(xy(i%3*2.54, i//3*2.54)); f.Add(pad)
    for layer in (p.F_CrtYd, p.B_CrtYd):
        for a, b in [((-1.5,-1.5),(6.58,-1.5)),((6.58,-1.5),(6.58,4.04)),
                     ((6.58,4.04),(-1.5,4.04)),((-1.5,4.04),(-1.5,-1.5))]:
            graphic(f, a, b, layer, .05)
    io.FootprintSave(str(local), f)
    for side in ('Left', 'Right'):
        f = p.FootprintLoad(str(LIB/'footprints/MountingHole.pretty'), 'MountingHole_2.2mm_M2')
        f.SetFPID(p.LIB_ID('Body', 'GF1002_Clamp_'+side))
        f.Models().clear(); keepout(f, (0, 0), 2.5)
        model = p.FP_3DMODEL(); model.m_Filename = '${KIPRJMOD}/3dmodels/clamp_'+side.lower()+'.step'
        f.Add3DModel(model); io.FootprintSave(str(local), f)
    f = p.FOOTPRINT(board); board.Add(f)
    f.SetFPID(p.LIB_ID('Body', 'GF1002_Module_Direct'))
    f.SetAttributes(p.FP_EXCLUDE_FROM_POS_FILES)
    for a,b in [((0,0),(20,0)),((20,0),(20,30)),((20,30),(0,30)),((0,30),(0,0))]:
        graphic(f,a,b,p.Dwgs_User)
    model=p.FP_3DMODEL(); model.m_Filename='${KIPRJMOD}/3dmodels/module_assembly.wrl'
    model.m_Offset.z=4.6  # 3 mm insulating gap plus module PCB's 1.6 mm.
    f.Add3DModel(model); io.FootprintSave(str(local), f)
    (folder/'fp-lib-table').write_text('(fp_lib_table (version 7)\n (lib (name "Body")(type "KiCad")(uri "${KIPRJMOD}/Body.pretty")(options "")(descr "Preserved harness footprints and provisional GF1002 clamps")))\n')


def make(original_name, stem, positions, module_origin, clamps, extra):
    folder=CAD/(original_name+' v2'); folder.mkdir(exist_ok=True)
    (folder/'reports').mkdir(exist_ok=True); (folder/'3dmodels').mkdir(exist_ok=True)
    original=p.LoadBoard(str(CAD/original_name/(original_name+'.kicad_pcb')))
    local_footprints(folder, original)
    parts={}
    def add(ref,value,footprint,pins,description='',bom=True):
        parts[ref]=dict(ref=ref,value=value,footprint=footprint,
            pins={str(k):v for k,v in pins.items()},description=description,
            pin_names={str(k):str(k) for k in pins},pin_types={str(k):'passive' for k in pins},
            include_bom=bom,datasheet='',uuid=str(uuid.uuid5(uuid.NAMESPACE_URL,stem+'/'+ref)))
    for f in original.GetFootprints():
        pins={}
        for pad in f.Pads():
            net=pad.GetNetname()
            if net.startswith('unconnected-'): net=None
            elif 'speaker' in net: net='LINE_IN' if '+' in net else 'AUDIO_RETURN'
            if f.GetReference()=='J6': net='AMP_OUT_P' if pad.GetNumber()=='1' else 'AMP_OUT_N'
            pins[pad.GetNumber()]=net
        add(f.GetReference(),f.GetValue(),'Body:'+f.GetReference()+'_original',pins,
            'Original harness pin order retained. J6 now carries the local amplifier output.')
    add('JA1','GF1002 wire connections','Body:GF1002_WirePads_2x03',
        {1:'/5V',2:'GND',3:'AMP_INPUT',4:'AUDIO_RETURN',5:'AMP_OUT_P',6:'AMP_OUT_N'},
        'Short individually identified wires to module VDD, supply GND, Audio, input GND, ROUT+, ROUT-. Pad order is carrier-defined; verify module contacts.')
    add('R1','22K','Resistor_SMD:R_0603_1608Metric',{1:'LINE_IN',2:'AMP_INPUT'})
    add('R2','3K3','Resistor_SMD:R_0603_1608Metric',{1:'AMP_INPUT',2:'AUDIO_RETURN'})
    add('C1','220uF 10V / provisional','Capacitor_THT:CP_Radial_D6.3mm_P2.50mm',{1:'/5V',2:'GND'},
        'Provisional local reservoir; verify actual amplifier transients and rail sag before release.')
    add('C2','100nF','Capacitor_SMD:C_0603_1608Metric',{1:'/5V',2:'GND'})
    add('M1','GF1002 direct module','Body:GF1002_Module_Direct',{},
        'No perfboard. Photo-derived 20x30mm module, held by two insulating edge clamps; 3mm underside clearance.')
    for i,side in enumerate(('Left','Right'),1):
        add('H'+str(i),'M2 insulating clamp','Body:GF1002_Clamp_'+side,{},
            'Provisional edge clamp. No drilling of amplifier module; check actual fit.',False)
    # Use explicit global names without a leading slash (KiCad escapes slashes).
    for part in parts.values():
        part['pins']={pin:(net.lstrip('/') if net else net) for pin,net in part['pins'].items()}
    s.PROJECT=stem; s.HERE=folder
    root=s.uid('sheetfile/'+stem)
    for part in parts.values(): part['sheet_path']='/'+root
    sheet=s.Sheet(stem,'Colloquy '+original_name+' — directly mounted GF1002',parts,1)
    sheet.text('V2 ENGINEERING PROTOTYPE / DIRECT GF1002 / NO PERFBOARD',15,12,2,True)
    sheet.text('Harness speaker pair becomes LINE_IN / AUDIO_RETURN. Rack must be converted first.',15,20)
    sheet.text('JA1: 1=5V, 2=GND, 3=Audio, 4=Audio GND, 5=ROUT+, 6=ROUT-. Module contact positions unverified.',15,26)
    sheet.text('Insulating edge clamps: do not drill the module. Only harness +5V feeds the amplifier; 12V remains servo-only.',15,32)
    # DSUB's 17 pins need a tall block; use separate columns for original branches.
    def place(ref,x,y):
        sheet.place(ref,round(x/1.27)*1.27,round(y/1.27)*1.27)
    place('J7',45,110)
    others=[r for r in parts if r not in ('J7','M1','H1','H2')]
    for i,ref in enumerate(others):
        col=i//5; row=i%5
        place(ref,145+col*95,60+row*42)
    place('M1',340,275); place('H1',240,275); place('H2',290,275)
    sheet.save()
    sch=folder/(stem+'.kicad_sch')
    sch.write_text(sch.read_text().replace('2026-10-05','2026-10-09').replace('A-prototype','B-direct-amplifier'))
    (folder/'Colloquy.kicad_sym').write_text('(kicad_symbol_lib (version 20241209) (generator "kicad_symbol_editor")\n'+
        '\n'.join(s.lib_symbol(part,external=True) for part in parts.values())+'\n)\n')
    (folder/'sym-lib-table').write_text('(sym_lib_table (version 7) (lib (name "Colloquy")(type "KiCad")(uri "${KIPRJMOD}/Colloquy.kicad_sym")(options "")(descr "Body v2 harness and wire interface")))\n')
    subprocess.run([str(CLI),'sch','export','netlist','--format','kicadxml','-o',str(folder/'reports/netlist.xml'),str(sch)],check=True,capture_output=True)
    xml=ET.parse(folder/'reports/netlist.xml').getroot()
    pin_nets={(node.get('ref'),node.get('pin')):net.get('name')
              for net in xml.findall('./nets/net') for node in net.findall('node')}
    board=p.BOARD(); board.SetCopperLayerCount(2)
    board.GetDesignSettings().SetBoardThickness(p.FromMM(1.6))
    for drawing in original.GetDrawings():
        if drawing.GetLayer()==p.Edge_Cuts: board.Add(drawing.Duplicate())
    # Freerouting needs explicit obstacles around artwork fixing cutouts.
    for centre in ([(50,47),(50,90)] if original_name=='female base' else [(50,50),(50,100)]):
        keepout(board,centre,4.5)
    board.GetTitleBlock().SetTitle('Colloquy '+original_name+' / direct GF1002')
    board.GetTitleBlock().SetRevision('B-prototype'); board.GetTitleBlock().SetDate('2026-10-09')
    nets={}
    for name in sorted(set(pin_nets.values())):
        n=p.NETINFO_ITEM(board,name); board.Add(n); nets[name]=n
    positions=dict(positions); positions.update(extra)
    positions.update(M1=(*module_origin,0),H1=(*clamps[0],0),H2=(*clamps[1],0))
    for ref,part in parts.items():
        lib,name=part['footprint'].split(':')
        fp=p.FootprintLoad(str(folder/'Body.pretty' if lib=='Body' else LIB/'footprints'/(lib+'.pretty')),name)
        assert fp, part['footprint']
        board.Add(fp); fp.SetReference(ref); fp.SetValue(part['value'])
        fp.SetFPID(p.LIB_ID(lib,name)); fp.SetOrientationDegrees(positions[ref][2]); fp.SetPosition(xy(*positions[ref][:2]))
        fp.Reference().SetVisible(False); fp.Value().SetVisible(False)
        ids=p.KIID_PATH(); ids.push_back(p.KIID(root)); ids.push_back(p.KIID(part['uuid'])); fp.SetPath(ids)
        for pad in fp.Pads():
            net=pin_nets.get((ref,pad.GetNumber()))
            if net: pad.SetNet(nets[net])
        for model in fp.Models():
            if '${KIPRJMOD}' in model.m_Filename: continue
            path=LIB/'3dmodels'/model.m_Filename.split('}/')[-1]
            for suffix in ('.step','.wrl'):
                candidate=path.with_suffix(suffix)
                if candidate.exists(): shutil.copy2(candidate,folder/'3dmodels'/candidate.name)
    for suffix in ('.step','.wrl'):
        shutil.copy2(CAD/'shields/gf1002-reference/3dmodels'/('module_assembly'+suffix),folder/'3dmodels'/('module_assembly'+suffix))
    for ref in positions:
        if ref.startswith('J') and ref!='J7':
            x,y,_=positions[ref]
            if ref=='JA1': continue
            if ref=='J9' and original_name=='male static': text(board,ref,26,78,.8)
            else: text(board,ref,73 if x>60 else 26.3,y,.8)
    text(board,stem.upper(),50,40,.85)
    text(board,'GF1002 / DIRECT / NO PERFBOARD',module_origin[0]+10,module_origin[1]+31,.8,p.Dwgs_User)
    text(board,'5 G IN',positions['JA1'][0]+2.54,positions['JA1'][1]-2,.8)
    text(board,'R O+ O-',positions['JA1'][0]+2.54,positions['JA1'][1]+4.3,.8)
    text(board,'LINE INPUT ONLY',50,41.5,.8,p.B_SilkS)
    for ref in ('J7','J6'):
        f=next(f for f in board.GetFootprints() if f.GetReference()==ref)
        for pad in f.Pads():
            if pad.GetNetname() in ('LINE_IN','AUDIO_RETURN','AMP_OUT_P','AMP_OUT_N'):
                text(board,pad.GetNetname(),p.ToMM(pad.GetPosition().x),p.ToMM(pad.GetPosition().y)+2,.5,p.Dwgs_User)
    ns=board.GetDesignSettings().m_NetSettings
    nc=p.NETCLASS('Default'); nc.SetClearance(p.FromMM(.2)); nc.SetTrackWidth(p.FromMM(.25)); nc.SetViaDiameter(p.FromMM(.6)); nc.SetViaDrill(p.FromMM(.3)); ns.SetDefaultNetclass(nc)
    nc=p.NETCLASS('Power'); nc.SetClearance(p.FromMM(.2)); nc.SetTrackWidth(p.FromMM(.8)); nc.SetViaDiameter(p.FromMM(.8)); nc.SetViaDrill(p.FromMM(.4)); ns.SetNetclass('Power',nc)
    for net in ('5V','12V','GND','AMP_OUT_P','AMP_OUT_N'): ns.SetNetclassPatternAssignment(net,'Power')
    ns.ClearAllCaches(); board.SynchronizeNetsAndNetClasses(False)
    board.BuildListOfNets()
    path=folder/(stem+'-placed.kicad_pcb'); p.SaveBoard(str(path),board)
    raw=path.read_text(); raw=re.sub(r'\$\{KICAD9_3DMODEL_DIR\}/[^/]+/([^"\s]+)',r'${KIPRJMOD}/3dmodels/\1',raw)
    path.write_text(raw); shutil.copy2(path,folder/(stem+'.kicad_pcb'))
    # Project settings emitted from the original project, with matching new name.
    pro=json.loads((CAD/original_name/(original_name+'.kicad_pro')).read_text())
    pro['meta']['filename']=stem+'.kicad_pro'
    pro['net_settings']['classes']=[{'name':'Default','clearance':.2,'track_width':.25,'via_diameter':.6,'via_drill':.3,'microvia_diameter':.3,'microvia_drill':.1,'diff_pair_width':.25,'diff_pair_gap':.25,'diff_pair_via_gap':.25,'bus_width':12,'wire_width':6,'line_style':0,'pcb_color':'rgba(0, 0, 0, 0.000)','schematic_color':'rgba(0, 0, 0, 0.000)'},
        {'name':'Power','clearance':.2,'track_width':.8,'via_diameter':.8,'via_drill':.4,'microvia_diameter':.3,'microvia_drill':.1,'diff_pair_width':.25,'diff_pair_gap':.25,'diff_pair_via_gap':.25,'bus_width':12,'wire_width':6,'line_style':0,'pcb_color':'rgba(0, 0, 0, 0.000)','schematic_color':'rgba(0, 0, 0, 0.000)'}]
    pro['net_settings']['netclass_patterns']=[{'netclass':'Power','pattern':n} for n in ('5V','12V','GND','AMP_OUT_P','AMP_OUT_N')]
    (folder/(stem+'.kicad_pro')).write_text(json.dumps(pro,indent=2)+'\n')
    data={'name':stem,'components':list(parts.values()),'positions':positions,'module_origin_mm':module_origin,'clamp_centres_mm':clamps,
          'module_underside_gap_mm':3,'module_dimensions_mm':[20,30],'module_dimensions_verified':False,'original':original_name}
    (folder/'circuit.json').write_text(json.dumps(data,indent=2)+'\n')
    with (folder/'bom.csv').open('w',newline='') as stream:
        writer=csv.writer(stream); writer.writerow(['Reference','Value','Footprint','Description'])
        for part in parts.values():
            if part['include_bom']: writer.writerow([part['ref'],part['value'],part['footprint'],part['description']])
    print(stem,'generated; original outline and DSUB pad locations retained.')


if __name__=='__main__':
    make('female base','female-base-v2',
        {'J7':(40.61,34.84,180),'J2':(62,47,0),'J4':(62,60,0),'J5':(62,73,0),'J3':(62,86,0),'J6':(63,95,0)},
        (31,55),((28.5,74.5),(53.5,74.5)),
        {'JA1':(31,91,0),'R1':(56,81,90),'R2':(56,84,90),'C1':(41,91,0),'C2':(38,88,0)})
    make('male static','male-static-v2',
        {'J7':(40.305,34.84,180),'J3':(31,47,0),'J9':(30,74,90),'J8':(31,82,0),'J1':(31,92,0),'J4':(31,102,0),
         'J6':(66.5,47,0),'J10':(66.5,58,0),'J11':(64,66,0),'J5':(64,85,0),'J2':(64,98,0)},
        (40,55),((37.5,74.5),(62.5,74.5)),
        {'JA1':(43,91,0),'R1':(54,88,0),'R2':(58,88,0),'C1':(55.5,92.5,0),'C2':(52,92,90)})
