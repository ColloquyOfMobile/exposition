# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/pcb_files/gerbers.py

"""The fabrication package: Gerbers and drill files, one zip per board.

**The files are exported on a machine that has KiCad and committed**
(`py export_gerbers.py`, into `CAD/KiCad/production/`), and this module
only reads them. The machine that serves the download is the
installation's laptop, which has no KiCad and should not need one - it
gets the files the way it gets everything else, by pulling.

`manifest.json` beside them is what makes that safe. For every board it
records which `.kicad_pcb` the files were plotted from and that file's
digest, so the two questions worth asking of a fabrication package can
be answered without KiCad: **is every file here**, and **has the board
changed since**. A package that is out of step with its board is the
quietly-wrong kind of fault - the files still open in a viewer, the order
still goes through, and what comes back in the post is last week's
layout. So a stale board is said on the page that offers the download
and written into the README inside it, and `pytest_tests` fails on one.

What is exported and what is *released* are different things, and this
does not blur them: every one of these designs says in its own README
which physical checks are still open, and those documents travel inside
the package.

Nothing here imports from `colloquy` - see `pcb_files/__init__.py`.
"""
from __future__ import annotations

import hashlib
import io
import json
import zipfile
from dataclasses import dataclass
from pathlib import Path

# .../exposition/Source code/Python/colloquy/hardware/pcb_files/gerbers.py
#      [5]         [4]         [3]     [2]      [1]       [0]
REPO_FOLDER = Path(__file__).resolve().parents[5]
KICAD_FOLDER = REPO_FOLDER / "CAD" / "KiCad"
PRODUCTION_FOLDER = KICAD_FOLDER / "production"
MANIFEST_PATH = PRODUCTION_FOLDER / "manifest.json"

# What a two-layer board's package holds, by the Protel extension KiCad
# gives each layer - the names both fabs read the layer off. A four-layer
# board adds the two inner coppers. Paste is not listed: a board with no
# surface-mount pad plots an empty one and neither fab wants it for a
# bare board, so its absence is not a fault.
REQUIRED_SUFFIXES = (".gtl", ".gbl", ".gts", ".gbs", ".gto", ".gbo", ".gm1")
INNER_SUFFIXES = (".g1", ".g2")
DRILL_SUFFIX = ".drl"


class PackageError(Exception):
    """The package cannot be offered, and this says why in one sentence.

    Something to show on the page. Never something to raise out of a
    render: the page that offers these downloads is the installation's
    front page while its board is out.
    """


@dataclass(frozen=True)
class Board:
    """One board's entry in the manifest."""

    id: str
    title: str
    what: str
    group: str
    # How many the piece needs - not an order quantity, which is whatever
    # the fab's minimum makes it.
    quantity: int
    # Relative to CAD/KiCad, forward slashes.
    source: str
    source_sha256: str
    exported_at: str
    copper_layers: int
    # Millimetres, all four. Three small floats that read alike.
    width_mm: float
    height_mm: float
    thickness_mm: float
    smallest_drill_mm: float
    drc_errors: int
    drc_warnings: int
    unconnected: int
    files: tuple[str, ...]
    # Relative to CAD/KiCad: what to read before ordering, and what an
    # assembly service asks for.
    read_first: tuple[str, ...]
    assembly: tuple[str, ...]

    @property
    def folder(self) -> Path:
        return PRODUCTION_FOLDER / self.id

    @property
    def source_path(self) -> Path:
        return KICAD_FOLDER / self.source

    @property
    def zip_name(self) -> str:
        return f"colloquy-{self.id}-gerbers.zip"

    @property
    def size(self) -> str:
        return f"{_millimetres(self.width_mm)} x {_millimetres(self.height_mm)} mm"


def _millimetres(value: float) -> str:
    """210.0 as `210`, 62.5 as `62.5` - what goes into an order form."""
    return f"{value:.2f}".rstrip("0").rstrip(".")


