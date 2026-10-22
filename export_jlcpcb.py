"""Export checked JLCPCB Gerbers, exact SMD BOM and matching CPL for every PCB.

Run with KiCad Python: & 'C:/Program Files/KiCad/9.0/bin/python.exe' export_jlcpcb.py
No source PCB or schematic is modified. Unknown SMD parts fail the export.
"""
import argparse
import csv
import hashlib
import io
import json
import subprocess
import sys
import tempfile
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
KICAD = ROOT / "CAD/KiCad"
PARTS_PATH = KICAD / "assembly-parts.json"
OUTPUT = KICAD / "production/assembly"
CLI = Path("C:/Program Files/KiCad/9.0/bin/kicad-cli.exe")
BOM_COLUMNS = ("Comment", "Designator", "Footprint", "Quantity", "Manufacturer", "Manufacturer Part Number", "LCSC Part #", "Specification")
CPL_COLUMNS = ("Designator", "Mid X", "Mid Y", "Layer", "Rotation")


def csv_bytes(columns, rows):
    out = io.StringIO(newline="")
    writer = csv.DictWriter(out, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    return out.getvalue().encode("utf-8-sig")


def part_for(footprint, value, catalog):
    """Require an exact footprint/value match, never guess an unknown part."""
    if footprint in ("R_0603_1608Metric", "R_0805_2012Metric"):
        size = "0603" if "0603" in footprint else "0805"
        # These annotations describe the existing circuit's population, not another value.
        nominal = value.split(" / ")[0].removesuffix(" provisional")
        selected = catalog[f"resistors_{size}"][nominal]
        # Existing pairs are YAGEO; explicit triples permit reviewed alternatives.
        if len(selected) == 2:
            manufacturer = "YAGEO"
            mpn, lcsc = selected
        else:
            manufacturer, mpn, lcsc = selected
        return {"manufacturer": manufacturer, "mpn": mpn, "lcsc": lcsc,
                "specification": f'{nominal} {size}, {"jumper" if nominal == "0R" else "+/-1%"}, {"0.1W" if size == "0603" else "0.125W"}'}
    for part in catalog["parts"]:
        if (part["footprint"], part["value"]) == (footprint, value):
            return part
    raise ValueError(f"No exact assembly part for {footprint}: {value}")


def assembly_rows(components, positions, catalog):
    """The same selected component set drives both files."""
    bom, cpl = [], []
    seen = set()
    for component in sorted(components, key=lambda c: c["reference"]):
        ref = component["reference"]
        if ref in seen:
            raise ValueError(f"Duplicate reference {ref}")
        seen.add(ref)
        part = part_for(component["footprint"], component["value"], catalog)
        position = positions[ref]
        if position["Side"] != "top":
            raise ValueError(f"{ref}: expected top-side assembly")
        if position["Val"] != component["value"] or position["Package"] != component["footprint"]:
            raise ValueError(f"{ref}: placement and PCB disagree")
        bom.append(dict(zip(BOM_COLUMNS, (component["value"], ref, component["footprint"],
            "1", part["manufacturer"], part["mpn"], part["lcsc"], part["specification"]))))
        rotation = (float(position["Rot"]) + float(part.get("rotation_ccw_degrees", 0))) % 360
        cpl.append(dict(zip(CPL_COLUMNS, (ref, f'{float(position["PosX"]):.6f}mm',
            f'{float(position["PosY"]):.6f}mm', "Top", f'{rotation:.6f}'))))
    return bom, cpl


def run(*args):
    result = subprocess.run([str(CLI), *map(str, args)], capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stdout + result.stderr)


def digest(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def write_file(path, content):
    """Replace exports atomically while the running server may be reading them."""
    assert path.resolve().is_relative_to(KICAD.resolve())
    pending = path.with_name(path.name + ".new")
    for attempt in range(4):
        try:
            pending.write_bytes(content)
            pending.replace(path)
            return
        except OSError:
            if attempt == 3:
                raise
            time.sleep(0.2)


def build(entry, catalog):
    import pcbnew as p

    source = KICAD / entry["source"]
    source_hash = digest(source)
    board = p.LoadBoard(str(source))
    components, manual = [], []
    exclusions = catalog["manual_smd_footprints"].get(entry["id"], {})
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        footprint = str(fp.GetFPID().GetLibItemName())
        row = {"reference": ref, "value": fp.GetValue(), "footprint": footprint}
        reason = None
        if fp.IsDNP():
            reason = "Do not populate (PCB DNP flag)"
        elif not fp.GetAttributes() & p.FP_SMD:
            reason = "Through-hole, plug-in module or mechanical item; hand fit"
        elif ref in exclusions:
            expected, reason = exclusions[ref]
            if footprint != expected:
                raise ValueError(f"{ref}: manual exclusion footprint changed")
        elif fp.GetAttributes() & (p.FP_EXCLUDE_FROM_POS_FILES | p.FP_EXCLUDE_FROM_BOM):
            raise ValueError(f"{ref}: SMD excluded by PCB assembly flags; resolve explicitly")
        elif fp.GetLayer() != p.F_Cu:
            raise ValueError(f"{ref}: bottom-side SMD assembly is not configured")
        if reason:
            manual.append({**row, "reason": reason})
        else:
            part_for(footprint, fp.GetValue(), catalog)
            components.append(row)

    work = ROOT / "tmp/jlcpcb"
    work.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=entry["id"] + "-", dir=work) as temporary:
        stage = Path(temporary)
        plots = stage / "gerbers"
        plots.mkdir()
        run("pcb", "drc", "--format", "json", "-o", stage / "drc.json", source)
        drc = json.loads((stage / "drc.json").read_text())
        errors = [v for v in drc["violations"] if v["severity"] == "error"]
        if errors or drc["unconnected_items"]:
            raise ValueError(f'{entry["id"]}: DRC has {len(errors)} errors / {len(drc["unconnected_items"])} unconnected')
        copper = [board.GetLayerName(layer) for layer in board.GetEnabledLayers().CuStack()]
        layers = copper + ["F.Paste", "B.Paste", "F.Mask", "B.Mask", "F.Silkscreen", "B.Silkscreen", "Edge.Cuts"]
        run("pcb", "export", "gerbers", "--layers", ",".join(layers), "--no-x2", "--no-netlist",
            "--subtract-soldermask", "-o", str(plots) + "/", source)
        run("pcb", "export", "drill", "--format", "excellon", "--drill-origin", "absolute",
            "--excellon-units", "mm", "--excellon-zeros-format", "decimal", "--excellon-oval-format", "route",
            "--excellon-separate-th", "-o", str(plots) + "/", source)
        run("pcb", "export", "pos", "--format", "csv", "--side", "both", "--units", "mm",
            "--exclude-dnp", "-o", stage / "positions.csv", source)
        positions = {row["Ref"]: row for row in csv.DictReader((stage / "positions.csv").read_text().splitlines())}
        bom, cpl = assembly_rows(components, positions, catalog)
        run("pcb", "export", "svg", "--layers", "F.Fab,F.Silkscreen,Edge.Cuts",
            "--page-size-mode", "2", "--exclude-drawing-sheet", "-o", stage / "assembly-top.svg", source)
        gerber_buffer = io.BytesIO()
        with zipfile.ZipFile(gerber_buffer, "w", zipfile.ZIP_DEFLATED) as z:
            for path in sorted(plots.iterdir()):
                if path.suffix != ".gbrjob":
                    z.write(path, path.name)
        files = {
            "BOM.csv": csv_bytes(BOM_COLUMNS, bom),
            "CPL.csv": csv_bytes(CPL_COLUMNS, cpl),
            "gerbers.zip": gerber_buffer.getvalue(),
            "manual-and-DNP.csv": csv_bytes(("reference", "value", "footprint", "reason"), manual),
            "reference/positions-all-kicad.csv": (stage / "positions.csv").read_bytes(),
            "reference/assembly-top.svg": (stage / "assembly-top.svg").read_bytes(),
            "checks/drc.json": (stage / "drc.json").read_bytes(),
            "reference/assembly-parts.json": PARTS_PATH.read_bytes(),
        }
        for name in entry.get("read first", ()) + entry.get("assembly", ()):
            path = KICAD / name
            if path.is_file():
                files[f"reference/{name}"] = path.read_bytes()
        for path in source.parent.glob("*.md"):
            files[f"reference/project/{path.name}"] = path.read_bytes()
        for filename in ("mechanical.json", "mounting-template.svg", "enclosure-mounting.json", "enclosure-mounting-layout.svg"):
            path = source.parent / filename
            if path.is_file():
                files[f"reference/project/{filename}"] = path.read_bytes()
        for path in (source.parent / "variants").rglob("*.csv"):
            files[f"reference/project/{path.relative_to(source.parent).as_posix()}"] = path.read_bytes()
        notes = f'''# {entry["title"]}: JLCPCB fabrication and SMD assembly

Upload gerbers.zip for the PCB. {'Then upload BOM.csv and CPL.csv for assembly.' if bom else 'Turn PCB Assembly OFF; all components are hand fitted.'}
Fit exactly the {len(bom)} Top-side SMD references in BOM.csv; Quantity is per PCB.
Each row specifies the manufacturer, exact orderable MPN and LCSC part number.
Do not substitute parts automatically. Check JLCPCB's current stock/assembly options.
{'There are no SMD components: order this PCB bare; the BOM and CPL contain headers only.' if not bom else ''}
All through-hole parts, plug-in modules and mounting hardware are hand fitted.
manual-and-DNP.csv lists every excluded reference and why. DNP means do not fit.
The U2D2 and screw/power hardware are not machine-placed SMD parts even where
their KiCad footprint attribute says SMD. The voice card is entirely through-hole,
including its 100K axial R3; all its parts are hand fitted according to variants.

CPL coordinates are mm using the same absolute origin as Gerbers and drills.
KiCad's exported Y convention is retained. Rotations are CCW degrees, 0 <= angle < 360.
Do not mirror supplied coordinates. reference/assembly-top.svg shows the layout.
Confirm the JLCPCB assembly preview before ordering: LEDs and Schottky diodes
have pad 1 = cathode; electrolytics pad 1 = positive; IC pin 1 must match the drawing.
The CPL applies only exact-part rotation corrections recorded in assembly-parts.json.
On the Teensy adapter, C90755 (SN74LV4T125PWR) adds 270 degrees to KiCad's
footprint rotation; U1-U4 are therefore 270 degrees. Confirm pin 1 at the upper-left pad in
the top view (2.8625 mm left and 1.95 mm above each footprint center).
Other parts retain their KiCad rotation. Verify the assembly preview before payment.

Backplane RP1-RP11 remain the designed provisional 10K population for calibration.
Body-board C1 remains the designed provisional 220uF/10V reservoir; the chosen
exact part is specified, but this does not settle amplifier transient tests.
Existing module-fit, connector-keying and enclosure checks still apply.
This file supersedes older bare-board/hand-SMD advice in reference documents.

Source: CAD/KiCad/{entry["source"]}
Source SHA256 (LF normalized): {source_hash}
KiCad: {p.GetBuildVersion()}. DRC: zero errors and zero unconnected items.
JLCPCB formats: https://jlcpcb.com/help/article/how-to-generate-bom-and-centroid-files-from-kicad-8
https://jlcpcb.com/help/article/pick-place-file-for-pcb-assembly
'''
        files["README-JLCPCB.md"] = notes.encode("utf-8")
        manifest = {"board": entry["id"], "source": entry["source"], "source_sha256": source_hash,
            "exported_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "generator_sha256": digest(Path(__file__)),
            "parts_sha256": digest(PARTS_PATH), "smd_count": len(bom), "drc_errors": 0, "unconnected": 0,
            "files": {name: hashlib.sha256(data).hexdigest() for name, data in files.items()}}
        files["manifest.json"] = (json.dumps(manifest, indent=2) + "\n").encode()
        if source_hash != digest(source):
            raise ValueError(f'{entry["id"]}: PCB changed during export; retry')
        target = OUTPUT / entry["id"]
        target.mkdir(parents=True, exist_ok=True)
        for name in ("BOM.csv", "CPL.csv", "manual-and-DNP.csv", "README-JLCPCB.md", "manifest.json"):
            write_file(target / name, files[name])
        archive = target / f'{entry["id"]}-manufacturing.zip'
        pending = stage / archive.name
        with zipfile.ZipFile(pending, "w", zipfile.ZIP_DEFLATED) as z:
            for name, data in files.items():
                z.writestr(name, data)
        assert archive.resolve().is_relative_to(OUTPUT.resolve())
        pending.replace(archive)
        # Retain the existing per-project download location, now with assembly files.
        legacy = source.parent / "manufacturing" / archive.name
        legacy.parent.mkdir(exist_ok=True)
        assert legacy.resolve().is_relative_to(KICAD.resolve())
        write_file(legacy, archive.read_bytes())
        write_file(legacy.with_name("README.md"), (
            f'# JLCPCB manufacturing package\n\nUnpack `{archive.name}`. Upload `gerbers.zip`, '
            + ('`BOM.csv` and `CPL.csv` separately as directed by `README-JLCPCB.md`.\n\n' if bom else
               'order this PCB bare with PCB Assembly OFF. BOM/CPL contain headers only.\n\n')
            + 'Regenerate with KiCad Python and `export_jlcpcb.py` at the repository root.\n').encode("utf-8"))
        # Keep the shields' existing ZIP checksum index accurate, preserving its other entries.
        index_path = KICAD / "proposed-solutions/shields/MANUFACTURING.json"
        index = json.loads(index_path.read_text())
        for recorded in index:
            if recorded["project"] == entry["id"]:
                recorded.update(sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),
                    assembly_policy="front_smd_only" if bom else "hand_assembled_bare_board",
                    files=len(files), smd_count=len(bom), drc_errors=0,
                    drc_warnings=len(drc["violations"]) - len(errors), unconnected=0)
        write_file(index_path, (json.dumps(index, indent=2) + "\n").encode("utf-8"))
        print(f'{entry["id"]}: {len(bom)} SMD placements; {archive.relative_to(ROOT)}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--only", action="append")
    args = parser.parse_args()
    gerber_args = [flag for name in args.only or () for flag in ("--only", name)]
    subprocess.run([sys.executable, str(ROOT / "export_gerbers.py"), *gerber_args], check=True)
    catalog = json.loads(PARTS_PATH.read_text())
    boards = json.loads((KICAD / "production/manifest.json").read_text())["boards"]
    if args.only and set(args.only) - {b["id"] for b in boards}:
        parser.error("unknown PCB")
    for entry in boards:
        if not args.only or entry["id"] in args.only:
            build(entry, catalog)
    if not args.only:
        # A directly shareable copy of the same collection served on the home page.
        collection = io.BytesIO()
        with zipfile.ZipFile(collection, "w", zipfile.ZIP_STORED) as archive:
            for entry in boards:
                name = f'{entry["id"]}-manufacturing.zip'
                archive.write(OUTPUT / entry["id"] / name, name)
        write_file(OUTPUT / "colloquy-production.zip", collection.getvalue())
    subprocess.run([sys.executable, str(ROOT / "export_pcb_web.py"), "--kicad-cli", str(CLI)], check=True)


if __name__ == "__main__":
    main()
