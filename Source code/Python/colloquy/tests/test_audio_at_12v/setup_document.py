# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_audio_at_12v/setup_document.py

from pathlib import Path

from colloquy.markdown_document import MarkdownDocument


class SupplySetup(MarkdownDocument):
    """How to change the amplifier supply without destroying anything.

    Beside `test audio subsystem`'s `hardware setup` and hanging off its
    own test for the same reason: the moment somebody needs telling is
    the moment they are about to press one of the two buttons next to it.

    What it covers that the other document does not is the half-hour
    with a screwdriver in it. Every other bench test in this tree can be
    got wrong and produce a bad number; this one can be got wrong and
    produce a dead Mega, because the thing being changed is a supply rail
    and the thing next to it is a 5 V ADC pin.

    Not gated by is_simulated, exactly as its neighbour is not: a bench
    is where it is wanted, and the machine somebody is about to hold a
    screwdriver over is by definition not the installation.
    """

    folder = Path(__file__).resolve().parent
    file_name = "SUPPLY_SETUP.md"
    document_name = "supply setup"
