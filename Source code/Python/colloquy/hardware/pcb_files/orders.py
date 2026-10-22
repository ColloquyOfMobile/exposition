# -*- coding: utf-8 -*-
# Source code/Python/colloquy/hardware/pcb_files/orders.py

"""Ordering the PCBs at JLCPCB, one instruction page per step.

Every board in the fabrication manifest has an order status, shown on its
card on the home page:

- **waiting order** - nobody has put it in a cart yet (the default);
- **in the cart** - its five steps were walked and JLC's form saved it;
- **ordered** - the cart it was in has been paid for;
- **error** - a step went wrong, with the person's note and, if they gave
  one, a screenshot.

`order now` walks every board still waiting or in error through the same
five steps - upload the Gerbers, check the order options, upload the BOM
and CPL, anything else worth checking, put it in the cart - with the
board's preview at the top of every page. Each step has `next` and
`something went wrong`; the second takes a note and a screenshot, marks
the board as error and goes on to the next board, because one board that
cannot be ordered is no reason to hold up the rest. The walk ends on the
cart page, which marks everything in the cart as ordered at once: the
cart is paid once, for all of it.

The statuses are notes in `params["pcb orders"]`, one record per board,
written only by a press on these pages. That makes them this machine's:
a board put in the cart from the bench machine is still waiting on the
laptop. Screenshots go beside the logs under `local/`.

Routes, not tree commands (`/pcb-order/...`, see `server2/wsgi2.py`): the
pages are the ordering's own, a press has to land on the *next* page
rather than re-render a node, and a screenshot needs a multipart form,
which the tree's POST does not take. They are answered whether or not the
main PCB is in the rack - the board being out is when they matter most.
**Nothing raised in here may leave `response()`**: outside a command, an
exception emergency-stops the installation.

What to set on JLC's form is said with where it comes from: the manifest
for what was plotted, the package for what is placed, and the designs'
own documents (`CHECKS`, step 4) for what is still open. A requirement
nobody has decided - the finish, the copper weight - is said as a choice
to make and note, not made here.

Stdlib only, like the rest of `pcb_files` - see `__init__.py`.
"""
from __future__ import annotations

import csv
import email.parser
import email.policy
import io
import json
import re
import zipfile
from collections.abc import Callable, Mapping, MutableMapping
from dataclasses import dataclass
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs

from . import catalog, gerbers

PARAMS_KEY = "pcb orders"
ROUTE = "/pcb-order"

WAITING = "waiting order"
IN_CART = "in the cart"
ORDERED = "ordered"
ERROR = "error"
STATUSES = (WAITING, IN_CART, ORDERED, ERROR)
# What `order now` walks: everything that is not in a cart or bought.
TO_ORDER = (WAITING, ERROR)

STEPS = (
    "Upload the Gerbers",
    "Check the order options",
    "Upload the BOM and CPL",
    "Anything else to check",
    "Put it in the cart",
)

QUOTE_PAGE = "https://cart.jlcpcb.com/quote"
# Asked for with this order (2026-10-21); every board, the same.
COLOUR = "White"

# A screenshot of a browser window is a few hundred kilobytes; this is
# only there so that a wrong file cannot fill the disk.
MAX_UPLOAD_BYTES = 20 << 20
IMAGE_TYPES = {"png": "image/png", "jpg": "image/jpeg", "gif": "image/gif", "webp": "image/webp"}
SCREENSHOT_NAME = re.compile(r"[a-z0-9-]+-\d{8}-\d{6}(-\d+)?\.(png|jpg|gif|webp)")

