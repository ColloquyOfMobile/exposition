"""Export the home page's PCB SVGs on a machine with KiCad; commit the results.

The installation only reads these files. Run again after changing a PCB or
its wired schematic. Existing design files and fabrication exports are untouched.
"""
import argparse
import json
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KICAD = ROOT / "CAD/KiCad"
WEB = KICAD / "production/web"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", default="kicad-cli")
    args = parser.parse_args()
    boards = json.loads((KICAD / "production/manifest.json").read_text())["boards"]
    ET.register_namespace("", "http://www.w3.org/2000/svg")
    for board in boards:
        name = board["id"]
        source = KICAD / board["source"]
        target = WEB / name
        target.mkdir(parents=True, exist_ok=True)
        preview = source.parent / "reports/board.svg"
        if not preview.is_file():
            preview = source.parent / "reports/assembly-front.svg"
        shutil.copyfile(preview, target / "preview.svg")
        schematic = source.parent / "wired" / f"{name}-wired.kicad_sch"
        if not schematic.is_file():
            schematic = source.with_suffix(".kicad_sch")
        with tempfile.TemporaryDirectory(dir=WEB) as temporary:
            subprocess.run([args.kicad_cli, "sch", "export", "svg", "-o", temporary, str(schematic)], check=True)
            pages = sorted(Path(temporary).glob("*.svg"), key=lambda p: (p.stem != schematic.stem, p.name))
            if not pages:
                raise RuntimeError(f"No schematic exported for {name}")
            # A multi-sheet schematic is one full-page SVG, with sheets stacked.
            combined = ET.Element("{http://www.w3.org/2000/svg}svg")
            height = width = 0.0
            for page in pages:
                svg = ET.parse(page).getroot()
                x, y, w, h = map(float, svg.attrib["viewBox"].split())
                svg.set("x", "0")
                svg.set("y", str(height))
                svg.set("width", str(w))
                svg.set("height", str(h))
                combined.append(svg)
                width = max(width, w)
                height += h
            combined.set("viewBox", f"0 0 {width} {height}")
            ET.ElementTree(combined).write(target / "schematic.svg", encoding="utf-8", xml_declaration=True)
        print(name)


if __name__ == "__main__":
    main()
