# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/pcb_files/kicad_projects.py

"""Everything under `CAD/KiCad`, as one zip somebody can open in KiCad.

"Everything" is what the repository holds, not what the folder holds. On
a machine where the boards are worked on, the folder is several times the
size of the design: KiCad leaves an autosave zip beside every project on
every save, Blender leaves a `.blend1` beside every scene, and none of it
is anything a second person wants. So the listing is asked of git when
git will answer, and made by walking with the same things left out when
it will not - a download that depended on git being healthy would be a
download that failed on exactly the day somebody needed the files off a
laptop that could not reach its remote.

**The archive is built once and kept** (`local/downloads/`), named after
a fingerprint of what went into it - every path, size and modification
time - so the same files are never zipped twice and a changed board never
comes out of a stale archive. It is about 300 MB before compression,
which is most of a minute of zipping and far too much to hold in memory,
so it is written to disk and handed out in pieces.

Nothing here imports from `colloquy` - see `pcb_files/__init__.py`.
"""
from __future__ import annotations

import hashlib
import os
import zipfile
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path
from threading import Lock
from time import time

# .../exposition/Source code/Python/colloquy/hardware/pcb_files/kicad_projects.py
#      [5]         [4]         [3]     [2]      [1]       [0]
REPO_FOLDER = Path(__file__).resolve().parents[5]
KICAD_FOLDER = REPO_FOLDER / "CAD" / "KiCad"

# Where git is asked, and what the paths inside the zip are relative to:
# the archive unpacks as `KiCad/...`.
TRACKED_FOLDER = "CAD/KiCad"
ARCHIVE_ROOT = REPO_FOLDER / "CAD"

ARCHIVE_PREFIX = "colloquy-kicad-"

# What the walk leaves out: the same working state `.gitignore` leaves
# out, restated because the walk is what runs when git cannot be asked.
SKIPPED_FOLDER_ENDINGS = ("-backups", "__pycache__", "__MACOSX")
SKIPPED_NAMES = ("fp-info-cache",)
SKIPPED_SUFFIXES = (".kicad_prl", ".lck", ".blend1", ".pyc")

# Already compressed. Deflating these again costs build time and saves
# nothing. (`.blend` is here because the scenes in this tree are saved
# compressed - they open with a zstd header, not `BLENDER`.)
STORED_SUFFIXES = frozenset(
    {".zip", ".png", ".jpg", ".jpeg", ".pdf", ".blend", ".gz", ".7z", ".mp4"}
)

CHUNK = 1 << 16

# How long a count of the files is believed. The page that shows it is
# redrawn on every refresh, and asking git each time would be a
# subprocess per page view for a number that changes when a board does.
SUMMARY_LIFETIME = 300.0

_build_lock = Lock()
_summary: tuple[float, "Summary"] | None = None


class Summary:
    """How much there is to download, for the page that offers it."""

    def __init__(self, files: Sequence[Path]):
        self.count = len(files)
        self.bytes = sum(_size(path) for path in files)

    @property
    def megabytes(self) -> int:
        return round(self.bytes / 1e6)


def _size(path: Path) -> int:
    try:
        return path.stat().st_size
    except OSError:
        return 0


def _is_skipped(path: Path) -> bool:
    if path.name in SKIPPED_NAMES or path.suffix.lower() in SKIPPED_SUFFIXES:
        return True
    if path.name.startswith("~"):
        return True
    return any(
        part.endswith(SKIPPED_FOLDER_ENDINGS)
        for part in path.relative_to(KICAD_FOLDER).parts[:-1]
    )


def walked() -> tuple[Path, ...]:
    """Every design file under CAD/KiCad, found by looking."""
    return tuple(
        sorted(
            path
            for path in KICAD_FOLDER.rglob("*")
            if path.is_file() and not _is_skipped(path)
        )
    )


def files(tracked: Callable[[str], Sequence[str]] | None = None) -> tuple[Path, ...]:
    """What goes in the archive.

    `tracked` is how git is asked - `Git.tracked`, handed in rather than
    imported so that this module stays free of the package. It may raise
    anything at all; whatever it raises, the answer is the walk.
    """
    if tracked is not None:
        try:
            listed = tuple(
                sorted(
                    path
                    for path in (REPO_FOLDER / name for name in tracked(TRACKED_FOLDER))
                    if path.is_file()
                )
            )
        except Exception:  # noqa: BLE001 - see the docstring
            listed = ()
        if listed:
            return listed
    return walked()


def summary(tracked: Callable[[str], Sequence[str]] | None = None) -> Summary:
    """How many files and how big, remembered for a few minutes."""
    global _summary
    now = time()
    if _summary is not None and now - _summary[0] < SUMMARY_LIFETIME:
        return _summary[1]
    counted = Summary(files(tracked))
    _summary = (now, counted)
    return counted


def fingerprint(listed: Sequence[Path]) -> str:
    """One name for this exact set of files as they are now."""
    seen = hashlib.sha1()
    for path in listed:
        try:
            stat = path.stat()
        except OSError:
            continue
        line = f"{path.relative_to(ARCHIVE_ROOT).as_posix()}\0{stat.st_size}\0{stat.st_mtime_ns}\n"
        seen.update(line.encode("utf-8"))
    return seen.hexdigest()[:12]


def archive(cache_folder: Path, listed: Sequence[Path]) -> Path:
    """The zip of these files, built now if it has not been already.

    One at a time: two people pressing the link together would otherwise
    write the same several hundred megabytes twice over, to the same
    name. The second waits for the first and is handed its file.

    Written under a `.part` name and renamed when whole, so a build cut
    short by a restart - which this installation now does by itself -
    never leaves something that looks like an archive. Older archives are
    removed on the way out; one board changing would otherwise leave
    another copy of everything behind it each time.
    """
    cache_folder.mkdir(parents=True, exist_ok=True)
    target = cache_folder / f"{ARCHIVE_PREFIX}{fingerprint(listed)}.zip"

    with _build_lock:
        if target.is_file():
            return target

        partial = target.with_suffix(".part")
        with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as out:
            for path in listed:
                if not path.is_file():
                    continue
                stored = path.suffix.lower() in STORED_SUFFIXES
                out.write(
                    path,
                    path.relative_to(ARCHIVE_ROOT).as_posix(),
                    zipfile.ZIP_STORED if stored else zipfile.ZIP_DEFLATED,
                )
        os.replace(partial, target)

        for old in cache_folder.glob(f"{ARCHIVE_PREFIX}*"):
            if old != target:
                try:
                    old.unlink()
                except OSError:
                    pass
    return target


def chunks(path: Path, size: int = CHUNK) -> Iterator[bytes]:
    """A file in pieces, for a response too big to hold whole."""
    with path.open("rb") as handle:
        while True:
            piece = handle.read(size)
            if not piece:
                return
            yield piece