# Step 4, per board: (what to check, where it is said). The documents are
# relative to CAD/KiCad, and a test holds every one to a file that exists
# and every board in the manifest to an entry here - a new board gets its
# reminders written, not an empty page.
_REVIEW = "proposed-solutions/shields/RELEASE_REVIEW.md"
_SHIELDS_README = "production/assembly/{board}/README-JLCPCB.md"
CHECKS: dict[str, tuple[tuple[str, str], ...]] = {
    "backplane": (
        ("The mirrored Mega slot: print the front copper and Edge.Cuts at 1:1, "
         "lay a real Mega on it component side down, and check every header pin "
         "and all four holes. A wrong mirror swaps every pin - the costliest "
         "mistake in the set.", f"{_REVIEW} 2.2"),
        ("+12 V (servo supply) runs on the outer layers: compare the worst-case "
         "servo current with the outer copper weight chosen in step 2.", f"{_REVIEW} 2.2"),
        ("4 layers at 210 x 297 mm drives the cost of the whole order: look at "
         "its price before the others.", f"{_REVIEW} 3"),
        ("C1, the 470 uF electrolytic, is the likeliest extended-library part: "
         "its stock and setup fee.", f"{_REVIEW} 3"),
        ("RP1-RP11 are the provisional 10K calibration population; assembling "
         "them fixes that value on the board.", _SHIELDS_README),
    ),
    "teensy-adapter": (
        ("Step 2 of the shields plan: the exhibition depends on step 1 alone, "
         "so this one can wait. Skip it if it is not in this order.", f"{_REVIEW} 1"),
        ("CM1-CM5 sit beside the Teensy socket, clear of its body.", f"{_REVIEW} 2.6"),
        ("The Teensy stands tallest: its height against the enclosure.", f"{_REVIEW} 2.6"),
        ("U1-U4 (TSSOP-14, 0.65 mm pitch): pin 1 on its mark in JLC's placement "
         "preview.", _SHIELDS_README),
    ),
    "voice-thomas": (
        ("All components are through-hole, including R3 (100K axial, 7.62 mm pitch). "
         "PCB Assembly off: order the cards bare and hand fit the parts.",
         "JLCPCB_ASSEMBLY.md; proposed-solutions/shields/MANUFACTURING.md"),
        ("Five are drawn, one per body; the review suggests spares and cards for "
         "new pitches.", f"{_REVIEW} 1"),
        ("R1/R2 at 7.62 mm pitch, C1/C2 at 5 mm: the envelope (7 x 6.5 mm) "
         "against the film capacitors you will actually buy, 470 nF included.",
         f"{_REVIEW} 2.3"),
        ("Board-setup track and clearance minimums are 0.15 mm (F6 resolved). "
         "The regenerated package must pass DRC with these floors.", f"{_REVIEW} 0"),
    ),
    "analyser-carrier": (
        ("Print mounting-template.svg at 100 %, check its 50 mm scale bar, and "
         "lay one converted module on it: all eight pins and both holes. The "
         "socket positions are photo-derived.", f"{_REVIEW} 2.4"),
        ("No SMD part: PCB Assembly off, ordered bare.", "JLCPCB_ASSEMBLY.md"),
        ("Board-setup track and clearance minimums are 0.15 mm (F6 resolved). "
         "The regenerated package must pass DRC with these floors.", f"{_REVIEW} 0"),
    ),
    "microphone-flex": (
        ("The microphone holders belong to no step of the shields plan yet: "
         "decide whether they are in this order.", f"{_REVIEW} 1"),
        ("Measure a real violet MAX9814 module: pin pitch, the 10.033 mm hole "
         "spacing, the header offset and the seated height (11.04 mm nominal).",
         f"{_REVIEW} 2.5"),
        ("J1 is GND / +5V / OUT, pin 1 to pin 1 with the existing harness.", f"{_REVIEW} 2.5"),
        ("The M5 slots 50 mm apart, against the actual extrusion profile.", f"{_REVIEW} 2.5"),
    ),
    "female-base-v2": (
        ("Physical fit still blocks the body boards (F8): measure a real GF1002 "
         "and the socket/header stack, read the ROUT pair polarity off the module "
         "(M1 pins 10/11 are provisional), and confirm the module bonds input G "
         "to power minus. If that bond is absent, stop.", f"{_REVIEW} F8"),
        ("The pot stands about 28 mm above the board and its shaft overhangs "
         "the left edge by about 16 mm: check both inside a female body.",
         "proposed-solutions/female base v2/README.md"),
        ("C1, 220 uF, is a provisional value; assembling it fixes it on the board.",
         _SHIELDS_README),
    ),
    "male-static-v2": (
        ("Physical fit still blocks the body boards (F8): measure a real GF1002 "
         "and the socket/header stack, read the ROUT pair polarity off the module "
         "(M1 pins 10/11 are provisional), and confirm the module bonds input G "
         "to power minus. If that bond is absent, stop.", f"{_REVIEW} F8"),
        ("The pot stands about 28 mm above the board: check it, and the H1/H2 "
         "supports, inside a male body.", "proposed-solutions/male static v2/README.md"),
        ("C1, 220 uF, is a provisional value; assembling it fixes it on the board.",
         _SHIELDS_README),
    ),
}
# Every board, after its own.
COMMON_CHECKS = (
    ("In JLC's Gerber viewer rather than KiCad: every layer there, the outline "
     "closed, the drills in their pads, no silkscreen on a pad.", f"{_REVIEW} 2.1"),
    ("Polarity marks visible on the silkscreen: + and - beside the pads of "
     "every electrolytic, diode and LED, and pin 1.", f"{_REVIEW} 2.1"),
)

STYLE = (
    "body { font-family: system-ui, sans-serif; margin: 0; "
    "padding: 0.75rem 2ch 2rem; line-height: 1.4; } "
    ".furniture { display: flex; gap: 2ch; font-size: 0.9rem; flex-wrap: wrap; } "
    ".board { display: flex; gap: 2ch; align-items: center; flex-wrap: wrap; "
    "border-bottom: 1px solid #8886; padding: 0.5rem 0 0.75rem; } "
    ".board img { width: 300px; max-width: 100%; height: 200px; object-fit: contain; } "
    ".board h1 { margin: 0; font-size: 1.5rem; } "
    ".board p { margin: 0.2rem 0; } "
    ".progress { opacity: 0.7; } "
    "ol.steps { display: flex; flex-wrap: wrap; gap: 0.5ch 2ch; list-style: none; "
    "padding: 0; margin: 0.75rem 0; font-size: 0.9rem; } "
    "ol.steps li { opacity: 0.6; } "
    "ol.steps li.now { opacity: 1; font-weight: bold; text-decoration: underline; } "
    ".step { max-width: 100ch; } "
    ".step h2 { font-size: 1.2rem; margin: 0.5rem 0; } "
    "table { border-collapse: collapse; margin: 0.5rem 0; font-size: 0.9rem; } "
    "th, td { border-bottom: 1px solid #8884; padding: 0.25rem 2ch 0.25rem 0; "
    "text-align: left; vertical-align: top; } "
    "th { font-weight: normal; opacity: 0.7; } "
    ".why { opacity: 0.7; } "
    ".source { opacity: 0.6; font-size: 0.85rem; } "
    "ul.checks { list-style: none; padding: 0; } "
    "ul.checks li { margin: 0.4rem 0; } "
    "a.button, button { display: inline-block; padding: 0.5rem 2ch; "
    "border: 2px solid currentColor; border-radius: 6px; font: inherit; "
    "font-weight: bold; text-decoration: none; margin: 0.4rem 1ch 0.4rem 0; "
    "background: none; color: inherit; cursor: pointer; } "
    ".actions { display: flex; flex-wrap: wrap; align-items: center; gap: 1ch; "
    "margin: 1rem 0; } "
    ".small { font-size: 0.85rem; opacity: 0.75; } "
    ".problem { color: #d02; font-weight: bold; } "
    "details.error { border: 1px solid #d026; border-radius: 6px; "
    "padding: 0.5rem 2ch; margin: 1.5rem 0; max-width: 100ch; } "
    "details.error summary { color: #d02; font-weight: bold; cursor: pointer; } "
    "textarea { width: 100%; min-height: 6rem; font: inherit; box-sizing: border-box; } "
    ".shot { max-width: 100%; max-height: 24rem; border: 1px solid #8886; display: block; }"
)


