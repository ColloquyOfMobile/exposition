# -*- coding: utf-8 -*-
# Source code/Python/colloquy/server2/updates.py

"""Telling whoever is at a page that the server is about to restart.

On the installation's laptop the repository pulls by itself and the
server restarts onto what it pulled (`colloquy/repository/`). Neither is
something a person asked for at the moment it happens, so both have to
be said - on **every** page, since the restart takes all of them down,
and *before* it happens rather than as a link that stopped answering.

Two halves, and the first works alone:

- `banner_html` is drawn into the page when it is rendered, so any page
  loaded while an update is under way says so with no script at all.
- `static/update_watch.js` keeps that banner true on a page that is just
  sitting open: it asks `/update-status` every few seconds, and when the
  process that answers is no longer the one that drew the page, the page
  loads itself again. `BOOT` is how it tells.

Nothing is drawn, and no script is sent, on a machine that does not
update itself: there the repository's `notice` is always None, and a
banner that could never say anything is furniture.

Installation-side only, like `remedies.py`. The mock has no repository.
"""
import json
import os
from math import ceil
from time import time
from urllib.parse import quote

from yattag import Doc

# One value per process, fixed when this module is first imported. A page
# holds the value it was drawn under; a different one coming back from
# /update-status means the server has been restarted since.
BOOT = f"{os.getpid()}-{int(time() * 1000)}"

STYLE = (
    "#update-notice { padding: 0.4rem 1ch; margin: 0.25rem 0; "
    "border: 1px solid #8886; border-left: 0.6ch solid #888; "
    "font-weight: bold; } "
    "#update-notice[hidden] { display: none; } "
    '#update-notice[data-phase="pulling"], '
    '#update-notice[data-phase="restarting"], '
    '#update-notice[data-phase="waiting"] '
    "{ background: #fc03; border-left-color: #e90; } "
    '#update-notice[data-phase="blocked"], '
    '#update-notice[data-phase="stopped"], '
    '#update-notice[data-phase="down"] '
    "{ background: #f002; border-left-color: #d02; } "
    '#update-notice[data-phase="updated"] '
    "{ background: #0a02; border-left-color: #0a0; }"
)


def status(repository):
    """What the banner says right now, as the script is told it."""
    notice = repository.notice
    if notice is None:
        return {"boot": BOOT, "phase": "", "text": ""}

    text = notice.text
    if notice.restart_in is not None and notice.restart_in > 0:
        text = f"{text} Restarting in {ceil(notice.restart_in)} s."
    return {"boot": BOOT, "phase": notice.phase, "text": text}


def status_json(repository):
    return json.dumps(status(repository)).encode("utf-8")


def banner_html(repository, back="/", phase=None, text=None):
    """The banner, as drawn into a page.

    `back` is where the page should load itself again after a restart:
    its own node's path, never whatever `/call/...` led to it, for the
    reason `refresh` gives - coming back must not run a command twice.

    `phase` and `text` are for the one page that announces a restart of
    its own (`/mount-main-pcb`); every other page says what the
    repository says, and says nothing where it does not update itself.
    Such a page is marked sticky: the process that drew it is on its way
    down and will not be saying anything further, so the script keeps the
    sentence it was given until a new process answers.
    """
    sticky = phase is not None
    if not sticky:
        if not repository.auto_update:
            return ""
        said = status(repository)
        phase, text = said["phase"], said["text"]

    doc, tag, text_ = Doc().tagtext()
    with tag("style"):
        doc.asis(STYLE)
    attributes = {
        "id": "update-notice",
        "data-boot": BOOT,
        "data-back": quote(back, safe="/"),
        "data-phase": phase,
    }
    if sticky:
        attributes["data-sticky"] = "1"
    if not phase:
        attributes["hidden"] = "hidden"
    with tag("div", **attributes):
        text_(text or "")
    return doc.getvalue()


def script_html(repository=None):
    """The script that keeps the banner true, where there is a banner."""
    if repository is not None and not repository.auto_update:
        return ""
    return '<script src="/static/update_watch.js"></script>'
