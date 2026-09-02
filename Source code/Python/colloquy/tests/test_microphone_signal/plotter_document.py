# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_microphone_signal/plotter_document.py

from pathlib import Path

from colloquy.markdown_document import MarkdownDocument


class MicrophonePlotter(MarkdownDocument):
    """How to get one microphone onto a plot, and how to read it.

    Beside `test audio at 12v`'s `supply setup` and `test audio
    subsystem`'s `hardware setup`, and hanging off its own test for the
    same reason: the moment somebody needs telling is the moment they
    are about to clip a lead onto a connector. One of the two routes it
    describes pulls something off `J11` and reflashes the installation's
    own Mega, and there is an order to do that in.

    Not gated by is_simulated, exactly as its two neighbours are not.
    The machine with the board in it is the one place none of it is
    hypothetical.
    """

    folder = Path(__file__).resolve().parent
    file_name = "MICROPHONE_PLOTTER.md"
    document_name = "plotter setup"
