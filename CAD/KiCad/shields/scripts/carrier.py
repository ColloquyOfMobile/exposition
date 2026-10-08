"""Photo-derived DFR0126 carrier. Run with KiCad 9 Python."""
import json,shutil
import pcbnew as p
from design import ROOT,Circuit,analyser_pins,BODY,HOLE,emit
from boards import xy,rect,text,project,LOCAL,LIB

PITCH=2.54
HOLE_SPACING=8*PITCH

def circuit():
 d=Circuit('analyser-carrier')
 d.add('JA1','ANALYSER - KEY 22','Shields:Socket_2x11_Key22_PlugCarrier',analyser_pins(),'interface')
 d.parts['JA1']['pins'].update({'20':None,'21':None})
 for i in [1,2]:d.add(f'H{i}','M3 carrier retention',HOLE,{},'interface')
 for i,body in enumerate(BODY):
  n=i+1
  d.add(f'M{n}','DFR0126 MODIFIED / PLUG-IN','Shields:DFR0126_PlugIn_Photo',
        {'1':body+'/analyser out','2':'MEGA_5V','3':'AGND','4':body+'/microphone','5':'MEGA_5V','6':'AGND','7':'analyser/reset','8':'analyser/strobe'},body,
        names={'1':'L_REPURPOSED_OUT','2':'+5V','3':'GND','4':'R_MIC','5':'+5V','6':'GND','7':'RESET','8':'STROBE'},
        description='Modified module: remove module R4 (left-input 22K), jumper isolated L to OUT, fit downward 2.54mm headers. Carrier sockets: one 1x6 and one 1x2. Photo-derived geometry.',mpn='DFR0126 + 1x6/1x2 sockets',ds='https://wiki.dfrobot.com/dfr0126/')
  d.tp(f'TPA{i}',body+'/analyser out',body)
 d.tp('TPG','AGND','interface');d.tp('TP5','MEGA_5V','interface')
 return d

def footprint():
 socket=p.FootprintLoad(str(LOCAL),'Socket_2x11_Key22');socket.SetFPID(p.LIB_ID('Shields','Socket_2x11_Key22_PlugCarrier'))
 for g in socket.GraphicalItems():
  if g.GetLayer()==p.F_SilkS:g.SetLayer(p.F_Fab)
 p.PCB_IO_MGR.PluginFind(p.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(LOCAL),socket)
 for n in [2,3]:
  name=f'PinHeader_1x{n:02d}_P2.54mm_Vertical.kicad_mod';shutil.copy2(LIB/'Connector_PinHeader_2.54mm.pretty'/name,LOCAL/name)
 b=p.BOARD();f=p.FOOTPRINT(b);b.Add(f);f.SetFPID(p.LIB_ID('Shields','DFR0126_PlugIn_Photo'));f.SetAttributes(p.FP_THROUGH_HOLE)
 f.SetLibDescription('Photo estimate: 8 x 2.54mm holes, +/-1.27mm longitudinal slot tolerance; 29x32mm reserved envelope. Plug-in header grid inferred from photos; modified modules only.')
 for x,slot in [(0,False),(HOLE_SPACING,True)]:
  pad=p.PAD(f);pad.SetAttribute(p.PAD_ATTRIB_NPTH);pad.SetNumber('');pad.SetPosition(xy(x,0))
  pad.SetShape(p.PAD_SHAPE_OVAL if slot else p.PAD_SHAPE_CIRCLE)
  pad.SetDrillShape(p.PAD_DRILL_SHAPE_OBLONG if slot else p.PAD_DRILL_SHAPE_CIRCLE)
  pad.SetSize(xy(5.74 if slot else 3.2,3.2));pad.SetDrillSize(xy(5.74 if slot else 3.2,3.2));pad.SetLayerSet(p.LSET.AllCuMask());f.Add(pad)
 # Component-side projection: six inline L/+/-/R/+/- contacts and R/S control.
 # Module L is isolated by removing R4 and rewired to its output before fitting.
 for number,x,y in [(i+1,3.81+i*2.54,-5.08) for i in range(6)]+[(7,16.51,17.78),(8,19.05,17.78)]:
  pad=p.PAD(f);pad.SetNumber(str(number));pad.SetAttribute(p.PAD_ATTRIB_PTH);pad.SetShape(p.PAD_SHAPE_RECT if number in [1,7] else p.PAD_SHAPE_OVAL)
  pad.SetPosition(xy(x,y));pad.SetSize(xy(1.7,1.7));pad.SetDrillSize(xy(1,1));layers=p.LSET.AllCuMask();layers.AddLayer(p.F_Mask);layers.AddLayer(p.B_Mask);pad.SetLayerSet(layers);f.Add(pad)
 for x,y,w in [(2.54,-6.35,15.24),(15.24,16.51,5.08)]:
  rect(f,x,y,w,2.54,p.F_SilkS);rect(f,x,y,w,2.54,p.F_Fab)
 rect(f,-4.34,-8,29,32,p.F_CrtYd);rect(f,-4.34,-8,29,32,p.F_Fab)
 # Module envelope is assembly-only; its edge crosses underside socket pads.
 for x,rx in [(0,2.0),(HOLE_SPACING,3.2)]:
  for layer in [p.F_Cu,p.B_Cu]:
   z=p.ZONE(f);z.SetIsRuleArea(True);z.SetLayer(layer);z.SetDoNotAllowTracks(True);z.SetDoNotAllowVias(True);z.SetDoNotAllowPads(False);z.SetDoNotAllowCopperPour(True);z.SetDoNotAllowFootprints(False)
   z.Outline().NewOutline()
   for xx,yy in [(x-rx,-2),(x+rx,-2),(x+rx,2),(x-rx,2)]:z.Outline().Append(p.FromMM(xx),p.FromMM(yy))
   f.Add(z)
 p.PCB_IO_MGR.PluginFind(p.PCB_IO_MGR.KICAD_SEXP).FootprintSave(str(LOCAL),f)

