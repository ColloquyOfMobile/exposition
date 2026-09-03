# -*- coding: utf-8 -*-
# export_pcb_layout.py

"""Draw the board that exists, out of the board file that describes it.

    py export_pcb_layout.py

Writes `electronic-box-layout.svg` (and a back view) under `Source code/
Python/colloquy/server2/static/hardware/`, which is what `AS_BUILT.md`
shows on the page (see `colloquy/hardware/electronics/`).

**Why a picture at all, in a tree that prefers prose and tables.**
`as built` is the current PCB read out of the KiCad netlist pin by pin,
and it is exact about nets in a way no drawing is. What it cannot do is
put a scalpel in the right place. Its two load-bearing findings are
*geometry*: `J4`/`J8`/`J10` are a 1:1 breakout whose shield pads sit at
x = 191.96 mm and whose header pins sit at x = 200.85 mm, joined by one
track each across an 8.89 mm gap - and `J11`/`J12` are break points
rather than headers. Both of those are sentences about where things are,
and a reader holding the board wants to see the gap before cutting it.

**Why it is generated and not committed by hand.** Same rule as
`next_pcb.py`, `harness.py` and `extract_hardware_photos.py`: the copper
is the source of truth, and a drawing exported once and forgotten is a
drawing that quietly stops matching the board. Re-run this after any
change to `electronic box.kicad_pcb`.

**Why the colours are remapped.** `kicad-cli` plots in whatever theme
this machine's KiCad is set to, and on this one that is the dark theme:
silkscreen comes out `#F2EDA1` (pale yellow) and the board outline
`#D0D2CD` (light grey). Both are close to invisible on a page with a
white background, and the silkscreen is exactly where the reference
designators live - so the one thing a reader is looking for would be the
one thing they could not see. Copper is left alone: `#C83434` and
`#4D7FC4` read perfectly well on white, and red-is-front /
blue-is-back is the convention anybody who has opened this board in
Pcbnew already has. The mapping is by layer rather than by literal
colour, and each layer is exported once on its own to find out what
colour it actually came out as, so a machine with a light theme set
needs no edit here.

`kicad-cli` ships inside KiCad; this looks for it in the usual places
and takes `--kicad-cli` otherwise. It is a dev dependency of this script
alone, exactly as `pymupdf` is of `extract_hardware_photos.py`: nothing
the installation runs needs KiCad, and this is run again only when the
board changes.
"""
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BOARD = Path("CAD/KiCad/electronic box/electronic box.kicad_pcb")
FOLDER = Path("Source code/Python/colloquy/server2/static/hardware")

# Where KiCad puts kicad-cli on a Windows install, newest first. `which`
# is tried before any of these.
CANDIDATES = (
    Path(r"C:\Program Files\KiCad\9.0\bin\kicad-cli.exe"),
    Path(r"C:\Program Files\KiCad\8.0\bin\kicad-cli.exe"),
    Path(r"C:\Program Files\KiCad\7.0\bin\kicad-cli.exe"),
)

# What each view is for. Two, because a board has two sides and somebody
# reading this has one in their hand to turn over. The front is the one
# every finding in `as built` is about - the J4/J8/J10 breakout is front
# copper and both of the scalpel cuts are on F.Cu - so it is the one the
# document leads with. A third view with both coppers overlaid was tried
# and dropped: it is the largest file of the three and the least legible,
# since red over blue at this density stops reading as either.
VIEWS = {
    "electronic-box-layout": (
        ("F.Cu", "F.Silkscreen", "Edge.Cuts"),
        False,
        "front copper and silkscreen",
    ),
    "electronic-box-layout-back": (
        ("B.Cu", "B.Silkscreen", "Edge.Cuts"),
        True,
        "back copper, mirrored so it reads as seen from behind",
    ),
}

# Layers whose own colour is unreadable on a white page, and what to draw
# them in instead. Copper is deliberately absent - see the docstring.
READABLE = {
    "F.Silkscreen": "#3A3A3A",
    "B.Silkscreen": "#3A3A3A",
    "Edge.Cuts": "#000000",
}

