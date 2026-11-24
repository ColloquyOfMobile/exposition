# -*- coding: utf-8 -*-
# Source code/Python/colloquy/virtual_drivers/room.py

"""The room the simulation stands in, from TJ's Rhino model. Pure.

`room.json` is what `export_room.py` took out of the model (which is not
in git): each body's axis seen from above, in millimetres, and what each
looks like from above in its own frame. Three females 120° apart about
1.75 m out, two males at the ends of the bar 180° apart, 648 mm out - so
as the bar turns, a male meets a female every 60° and the two males take
turns: male1, male2, male1, ...

**Names.** The model names no female; it is one female copied round the
circle. Which copy is female1, 2 and 3 comes from the calibration:
female1 is the one male1 faces at `interaction_origins[male1][female1]`
(the bar's zero is only ever defined against the room through that
entry), and of the two ways round for female2 and female3, the one that
agrees with more of the six calibrated meetings is taken.

**Which way round.** Angles here grow clockwise seen from above, and the
bar's positive turn is drawn that way. Nothing recorded says which way
the servo actually turns the bar; if it is the other way, the drawing is
the room's mirror image. Nothing below depends on it: every conclusion
holds either way round.

**The check.** `meetings()` says, for each calibrated meeting, who the
model puts face to face at that bar angle. The geometry forces the males
to alternate; a table in which one male meets all three females inside
126° of bar travel cannot be right about all of them.
"""
from __future__ import annotations

import json
from typing import Any
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

ROOM_JSON = Path(__file__).with_name("room.json")

FEMALES = ("female1", "female2", "female3")
MALES = ("male1", "male2")

Table = dict[tuple[str, str], float]


@lru_cache(maxsize=1)
def load() -> dict:
    """room.json, read once: it changes only when the generator runs."""
    return json.loads(ROOM_JSON.read_text(encoding="utf-8"))


def _number(value: Any, fallback: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return fallback
    return number if number == number else fallback  # NaN


def table(params: Any) -> Table:
    """`interaction_origins` as (male, female) -> degrees of the bar, read
    defensively: params are hand-editable and a render must never raise.
    A missing or broken entry is the default's."""
    from colloquy.params import DEFAULTS

    bar_defaults: Any = DEFAULTS["bar"]
    defaults = bar_defaults["interaction_origins"]
    try:
        origins: Any = params["bar"]["interaction_origins"]
    except (KeyError, TypeError, IndexError):
        origins = defaults
    result: Table = {}
    for male in MALES:
        for female in FEMALES:
            fallback = float(defaults[male][female])
            try:
                value = origins[male][female]
            except (KeyError, TypeError, IndexError):
                value = fallback
            result[(male, female)] = _number(value, fallback)
    return result


def gap(a: float, b: float) -> float:
    """How far apart two angles are, the short way round."""
    return abs((a - b + 180) % 360 - 180)


@dataclass(frozen=True)
class Placement:
    """The room with names on it, in the drawing's frame: angles clockwise
    from female1, seen from above."""

    females: dict[str, dict]  # name -> her record in room.json
    males: dict[str, dict]
    at: dict[str, float]  # female -> where she is, degrees from female1
    offset: dict[str, float]  # male -> where he is on the bar, from male1
    anchor: float  # the bar angle at which male1 faces female1
    agreeing: int = 0  # how many calibrated meetings this order fits
    bar: dict = field(default_factory=dict)

    def radius(self, body: str) -> float:
        record = self.females.get(body) or self.males[body]
        x, y = record["axis"]
        return float((x * x + y * y) ** 0.5)

    def meeting(self, male: str, female: str) -> float:
        """The bar angle, in [0, 360), at which the model has this male
        facing this female."""
        return (self.at[female] + self.anchor - self.offset[male]) % 360

    def nearest(self, bar_angle: float) -> tuple[str, str, float]:
        """Who the model puts face to face nearest this bar angle, and how
        far off it is."""
        return min(
            (
                (male, female, gap(bar_angle, self.meeting(male, female)))
                for male in MALES
                for female in FEMALES
            ),
            key=lambda found: found[2],
        )


def _fits(placement: Placement, calibrated: Table) -> tuple[int, float]:
    agreeing, off = 0, 0.0
    for (male, female), bar_angle in calibrated.items():
        found = placement.nearest(bar_angle)
        if found[:2] == (male, female):
            agreeing += 1
        off += found[2]
    return agreeing, off


def place(params: Any, room: dict | None = None) -> Placement:
    """Put names on the model's bodies, from the calibration."""
    room = room if room is not None else load()
    calibrated = table(params)
    anchor = calibrated[("male1", "female1")]

    # Female1 is the copy at the top of the model (any copy would do: they
    # are one female turned round the circle); the drawing is turned so
    # that she is at the top of it too.
    copies = sorted(room["females"], key=lambda f: f["at"])
    first, others = copies[0], copies[1:]
    males = sorted(room["males"], key=lambda m: m["at"])
    offset = {
        "male1": 0.0,
        "male2": (float(males[1]["at"]) - float(males[0]["at"])) % 360,
    }

    def relative(record: dict) -> float:
        return (float(record["at"]) - float(first["at"])) % 360

    best: Placement | None = None
    best_fit: tuple[int, float] = (-1, 0.0)
    for second, third in (others, others[::-1]):
        candidate = Placement(
            females={"female1": first, "female2": second, "female3": third},
            males={"male1": males[0], "male2": males[1]},
            at={
                "female1": 0.0,
                "female2": relative(second),
                "female3": relative(third),
            },
            offset=offset,
            anchor=anchor,
            bar=room.get("bar", {}),
        )
        agreeing, off = _fits(candidate, calibrated)
        # More meetings agreeing wins; then less error in all six; then
        # the first way round tried.
        if agreeing > best_fit[0] or (agreeing == best_fit[0] and off < best_fit[1]):
            best, best_fit = candidate, (agreeing, off)
    assert best is not None
    return Placement(
        females=best.females,
        males=best.males,
        at=best.at,
        offset=best.offset,
        anchor=best.anchor,
        agreeing=best_fit[0],
        bar=best.bar,
    )


@dataclass(frozen=True)
class Meeting:
    """One calibrated meeting, held against the model."""

    male: str
    female: str
    bar_angle: float  # what the calibration says
    faces: tuple[str, str]  # who the model has face to face nearest there
    off: float  # how far that meeting is from bar_angle

    @property
    def agrees(self) -> bool:
        return self.faces == (self.male, self.female)

    def describe(self) -> str:
        where = f"{self.bar_angle:.2f}°"
        if self.agrees:
            return f"{where}: agrees with the model ({self.off:.1f}° off)"
        male, female = self.faces
        return (
            f"{where}: the model has {male} facing {female} there "
            f"({self.off:.1f}° off), and {self.male} facing nobody"
            if male != self.male
            else f"{where}: the model has {male} facing {female} there ({self.off:.1f}° off)"
        )


def meetings(placement: Placement, params: Any) -> list[Meeting]:
    """Every calibrated meeting, with what the model says happens there."""
    found = []
    for (male, female), bar_angle in table(params).items():
        faces_male, faces_female, off = placement.nearest(bar_angle)
        found.append(Meeting(male, female, bar_angle, (faces_male, faces_female), off))
    return found