def operating_labels(b):
 text(b,'DFROBOT PLUG-IN CARRIER - MODIFIED MODULES ONLY',125,51.5,.9)
 text(b,'MODULE: REMOVE R4 / LINK L TO OUT',125,82,.9,p.B_SilkS)
 for i,body in enumerate(['F1','F2','F3','M1','M2']):
  x=68+i*29
  text(b,f'MODULE {i} - {body}',x,56,.9)
  text(b,'OUT + - MIC + -' if i else '- + MIC - + OUT',x,61 if i else 96,.8)
  text(b,'R  S' if i else 'S  R',x+8.89 if i else x-8.89,89 if i else 67.5,.8)
  text(b,f'ANA {i}',x-6,100,.8)
  text(b,'PHOTO GRID / VERIFY FIT',x,75,.8,p.F_Fab)
 text(b,'AGND',196,104,.8);text(b,'MEGA 5V',194,58,.8)

def main():
 footprint();emit(circuit());folder=ROOT/'analyser-carrier';d=json.loads((folder/'circuit.json').read_text());b=p.BOARD();b.SetCopperLayerCount(2)
 b.GetDesignSettings().SetBoardThickness(p.FromMM(1.6))
 rect(b,50,50,150,55)
 nets={}
 for name in sorted({n for c in d['components'] for n in c['pins'].values() if n}):
  net=p.NETINFO_ITEM(b,name.replace('/','{slash}'));b.Add(net);nets[name]=net
 places={'JA1':(53,54,0),'H1':(192,54,0),'H2':(192,97,0),'TPG':(197.5,98.5,0),'TP5':(197.5,54,0)}
 for i in range(5):
  x=68+i*29;n=i+1
  places.update({f'M{n}':((x+HOLE_SPACING/2,88,180) if i==0 else (x-HOLE_SPACING/2,68,0)),f'TPA{i}':(x-6,98,0)})
 for c in d['components']:
  fp=p.FootprintLoad(str(LOCAL),c['footprint'].split(':')[1]);assert fp,c['footprint'];b.Add(fp);fp.SetFPID(p.LIB_ID('Shields',c['footprint'].split(':')[1]));fp.SetReference(c['ref']);fp.SetValue(c['value'])
  if c['ref']=='JA1':fp.Flip(fp.GetPosition(),True)
  x,y,a=places[c['ref']];fp.SetOrientationDegrees(a);fp.SetPosition(xy(x,y));fp.Value().SetVisible(False)
  fp.Reference().SetPosition(xy(x,y-2));fp.Reference().SetLayer(p.B_SilkS if c['ref']=='JA1' else p.F_SilkS);fp.Reference().SetTextSize(xy(.8,.8));fp.Reference().SetTextThickness(p.FromMM(.12))
  ids=p.KIID_PATH()
  for u in (c['sheet_path'].strip('/')+'/'+c['uuid']).split('/'):ids.push_back(p.KIID(u))
  fp.SetPath(ids)
  for pad in fp.Pads():
   net=c['pins'].get(pad.GetNumber());pad.SetNet(nets[net] if net else b.FindNet(0))
 # Body outline represents suspended modules; no component is fitted under them.
 operating_labels(b)
 b.BuildConnectivity();p.SaveBoard(str(folder/'analyser-carrier-placed.kicad_pcb'),b);project(folder,'analyser-carrier')
 (folder/'fp-lib-table').write_text('(fp_lib_table (version 7) (lib (name "Shields") (type "KiCad") (uri "${KIPRJMOD}/../Shields.pretty") (options "") (descr "Local footprints")))')
 (folder/'mechanical.json').write_text(json.dumps({'basis':'User-authorized photo inference on assumed 2.54mm grid, 2026-10-07; not a measured manufacturer drawing','hole_spacing_mm':HOLE_SPACING,'round_hole_mm':3.2,'slot_mm':[5.74,3.2],'nominal_spacing_range_mm':[19.05,21.59],'module_reserved_envelope_mm':[29,32],'board_mm':[150,55],'module_origins_mm':[[78.16,88,180]]+[[68+i*29-HOLE_SPACING/2,68,0] for i in range(1,5)],'carrier_to_backplane_translation_mm':[25,215],'short_leads':False,'module_modification':'Remove R4; link isolated L to OUT; downward headers','socket_grid_mm':[[i+1,3.81+i*2.54,-5.08] for i in range(6)]+[[7,16.51,17.78],[8,19.05,17.78]],'physical_fit_verified':False},indent=2)+'\n')
 print('analyser-carrier: generated',len(d['components']),'components')
if __name__=='__main__':main()
