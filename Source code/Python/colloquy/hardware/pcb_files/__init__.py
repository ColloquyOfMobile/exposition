# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/pcb_files/__init__.py

"""The files a board is made from, as things somebody can download.

Two of them, and they answer two different people. `gerbers` is for
whoever is ordering: the fabrication package of every new board, in the
form PCBWay and JLCPCB take. `kicad_projects` is for whoever is going to
open the design: everything under `CAD/KiCad`, as this checkout has it.

Both are served by routes rather than by tree commands (`/download/...`,
see `server2/wsgi2.py`) - a command answers with a re-render of its node,
and the answer here is a zip. `catalog` draws the boards on the home page
and serves each one's files; `orders` walks them through a JLCPCB order
(`/pcb-order/...`) and keeps where each one stands.

Neither module imports anything from `colloquy`, on purpose: the script
that writes the fabrication package (`export_gerbers.py` at the repo
root) loads `gerbers` by path, because importing the package wipes
`local/logs` under a running server.
"""
