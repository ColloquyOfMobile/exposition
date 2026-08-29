# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/electronics/next_pcb_kicad.py

"""The next board as a netlist KiCad will import, and an audit of it.

`py next_pcb.py` writes `next_pcb.net` beside the three markdown files.
In Pcbnew: **File > Import Netlist**, and 113 footprints arrive with a
ratsnest that came from `drivers/audio.py` rather than from anybody's
memory. Placement and routing are not here and are not generated: one
analogue ground region under the filters and the analysers, joined to
power ground at a single point, with class-D and NeoPixel current kept
out of it, is judgement exercised on a physical thing.

**The design names terminals; a footprint numbers pads, and the two are
not the same list.** `next_pcb.py` deliberately calls the MSGEQ7's
terminals `IN`, `OUT`, `STROBE` and so on rather than numbering them,
because numbering them would be inventing the part. That decision stays
where it is and the translation happens here, in `PADS` - so the design
stays readable and the netlist stays importable, and neither has to
pretend to be the other.

**`audit()` is the part worth having.** It reads the footprint libraries
this machine actually has and answers three questions the netlist cannot
answer for itself: is every footprint findable, does every terminal
correspond to a real pad, and which terminals are known not to have one.
A netlist naming a pad that does not exist imports quietly and leaves a
net unconnected, which is the kind of thing found at the end with a
multimeter. It never raises: a missing library is a fact about a machine,
not an error in the design, and the other computer has different ones.
"""
from __future__ import annotations

import re
import uuid
from datetime import datetime
from pathlib import Path

from . import next_pcb

# A namespace of our own, so the same reference always gets the same UUID.
# Pcbnew matches an imported netlist against what is already on the board
# by timestamp before it falls back to the reference, so stable ones mean
# a re-import updates the board instead of arriving as 113 duplicates.
_NAMESPACE = uuid.UUID("6f9619ff-8b86-d011-b42d-00c04fc964ff")

# Where the design's terminal names differ from the footprint's pad names.
# Both halves are facts rather than preferences: the left is what
# `next_pcb.py` calls the terminal, the right is what the footprint calls
# the pad, read out of the .kicad_mod.
PADS = {
    # The shield brings the Mega's rails out on several pads each. Pad 1
    # of each, arbitrarily and consistently - they are the same copper on
    # the board above.
    ("board", "Arduino Mega 2560"): {"5V": "5V1", "GND": "GND1"},
}

# Terminals that are real connections with no pad to make them on, which
# is not a fault to fix but a fact to state. The U2D2 is a module on a
# mounting outline: its footprint has no pads at all, and its data wire is
# a flying lead to a screw terminal. Saying so here keeps it out of the
# audit's findings without hiding it.
FLYING_LEADS = {("M1", "data"): "the U2D2 is mounted, and its data wire is a lead"}

# The one part whose pads this repository is not entitled to number. The
# BOM says the same thing about its support network: read the pin
# numbering off the datasheet, because a plausible-looking number passing
# for a known one is how a board comes back wrong.
UNNUMBERED = {("analyser", "MSGEQ7")}


def _pad_for(part, pin):
    """The pad name for one terminal of one part, or None if there is not
    one to give."""
    key = (part.kind, part.value)
    if key in UNNUMBERED:
        return None
    return PADS.get(key, {}).get(str(pin), str(pin))


# --- the netlist ----------------------------------------------------------


def _quote(text):
    return '"' + str(text).replace("\\", "\\\\").replace('"', '\\"') + '"'


def netlist_text(design=None, now=None):
    """The whole board in KiCad's netlist s-expression."""
    design = design or next_pcb.Design()
    stamp = (now or datetime.now()).strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "(export (version \"E\")",
        "  (design",
        f"    (source {_quote('next_pcb.py')})",
        f"    (date {_quote(stamp)})",
        f"    (tool {_quote('colloquy next_pcb.py')})",
        "    (sheet (number \"1\") (name \"/\") (tstamps \"/\")",
        "      (title_block",
        f"        (title {_quote('Colloquy of Mobiles - electronic box v2')})",
        f"        (comment (number \"1\") (value {_quote(_PROVENANCE)}))))",
        "  )",
        "  (components",
    ]

    for part in design.parts:
        stamps = uuid.uuid5(_NAMESPACE, part.ref)
        value = f"{part.value} (confirm)" if part.confirm else part.value
        lines += [
            f"    (comp (ref {_quote(part.ref)})",
            f"      (value {_quote(value)})",
            f"      (footprint {_quote(part.footprint)})",
            f"      (description {_quote(part.description)})",
            f"      (tstamps {_quote('/' + str(stamps))}))",
        ]

    lines.append("  )")
    lines.append("  (nets")

    for code, net in enumerate(design.nets, start=1):
        lines.append(f"    (net (code {_quote(code)}) (name {_quote(net.name)})")
        for ref, pin in net.terminals:
            part = _part(design, ref)
            pad = _pad_for(part, pin) if part is not None else str(pin)
            if pad is None:
                continue
            lines.append(f"      (node (ref {_quote(ref)}) (pin {_quote(pad)}))")
        lines.append("    )")

    lines.append("  )")
    lines.append(")")
    return "\n".join(lines) + "\n"