# The copper layers, and how far to knock their *filled* areas back.
#
# This board is two ground pours over almost its whole area, so a plain
# copper plot is a solid red sheet with the routing showing through as
# white clearance gaps - and the silkscreen, which is the half a reader
# is looking for, disappears underneath it. Verified by looking: the
# first export of this was unusable.
#
# The fix is in how KiCad draws the two things. A pour and a pad are
# *filled* groups (`fill:#C83434; ... stroke:none`); a track is a
# *stroked* one. So fading fill alone turns the pour into a wash and
# leaves every track at full strength, which is the drawing somebody
# tracing a net actually wants. 0.16 was picked by eye against the
# silkscreen over it.
POUR_OPACITY = "0.16"
COPPER = ("F.Cu", "B.Cu")


def find_cli(override):
    if override:
        return Path(override)
    found = shutil.which("kicad-cli")
    if found:
        return Path(found)
    for candidate in CANDIDATES:
        if candidate.is_file():
            return candidate
    raise SystemExit(
        "kicad-cli not found. It ships inside KiCad - pass --kicad-cli "
        "with the path to it."
    )


def plot(cli, layers, target, mirror=False):
    command = [
        str(cli), "pcb", "export", "svg",
        "--mode-single",
        # Board area only, and no drawing sheet: a title block sized for
        # A4 around a board that *is* A4 wastes most of the picture.
        "--page-size-mode", "2",
        "--exclude-drawing-sheet",
        "--layers", ",".join(layers),
        "-o", str(target),
    ]
    if mirror:
        command.append("--mirror")
    command.append(str(BOARD))
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0 or not target.is_file():
        raise SystemExit(
            f"kicad-cli failed for {target.name}:\n"
            f"{result.stdout.strip()}\n{result.stderr.strip()}"
        )


def colour_of(cli, layer, scratch):
    """What this machine's theme plots `layer` in.

    Asked rather than assumed: the whole point of remapping is that the
    theme is a property of the machine, so reading a literal out of this
    file would be the same mistake one level down.
    """
    target = scratch / f"probe-{layer}.svg"
    plot(cli, (layer,), target)
    colours = set(re.findall(r"stroke:(#[0-9A-Fa-f]{6})", target.read_text("utf-8")))
    # Black and white are the drill marks and the pad holes, on every
    # layer; whatever is left is the layer's own colour.
    colours -= {"#000000", "#FFFFFF"}
    if len(colours) != 1:
        return None
    return colours.pop()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--kicad-cli", default=None)
    args = parser.parse_args(argv)

    if not BOARD.is_file():
        print(f"{BOARD} is not there - run this from the repository root.")
        return 1
    FOLDER.mkdir(parents=True, exist_ok=True)

    cli = find_cli(args.kicad_cli)
    print(f"kicad-cli: {cli}")

    with tempfile.TemporaryDirectory() as temporary:
        scratch = Path(temporary)
        remap = {}
        for layer, wanted in READABLE.items():
            found = colour_of(cli, layer, scratch)
            if found is None:
                print(f"  {layer}: nothing plotted, or more than one colour")
                continue
            if found.upper() == wanted.upper():
                print(f"  {layer}: already {found}")
                continue
            remap[found.upper()] = wanted
            print(f"  {layer}: {found} -> {wanted}")

        fades = {}
        for layer in COPPER:
            found = colour_of(cli, layer, scratch)
            if found is None:
                print(f"  {layer}: nothing plotted, or more than one colour")
                continue
            fades[
                f"fill:{found}; fill-opacity:1.0000; stroke:none;"
            ] = f"fill:{found}; fill-opacity:{POUR_OPACITY}; stroke:none;"
            print(f"  {layer}: {found} pours faded to {POUR_OPACITY}, tracks left alone")

        for name, (layers, mirror, what) in VIEWS.items():
            target = FOLDER / f"{name}.svg"
            plot(cli, layers, target, mirror=mirror)
            text = target.read_text(encoding="utf-8")
            for found, wanted in remap.items():
                text = re.sub(found, wanted, text, flags=re.IGNORECASE)
            # After the recolour, so the copper colours are still their
            # own - these two keys are whole style strings, not colours.
            for found, wanted in fades.items():
                text = text.replace(found, wanted)
            target.write_text(text, encoding="utf-8")
            print(
                f"{target.name}: {what}, "
                f"{target.stat().st_size // 1024} kB"
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
