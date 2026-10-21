"""Export the native sheet plus cropped reading pages using pypdf/reportlab.

Run with the bundled document Python (pypdf and reportlab required).
"""
import copy
from io import BytesIO
import json
from pathlib import Path
import re
import subprocess

from pypdf import PdfReader, PdfWriter
from pypdf.generic import DecodedStreamObject, NameObject, RectangleObject
from reportlab.pdfgen import canvas

HERE=Path(__file__).resolve().parent
OUT=HERE/'wired'
MM=72/25.4


def main():
    master=OUT/'backplane-wired-master.pdf'
    subprocess.run(['C:/Program Files/KiCad/9.0/bin/kicad-cli.exe','sch','export','pdf',
        '--output',str(master),str(OUT/'backplane-wired.kicad_sch')],check=True)
    reader=PdfReader(master)
    # KiCad 9 emits exponent notation for the large-sheet background rectangle.
    # PDF numbers cannot use exponents. Normalize these numeric tokens only.
    stream=DecodedStreamObject()
    raw=reader.pages[0]['/Contents'].get_object().get_data()
    stream.set_data(re.sub(rb'(?<![A-Za-z])[-+]?\d+(?:\.\d+)?[eE][-+]?\d+',
        lambda m:format(float(m[0]),'.8f').encode(),raw))
    reader.pages[0][NameObject('/Contents')]=stream
    writer=PdfWriter()
    writer.add_page(reader.pages[0])
    writer.pages[0].compress_content_streams()
    writer.write(str(master))

    result=PdfWriter()
    # A short companion page explains the exact comparison baseline.
    buf=BytesIO()
    c=canvas.Canvas(buf,pagesize=(460*MM,297*MM))
    def line(value,y,size=13):
        c.setFont('Helvetica',size)
        c.drawString(18*MM,y*MM,value)
    line('BACKPLANE / WIRED READING COPY',273,25)
    line('Same 137 components, 94 nets and 366 connected pins as backplane.kicad_sch.',256)
    line('No electronic or mechanical components were added, removed or changed.',244,15)
    line('Original hierarchical schematic and PCB retained. 20 October 2026.',233)
    line('HOW TO READ',211,17)
    for y,t in [(198,'Each channel groups tone, audio, microphone, analyser, LED data and photosensors.'),
                (187,'Follow the continuous green wires. Dots join wires; crossings without dots stay separate.'),
                (176,'Repeated A1, JA1, JVx or harness references show contacts of the same physical connector.'),
                (165,'Pin numbers are unchanged. Contact placement is logical, not a physical connector layout.'),
                (154,'Captions are plain text: they do not make electrical connections.'),
                (143,'These pages crop one continuous master sheet. Shared rails continue across crop boundaries.')]:
        line(t,y)
    line('DRAWING CHANGES / WHY / NECESSARY?',119,17)
    for y,t in [(106,'Continuous wires replace labels: requested so connections can be followed visually.'),
                (95,'Five channel sections and split connector symbols: readability only; no extra connectors.'),
                (84,'Signal captions and explicit junction dots: readability only; no extra electrical function.'),
                (73,'Cropped reading pages: easier navigation; the master PDF and KiCad sheet show full continuity.')]:
        line(t,y)
    line('CHECKS AND COMPONENT EXPLANATIONS',51,17)
    line('Native KiCad netlists match the original, circuit.json and PCB. ERC: zero violations.',38)
    line('See README.md for each existing component family: purpose and whether it is necessary.',27)
    line('Drawing equivalence does not establish physical hardware behavior.',16,11)
    c.save()
    result.add_page(PdfReader(buf).pages[0])
    source=PdfReader(master).pages[0]
    height=float(source.mediabox.height)
    sections=json.loads((OUT/'sections.json').read_text())
    crops=[('Introduction and female1',0,sections[0][2]+5)]
    crops.extend((name,a-5,b+5) for name,a,b in sections[1:5])
    # Use overlapping crops for the lower shared section; no drawings are omitted.
    start=sections[5][1]-5
    stop=sections[5][2]+10
    index=1
    while start<stop:
        end=min(start+355,stop)
        crops.append((f'Power / control / spares / unused contacts - {index}',start,end))
        if end==stop:
            break
        start=end-18
        index+=1
    for title,top,bottom in crops:
        page=copy.deepcopy(source)
        rect=RectangleObject((0,height-bottom*MM,460*MM,height-top*MM))
        page.mediabox=rect
        page.cropbox=rect
        result.add_page(page)
        result.add_outline_item(title,len(result.pages)-1)
    target=OUT/'backplane-wired.pdf'
    result.write(str(target))
    dest=HERE.parents[3]/'output'/'pdf'
    dest.mkdir(parents=True,exist_ok=True)
    (dest/target.name).write_bytes(target.read_bytes())
    print(f'{target}: {len(result.pages)} pages')


if __name__=='__main__':
    main()