_PROVENANCE = (
    "Generated by next_pcb.py - do not edit. The wiring comes from "
    "colloquy/drivers/audio.py; see NEXT_PCB.md for why each of it is so."
)


def _part(design, ref):
    for part in design.parts:
        if part.ref == ref:
            return part
    return None


# --- the audit ------------------------------------------------------------


class Finding:
    """One thing wrong, or one thing worth saying, about the netlist."""

    def __init__(self, kind, subject, detail):
        self.kind = kind
        self.subject = subject
        self.detail = detail

    def __repr__(self):
        return f"{self.kind}: {self.subject} - {self.detail}"


def library_paths():
    """Every footprint library this machine has, as nickname -> folder.

    Read out of KiCad's own tables, and empty rather than raised when
    there are none - CI has no KiCad on it, and the audit is a
    convenience for whoever is about to import the file, not a gate on
    generating it.
    """
    found = {}
    tables = [
        Path.home() / "AppData/Roaming/kicad/9.0/fp-lib-table",
        Path.home() / ".config/kicad/9.0/fp-lib-table",
    ]
    pattern = re.compile(r'\(name "([^"]+)"\).*?\(uri "([^"]+)"\)')
    for table in tables:
        try:
            text = table.read_text(encoding="utf-8")
        except OSError:
            continue
        for name, uri in pattern.findall(text):
            found[name] = Path(_expand(uri))

    # PCM packages are not always written into the table, so look where
    # the plugin manager puts them as well.
    for third_party in (
        Path.home() / "Documents/KiCad/9.0/3rdparty/footprints",
    ):
        if not third_party.is_dir():
            continue
        for package in third_party.iterdir():
            for pretty in package.glob("*.pretty"):
                found.setdefault(f"PCM_{pretty.stem}", pretty)
    return found


def _expand(uri):
    return (
        uri.replace("${KIPRJMOD}", ".")
        .replace("${KICAD9_FOOTPRINT_DIR}",
                 "C:/Program Files/KiCad/9.0/share/kicad/footprints")
        .replace("${KICAD9_3RD_PARTY}",
                 str(Path.home() / "Documents/KiCad/9.0/3rdparty"))
    )


def pads_of(footprint, libraries=None):
    """Every pad name in a footprint, or None if it cannot be found."""
    libraries = library_paths() if libraries is None else libraries
    if ":" not in footprint:
        return None
    nickname, name = footprint.split(":", 1)
    folder = libraries.get(nickname)
    if folder is None:
        return None
    path = folder / f"{name}.kicad_mod"
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return None
    return set(re.findall(r'\(pad "([^"]*)"', text))


def audit(design=None, libraries=None):
    """What would go wrong on import, before it does.

    Three kinds of finding, and only the first two are faults:
    `missing library` (KiCad here cannot find the footprint at all),
    `no such pad` (the netlist names a pad the footprint does not have,
    which imports quietly and leaves the net unconnected), and `not
    numbered` (a part whose pads this repository will not invent - the
    MSGEQ7, whose numbering has to come off its datasheet).
    """
    design = design or next_pcb.Design()
    libraries = library_paths() if libraries is None else libraries
    findings = []

    cache = {}
    for part in design.parts:
        if part.footprint not in cache:
            cache[part.footprint] = pads_of(part.footprint, libraries)

    for footprint, pads in sorted(cache.items()):
        if pads is None:
            findings.append(
                Finding("missing library", footprint,
                        "not found in this machine's footprint libraries")
            )

    for net in design.nets:
        for ref, pin in net.terminals:
            part = _part(design, ref)
            if part is None:
                continue
            if (ref, str(pin)) in FLYING_LEADS:
                continue
            if (part.kind, part.value) in UNNUMBERED:
                findings.append(
                    Finding("not numbered", f"{ref}.{pin}",
                            f"on net {net.name} - number it off the datasheet")
                )
                continue
            pads = cache[part.footprint]
            if pads is None:
                continue
            pad = _pad_for(part, pin)
            if pad not in pads:
                findings.append(
                    Finding("no such pad", f"{ref}.{pin}",
                            f"{part.footprint} has no pad {pad!r} "
                            f"(net {net.name})")
                )
    return findings