class OrderError(Exception):
    """A press that cannot be done, said in one sentence on a page."""


def _now() -> datetime:
    return datetime.now()


# --- the records ------------------------------------------------------


def book_of(owner: object) -> MutableMapping[str, Any] | None:
    """The order records kept in `owner.params`, or None where there are none.

    None on the mock and on a test double, which have no params: the
    catalog is then drawn as it always was, with no status and no order.
    """
    try:
        params = getattr(owner, "params")
        book = params.get(PARAMS_KEY)
        if book is None:
            params[PARAMS_KEY] = {}
            book = params[PARAMS_KEY]
        return book if isinstance(book, MutableMapping) else None
    except Exception:  # noqa: BLE001 - asked while drawing a page
        return None


def record(book: Mapping[str, Any] | None, board_id: str) -> dict[str, Any]:
    """One board's record, read defensively: params.json is hand-editable.

    A status this module does not know is read as an error, not as
    waiting: a hand-typed "Ordered" must not put a bought board back into
    the next walk.
    """
    try:
        entry = book.get(board_id) if book is not None else None
    except Exception:  # noqa: BLE001 - see the docstring
        entry = None
    if entry is None:
        return {"status": WAITING}
    if not isinstance(entry, Mapping):
        return {"status": ERROR, "note": f"unreadable record in params: {entry!r}"}
    found = dict(entry)
    if found.get("status") not in STATUSES:
        found["note"] = f"unknown status {found.get('status')!r} in params"
        found["status"] = ERROR
    return found


def status_of(book: Mapping[str, Any] | None, board_id: str) -> str:
    return str(record(book, board_id)["status"])


def _write(book: MutableMapping[str, Any] | None, board: gerbers.Board, status: str,
           **fields: Any) -> None:
    if book is None:
        raise OrderError("this server keeps no order records (no params)")
    book[board.id] = {
        "status": status,
        "changed at": _now().isoformat(timespec="seconds"),
        **fields,
    }


def _walk(boards: tuple[gerbers.Board, ...], book: Mapping[str, Any] | None) -> list[gerbers.Board]:
    return [board for board in boards if status_of(book, board.id) in TO_ORDER]


def next_url(boards: tuple[gerbers.Board, ...], book: Mapping[str, Any] | None,
             after: gerbers.Board | None = None) -> str:
    """Where the walk goes next: the first board after `after` still to
    order, in manifest order, or the cart once there is none."""
    start = boards.index(after) + 1 if after is not None else 0
    for board in boards[start:]:
        if status_of(book, board.id) in TO_ORDER:
            return f"{ROUTE}/{board.id}/1"
    return f"{ROUTE}/done"


# --- the package, as the steps need it --------------------------------


@dataclass(frozen=True)
class Package:
    """What the steps say about one board's checked production package."""

    smd_count: int
    bom: tuple[dict[str, str], ...]
    sides: tuple[str, ...]
    hand_fitted: int


def _rows(data: bytes) -> list[dict[str, str]]:
    return list(csv.DictReader(io.StringIO(data.decode("utf-8-sig"))))


def package(board: gerbers.Board) -> Package:
    """Raises `gerbers.PackageError` when the package cannot be offered."""
    content = catalog.production_bytes(board)
    with zipfile.ZipFile(io.BytesIO(content)) as archive:
        recorded = json.loads(archive.read("manifest.json"))
        bom = _rows(archive.read("BOM.csv"))
        cpl = _rows(archive.read("CPL.csv"))
        names = set(archive.namelist())
        manual = _rows(archive.read("manual-and-DNP.csv")) if "manual-and-DNP.csv" in names else []
    return Package(
        smd_count=int(recorded.get("smd_count") or len(cpl)),
        bom=tuple(bom),
        sides=tuple(sorted({row.get("Layer", "") for row in cpl})),
        hand_fitted=len(manual),
    )


# --- pieces of page ---------------------------------------------------


# Inline rather than a class: the cards are drawn on the installation's
# home page, which has no stylesheet of its own.
_COLOURS = {IN_CART: "#08a", ORDERED: "#080", ERROR: "#d02"}


