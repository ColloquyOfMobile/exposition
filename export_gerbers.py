# -*- coding: utf-8 -*-
# export_gerbers.py

"""Plot the fabrication package of every new board.

    py export_gerbers.py            plot the boards that have changed
    py export_gerbers.py --all      plot every board again
    py export_gerbers.py --check    say what is out of date, write nothing

Writes Gerbers and Excellon drill files into `CAD/KiCad/production/<board>/`
and records what it plotted in `CAD/KiCad/production/manifest.json`. Those
are committed: the machine that offers them for download is the
installation's laptop, which has no KiCad and gets them by pulling
(`colloquy/hardware/pcb_files/gerbers.py` is the reading half).

**Re-run this after any change to one of the boards below.** The manifest
holds each board file's digest, so a package plotted from an older layout
says so on the page that offers it, and `pytest_tests` fails on it.

It runs KiCad's own `kicad-cli`, with the settings both PCBWay and JLCPCB
ask for: Protel file extensions, RS-274X without the X2 attributes, the
solder mask subtracted from the silkscreen, and Excellon drills in
millimetres with plated and non-plated holes in separate files.

**A board that fails KiCad's design rule check is not plotted** (errors
or unconnected items; `--force` plots it anyway and the manifest says
what was found). Passing it is not a release: each design's README lists
the physical checks that are still open, and no file settles those.

The reading module is loaded from its own folder rather than through the
`colloquy` package, because importing the package wipes `local/logs` -
which, on a machine where the server is running, are its logs.
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(
    0, str(ROOT / "Source code" / "Python" / "colloquy" / "hardware" / "pcb_files")
)

import gerbers  # noqa: E402

SHIELDS = "The main board and its shields"
BODIES = "The boards inside the bodies"

# The boards to make. Which ones is a decision and this table is where it
# is taken: the shields set (`CAD/KiCad/shields/README.md` has the same
# five, with the same quantities) and the two v2 body boards that carry
# an amplifier. The boards already built - `electronic box`, `center`,
# `female base`, `female static`, `male static` - are not here, and
# neither are the two other candidates for the main board
# (`colloquy-control-v2`, `thomas-or-teensy`): a package that offered
# three main boards would get three ordered.
BOARDS = (
    {
        "id": "backplane",
        "title": "Shields backplane",
        "what": "the main board: harness connectors, power entry and the shield slots",
        "group": SHIELDS,
        "quantity": 1,
        "source": "shields/backplane/backplane.kicad_pcb",
        "read first": ["shields/README.md", "shields/REVIEW.md", "shields/ASSEMBLY.md"],
        "assembly": ["shields/backplane/bom.csv", "shields/backplane/positions.csv"],
    },
    {
        "id": "teensy-adapter",
        "title": "Teensy 4.1 adapter",
        "what": "a Teensy 4.1 in the backplane's Mega slot",
        "group": SHIELDS,
        "quantity": 1,
        "source": "shields/teensy-adapter/teensy-adapter.kicad_pcb",
        "read first": ["shields/README.md", "shields/REVIEW.md", "shields/ASSEMBLY.md"],
        "assembly": [
            "shields/teensy-adapter/bom.csv",
            "shields/teensy-adapter/positions.csv",
        ],
    },
    {
        "id": "voice-thomas",
        "title": "Voice card",
        "what": "Thomas's RC output filter, one per body",
        "group": SHIELDS,
        "quantity": 5,
        "source": "shields/voice-thomas/voice-thomas.kicad_pcb",
        "read first": ["shields/README.md", "shields/REVIEW.md", "shields/ASSEMBLY.md"],
        # No positions.csv here or on the analyser carrier: both are
        # ordered bare and built by hand (shields/ASSEMBLY.md), so there
        # is nothing for a machine to place.
        "assembly": [
            "shields/voice-thomas/bom.csv",
            "shields/voice-thomas/variants.csv",
        ],
    },
    {
        "id": "analyser-carrier",
        "title": "Analyser carrier",
        "what": "carries the five DFRobot audio analyser modules",
        "group": SHIELDS,
        "quantity": 1,
        "source": "shields/analyser-carrier/analyser-carrier.kicad_pcb",
        "read first": [
            "shields/README.md",
            "shields/REVIEW.md",
            "shields/analyser-carrier/README.md",
        ],
        "assembly": [
            "shields/analyser-carrier/bom.csv",
            "shields/analyser-carrier/socket-assembly.csv",
        ],
    },
    {
        "id": "microphone",
        "title": "Microphone holder",
        "what": "holds a MAX9814 module on a body's extrusion, one per body and a spare",
        "group": SHIELDS,
        "quantity": 6,
        "source": "shields/microphone/microphone.kicad_pcb",
        "read first": ["shields/README.md", "shields/REVIEW.md", "shields/ASSEMBLY.md"],
        "assembly": ["shields/microphone/bom.csv", "shields/microphone/positions.csv"],
    },
    {
        "id": "female-base-v2",
        "title": "Female base v2",
        "what": "inside each female, with her amplifier module mounted on it",
        "group": BODIES,
        "quantity": 3,
        "source": "female base v2/female-base-v2.kicad_pcb",
        "read first": ["female base v2/README.md"],
        "assembly": ["female base v2/bom.csv"],
    },
    {
        "id": "male-static-v2",
        "title": "Male static v2",
        "what": "inside each male, with his amplifier module mounted on it",
        "group": BODIES,
        "quantity": 2,
        "source": "male static v2/male-static-v2.kicad_pcb",
        "read first": ["male static v2/README.md"],
        "assembly": ["male static v2/bom.csv"],
    },
)

OUTER_LAYERS = (
    "F.Cu",
    "B.Cu",
    "F.Paste",
    "B.Paste",
    "F.Silkscreen",
    "B.Silkscreen",
    "F.Mask",
    "B.Mask",
    "Edge.Cuts",
)


class ExportError(Exception):
    """One board could not be plotted. The others still are."""


def find_kicad_cli():
    """`kicad-cli`, from $KICAD_CLI, the PATH, or where KiCad installs it."""
    named = os.environ.get("KICAD_CLI")
    if named:
        return named
    on_path = shutil.which("kicad-cli")
    if on_path:
        return on_path
    program_files = Path(os.environ.get("ProgramFiles", "C:/Program Files"))
    # Newest first: "9.0" sorts above "8.0".
    for candidate in sorted(program_files.glob("KiCad/*/bin/kicad-cli.exe"), reverse=True):
        return str(candidate)
    for candidate in (
        Path("/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"),
        Path("/usr/bin/kicad-cli"),
    ):
        if candidate.is_file():
            return str(candidate)
    raise SystemExit(
        "kicad-cli was not found. Install KiCad 9, or set KICAD_CLI to its path."
    )


def run(cli, *args):
    completed = subprocess.run(
        (cli,) + tuple(str(arg) for arg in args), capture_output=True, text=True
    )
    if completed.returncode != 0:
        said = (completed.stderr or completed.stdout or "").strip().splitlines()
        raise ExportError(
            f"kicad-cli {args[0]} {args[1]} failed: "
            f"{said[-1] if said else completed.returncode}"
        )
    return completed.stdout


def copper_layers(board_path):
    """How many copper layers the board file declares."""
    text = board_path.read_text(encoding="utf-8", errors="replace")
    return len(set(re.findall(r'\(\d+ "((?:F|B|In\d+)\.Cu)"', text)))


def design_rule_check(cli, board_path, folder):
    report = folder / "drc.json"
    run(
        cli, "pcb", "drc", "--format", "json", "--severity-error",
        "--severity-warning", "-o", report, board_path,
    )
    found = json.loads(report.read_text(encoding="utf-8"))
    severities = [item.get("severity") for item in found.get("violations", [])]
    return {
        "errors": severities.count("error"),
        "warnings": severities.count("warning"),
        "unconnected": len(found.get("unconnected_items", [])),
    }


def outline_size(edge_cuts, job):
    """The board's width and height in millimetres.

    The Gerber job file gives one, but it measures the Edge.Cuts *ink* -
    a 210 mm board drawn with a 0.2 mm line comes out as 210.2 - and an
    order form wants the board. So the outline's own coordinates are read
    off the plot, and the job file is kept as the check on that reading:
    the two may differ by the width of a line and by nothing else.
    """
    stated = job["GeneralSpecs"]["Size"]
    text = edge_cuts.read_text(encoding="utf-8", errors="replace")
    # %FSLAX46Y46*%: six decimals, millimetres. Only the draw and move
    # commands - that format statement itself reads as a point at 46, 46.
    points = [
        (int(x) / 1e6, int(y) / 1e6)
        for x, y in re.findall(
            r"^X(-?\d+)Y(-?\d+)(?:I-?\d+J-?\d+)?D0[123]\*", text, re.M
        )
    ]
    if points:
        width = max(x for x, _ in points) - min(x for x, _ in points)
        height = max(y for _, y in points) - min(y for _, y in points)
        if 0 <= stated["X"] - width < 1.0 and 0 <= stated["Y"] - height < 1.0:
            return [round(width, 3), round(height, 3)]
    return [stated["X"], stated["Y"]]


def smallest_drill(folder):
    sizes = []
    for path in folder.glob("*.drl"):
        text = path.read_text(encoding="utf-8", errors="replace")
        sizes.extend(float(size) for size in re.findall(r"^T\d+C([\d.]+)", text, re.M))
    return min(sizes) if sizes else 0.0


def plot(cli, entry, force):
    """Plot one board into a scratch folder and return (folder, facts)."""
    board_path = gerbers.KICAD_FOLDER / entry["source"]
    if not board_path.is_file():
        raise ExportError(f"{entry['source']} is not there")

    scratch = Path(tempfile.mkdtemp(prefix=f"gerbers-{entry['id']}-"))
    drc = design_rule_check(cli, board_path, scratch)
    (scratch / "drc.json").unlink()
    if (drc["errors"] or drc["unconnected"]) and not force:
        shutil.rmtree(scratch, ignore_errors=True)
        raise ExportError(
            f"the design rule check found {drc['errors']} errors and "
            f"{drc['unconnected']} unconnected items - not plotted "
            "(--force plots it anyway)"
        )

    count = copper_layers(board_path)
    layers = list(OUTER_LAYERS)
    layers[1:1] = [f"In{index}.Cu" for index in range(1, count - 1)]

    run(
        cli, "pcb", "export", "gerbers", "-o", f"{scratch}{os.sep}",
        "-l", ",".join(layers), "--no-x2", "--no-netlist",
        "--subtract-soldermask", board_path,
    )
    run(
        cli, "pcb", "export", "drill", "-o", f"{scratch}{os.sep}",
        "--format", "excellon", "--drill-origin", "absolute",
        "--excellon-zeros-format", "decimal", "--excellon-oval-format",
        "alternate", "-u", "mm", "--excellon-separate-th", board_path,
    )

    job_path = next(scratch.glob("*.gbrjob"))
    job = json.loads(job_path.read_text(encoding="utf-8"))
    edge_cuts = next(scratch.glob("*.gm1"))
    facts = {
        "copper layers": count,
        "size mm": outline_size(edge_cuts, job),
        "thickness mm": job["GeneralSpecs"]["BoardThickness"],
        "smallest drill mm": smallest_drill(scratch),
        "drc": drc,
    }
    # The job file is KiCad's own index of the plot and no fab reads it;
    # left out so that every file in a board's zip is a layer or a drill.
    job_path.unlink()
    facts["files"] = sorted(path.name for path in scratch.iterdir())
    return scratch, facts


def read_manifest():
    if not gerbers.MANIFEST_PATH.is_file():
        return {}
    try:
        data = json.loads(gerbers.MANIFEST_PATH.read_text(encoding="utf-8"))
        return {entry["id"]: entry for entry in data["boards"]}
    except (ValueError, KeyError, TypeError):
        return {}


def is_current(entry, recorded):
    """Was this board already plotted from the file as it is now?"""
    if recorded is None:
        return False
    folder = gerbers.PRODUCTION_FOLDER / entry["id"]
    if recorded.get("source") != entry["source"]:
        return False
    if any(not (folder / name).is_file() for name in recorded.get("files", ())):
        return False
    return recorded.get("source sha256") == gerbers.digest(
        gerbers.KICAD_FOLDER / entry["source"]
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--all", action="store_true", help="plot every board again")
    parser.add_argument("--check", action="store_true", help="report, write nothing")
    parser.add_argument("--only", action="append", choices=[b['id'] for b in BOARDS],
                        help="limit exports/checks to this board; may be repeated")
    parser.add_argument(
        "--force", action="store_true",
        help="plot a board even if its design rule check fails",
    )
    options = parser.parse_args()

    assert "colloquy" not in sys.modules, "the package ran - local/logs would be gone"

    recorded = read_manifest()
    selected = set(options.only or (entry['id'] for entry in BOARDS))
    stale = [
        entry for entry in BOARDS
        if entry['id'] in selected and (options.all or not is_current(entry, recorded.get(entry["id"])))
    ]

    if options.check:
        for entry in BOARDS:
            if entry['id'] not in selected:
                continue
            state = "OUT OF DATE" if entry in stale else "current"
            print(f"{entry['id']:20} {state}")
        return 1 if stale else 0

    # A board whose file has not changed keeps its plot but takes this
    # table's descriptions afresh. Otherwise a document added to or
    # dropped from "assembly" never reaches the manifest, since only a
    # changed board file makes a board stale.
    refreshed = {
        entry["id"]: ({**recorded[entry["id"]], **entry} if entry['id'] in selected else recorded[entry['id']])
        for entry in BOARDS if entry not in stale and entry['id'] in recorded
    }
    if not stale and list(refreshed.values()) == list(recorded.values()):
        print("every board's package is current - nothing to plot")
        return 0

    if stale:
        cli = find_kicad_cli()
        version = run(cli, "version").strip()
    failed = 0
    entries = []
    for entry in BOARDS:
        if entry['id'] not in selected:
            if entry['id'] in recorded:
                entries.append(recorded[entry['id']])
            continue
        if entry not in stale:
            entries.append(refreshed[entry["id"]])
            print(f"{entry['id']:20} current")
            continue
        try:
            scratch, facts = plot(cli, entry, options.force)
        except ExportError as error:
            failed += 1
            print(f"{entry['id']:20} FAILED: {error}")
            # Keep what was there: a package from the last good layout,
            # which the manifest's digest will go on calling stale.
            if entry["id"] in recorded:
                entries.append(recorded[entry["id"]])
            continue

        folder = gerbers.PRODUCTION_FOLDER / entry["id"]
        assert folder.resolve().parent == gerbers.PRODUCTION_FOLDER.resolve()
        shutil.rmtree(folder, ignore_errors=True)
        folder.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(scratch), str(folder))

        written = dict(entry)
        written["source sha256"] = gerbers.digest(gerbers.KICAD_FOLDER / entry["source"])
        written["exported at"] = datetime.now().isoformat(timespec="seconds")
        written["exported with"] = f"KiCad {version}"
        written.update(facts)
        entries.append(written)
        width, height = facts["size mm"]
        print(
            f"{entry['id']:20} plotted: {facts['copper layers']} layers, "
            f"{width} x {height} mm, {len(facts['files'])} files, "
            f"DRC {facts['drc']['errors']} errors / "
            f"{facts['drc']['unconnected']} unconnected / "
            f"{facts['drc']['warnings']} warnings"
        )

    gerbers.PRODUCTION_FOLDER.mkdir(parents=True, exist_ok=True)
    gerbers.MANIFEST_PATH.write_text(
        json.dumps({"boards": entries}, indent=2) + "\n", encoding="utf-8"
    )
    print(f"wrote {gerbers.MANIFEST_PATH.relative_to(ROOT.resolve())}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