def digest(path: Path) -> str:
    """A board file's digest, the same on every machine that has it.

    Line endings are taken out first. This repository is checked out
    with `core.autocrlf` on Windows, so one commit's `.kicad_pcb` is a
    different run of bytes on the machine KiCad wrote it on and on a
    machine that pulled it - and a digest that noticed would call every
    board stale everywhere except where it was exported.
    """
    data = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(data).hexdigest()


def _board(entry: dict) -> Board:
    drc = entry.get("drc") or {}
    size = entry.get("size mm") or (0.0, 0.0)
    return Board(
        id=str(entry["id"]),
        title=str(entry.get("title") or entry["id"]),
        what=str(entry.get("what") or ""),
        group=str(entry.get("group") or ""),
        quantity=int(entry.get("quantity") or 1),
        source=str(entry["source"]),
        source_sha256=str(entry.get("source sha256") or ""),
        exported_at=str(entry.get("exported at") or ""),
        copper_layers=int(entry.get("copper layers") or 2),
        width_mm=float(size[0]),
        height_mm=float(size[1]),
        thickness_mm=float(entry.get("thickness mm") or 0.0),
        smallest_drill_mm=float(entry.get("smallest drill mm") or 0.0),
        drc_errors=int(drc.get("errors") or 0),
        drc_warnings=int(drc.get("warnings") or 0),
        unconnected=int(drc.get("unconnected") or 0),
        files=tuple(str(name) for name in entry.get("files") or ()),
        read_first=tuple(str(name) for name in entry.get("read first") or ()),
        assembly=tuple(str(name) for name in entry.get("assembly") or ()),
    )


def load(manifest_path: Path = MANIFEST_PATH) -> tuple[Board, ...]:
    """Every board in the package, in the order the manifest lists them.

    Raises `PackageError` for every way the manifest can be unreadable -
    it is written by a script, and it is still a file in a working tree
    that a merge or an editor can leave in any state.
    """
    if not manifest_path.is_file():
        raise PackageError(
            "no fabrication package has been exported yet - "
            "run `py export_gerbers.py` on a machine that has KiCad"
        )
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        boards = tuple(_board(entry) for entry in data["boards"])
    except (OSError, ValueError, KeyError, TypeError, IndexError) as error:
        raise PackageError(
            f"the fabrication manifest cannot be read ({type(error).__name__}: {error})"
        ) from error

    if not boards:
        raise PackageError("the fabrication manifest lists no board")
    return boards


def find(boards: tuple[Board, ...], board_id: str) -> Board:
    for board in boards:
        if board.id == board_id:
            return board
    raise PackageError(f"there is no board called {board_id!r} in the package")


# --- is it any good ---------------------------------------------------


def missing_files(board: Board) -> tuple[str, ...]:
    """Files the manifest names that are not on disk."""
    return tuple(name for name in board.files if not (board.folder / name).is_file())


def missing_layers(board: Board) -> tuple[str, ...]:
    """Layers a fab needs that the manifest does not list at all."""
    suffixes = {Path(name).suffix.lower() for name in board.files}
    wanted: tuple[str, ...] = REQUIRED_SUFFIXES
    if board.copper_layers >= 4:
        wanted = wanted + INNER_SUFFIXES
    missing = [suffix for suffix in wanted if suffix not in suffixes]
    if DRILL_SUFFIX not in suffixes:
        missing.append(DRILL_SUFFIX)
    return tuple(missing)


def is_stale(board: Board) -> bool:
    """Has the board file changed since these files were plotted?

    A source that is not there at all is not called stale: there is
    nothing to be out of step with, and the files in hand are still the
    last thing anybody plotted.
    """
    source = board.source_path
    if not source.is_file():
        return False
    return digest(source) != board.source_sha256


def problems(board: Board) -> tuple[str, ...]:
    """Everything wrong with one board's package, as sentences."""
    found = []
    absent = missing_files(board)
    if absent:
        found.append(f"{len(absent)} of its files are missing: {', '.join(absent)}")
    layers = missing_layers(board)
    if layers:
        found.append(f"it has no {', '.join(layers)} file")
    if is_stale(board):
        found.append(
            f"{board.source} has changed since these were exported - "
            "they are the previous layout"
        )
    if board.drc_errors or board.unconnected:
        found.append(
            f"KiCad's design rule check found {board.drc_errors} errors and "
            f"{board.unconnected} unconnected items when it was exported"
        )
    return tuple(found)


