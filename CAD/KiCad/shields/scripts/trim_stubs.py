"""Remove only tracks/vias explicitly reported dangling by KiCad, then recheck."""
import json
import subprocess
import pcbnew as p
from design import ROOT
from check import CLI

for name in ['backplane','teensy-adapter','voice-active','voice-thomas','analyser-direct','analyser-msgeq7']:
    path=ROOT/name/(name+'.kicad_pcb');report=ROOT/name/'reports/drc.json'
    for attempt in range(30):
        subprocess.run([str(CLI),'pcb','drc','--format','json','-o',str(report),str(path)],check=True,capture_output=True)
        drc=json.loads(report.read_text())
        uuids={i['uuid'] for v in drc['violations'] if v['type'] in ['track_dangling','via_dangling'] for i in v['items']}
        if not uuids:break
        b=p.LoadBoard(str(path));count=0
        for t in list(b.GetTracks()):
            if t.m_Uuid.AsString() in uuids:b.Delete(t);count+=1
        assert count
        p.SaveBoard(str(path),b)
    else:raise RuntimeError('Dangling cleanup did not converge')
    print(name,'trimmed in',attempt,'passes; remaining violations',len(drc['violations']),'unconnected',len(drc['unconnected_items']))