def _status_words(found: Mapping[str, Any], board: gerbers.Board) -> str:
    """The status as a short HTML sentence, with what goes with it."""
    status = str(found["status"])
    words = f'<strong style="color:{_COLOURS.get(status, "inherit")}">{escape(status)}</strong>'
    when = str(found.get("changed at") or "").replace("T", " ")
    if when and status != WAITING:
        words += f" since {escape(when)}"
    if found.get("order number"):
        words += f", JLC order {escape(str(found['order number']))}"
    if status in (IN_CART, ORDERED) and found.get("pcb") and found["pcb"] != board.source_sha256:
        words += " - <strong>for an earlier revision: the PCB has changed since</strong>"
    return words


def _error_details(found: Mapping[str, Any], picture: bool = False) -> str:
    """The note of a board in error, and its screenshot as a link or,
    with `picture`, drawn."""
    if found["status"] != ERROR:
        return ""
    parts = []
    if found.get("step"):
        parts.append(f'<p>at step {escape(str(found["step"]))}: '
                     f'{escape(str(found.get("step title") or ""))}</p>')
    if found.get("note"):
        parts.append(f'<p>{escape(str(found["note"]))}</p>')
    if found.get("screenshot"):
        href = f'{ROUTE}/screenshot/{escape(str(found["screenshot"]), quote=True)}'
        if picture:
            parts.append(f'<a href="{href}"><img class="shot" src="{href}" alt="screenshot"></a>')
        else:
            parts.append(f'<p><a href="{href}">screenshot</a></p>')
    return "".join(parts)


def catalog_html(book: MutableMapping[str, Any] | None) -> str:
    """The home page's PCB section, with each card's order status and the
    `order now` that walks them. Without records, the plain catalog."""
    if book is None:
        return str(catalog.html())

    def card(board: gerbers.Board) -> str:
        try:
            found = record(book, board.id)
            return (f'<div name="order status"><p>order: {_status_words(found, board)}</p>'
                    f"{_error_details(found)}</div>")
        except Exception as error:  # noqa: BLE001 - the home page must not raise
            return f'<p name="order status">order status unreadable: {escape(str(error))}</p>'

    lead = (
        '<p name="order now">'
        f'<a href="{ROUTE}" style="font-weight:bold;padding:0.25rem 1ch;border:2px solid currentColor;'
        'border-radius:6px;text-decoration:none">order now</a> '
        'walks every PCB still waiting (or in error) through the JLCPCB order, one page per step. '
        f'<a href="{ROUTE}/done">the cart</a></p>'
    )
    return str(catalog.html(card_extra=card, lead=lead))


def _page(title: str, body: str) -> bytes:
    return (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\">"
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        f"<title>{escape(title)}</title><style>{STYLE}</style></head><body>"
        '<div name="server commands" class="furniture">'
        '<a href="/">home</a>'
        f'<a href="{ROUTE}">order now</a>'
        f'<a href="{ROUTE}/done">the cart</a>'
        "</div>"
        f"{body}</body></html>"
    ).encode("utf-8")


def _html(status: str, title: str, body: str) -> tuple[str, list[tuple[str, str]], bytes]:
    headers = [("Content-Type", "text/html; charset=utf-8"), ("Cache-Control", "no-store")]
    return status, headers, _page(title, body)


def _redirect(location: str) -> tuple[str, list[tuple[str, str]], bytes]:
    return "303 See Other", [("Location", location), ("Cache-Control", "no-store")], b""


def _board_header(board: gerbers.Board, boards: tuple[gerbers.Board, ...],
                  book: Mapping[str, Any] | None, step: int) -> str:
    found = record(book, board.id)
    return (
        '<div class="board" name="board">'
        f'<a href="/pcb/{board.id}/preview" target="_blank"><img src="/pcb/{board.id}/preview" '
        f'alt="{escape(board.title, quote=True)} 3D model at 45 degrees"></a>'
        "<div>"
        f'<p class="progress">PCB {boards.index(board) + 1} of {len(boards)} · '
        f"step {step} of {len(STEPS)}</p>"
        f"<h1>{escape(board.title)}</h1>"
        f'<p class="why">{escape(board.what)}</p>'
        f"<p>{board.copper_layers} copper layers · {escape(board.size)} · "
        f"{board.quantity} needed</p>"
        f'<p name="status">order: {_status_words(found, board)}</p>'
        "</div></div>"
        '<ol class="steps">'
        + "".join(
            f'<li class="{"now" if number == step else ""}">'
            f'<a href="{ROUTE}/{board.id}/{number}">{number}. {escape(name)}</a></li>'
            for number, name in enumerate(STEPS, 1)
        )
        + "</ol>"
    )


def _error_form(board: gerbers.Board, step: int, is_open: bool) -> str:
    return (
        f'<details class="error" name="something went wrong"{" open" if is_open else ""}>'
        "<summary>Something went wrong on this step</summary>"
        f'<form method="post" action="{ROUTE}/{board.id}/error" enctype="multipart/form-data">'
        f'<input type="hidden" name="step" value="{step}">'
        '<p><label>What happened (this is what the next attempt starts from)<br>'
        '<textarea name="note" required></textarea></label></p>'
        '<p><label>Screenshot, if it helps<br>'
        '<input type="file" name="screenshot" accept="image/png,image/jpeg,image/gif,image/webp">'
        "</label></p>"
        '<p class="small">On Windows, Win+PrtScn saves the whole screen to Pictures\\Screenshots; '
        "Win+Shift+S cuts out part of it.</p>"
        f"<button type=\"submit\">mark the {escape(board.title)} as error and go to the next PCB</button>"
        "</form></details>"
    )