# --- the zips ---------------------------------------------------------


def board_zip(board: Board) -> bytes:
    """One board's Gerbers and drill files, as a fab takes them.

    Flat, and nothing in it but the plots: both fabs read the layers off
    the file names, and a README or a BOM beside them is one more file
    for an upload form to fail to recognise. Those travel in the outer
    package instead.
    """
    absent = missing_files(board)
    if absent:
        raise PackageError(
            f"{board.title} cannot be packaged - missing {', '.join(absent)}"
        )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(board.files):
            archive.writestr(name, (board.folder / name).read_bytes())
    return buffer.getvalue()


def readme(boards: tuple[Board, ...], commit: str = "") -> str:
    """The text file at the top of the package: what to order, and how."""
    lines = [
        "COLLOQUY OF MOBILES - PCB fabrication package",
        "",
        "One zip per board, each ready to upload as it is to PCBWay or",
        "JLCPCB: both take one zip of Gerbers for one board. Do not unzip",
        "them first, and upload one board at a time.",
        "",
    ]
    if commit:
        lines.append(f"Taken from the repository at commit {commit}.")
        lines.append("")

    group = None
    for board in boards:
        if board.group != group:
            group = board.group
            lines.append(group.upper() if group else "BOARDS")
            lines.append("")
        lines.append(f"  {board.zip_name}")
        lines.append(f"    {board.title} - {board.what}")
        lines.append(
            f"    {board.copper_layers} copper layers, {board.size}, "
            f"{_millimetres(board.thickness_mm)} mm thick, "
            f"smallest hole {_millimetres(board.smallest_drill_mm)} mm"
        )
        lines.append(f"    the piece needs {board.quantity}")
        lines.append(
            f"    plotted {board.exported_at} from CAD/KiCad/{board.source}; "
            f"design rule check: {board.drc_errors} errors, "
            f"{board.unconnected} unconnected, {board.drc_warnings} warnings"
        )
        for problem in problems(board):
            lines.append(f"    *** {problem}")
        lines.append("")

    lines.extend(
        [
            "FOR THE ORDER FORM",
            "",
            "  Layers, size and thickness per board as above. The Gerbers are",
            "  RS-274X in millimetres with Protel file extensions. The drill",
            "  files are Excellon, metric, absolute origin, with plated (PTH)",
            "  and non-plated (NPTH) holes in separate files.",
            "",
            "BEFORE ORDERING",
            "",
            "  These are plots of the routed boards as they stand. Each",
            "  design's own README lists the physical checks that are still",
            "  open - module fit, connector heights, supply current - and",
            "  none of them is settled by a file. Those documents are in",
            "  docs/, and the bills of materials and placement files an",
            "  assembly service asks for are in assembly/.",
            "",
        ]
    )
    return "\n".join(lines)


def package_zip(boards: tuple[Board, ...], commit: str = "") -> bytes:
    """Everything, in one download: a zip per board, and what to read.

    A board whose files are incomplete is left out and named in the
    README rather than failing the whole download - the other boards are
    still worth ordering.
    """
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.txt", readme(boards, commit))

        written = set()
        for board in boards:
            if missing_files(board):
                continue
            # Stored, not deflated twice over.
            archive.writestr(
                zipfile.ZipInfo(board.zip_name), board_zip(board), zipfile.ZIP_STORED
            )
            for folder, names in (("docs", board.read_first), ("assembly", board.assembly)):
                for name in names:
                    path = KICAD_FOLDER / name
                    arcname = f"{folder}/{name}"
                    if arcname in written or not path.is_file():
                        continue
                    written.add(arcname)
                    archive.writestr(arcname, path.read_bytes())
    return buffer.getvalue()
