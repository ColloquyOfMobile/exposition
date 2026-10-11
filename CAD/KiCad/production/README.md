# Fabrication package

Gerbers and Excellon drill files for the boards that are still to be made,
one folder per board, in the form PCBWay and JLCPCB take.

**Everything here is written by `py export_gerbers.py`** at the repository
root. Do not edit a file in these folders, and re-run the script after any
change to one of the boards it lists: `manifest.json` records the digest of
the `.kicad_pcb` each folder was plotted from, and a folder plotted from an
older layout is reported as out of date on the page that offers the
download and fails `pytest_tests/hardware/test_pcb_files.py`.

```
py export_gerbers.py            plot the boards that have changed
py export_gerbers.py --all      plot every board again
py export_gerbers.py --check    say what is out of date, write nothing
```

The running program serves these as zips (`/download/gerbers`), which is
how they reach whoever is ordering. The installation's laptop has no KiCad;
it gets the files by pulling.

## What this is not

A plot is not a release. Each design's own README lists the physical checks
that are still open, and those documents remain the authority:

- `../shields/README.md`, `REVIEW.md` and `ASSEMBLY.md` for the backplane,
  the Teensy adapter, the voice card, the analyser carrier and the
  microphone holder;
- `../female base v2/README.md` and `../male static v2/README.md` for the
  two body boards.

The script refuses to plot a board that fails KiCad's design rule check,
which establishes that the copper matches the rules it was drawn to and
nothing about whether a module fits.

## Which boards

The table at the top of `export_gerbers.py` is where that is decided. The
boards already built (`electronic box`, `center`, `female base`,
`female static`, `male static`) keep the Gerbers in their own folders, and
the two other candidates for the main board (`colloquy-control-v2`,
`thomas-or-teensy`) are deliberately left out, so that one download holds
one set of boards to order.
