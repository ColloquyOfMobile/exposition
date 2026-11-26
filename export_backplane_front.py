# -*- coding: utf-8 -*-
# export_backplane_front.py

"""Plot the shields backplane's front, and where its measure points are.

    py export_backplane_front.py

Needs KiCad (its `kicad-cli`). Writes, under `Source code/Python/colloquy/
server2/static/hardware/`:

- `backplane-front.svg` - KiCad's own plot of Edge.Cuts, F.Silkscreen and
  F.Mask, board area only: the board as it looks, every label on it.
- `backplane-front.json` - the plot's offset from board coordinates, its
  size, and the pad box of every part the installation guide points at,
  in board millimetres; plus the `.kicad_pcb`'s line-ending-normalised
  digest, so a test can say the plot is stale without KiCad.

The sol2 guide (`colloquy/tests/installation_sol2/pictures.py`) draws the
plot and rings the points a step measures. Re-run after any change to
`backplane.kicad_pcb`.

Stdlib only, and the `colloquy` package is not imported: importing it
wipes `local/logs`, which on a machine running the server are its logs.
"""
import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PCB = ROOT / "CAD" / "KiCad" / "proposed-solutions" / "shields" / "backplane" / "backplane.kicad_pcb"
OUT = ROOT / "Source code" / "Python" / "colloquy" / "server2" / "static" / "hardware"
SVG = OUT / "backplane-front.svg"
JSON = OUT / "backplane-front.json"

# The parts the guide points at. A pattern per family.
WANTED = re.compile(r"^(TP\w*|JP1|DP5|DP12|DPUSB|DT\d|J1|J2|J5|J6|J7|A-J3|B-J4|JV\d|JA1|A1)$")
# Parts whose holes the guide labels one by one, with each hole's net:
# J6, the screw terminal's landing, has no silkscreen at all.
HOLES_OF = {"J6"}


def digest(path):
    """As `hardware/pcb_files/gerbers.digest`: line endings taken out."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def kicad_cli():
    named = os.environ.get("KICAD_CLI") or shutil.which("kicad-cli")
    if named:
        return named
    program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
    for candidate in sorted(program_files.glob("KiCad/*/bin/kicad-cli.exe"), reverse=True):
        return str(candidate)
    sys.exit("kicad-cli not found: install KiCad, or set KICAD_CLI")


def pads(text):
    """Every wanted footprint -> (pad box in board mm, every pad centre)."""
    found = {}
    for block in re.split(r"\n\t\(footprint ", text)[1:]:
        ref = re.search(r'\(property "Reference" "([^"]+)"', block).group(1)
        if not WANTED.match(ref):
            continue
        at = re.search(r"\n\t\t\(at ([-\d.]+) ([-\d.]+)(?: ([-\d.]+))?\)", block)
        fx, fy, rot = float(at.group(1)), float(at.group(2)), float(at.group(3) or 0)
        angle = math.radians(-rot)
        centres = []
        holes = []
        kinds = set()
        matches = list(re.finditer(r'\(pad "[^"]*" (\w+) \w+\s*\(at ([-\d.]+) ([-\d.]+)', block))
        for index, m in enumerate(matches):
            kinds.add(m.group(1))
            px, py = float(m.group(2)), float(m.group(3))
            centre = (
                round(fx + px * math.cos(angle) - py * math.sin(angle), 3),
                round(fy + px * math.sin(angle) + py * math.cos(angle), 3),
            )
            centres.append(centre)
            end = matches[index + 1].start() if index + 1 < len(matches) else len(block)
            net = re.search(r'\(net \d+ "([^"]+)"\)', block[m.end():end])
            holes.append([*centre, net.group(1) if net else ""])
        if not centres:
            continue
        xs, ys = [c[0] for c in centres], [c[1] for c in centres]
        found[ref] = {
            "box": [min(xs), min(ys), max(xs), max(ys)],
            "pads": len(centres),
            "pin": kinds == {"thru_hole"} and len(centres) == 1,
        }
        if ref in HOLES_OF:
            found[ref]["holes"] = holes
    return found


def offset(svg_text, points):
    """Where board (0, 0) lands in the plot. Found, not assumed: every
    one-pin through-hole test pin's drill circle is matched in the plot,
    and all of them have to agree (the power row alone has a twin)."""
    circles = [
        (float(x), float(y))
        for x, y in re.findall(r'<circle cx="([-\d.]+)" cy="([-\d.]+)"', svg_text)
    ]
    anchors = [part["box"][:2] for ref, part in points.items() if ref.startswith("TP") and part["pin"]]
    ax, ay = anchors[0]
    for cx, cy in circles:
        dx, dy = ax - cx, ay - cy
        if all(
            any(abs(bx - dx - x) < 0.01 and abs(by - dy - y) < 0.01 for x, y in circles)
            for bx, by in anchors
        ):
            return [round(-dx, 4), round(-dy, 4)]
    sys.exit("could not place the plot: the power row's test pins are not in it")


def main():
    with tempfile.TemporaryDirectory() as folder:
        plotted = Path(folder) / "front.svg"
        subprocess.run(
            [
                kicad_cli(), "pcb", "export", "svg", "--mode-single",
                "-l", "Edge.Cuts,F.Silkscreen,F.Mask",
                "--page-size-mode", "2", "--exclude-drawing-sheet",
                "--drill-shape-opt", "1", "-o", str(plotted), str(PCB),
            ],
            check=True,
        )
        svg_text = plotted.read_text(encoding="utf-8")
    # No dated title: the file would change on every run.
    svg_text = re.sub(r"<title>.*?</title>", "<title>Shields backplane, front</title>", svg_text)
    size = re.search(r'viewBox="0\.0000 0\.0000 ([\d.]+) ([\d.]+)"', svg_text)

    points = pads(PCB.read_text(encoding="utf-8"))
    record = {
        "source": PCB.relative_to(ROOT).as_posix(),
        "source sha256": digest(PCB),
        "offset mm": offset(svg_text, points),
        "size mm": [float(size.group(1)), float(size.group(2))],
        "parts": points,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    SVG.write_text(svg_text, encoding="utf-8", newline="\n")
    JSON.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    print(f"wrote {SVG.relative_to(ROOT)} and {JSON.name}: {len(points)} parts, offset {record['offset mm']}")


if __name__ == "__main__":
    main()
