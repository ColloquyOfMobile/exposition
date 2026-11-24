# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/installation_sol2/progress.py

"""What has been done of the installation of PCB solution 2: the record,
its file format, and how two copies of it become one. Pure.

A record is, per step key, whether it is done (and when that was said)
and the person's note (and when that was written). The two halves are
separate because they are said separately: ticking a step must not wipe
a note, and a note must not untick a step.

**Two copies meet** whenever the laptop's push finds origin moved on, and
whenever a page reads both the local branch and origin's. They are merged
half by half, the later word winning - which is also how `not done after
all` beats an earlier `done`. Nothing is ever lost by a merge except a
word somebody has since replaced.

Times are ISO strings in the laptop's local time, which sort as text.
Everything read is read defensively: the file is on a branch anybody can
push to, and a render that raises emergency-stops the installation.
"""
import json
from collections.abc import Mapping
from typing import Final, NamedTuple

FORMAT: Final = 1
# Where the record lives in the branch's tree.
FILE_NAME: Final = "progress.json"


class Entry(NamedTuple):
    done: bool = False
    done_at: str = ""
    note: str = ""
    note_at: str = ""


Record = dict[str, Entry]


def _text(value: object) -> str:
    return value if isinstance(value, str) else ""


def parse(text: str | None) -> Record:
    """A file's text -> a record. Anything unreadable is an empty record,
    and any entry that is not a dict is left out."""
    if not text:
        return {}
    try:
        data = json.loads(text)
    except ValueError:
        return {}
    steps = data.get("steps") if isinstance(data, Mapping) else None
    if not isinstance(steps, Mapping):
        return {}
    record: Record = {}
    for key, raw in steps.items():
        if not isinstance(key, str) or not isinstance(raw, Mapping):
            continue
        record[key] = Entry(
            done=raw.get("done") is True,
            done_at=_text(raw.get("done at")),
            note=_text(raw.get("note")),
            note_at=_text(raw.get("note at")),
        )
    return record


def dump(record: Record) -> str:
    """A record -> the file's text. ASCII only (`ensure_ascii`), so it
    survives any console code page git is run under; keys sorted, so two
    equal records are byte-equal and a no-change write makes no commit."""
    steps = {
        key: {
            "done": entry.done,
            "done at": entry.done_at,
            "note": entry.note,
            "note at": entry.note_at,
        }
        for key, entry in sorted(record.items())
    }
    return json.dumps({"format": FORMAT, "steps": steps}, indent=2, sort_keys=True) + "\n"


def merge(*records: Record) -> Record:
    """Several copies -> one, each half of each entry the latest said."""
    merged: Record = {}
    for record in records:
        for key, entry in record.items():
            old = merged.get(key, Entry())
            done, done_at = (
                (entry.done, entry.done_at)
                if entry.done_at > old.done_at
                else (old.done, old.done_at)
            )
            note, note_at = (
                (entry.note, entry.note_at)
                if entry.note_at > old.note_at
                else (old.note, old.note_at)
            )
            merged[key] = Entry(done, done_at, note, note_at)
    return merged


def mark(record: Record, key: str, done: bool, at: str) -> Record:
    """A copy with one step ticked or unticked."""
    old = record.get(key, Entry())
    return {**record, key: old._replace(done=done, done_at=at)}


def annotate(record: Record, key: str, note: str, at: str) -> Record:
    """A copy with one step's note replaced."""
    old = record.get(key, Entry())
    return {**record, key: old._replace(note=note, note_at=at)}


def next_step(record: Record, keys: tuple[str, ...]) -> str | None:
    """The first step, in order, not done; None when all are."""
    for key in keys:
        if not record.get(key, Entry()).done:
            return key
    return None
