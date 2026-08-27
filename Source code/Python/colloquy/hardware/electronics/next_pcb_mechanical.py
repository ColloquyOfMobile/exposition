# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/electronics/next_pcb_mechanical.py

"""Where the next board's edges and its connectors have to be.

**Read out of the board that exists, not remembered.** The enclosure was
cut for `CAD/KiCad/electronic box/electronic box.kicad_pcb`, and a
replacement that is a millimetre out in any of these is a replacement that
does not go in the rack. So this parses that file for the outline, the
corner radius and the position of everything the panel has a hole for,
the same way `drivers/arduino/firmware.py` reads the baud rate straight
out of the `.ino`.

**What it is not.** It says where things must be, not where the rest
should go - that is a layout decision and a person makes it in front of a
screen. What it can do is say which of the old board's parts are gone and
how much room they free, because that answer is arithmetic and it happens
to be the answer to "where do the filters and the analysers live".

The parse is deliberately narrow: `gr_line`/`gr_arc` on `Edge.Cuts`, and
`(at ...)` plus the Reference property of each footprint. Anything more
would be re-implementing a PCB reader to no purpose.
"""
import re
from functools import lru_cache
from pathlib import Path

# The board this one replaces. Five directories up from here is the repo
# root: electronics -> hardware -> colloquy -> Python -> Source code -> repo.
EXISTING_PCB = (
    Path(__file__).resolve().parents[5]
    / "CAD"
    / "KiCad"
    / "electronic box"
    / "electronic box.kicad_pcb"
)

# What the panel has a hole for, and why it cannot move. Everything else
# on the old board is free to go wherever the new layout wants it.
FIXED = {
    "J5": "female1's DSUB - right edge",
    "J1": "female2's DSUB - left edge",
    "A-J3": "female3 and male1's DSUB - bottom edge",
    "B-J4": "male1's audio and male2's everything - bottom edge",
    "J2": "the DC jack - right edge, near the top",
    "A1": "the Mega, whose USB socket the driver plugs into",
    "U1": "the U2D2's mount, whose USB lead has to reach out too",
}

# Gone from the new board, because the amplifier moved to the body. Five
# breakouts and five volume pots, and the room they free is the room the
# filter board and the analyser array need.
REMOVED = (
    "female1/amp1", "female2/amp1", "female3/amp1", "male1/amp1", "male2/amp1",
    "RV1", "RV2", "RV3", "RV4", "RV5",
)


def _text():
    return EXISTING_PCB.read_text(encoding="utf-8")


@lru_cache(maxsize=1)
def outline():
    """The board edge: its bounding box, its size and its corner radius.

    Every `Edge.Cuts` point, which for a rounded rectangle is the four
    straight sides plus the four corner arcs - so the extreme values are
    the true extent whichever way round the arcs were drawn.
    """
    xs, ys, radii = [], [], []
    for match in re.finditer(r"\((gr_line|gr_arc)\b(.*?)\n\t\)", _text(), re.S):
        kind, block = match.group(1), match.group(2)
        if "Edge.Cuts" not in block:
            continue
        points = [
            (name, float(x), float(y))
            for name, x, y in re.findall(
                r"\((start|end|mid)\s+([-\d.]+)\s+([-\d.]+)\)", block
            )
        ]
        for _, x, y in points:
            xs.append(x)
            ys.append(y)
        if kind == "gr_arc":
            named = {name: (x, y) for name, x, y in points}
            start, end = named.get("start"), named.get("end")
            if start and end:
                # A quarter turn, so the radius is the leg of the corner.
                radii.append(round(max(abs(start[0] - end[0]),
                                       abs(start[1] - end[1])), 2))
    return {
        "left": min(xs), "right": max(xs), "top": min(ys), "bottom": max(ys),
        "width": round(max(xs) - min(xs), 2),
        "height": round(max(ys) - min(ys), 2),
        "corner_radius": min(radii) if radii else None,
    }


@lru_cache(maxsize=1)
def placements():
    """Every footprint on the old board: reference -> where and what."""
    found = {}
    for match in re.finditer(r'\(footprint\s+"([^"]+)"(.*?)\n\t\)\n', _text(), re.S):
        library, block = match.group(1), match.group(2)
        at = re.search(r"\(at\s+([-\d.]+)\s+([-\d.]+)(?:\s+([-\d.]+))?\)", block)
        reference = re.search(r'\(property\s+"Reference"\s+"([^"]+)"', block)
        if at is None or reference is None:
            continue
        found[reference.group(1)] = {
            "x": float(at.group(1)),
            "y": float(at.group(2)),
            "rotation": float(at.group(3) or 0),
            "footprint": library,
        }
    return found


def fixed_placements():
    """The ones the enclosure dictates, with the reason for each."""
    where = placements()
    return {
        reference: {**where[reference], "why": why}
        for reference, why in FIXED.items()
        if reference in where
    }


def freed_region():
    """The bounding box of what the amplifiers and their pots vacate.

    Not a keep-out and not a promise - the parts around it have not moved
    - but it is where the ten largest things on the old board used to be,
    and the filter stages and analysers have to go somewhere.
    """
    where = placements()
    points = [where[reference] for reference in REMOVED if reference in where]
    if not points:
        return None
    xs = [point["x"] for point in points]
    ys = [point["y"] for point in points]
    return {
        "left": min(xs), "right": max(xs), "top": min(ys), "bottom": max(ys),
        "width": round(max(xs) - min(xs), 2),
        "height": round(max(ys) - min(ys), 2),
        "parts": len(points),
    }


def edges_of(reference):
    """Which edge a part sits against, if any, and how far off it is.

    Said in words because "14.2 mm from the bottom" is what tells somebody
    the panel cutout is on the bottom, and a pair of coordinates is not.
    """
    board = outline()
    where = placements().get(reference)
    if where is None:
        return None
    distances = {
        "left": where["x"] - board["left"],
        "right": board["right"] - where["x"],
        "top": where["y"] - board["top"],
        "bottom": board["bottom"] - where["y"],
    }
    edge = min(distances, key=distances.get)
    return edge, round(distances[edge], 2)

def mounting_holes():
    """Every non-plated hole on the old board, which is none of them.

    Read out of the exported NPTH drill file rather than inferred: the
    file exists, it has a header and an `M30`, and not one coordinate
    between them. There is no `MountingHole` footprint either.

    That is a finding and not a detail. The board is A4, it carries a Mega
    2560 as a shield, five DSUB housings and a DC jack, and it is held by
    nothing but those housings' own jackscrews. Whatever the next one
    does, it should decide this on purpose.
    """
    drill = EXISTING_PCB.with_name(EXISTING_PCB.stem + "-NPTH.drl")
    if not drill.exists():
        return None
    holes = [
        line for line in drill.read_text(encoding="utf-8").splitlines()
        if re.match(r"^X[-\d.]+Y[-\d.]+", line.strip())
    ]
    return holes


def has_mounting_holes():
    holes = mounting_holes()
    return bool(holes)
