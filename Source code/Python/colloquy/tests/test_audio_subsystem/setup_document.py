# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/test_audio_subsystem/setup_document.py

from pathlib import Path

from colloquy.markdown_document import MarkdownDocument


class HardwareSetup(MarkdownDocument):
    """How to wire the audio subsystem, hanging off the test that checks it.

    It sat on the root for a while, covering the whole installation. That
    was a document about everything, which is a document nobody opens: the
    only hardware here that anybody has to *set up* from nothing is
    Thomas's board, and the moment they need telling is the moment they
    are about to press start on the test below it.

    So it lives beside that test's own scenario - the scenario says what
    the run will do, this says what has to be plugged in for it to mean
    anything - and it is not gated by is_simulated, since a bench is
    exactly where it is wanted.
    """

    folder = Path(__file__).resolve().parent
    file_name = "HARDWARE_SETUP.md"
    document_name = "hardware setup"
