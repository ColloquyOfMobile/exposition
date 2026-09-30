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
    "Default": (0.3, 0.8, 0.4, ()),
    "Power": (2.0, 1.2, 0.6, ("+5V", "+12V", "GND")),
    "Analog": (0.5, 0.8, 0.4, ("MEGA_5V", "AGND")),
}
POWER_NETS = {"+5V", "+12V", "GND"}
ANALOG_RECTANGLE_MM = (72, 171, 230, 292)


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
        netclass.SetClearance(pcbnew.FromMM(0.25))
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
    # clearance. This through-hole project uses 0.25 mm for every pad pairing.
    data = re.sub(r"\(clearance [\d.]+ \(type smd_smd\)\)",
                  "(clearance 250 (type smd_smd))", data)
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
        expected = (f"(width {width * 1000:g})", "(clearance 250)",
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


def route_power_first(source: Path, board: pcbnew.BOARD, work: Path, args) -> None:
    """Keep distribution current outside the analogue circuit/ground region."""
    power_board = pcbnew.LoadBoard(str(source))
    for footprint in power_board.GetFootprints():
        for pad in footprint.Pads():
            if pad.GetNetname() not in POWER_NETS:
                pad.SetNetCode(0)
    for track in list(power_board.GetTracks()):
        if track.GetNetname() not in POWER_NETS:
            power_board.Remove(track)
    keepout = pcbnew.ZONE(power_board)
    keepout.SetLayerSet(pcbnew.LSET.AllCuMask())
    keepout.SetIsRuleArea(True)
    keepout.SetDoNotAllowTracks(True)
    keepout.SetDoNotAllowVias(True)
    keepout.SetDoNotAllowCopperPour(True)
    keepout.SetZoneName("TEMP_POWER_ROUTING_ANALOG_EXCLUSION")
    keepout.Outline().NewOutline()
    left, top, right, bottom = ANALOG_RECTANGLE_MM
    for x, y in ((left, top), (right, top), (right, bottom), (left, bottom)):
        keepout.Outline().Append(pcbnew.FromMM(x), pcbnew.FromMM(y))
    power_board.Add(keepout)
    power_board.BuildConnectivity()
    ses = run_router(power_board, source.stem + "-power", work / "power", args)
    # Import into the ORIGINAL board: the temporary no-net pads and keepout
    # must not become part of the native electrical design.
    if not pcbnew.ImportSpecctraSES(board, str(ses)):
        raise RuntimeError(f"Could not import power session {ses}")
    for track in board.GetTracks():
        if track.GetNetname() in POWER_NETS:
            track.SetLocked(True)
    pcbnew.SaveBoard(str(work / "power-locked.kicad_pcb"), board)


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
    parser.add_argument("--power-first", action="store_true",
                        help="Route and lock perimeter power before all signals")
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
    if args.power_first:
        route_power_first(source, board, work, args)
    ses = run_router(board, source.stem, work / "signals", args)
    if not pcbnew.ImportSpecctraSES(board, str(ses)):
        raise RuntimeError(f"Could not import {ses}")
    if args.power_first:
        for track in board.GetTracks():
            if track.GetNetname() in POWER_NETS:
                track.SetLocked(True)
    board.BuildConnectivity()
    save_board_preserving_project(output, board)
    print(f"Saved {output}; verify it with kicad-cli pcb drc", flush=True)


if __name__ == "__main__":
    main()