def _table(rows: list[tuple[str, str, str]]) -> str:
    return (
        "<table><tr><th>on JLC's form</th><th>set to</th><th>why</th></tr>"
        + "".join(
            f"<tr><td>{escape(option)}</td><td><strong>{escape(value)}</strong></td>"
            f'<td class="why">{escape(why)}</td></tr>'
            for option, value, why in rows
        )
        + "</table>"
    )


def _mm(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


# --- the five steps ---------------------------------------------------


def _upload_gerbers(board: gerbers.Board, found: Package) -> str:
    return (
        f'<p>On <a href="{QUOTE_PAGE}" target="_blank" rel="noopener">JLCPCB\'s quote page</a> '
        "(logged in, in another tab), press <strong>Add gerber file</strong> and give it this "
        "zip as it is - do not unzip it:</p>"
        f'<p><a class="button" href="/pcb/{board.id}/gerbers">Gerbers of the {escape(board.title)} (.zip)</a></p>'
        "<p>Once JLC has read it, its form and viewer should say:</p>"
        + _table([
            ("Layers", str(board.copper_layers), "plotted from the board (the manifest)"),
            ("Dimensions", board.size, "read off the outline; check it, do not type it"),
        ])
        + "<p>and the viewer should look like the preview above: the same outline and "
        "cut-outs, the holes in their pads. Another size, a missing layer or a refused "
        "upload is <em>something went wrong</em> below.</p>"
    )


def _order_options(board: gerbers.Board, found: Package) -> str:
    rows = [
        ("Base Material", "FR-4", "the form's default; the board specifies no other"),
        ("Layers", str(board.copper_layers), "as plotted"),
        ("Dimensions", board.size, "from the Gerbers"),
        ("PCB Qty", f"at least {board.quantity}",
         f"the piece needs {board.quantity}: the smallest quantity the form offers at or above it"),
        ("Different Design", "1", "one board per upload"),
        ("Delivery Format", "Single PCB", "the board is not panelised"),
        ("PCB Thickness", f"{_mm(board.thickness_mm)} mm", "as drawn (the manifest)"),
        ("PCB Color", COLOUR, "chosen for this order"),
        ("Silkscreen", "Black", "follows from a white mask; check that it says so"),
        ("Surface Finish", "decide, and note it",
         "HASL, lead-free HASL or ENIG: RELEASE_REVIEW.md 3 leaves it to the order"),
    ]
    if board.id == "backplane":
        rows.append(("Outer Copper Weight", "1 oz or 2 oz",
                     "+12 V servo copper: compare the worst-case servo current (RELEASE_REVIEW.md 2.2)"))
    else:
        rows.append(("Outer Copper Weight", "1 oz", "the form's default; nothing on it asks for more"))
    if board.copper_layers >= 4:
        rows.append(("Specify Stackup / Impedance Control", "the maker's standard 4-layer stack-up, no impedance control",
                     "RELEASE_REVIEW.md 3: the maker's standard 4-layer stack-up, 1.6 mm"))
    rows += [
        ("Min via hole size / diameter", f"smallest hole {_mm(board.smallest_drill_mm)} mm",
         "0.3 mm drill and 0.6 mm via are JLC's standard process (RELEASE_REVIEW.md 0): "
         "the price must not carry an advanced-process charge"),
        ("Mark on PCB", "decide",
         "JLC prints its order number on the silkscreen unless told where, or to leave it off"),
        ("Gold fingers, castellated holes, edge plating", "No", "none on the board"),
    ]
    if found.smd_count:
        sides = ", ".join(found.sides) or "none"
        rows += [
            ("PCB Assembly", "On", f"{found.smd_count} SMD placements per board (the package)"),
            ("Assembly Side", "Top Side" if found.sides == ("Top",) else f"check: the CPL says {sides}",
             "every placement is on the top" if found.sides == ("Top",) else "not all on the top"),
            ("PCBA Qty", f"at least {board.quantity}",
             "every board the piece needs comes assembled; the form may ask for a higher minimum"),
            ("PCBA Type", "Economic if the form offers it for this board, else Standard", "note which"),
            ("Tooling holes", "look where they go",
             "if JLC adds them, check in its preview that none lands on a part or a fixing"),
            ("Confirm Parts Placement", "Yes",
             "the CPL keeps KiCad's rotations with no reel offset applied (README-JLCPCB.md)"),
        ]
    else:
        rows.append(("PCB Assembly", "Off", "no SMD part: this board is ordered bare (JLCPCB_ASSEMBLY.md)"))
    return (
        "<p>Below the upload, JLC's form. Most of it reads itself from the Gerbers; "
        "these are the ones to set or to check. If the form will not take one - white "
        "refused with assembly, say - that is <em>something went wrong</em>, not a "
        "quiet fall-back to its default.</p>"
        + _table(rows)
    )


_POLARISED = re.compile(r"\b(pad|pin) 1\b")


def _reference_order(row: Mapping[str, str]) -> list[Any]:
    """RP2 before RP10, as on the board."""
    return [int(piece) if piece.isdigit() else piece
            for piece in re.split(r"(\d+)", row.get("Designator", ""))]


def _upload_bom_cpl(board: gerbers.Board, found: Package) -> str:
    if not found.smd_count:
        return (
            f"<p>Nothing to upload: the {escape(board.title)} has no SMD part (its BOM and "
            "CPL are headers only), so it is ordered bare. Check that "
            "<strong>PCB Assembly</strong> is off, then go on.</p>"
        )
    parts: dict[str, list[dict[str, str]]] = {}
    for row in found.bom:
        parts.setdefault(row.get("LCSC Part #", ""), []).append(row)
    lines = []
    for lcsc, rows in parts.items():
        first = rows[0]
        references = ", ".join(row.get("Designator", "") for row in sorted(rows, key=_reference_order))
        polarity = "check" if _POLARISED.search(first.get("Specification", "")) else ""
        lines.append(
            f"<tr><td>{escape(lcsc)}</td><td>{escape(first.get('Manufacturer Part Number', ''))}</td>"
            f"<td>{escape(first.get('Comment', ''))}</td><td>{len(rows)}</td>"
            f"<td>{escape(references)}</td><td><strong>{polarity}</strong></td></tr>"
        )
    return (
        "<p>With <strong>PCB Assembly</strong> on, the form asks for two files. Give it these:</p>"
        f'<p><a class="button" href="/pcb/{board.id}/bom">BOM.csv</a>'
        f'<a class="button" href="/pcb/{board.id}/cpl">CPL.csv</a></p>'
        f"<p>Then <strong>Process BOM &amp; CPL</strong>. JLC should match all {len(found.bom)} "
        f"rows - {len(parts)} distinct parts - each to the LCSC part below. Check:</p>"
        "<ul>"
        "<li>no row is left unmatched, and none is matched to another LCSC number than the one "
        "listed: <strong>do not let it substitute</strong> (README-JLCPCB.md);</li>"
        "<li>the stock covers the PCBA quantity times the count per board;</li>"
        "<li>each part JLC calls <em>Extended</em> adds a setup fee: note which;</li>"
        f'<li>references JLC says are in the design but not placed: the {found.hand_fitted} in '
        f'<a href="/pcb/{board.id}/manual">manual-and-DNP.csv</a> are hand fitted or not fitted, on purpose;</li>'
        "<li>in the placement preview, every part marked <em>check</em> sits as the "
        f'<a href="/pcb/{board.id}/assembly" target="_blank">assembly drawing</a> shows it: LEDs and '
        "Schottky diodes pad 1 = cathode (the silkscreen's -), electrolytics pad 1 = positive (+), "
        "IC pin 1 on its mark "
        "(README-JLCPCB.md).</li>"
        "</ul>"
        "<table><tr><th>LCSC</th><th>part number</th><th>value</th><th>per board</th>"
        "<th>references</th><th>polarity</th></tr>"
        + "".join(lines)
        + "</table>"
    )


def _anything_else(board: gerbers.Board, found: Package) -> str:
    checks = CHECKS.get(board.id, ()) + COMMON_CHECKS
    read = ", ".join(board.read_first)
    return (
        "<p>What the designs' own documents still leave open for this board, before it "
        "goes in the cart. Tick them as you go (the ticks are not kept). One that says "
        "stop is <em>something went wrong</em>: say which in the note.</p>"
        '<ul class="checks">'
        + "".join(
            f'<li><label><input type="checkbox"> {escape(check)}</label> '
            f'<span class="source">({escape(source.format(board=board.id))})</span></li>'
            for check, source in checks
        )
        + "</ul>"
        + (f'<p class="small">The board\'s own open checks are in {escape(read)} (under '
           "CAD/KiCad, and in the package's reference folder).</p>" if read else "")
    )


def _cart(board: gerbers.Board, found: Package) -> str:
    return (
        "<p>On JLC's page, press <strong>Save to Cart</strong>. Do not pay yet: the cart is "
        "paid once, at the end, for every PCB in it.</p>"
        f"<p>Then say so here. The {escape(board.title)} is marked <em>in the cart</em> and the "
        "next PCB comes up.</p>"
        f'<form method="post" action="{ROUTE}/{board.id}/cart">'
        '<button type="submit">it is in the cart - next PCB</button></form>'
    )


STEP_PAGES: tuple[Callable[[gerbers.Board, Package], str], ...] = (
    _upload_gerbers, _order_options, _upload_bom_cpl, _anything_else, _cart,
)


# --- the pages --------------------------------------------------------


def _overview(boards: tuple[gerbers.Board, ...], book: Mapping[str, Any] | None) -> str:
    walk = _walk(boards, book)
    rows = "".join(
        f"<tr><td>{escape(board.title)}</td><td>{board.quantity}</td>"
        f"<td>{_status_words(record(book, board.id), board)}</td>"
        f"<td>{'in this walk' if board in walk else 'skipped'}</td></tr>"
        for board in boards
    )
    if walk:
        begin = (f'<p><a class="button" href="{ROUTE}/{walk[0].id}/1">begin with the '
                 f"{escape(walk[0].title)}</a></p>")
    else:
        begin = (f'<p>Nothing is waiting to be ordered. <a href="{ROUTE}/done">The cart</a> '
                 "can set a board back to waiting.</p>")
    return (
        "<h1>Order the PCBs at JLCPCB</h1>"
        f"<p>One page per step for each of the {len(walk)} PCBs still to order "
        "(waiting, or in error from an earlier try), each in its own upload, all in one "
        "cart. Five steps each:</p>"
        "<ol>" + "".join(f"<li>{escape(name)}</li>" for name in STEPS) + "</ol>"
        "<p>Every step has <em>next</em>, and <em>something went wrong</em>, which asks "
        "for a note and a screenshot, marks that PCB as error and goes on to the next one. "
        "The walk ends on the cart, which marks everything in it as ordered once it is paid.</p>"
        f'<p>Log in at <a href="{QUOTE_PAGE}" target="_blank" rel="noopener">JLCPCB</a> in '
        "another tab first.</p>"
        '<p class="small">Which boards go in this order is still open in RELEASE_REVIEW.md 1: '
        "the Teensy adapter can wait, the microphone holders belong to no step yet, and the body "
        "boards wait on their fit checks (F8). A board that is not in this order: "
        "<em>skip</em>, which leaves it waiting.</p>"
        + begin
        + "<table><tr><th>PCB</th><th>needed</th><th>order</th><th></th></tr>"
        + rows + "</table>"
    )


def _step_page(boards: tuple[gerbers.Board, ...], book: Mapping[str, Any] | None,
               board: gerbers.Board, step: int) -> str:
    skip = next_url(boards, book, board)
    found: Package | None = None
    try:
        found = package(board)
        content = STEP_PAGES[step - 1](board, found)
        problem = ""
    except gerbers.PackageError as error:
        found, content, problem = None, "", str(error)

    actions = []
    if step > 1:
        actions.append(f'<a href="{ROUTE}/{board.id}/{step - 1}">previous step</a>')
    if found is not None and step < len(STEPS):
        actions.append(f'<a class="button" href="{ROUTE}/{board.id}/{step + 1}">next: '
                       f"{escape(STEPS[step])}</a>")
    actions.append(f'<a class="small" href="{skip}">skip this PCB for now (it stays as it is)</a>')

    status = status_of(book, board.id)
    already = ""
    if status in (IN_CART, ORDERED):
        already = (f'<p class="problem">This PCB is already {escape(status)}: putting it in '
                   "the cart again orders it twice.</p>")
    if problem:
        content = (f'<p class="problem">This PCB cannot be ordered from this checkout: '
                   f"{escape(problem)}</p><p>Say so below to go on to the next PCB.</p>")

    return (
        _board_header(board, boards, book, step)
        + already
        + f'<section class="step" name="step"><h2>{step}. {escape(STEPS[step - 1])}</h2>{content}</section>'
        + '<div class="actions">' + "".join(actions) + "</div>"
        + _error_form(board, step, is_open=bool(problem))
    )


def _done(boards: tuple[gerbers.Board, ...], book: Mapping[str, Any] | None) -> str:
    in_cart = [board for board in boards if status_of(book, board.id) == IN_CART]
    errors = [board for board in boards if status_of(book, board.id) == ERROR]
    walk = _walk(boards, book)

    if in_cart:
        listed = "".join(f"<li>{escape(board.title)}</li>" for board in in_cart)
        pay = (
            f"<p>JLC's cart should hold exactly these {len(in_cart)}, each with the "
            f"quantities chosen in step 2:</p><ul>{listed}</ul>"
            "<p>Pay for them there. Then:</p>"
            f'<form method="post" action="{ROUTE}/ordered">'
            "<p><label>JLC order number (optional) "
            '<input type="text" name="order number" size="24"></label></p>'
            f'<button type="submit">mark the {len(in_cart)} PCBs in the cart as ordered</button></form>'
        )
    else:
        pay = "<p>Nothing is in the cart.</p>"

    trouble = "".join(
        f"<h3>{escape(board.title)}</h3>{_error_details(record(book, board.id), picture=True)}"
        for board in errors
    )
    rows = "".join(
        f"<tr><td>{escape(board.title)}</td><td>{_status_words(record(book, board.id), board)}</td><td>"
        + ("" if status_of(book, board.id) == WAITING else
           f'<form method="post" action="{ROUTE}/{board.id}/reset">'
           '<button type="submit" class="small">set back to waiting order</button></form>')
        + "</td></tr>"
        for board in boards
    )
    again = (f'<p><a class="button" href="{ROUTE}/{walk[0].id}/1">order the {len(walk)} '
             "still waiting or in error</a></p>" if walk else "")
    return (
        "<h1>The cart</h1>"
        + pay
        + (f"<h2>In error</h2>{trouble}" if errors else "")
        + again
        + "<h2>Every PCB</h2><table>" + rows + "</table>"
    )


# --- forms ------------------------------------------------------------


def read_form(environ: Mapping[str, Any]) -> tuple[dict[str, str], dict[str, tuple[str, bytes]]]:
    """A POST body's fields, and its files as (file name, bytes).

    Urlencoded or multipart. Multipart goes through the `email` parser,
    which is what is left of the standard library's for it since `cgi`
    went (Python 3.13).
    """
    length = int(environ.get("CONTENT_LENGTH") or 0)
    if length > MAX_UPLOAD_BYTES:
        raise OrderError(f"that upload is {length >> 20} MB; the most this takes is "
                         f"{MAX_UPLOAD_BYTES >> 20} MB")
    body = environ["wsgi.input"].read(length) if length else b""
    content_type = str(environ.get("CONTENT_TYPE") or "")
    fields: dict[str, str] = {}
    files: dict[str, tuple[str, bytes]] = {}
    if content_type.startswith("multipart/form-data"):
        message = email.parser.BytesParser(policy=email.policy.HTTP).parsebytes(
            b"Content-Type: " + content_type.encode("latin-1") + b"\r\n\r\n" + body
        )
        for part in message.iter_parts() if message.is_multipart() else ():
            name = part.get_param("name", header="content-disposition")
            if not isinstance(name, str):
                continue
            payload = part.get_payload(decode=True)
            data = payload if isinstance(payload, bytes) else b""
            filename = part.get_filename()
            if filename is not None:
                files[name] = (filename, data)
            else:
                fields[name] = data.decode(part.get_content_charset() or "utf-8", "replace")
    else:
        for name, values in parse_qs(body.decode("utf-8", "replace")).items():
            fields[name] = values[0]
    return fields, files


def image_kind(data: bytes) -> str | None:
    """The file's own type, from its first bytes - never from its name."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data[:6] in (b"GIF87a", b"GIF89a"):
        return "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None


def _keep_screenshot(folder: Path, board: gerbers.Board, data: bytes) -> tuple[str, str]:
    """(file name, sentence for the note). Only an image is kept: the page
    serves it back, and serves it as what its bytes say it is."""
    if not data:
        return "", ""
    kind = image_kind(data)
    if kind is None:
        return "", " (the attached file was not a PNG, JPEG, GIF or WebP image and was not kept)"
    folder.mkdir(parents=True, exist_ok=True)
    stem = f"{board.id}-{_now():%Y%m%d-%H%M%S}"
    name = f"{stem}.{kind}"
    count = 1
    while (folder / name).exists():
        count += 1
        name = f"{stem}-{count}.{kind}"
    (folder / name).write_bytes(data)
    return name, ""


def _screenshot(folder: Path, name: str) -> tuple[str, list[tuple[str, str]], bytes]:
    if not SCREENSHOT_NAME.fullmatch(name):
        raise OrderError("there is no screenshot by that name")
    path = folder / name
    if not path.is_file():
        raise OrderError("there is no screenshot by that name")
    content = path.read_bytes()
    kind = image_kind(content)
    if kind is None:
        raise OrderError("that file is not an image")
    return "200 OK", [("Content-Type", IMAGE_TYPES[kind]), ("Cache-Control", "no-cache"),
                      ("Content-Length", str(len(content)))], content


# --- the route --------------------------------------------------------


def response(parts: tuple[str, ...], environ: Mapping[str, Any],
             book: MutableMapping[str, Any] | None,
             folder: Path) -> tuple[str, list[tuple[str, str]], bytes]:
    """Everything under /pcb-order. Never raises - see the module docstring."""
    try:
        return _respond(tuple(parts), environ, book, folder)
    except OrderError as error:
        return _html("409 Conflict", "PCB order",
                     f'<h1>That did not work</h1><p class="problem">{escape(str(error))}</p>'
                     f'<p><a href="{ROUTE}">back to the order</a></p>')
    except gerbers.PackageError as error:
        return _html("404 Not Found", "PCB order",
                     f'<h1>Not available</h1><p class="problem">{escape(str(error))}</p>')
    except Exception as error:  # noqa: BLE001 - see the module docstring
        return _html("500 Internal Server Error", "PCB order",
                     f'<h1>Something broke</h1><p class="problem">{escape(type(error).__name__)}: '
                     f"{escape(str(error))}</p>")


def _respond(parts: tuple[str, ...], environ: Mapping[str, Any],
             book: MutableMapping[str, Any] | None,
             folder: Path) -> tuple[str, list[tuple[str, str]], bytes]:
    is_post = environ.get("REQUEST_METHOD") == "POST"
    if is_post and book is None:
        # Before anything is read or kept, a screenshot included.
        raise OrderError("this server keeps no order records (no params)")
    boards = gerbers.load()

    if parts == ():
        return _html("200 OK", "Order the PCBs", _overview(boards, book))
    if parts == ("done",):
        return _html("200 OK", "The PCB cart", _done(boards, book))
    if len(parts) == 2 and parts[0] == "screenshot":
        return _screenshot(folder, parts[1])
    if parts == ("ordered",):
        if not is_post:
            return _redirect(f"{ROUTE}/done")
        fields, _ = read_form(environ)
        number = fields.get("order number", "").strip()
        for board in boards:
            found = record(book, board.id)
            if found["status"] == IN_CART:
                _write(book, board, ORDERED, pcb=found.get("pcb", ""),
                       **{"order number": number, "in the cart at": found.get("changed at", "")})
        return _redirect(f"{ROUTE}/done")

    if len(parts) != 2:
        raise gerbers.PackageError(f"there is no order page {'/'.join(parts)!r}")
    board = gerbers.find(boards, parts[0])
    action = parts[1]

    if action in {str(number) for number in range(1, len(STEPS) + 1)}:
        return _html("200 OK", f"{board.title} - step {action}",
                     _step_page(boards, book, board, int(action)))
    if action not in ("cart", "error", "reset"):
        raise gerbers.PackageError(f"there is no order page {'/'.join(parts)!r}")
    if not is_post:
        # A press is a form; a link or a reload that lands here does nothing.
        return _redirect(f"{ROUTE}/{board.id}/1")

    if action == "cart":
        _write(book, board, IN_CART, pcb=board.source_sha256)
        return _redirect(next_url(boards, book, board))
    if action == "reset":
        _write(book, board, WAITING)
        return _redirect(f"{ROUTE}/done")

    fields, files = read_form(environ)
    try:
        step = min(max(int(fields.get("step", "0")), 0), len(STEPS))
    except ValueError:
        step = 0
    _, data = files.get("screenshot", ("", b""))
    screenshot, said = _keep_screenshot(folder, board, data)
    _write(book, board, ERROR, pcb=board.source_sha256, step=step,
           note=(fields.get("note", "").strip() or "(no note)") + said,
           screenshot=screenshot, **{"step title": STEPS[step - 1] if step else ""})
    return _redirect(next_url(boards, book, board))
