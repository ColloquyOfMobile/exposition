"""Photo-derived DFR0126 carrier. Run with KiCad 9 Python."""
import json,shutil
import pcbnew as p
from design import ROOT,Circuit,analyser_pins,BODY,HOLE,emit
from boards import xy,rect,text,project,LOCAL,LIB

PITCH=2.54
HOLE_SPACING=8*PITCH

def circuit():
 d=Circuit('analyser-carrier')
 d.add('JA1','ANALYSER - KEY 22','Shields:Socket_2x11_Key22',analyser_pins(),'interface')
 d.parts['JA1']['pins'].update({'20':None,'21':None})
 for i in [1,2]:d.add(f'H{i}','M3 carrier retention',HOLE,{},'interface')
 for i,body in enumerate(BODY):
  n=i+1
  d.add(f'M{n}','DFRobot DFR0126 Audio Analyzer V2.0','Shields:DFR0126_PhotoMount',{},body,
        description='Purchased module on nylon standoffs. Photo-derived 20.32mm hole spacing; second hole slotted. Connections via labelled short leads.',mpn='DFR0126',ds='https://wiki.dfrobot.com/dfr0126/')
  d.add(f'JI{n}','INPUT R + -','Shields:PinHeader_1x03_P2.54mm_Vertical',{'1':body+'/microphone','2':'MEGA_5V','3':'AGND'},body,names={'1':'R_MIC','2':'+5V','3':'GND'})
  d.add(f'JO{n}','OUTPUT GND +5V SIG','Shields:PinHeader_1x03_P2.54mm_Vertical',{'1':'AGND','2':'MEGA_5V','3':body+'/analyser out'},body,names={'1':'GND','2':'+5V','3':'OUT'})
  d.add(f'JC{n}','CONTROL R S','Shields:PinHeader_1x02_P2.54mm_Vertical',{'1':'analyser/reset','2':'analyser/strobe'},body,names={'1':'RESET','2':'STROBE'})
  d.tp(f'TPA{i}',body+'/analyser out',body)
 d.tp('TPG','AGND','interface');d.tp('TP5','MEGA_5V','interface')
 return d

def footprint():
 for n in [2,3]:
  name=f'PinHeader_1x{n:02d}_P2.54mm_Vertical.kicad_mod';shutil.copy2(LIB/'Connector_PinHeader_2.54mm.pretty'/name,LOCAL/name)
 b=p.BOARD();f=p.FOOTPRINT(b);b.Add(f);f.SetFPID(p.LIB_ID('Shields','DFR0126_PhotoMount'));f.SetAttributes(p.FP_THROUGH_HOLE)
 f.SetLibDescription('Photo estimate: 8 x 2.54mm holes, +/-1.27mm longitudinal slot tolerance; 29x32mm reserved envelope. Short leads, not direct header mating.')
 for x,slot in [(0,False),(HOLE_SPACING,True)]:
  pad=p.PAD(f);pad.SetAttribute(p.PAD_ATTRIB_NPTH);pad.SetNumber('');pad.SetPosition(xy(x,0))
  pad.SetShape(p.PAD_SHAPE_OVAL if slot else p.PAD_SHAPE_CIRCLE)
  pad.SetDrillShape(p.PAD_DRILL_SHAPE_OBLONG if slot else p.PAD_DRILL_SHAPE_CIRCLE)
  pad.SetSize(xy(5.74 if slot else 3.2,3.2));pad.SetDrillSize(xy(5.74 if slot else 3.2,3.2));pad.SetLayerSet(p.LSET.AllCuMask());f.Add(pad)
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
 text(b,'ANALYSER CARRIER - 5 x DFROBOT - MEGA ONLY',130,51.5,1)
 text(b,'NYLON STANDOFFS / SHORT LEADS / MEGA ONLY',125,82,.9,p.B_SilkS)
 for i,body in enumerate(['F1','F2','F3','M1','M2']):
  x=65+i*30
  text(b,f'MODULE {i} - {body}',x,63,.9)
  text(b,'IN R  +5  GND',x-3,57,.8)
  text(b,'GND +5 OUT',x-3,104.3,.8);text(b,'R  S',x+7.27,104.3,.8)
  text(b,f'ANA {i}',x-6,95.5,.8)
  text(b,'20.32 NOMINAL / PHOTO',x,72,.8,p.F_Fab)
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
  x=65+i*30;n=i+1
  places.update({f'M{n}':((x+HOLE_SPACING/2,88,180) if i==0 else (x-HOLE_SPACING/2,68,0)),f'JI{n}':(x-6,54,90),f'JO{n}':(x-6,102.5,90),f'JC{n}':(x+6,102.5,90),f'TPA{i}':(x-6,98,0)})
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
 (folder/'mechanical.json').write_text(json.dumps({'basis':'User-authorized photo inference on assumed 2.54mm grid, 2026-10-06; not a measured manufacturer drawing','hole_spacing_mm':HOLE_SPACING,'round_hole_mm':3.2,'slot_mm':[5.74,3.2],'nominal_spacing_range_mm':[19.05,21.59],'module_reserved_envelope_mm':[29,32],'board_mm':[150,55],'module_origins_mm':[[75.16,88,180]]+[[65+i*30-HOLE_SPACING/2,68,0] for i in range(1,5)],'carrier_to_backplane_translation_mm':[25,215],'short_leads':True,'physical_fit_verified':False},indent=2)+'\n')
 print('analyser-carrier: generated',len(d['components']),'components')
if __name__=='__main__':main()
