"""Route a placed KiCad board locally through Freerouting and import its session.

Run with the Python interpreter supplied with KiCad (it provides ``pcbnew``).
Java 25 and the Freerouting 2.4.1 JAR are external, explicitly supplied tools.
The input board is untouched; write the routed board to a separate output path.
Always run KiCad DRC on the resulting board before using manufacturing exports.
"""

from __future__ import annotations

import argparse
from pathlib import Path
import re
import subprocess

import pcbnew


ROUTING_CLASSES = {
    "Default": (0.25, 0.7, 0.35, ()),
    "Power": (2.0, 1.2, 0.6, ("+5V", "+12V")),
    "Analog": (0.4, 0.7, 0.35, ("MEGA_5V", "AGND", "GND", "TEENSY_3V3", "DAC_3V3", "TEENSY_VIN", "COIL_LOW")),
}


def set_routing_classes(board: pcbnew.BOARD) -> None:
    """Apply project routing widths even if this filename has no .kicad_pro.

    KiCad's Python LoadBoard() must not be assumed to load a differently named
    project. These are the same fabrication classes as the project settings.
    """
    settings = board.GetDesignSettings().m_NetSettings
    settings.ClearNetclasses()
    settings.ClearNetclassPatternAssignments()
    settings.ClearNetclassLabelAssignments()
    for name, (width, diameter, drill, nets) in ROUTING_CLASSES.items():
        netclass = pcbnew.NETCLASS(name)
        netclass.SetTrackWidth(pcbnew.FromMM(width))
        netclass.SetClearance(pcbnew.FromMM(0.2))
        netclass.SetViaDiameter(pcbnew.FromMM(diameter))
        netclass.SetViaDrill(pcbnew.FromMM(drill))
        if name == "Default":
            settings.SetDefaultNetclass(netclass)
        else:
            settings.SetNetclass(name, netclass)
            for net in nets:
                settings.SetNetclassPatternAssignment(net, name)
    settings.ClearAllCaches()
    board.SynchronizeNetsAndNetClasses(False)


def check_exported_rules(path: Path) -> None:
    """Reject silent fallback to KiCad default routing widths in DSN export."""
    data = path.read_text(encoding="utf-8")
    # KiCad exports a special SMD-to-SMD clearance at one quarter of the class
    # clearance. This mixed SMD/THT project uses 0.20 mm for every pad pairing.
    data = re.sub(r"\(clearance [\d.]+ \(type smd_smd\)\)",
                  "(clearance 200 (type smd_smd))", data)
    for name, (width, diameter, drill, _) in ROUTING_CLASSES.items():
        exported_name = "kicad_default" if name == "Default" else name
        match = re.search(r"\(class " + exported_name + r"\s+(.*?)(?=\n    \(class |\n  \)\n  \(wiring)",
                          data, re.DOTALL)
        if not match:
            # KiCad can omit a class which has no assigned nets on a test board.
            if name != "Default":
                continue
            raise RuntimeError("DSN did not export the default netclass")
        block = match.group(0)
        expected = (f"(width {width * 1000:g})", "(clearance 200)",
                    f'Via[0-1]_{diameter * 1000:g}:{drill * 1000:g}_um')
        if any(token not in block for token in expected):
            raise RuntimeError(f"DSN routing rules differ from {name}: {block}")
    path.write_text(data, encoding="utf-8")


def run_router(board: pcbnew.BOARD, stem: str, work: Path, args) -> Path:
    """Export, route, and return the session; keep every intermediate file."""
    work.mkdir(parents=True, exist_ok=True)
    dsn, ses = work / f"{stem}.dsn", work / f"{stem}.ses"
    if ses.exists():
        raise RuntimeError(f"Refusing to reuse an existing routing session: {ses}")
    set_routing_classes(board)
    if not pcbnew.ExportSpecctraDSN(board, str(dsn)):
        raise RuntimeError(f"Could not export {dsn}")
    check_exported_rules(dsn)
    command = [
        str(args.java.resolve()), f"-Xmx{args.heap}", "-Djava.awt.headless=true",
        "-jar", str(args.jar.resolve()),
        "--gui.enabled=false", "--api_server.enabled=false",
        "--mcp_server.enabled=false", "-da", "-l", "en",
        f"--user_data_path={work / 'settings'}",
        f"--logging.file.location={work}",
        f"--router.result_json={work / 'routing-result.json'}",
        f"--router.optimizer.max_passes={args.optimizer_passes}",
        "-mp", str(args.passes), "-mt", "1",
        "-de", str(dsn), "-do", str(ses),
    ]
    subprocess.run(command, cwd=work, check=True)
    if not ses.is_file() or ses.stat().st_size == 0:
        raise RuntimeError("The router did not produce a non-empty session file")
    return ses


def save_board_preserving_project(path: Path, board: pcbnew.BOARD) -> None:
    """Prevent pcbnew from replacing the destination's fabrication settings."""
    project_path = path.with_suffix(".kicad_pro")
    project_bytes = project_path.read_bytes() if project_path.exists() else None
    try:
        pcbnew.SaveBoard(str(path), board)
    finally:
        if project_bytes is not None:
            project_path.write_bytes(project_bytes)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("board", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--java", type=Path, required=True)
    parser.add_argument("--jar", type=Path, required=True)
    parser.add_argument("--work-dir", type=Path, required=True)
    parser.add_argument("--passes", type=int, default=100)
    parser.add_argument("--optimizer-passes", type=int, default=5)
    parser.add_argument("--heap", default="4g")
    args = parser.parse_args()
    source, output = args.board.resolve(), args.output.resolve()
    if source == output:
        parser.error("Use a separate output filename to preserve the placed board")
    if not source.is_file() or not args.java.is_file() or not args.jar.is_file():
        parser.error("Board, Java executable, and router JAR must exist")
    work = args.work_dir.resolve()
    work.mkdir(parents=True, exist_ok=True)
    output.parent.mkdir(parents=True, exist_ok=True)
    board = pcbnew.LoadBoard(str(source))
    ses = run_router(board, source.stem, work / "signals", args)
    if not pcbnew.ImportSpecctraSES(board, str(ses)):
        raise RuntimeError(f"Could not import {ses}")
    board.BuildConnectivity()
    save_board_preserving_project(output, board)
    print(f"Saved {output}; verify it with kicad-cli pcb drc", flush=True)


if __name__ == "__main__":
    main()
