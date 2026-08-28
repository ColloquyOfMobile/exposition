# -*- coding: utf-8 -*-
# extract_hardware_photos.py

"""Take Thomas's four board photographs out of his PDF, with their labels.

    py extract_hardware_photos.py

Writes the four JPEGs under `Source code/Python/colloquy/server2/static/
hardware/`, which is what `HARDWARE_SETUP.md` shows on the page (see
`colloquy/tests/test_audio_subsystem/`).

**Why this exists, and why it renders rather than extracts.** The first
version of those four images was pulled out of the PDF as embedded
rasters, and every pin label vanished - because the labels are not part
of the photograph. They are text and leader lines the document draws *on
top* of it: `IN: 160 400 1K 2K5 6K25` down one edge of the filter board,
`GND / VDD / AOUT` beside each microphone header, `ROUT+ / ROUT-` on the
amplifier's terminals. Pulling the embedded image gets the board and
throws away the one thing that says which pin is which - which is the
whole reason somebody at a bench is looking at a photograph rather than
at a table.

So this renders the page region and lets it flatten. What comes out is
what Thomas's own figures 4 to 7 look like, which is the point: the
labels are his, and this repo should not be re-drawing them from prose.

`pymupdf` is a dev dependency of this script alone - `pip install
pymupdf`. It is deliberately not in requirements.txt: nothing the
installation runs needs a PDF renderer, and this is run again only if the
PDF is revised.

The clips are in PDF points, taken from where the figures actually sit on
the page (`page.get_image_info()` for the photograph, `page.get_text`
for the labels). They are stated rather than computed because two of them
need judgement a bounding box does not have: the analyser array's `AOUT`
label hangs off the left of its photograph, and every figure has a
caption underneath that belongs to the PDF and not to the page here.
"""
import sys
from pathlib import Path

PDF = Path("Source code/Thomas/Colloquy - Pask Redesign.pdf")
FOLDER = Path("Source code/Python/colloquy/server2/static/hardware")

# Big enough that "Microphone / AIN / VDD / GND" is readable on the
# analyser array, which is the smallest lettering of the four.
DPI = 220
QUALITY = 85

# file name -> (page, clip in PDF points, which figure of Thomas's it is)
FIGURES = {
    "low-pass-filter-board": (8, (69.0, 161.0, 350.0, 340.0), "Figure 4"),
    "microphone-module": (8, (76.0, 431.0, 305.0, 662.0), "Figure 5"),
    "amplifier-module": (9, (72.0, 96.0, 377.0, 325.0), "Figure 6"),
    "audio-analyzer-array": (9, (70.0, 372.0, 369.0, 685.0), "Figure 7"),
}


def main():
    try:
        import pymupdf
    except ImportError:
        print("This needs a PDF renderer: pip install pymupdf")
        return 1

    if not PDF.is_file():
        print(f"{PDF} is not there - run this from the repository root.")
        return 1

    document = pymupdf.open(PDF)
    for name, (page_number, clip, figure) in FIGURES.items():
        page = document[page_number - 1]
        pixmap = page.get_pixmap(dpi=DPI, clip=pymupdf.Rect(*clip))
        target = FOLDER / f"{name}.jpg"
        pixmap.save(target, jpg_quality=QUALITY)
        print(
            f"{target.name}: {figure}, page {page_number}, "
            f"{pixmap.width}x{pixmap.height}, {target.stat().st_size // 1024} kB"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
