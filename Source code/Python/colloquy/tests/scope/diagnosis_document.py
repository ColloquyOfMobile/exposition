# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/scope/diagnosis_document.py

from pathlib import Path

from colloquy.markdown_document import MarkdownDocument


class DiagnosingAMicrophone(MarkdownDocument):
    """How to take a microphone apart with two channels, hanging off the
    two channels.

    `HARDWARE_SETUP.md`'s reason: the moment somebody needs telling is the
    moment they are about to press start on the node below it. A document
    about diagnosing microphones filed anywhere else is a document nobody
    opens, because nobody goes looking for one until they are already
    standing at the bench with a quiet microphone.

    It is a method *and* the investigation that produced it, in that
    order, because every rule in it is traced to the run that earned it -
    the 95 per cent an open pin keeps, the 0.6 per cent two channels
    differ by, the peak-to-peak 294 a working AGC reaches in silence.
    This repository has been bitten before by a number with no source
    (`SUPPLY_SETUP.md`, and one destroyed amplifier), so the measurements
    travel with the advice rather than behind it.

    Not gated by `is_simulated`: a bench is exactly where it is wanted,
    and the installation is where the microphones actually are.
    """

    folder = Path(__file__).resolve().parent
    file_name = "DIAGNOSING_A_MICROPHONE.md"
    document_name = "diagnosing a microphone"
