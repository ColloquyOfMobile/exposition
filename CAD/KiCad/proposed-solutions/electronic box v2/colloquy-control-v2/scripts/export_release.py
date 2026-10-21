"""Check the final native design, then export a prototype fabrication package.

Run with Python 3.11+ and KiCad 9 CLI. No project runtime imports are performed.
Manufacturing outputs are generated only after ERC, DRC and netlist parity pass.
"""
from collections import defaultdict
from pathlib import Path
import argparse
import csv
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAME = "colloquy-control-v2"


def verify_npth(directory):
    """Check the actual manufacturing drill hits, not just PCB pad metadata."""
    paths = list(directory.glob("*-NPTH.drl"))
    if len(paths) != 1:
        raise RuntimeError(f"Expected one separate NPTH drill file, found {paths}")
    tools = {}
    selected = None
    holes = []
    number = r"[+-]?(?:\d+(?:\.\d*)?|\.\d+)"
    for line in paths[0].read_text(encoding="utf-8").splitlines():
        definition = re.fullmatch(r"T(\d+)C(" + number + r")", line)
        selection = re.fullmatch(r"T(\d+)", line)
        coordinate = re.fullmatch(r"X(" + number + r")Y(" + number + r")", line)
        if definition:
            tools[definition[1]] = float(definition[2])
        elif selection:
            selected = selection[1]
        elif coordinate:
            if selected not in tools:
                raise RuntimeError("NPTH coordinate precedes a valid tool selection")
            # KiCad's absolute Excellon Y axis is opposite the PCB editor's.
            holes.append(tuple(round(value, 4) for value in
                               (float(coordinate[1]), -float(coordinate[2]), tools[selected])))
        elif line.startswith(("X", "Y", "R", "G00", "G01", "G02", "G03", "G85")):
            raise RuntimeError(f"Unexpected NPTH drill command: {line}")
    expected = [(52,114,3.2), (244,82,3.2), (52,341,3.2), (244,341,3.2),
                (61,59.66,4.5), (103,59.66,4.5), (61,101.66,4.5),
                (103,101.66,4.5), (248.95,66.02,1.6)]
    if sorted(holes) != sorted(expected):
        raise RuntimeError(f"NPTH drill hits differ from the nine specified holes: {holes}")
    return {"passed": True, "file": paths[0].name, "hole_count": len(holes),
            "holes_x_y_diameter_mm": sorted(holes)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", default=r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe")
    args = parser.parse_args()
    reports = ROOT / "reports"
    out = ROOT / "manufacturing"
    gerber = out / "gerbers"
    reports.mkdir(exist_ok=True)
    gerber.mkdir(parents=True, exist_ok=True)
    pcb = ROOT / (NAME + ".kicad_pcb")
    sch = ROOT / (NAME + ".kicad_sch")

    def run(*command):
        subprocess.run([args.cli, *map(str, command)], cwd=ROOT, check=True)

    run("sch", "erc", sch, "--format", "json", "-o", reports / "erc.json")
    run("pcb", "drc", pcb, "--format", "json", "--schematic-parity",
        "-o", reports / "drc.json")
    erc = json.loads((reports / "erc.json").read_text())
    drc = json.loads((reports / "drc.json").read_text())
    if not erc.get("sheets") or any("violations" not in sheet for sheet in erc["sheets"]):
        raise SystemExit("Refusing fabrication export: unexpected or empty ERC report")
    if any(key not in drc for key in ("violations", "unconnected_items", "schematic_parity")):
        raise SystemExit("Refusing fabrication export: incomplete DRC/parity report")
    issues = sum(len(sheet.get("violations", [])) for sheet in erc.get("sheets", []))
    issues += sum(len(drc.get(key, [])) for key in
                  ("violations", "unconnected_items", "schematic_parity"))
    if issues:
        raise SystemExit(f"Refusing fabrication export: {issues} ERC/DRC findings remain")
    run("sch", "export", "netlist", sch, "-o", reports / "schematic.net")
    subprocess.run([sys.executable, str(ROOT / "scripts/verify_schematic.py"),
                    str(reports / "schematic.net"), "--pcb", str(pcb),
                    "--output", str(reports / "connectivity-parity.json")], check=True)
    run("sch", "export", "pdf", sch, "-o", reports / "schematic.pdf")
    # Never package stale fabrication files left by an earlier export.
    with tempfile.TemporaryDirectory(prefix=NAME+"-gerbers-") as temporary:
        staged = Path(temporary)
        run("pcb", "export", "gerbers", pcb, "-o", str(staged)+"/", "--layers",
            "F.Cu,B.Cu,F.Mask,B.Mask,F.SilkS,B.SilkS,Edge.Cuts", "--subtract-soldermask")
        run("pcb", "export", "drill", pcb, "-o", str(staged)+"/", "--excellon-separate-th",
            "--excellon-units", "mm", "--excellon-oval-format", "route",
            "--drill-origin", "absolute", "--excellon-zeros-format", "decimal",
            "--generate-map", "--map-format", "pdf")
        drill_report = verify_npth(staged)
        (reports / "npth-drill-check.json").write_text(json.dumps(drill_report, indent=2)+"\n")
        fabrication_files = []
        for path in sorted(staged.iterdir()):
            if path.is_file():
                target = gerber / path.name
                shutil.copy2(path, target)
                fabrication_files.append(target)
    run("pcb", "export", "pos", pcb, "--format", "csv", "--units", "mm",
        "--exclude-dnp", "-o", out / "component-positions.csv")
    for name, layers in [("assembly-front", "F.SilkS,F.Fab,Edge.Cuts"),
                         ("assembly-back", "B.SilkS,B.Fab,Edge.Cuts"),
                         ("copper-front", "F.Cu,Edge.Cuts"),
                         ("copper-back", "B.Cu,Edge.Cuts")]:
        run("pcb", "export", "pdf", pcb, "--layers", layers, "--mode-single",
            "--black-and-white", "-o", out / (name + ".pdf"))
    run("pcb", "export", "svg", pcb, "--layers", "F.Cu,B.Cu,F.SilkS,Edge.Cuts",
        "--page-size-mode", "2", "--mode-single", "-o", reports / "board.svg")
    design = json.loads((ROOT / "circuit.json").read_text())
    footprints = json.loads((ROOT / "footprint-map.json").read_text())
    with (out / "bom.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Reference", "Value", "Footprint", "Assembly", "Notes"])
        for item in design["components"]:
            if not item.get("include_bom", True):
                continue
            writer.writerow([item["ref"], item["value"], footprints.get(item["ref"], ""),
                             item.get("assembly", "fit"), item.get("description", "")])
    groups = defaultdict(list)
    for item in design["components"]:
        if not item.get("include_bom", True):
            continue
        groups[(item["value"], footprints.get(item["ref"], ""), item.get("assembly", "fit"))].append(item["ref"])
    with (out / "bom-grouped.csv").open("w", newline="", encoding="utf-8-sig") as stream:
        writer = csv.writer(stream)
        writer.writerow(["Quantity", "References", "Value", "Footprint", "Assembly"])
        for (value, footprint, fit), refs in groups.items():
            writer.writerow([len(refs), " ".join(refs), value, footprint, fit])
    instructions = """REV A PROTOTYPE — COLLOQUY CONTROL V2

210 x 297 mm, two copper layers, nominal 1.6 mm FR-4, 35 um copper per side.
Green solder mask both sides; white legend; lead-free HASL finish.
Minimum design clearance 0.25 mm; smallest via drill 0.40 mm.
Plated slots are intentional in the jack; bridge holes are round.
Separate PTH and NPTH Excellon files, metric, absolute origins, not mirrored.
Four 3.2 mm, four 4.5 mm, and one 1.6 mm NPTH mounting/locator holes.
Edge.Cuts is the closed external routing contour; corner radius 5 mm.
No impedance-control requirement; do not infer amp ratings from supply names.

Review README.md and CIRCUIT_NOTES.md before ordering or assembly.
Dry-fit the new M3 standoffs and custom mating components. Commission sensor
loads, signal attenuation, cable noise, supply drop and current capacity.
The Mega fits on the underside. JS1-JS5 are open solder jumpers by default.
Assembly positions are references for through-hole work, not a validated
automatic-placement program. Custom 3D bodies are not supplied.
"""
    (out / "FABRICATION_README.txt").write_text(instructions, encoding="utf-8")
    package = out / (NAME + "-revA-prototype-gerbers.zip")
    with zipfile.ZipFile(package, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.write(out / "FABRICATION_README.txt", "FABRICATION_README.txt")
        for path in fabrication_files:
            archive.write(path, path.name)
    native_sources = [pcb, *sorted(ROOT.glob("*.kicad_sch")),
                      ROOT / (NAME+".kicad_pro"), ROOT / "circuit.json",
                      ROOT / "Colloquy.kicad_sym", ROOT / "fp-lib-table",
                      ROOT / "sym-lib-table", *sorted((ROOT / "Colloquy.pretty").glob("*.kicad_mod"))]
    hashes = {str(path.relative_to(ROOT)).replace("\\", "/"):
              hashlib.sha256(path.read_bytes()).hexdigest()
              for path in [*native_sources, package]}
    (reports / "release-hashes.json").write_text(json.dumps(hashes, indent=2)+"\n")
    print(f"Prototype manufacturing outputs exported to {out}")


if __name__ == "__main__":
    main()
