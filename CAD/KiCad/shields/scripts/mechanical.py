"""Add the four peripheral Mega mounts from Arduino's published Eagle CAD.

Source: MEGA2560_Rev3e.brd plain/hole elements, downloaded from the official
Mega2560 documentation CAD Files link. Central two holes are optional and unused.
Only this explicit operation modifies routed boards; rerun DRC after it.
"""
import json
import pcbnew as p
from design import ROOT,HOLE
from boards import xy

EAGLE_HOLES=[(96.52,2.54),(15.24,50.8),(90.17,50.8),(13.97,2.54)]


def main():
    for name in ['backplane','teensy-adapter']:
        folder=ROOT/name
        for suffix in ['-placed','']:
            path=folder/(name+suffix+'.kicad_pcb')
            if not path.exists():continue
            board=p.LoadBoard(str(path));refs={f.GetReference() for f in board.GetFootprints()}
            for i,(ex,ey) in enumerate(EAGLE_HOLES,1):
                ref=f'HM{i}'
                if ref in refs:continue
                fp=p.FootprintLoad(str(ROOT/'Shields.pretty'),'MountingHole_3.2mm_M3')
                fp.SetFPID(p.LIB_ID('Shields','MountingHole_3.2mm_M3'));fp.SetReference(ref);fp.SetValue('M3 computing shield')
                board.Add(fp);x=141.16+ey if name=='backplane' else 194.50-ey;y=53.32+ex
                fp.SetPosition(xy(x,y));fp.Value().SetVisible(False);fp.Reference().SetVisible(False)
            p.SaveBoard(str(path),board)
    (ROOT/'mechanical.json').write_text(json.dumps(dict(source='https://docs.arduino.cc/static/00ab83283ad8f7aae17832d0fe1b1d51/A000067-cad-files.zip',
        file='MEGA2560_Rev3e.brd',eagle_peripheral_holes_mm=EAGLE_HOLES,drill_mm=3.2,
        backplane_transform='x=141.16+eagle_y; y=53.32+eagle_x',
        adapter_transform='x=194.50-eagle_y; y=53.32+eagle_x',
        voice_card_mm=[30,42],voice_connector=[3,6],voice_retention=[24,34],
        analyser_mm=[150,55],analyser_connector=[3,4],analyser_retention=[[142,4],[142,47]]),indent=2)+'\n')


if __name__=='__main__':main()
