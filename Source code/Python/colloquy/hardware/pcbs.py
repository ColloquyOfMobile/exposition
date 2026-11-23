# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/pcbs.py

"""The PCBs, on the page: each board's card, files and order status.

It sat on the home page from 2026-10-21 to 2026-11-23, and the home page
went back to being the tree. Here it is a node like any other under
`hardware`, because a board's state - waiting, ordered, received,
soldered - is a fact about the equipment, true with the software off.

The routes behind it (`/pcb/...`, `/pcb-order/...`) are unchanged, and the
standby page still draws the same catalog: with the board out, the tree
is not served, and that page is the only place to reach it.
"""
from html import escape

from colloquy.base import Base
from colloquy.hardware.pcb_files import orders
from colloquy.ui import leaves


class PCBs(Base):
    """Every board in the production manifest, with its order status."""

    @property
    def name(self):
        return "pcbs"

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def snapshot_children(self):
        return {}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        # `catalog_html` already swallows a damaged export; this guards the
        # params lookup too, since a render must never raise.
        try:
            markup = orders.catalog_html(orders.book_of(self.colloquy))
        except Exception as error:  # noqa: BLE001 - drawing a page
            markup = f"<p>PCBs unavailable: {escape(repr(error))}</p>"
        states["catalog"] = leaves.html(path, "catalog", markup)
        return states
