"""Export the one-page block schematic; preserve vector graphics for zooming."""
from pathlib import Path
import re
import subprocess

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject

HERE=Path(__file__).resolve().parent
OUT=HERE/'wired'


def main():
    target=OUT/'backplane-wired.pdf'
    native=OUT/'backplane-wired-export.pdf'
    subprocess.run(['C:/Program Files/KiCad/9.0/bin/kicad-cli.exe','sch','export','pdf',
        '--exclude-drawing-sheet','--no-background-color','--output',str(native),str(OUT/'backplane-wired.kicad_sch')],check=True)
    reader=PdfReader(native)
    stream=DecodedStreamObject()
    raw=reader.pages[0]['/Contents'].get_object().get_data()
    raw=re.sub(rb'(?<![A-Za-z])[-+]?\d+(?:\.\d+)?[eE][-+]?\d+',
        lambda m:format(float(m[0]),'.8f').encode(),raw)
    raw=raw.replace(b'0.960784 0.956863 0.937255 rg',b'1 1 1 rg',1)
    stream.set_data(raw)
    reader.pages[0][NameObject('/Contents')]=stream
    writer=PdfWriter();writer.add_page(reader.pages[0]);writer.pages[0].compress_content_streams()
    writer.add_metadata({'/Title':'Backplane - PCB-oriented connection blocks'})
    temporary=OUT/'backplane-wired.pdf.new'
    writer.write(str(temporary));temporary.replace(target)
    master=OUT/'backplane-wired-master.pdf'
    pending=OUT/'backplane-wired-master.pdf.new'
    pending.write_bytes(target.read_bytes());pending.replace(master)
    repo=next(parent for parent in HERE.parents if (parent/'main.py').exists())
    dest=repo/'output/pdf';dest.mkdir(parents=True,exist_ok=True)
    (dest/target.name).write_bytes(target.read_bytes())
    reader.stream.close()
    native.unlink(missing_ok=True)
    print(target)


if __name__=='__main__':main()
