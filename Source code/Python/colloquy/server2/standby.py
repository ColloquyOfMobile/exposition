# -*- coding: utf-8 -*-
# Source code/Python/colloquy/server2/standby.py

"""The front page while the main PCB is out of the rack.

With the board gone there is nothing for the usual page to drive: both
serial links land on that one PCB, so there is no Arduino and no servo
bus, and every node under `drivers` is a way to command hardware that is
on a bench somewhere or not yet made. So for as long as the board is
noted as unmounted the tree is not served at all, and this is what `/`
answers with instead. That is the whole of what keeps the drivers from
being activated: not a guard on each of them, but there being no page
that reaches one (`wsgi2._parse` holds the gate).

What somebody at this machine *does* want while the board is out is the
three things on the page:

1. **the Gerbers**, to order the boards that replace it;
2. **the KiCad projects**, to open the design;
3. **the way back** - saying the new board is in, which notes it as
   mounted and restarts onto the usual page with both links opened.

It is the installation's front page for weeks at a time, so nothing in it
may raise. Each section reads its own files and reports a failure as a
sentence in its own place; a manifest somebody merged badly must not be
what takes down the page the downloads are on.

No EMERGENCY STOP is drawn. There is nothing to stop, and that press
latches `BaseThread._shutdown`, which would silently end the one thing
still running here - the watch that keeps this machine up to date.

Installation-side only: the mock has no board to take out.
"""
from yattag import Doc

from colloquy.hardware.pcb_files import gerbers, kicad_projects

from . import updates

STYLE = (
    "body { font-family: system-ui, sans-serif; margin: 0; "
    "padding: 0.75rem 2ch 2rem; line-height: 1.4; } "
    ".furniture { display: flex; gap: 2ch; font-size: 0.9rem; } "
    ".piece { margin: 1.25rem 0 0; font-size: 0.8rem; letter-spacing: 0.12em; "
    "text-transform: uppercase; opacity: 0.6; } "
    "h1 { margin: 0 0 0.25rem; font-size: 1.7rem; } "
    ".lede { margin: 0 0 1rem; max-width: 85ch; opacity: 0.85; } "
    ".option { border: 1px solid #8886; border-radius: 6px; "
    "padding: 0.75rem 2ch 1rem; margin: 0.75rem 0; max-width: 110ch; } "
    ".option h2 { margin: 0 0 0.25rem; font-size: 1.15rem; } "
    ".option p { margin: 0.35rem 0; max-width: 85ch; } "
    "a.button { display: inline-block; padding: 0.5rem 2ch; "
    "border: 2px solid currentColor; border-radius: 6px; font-weight: bold; "
    "text-decoration: none; margin: 0.4rem 0; } "
    "table { border-collapse: collapse; margin: 0.5rem 0; font-size: 0.9rem; } "
    "th, td { border-bottom: 1px solid #8884; padding: 0.25rem 2ch 0.25rem 0; "
    "text-align: left; vertical-align: top; } "
    "th { font-weight: normal; opacity: 0.6; } "
    ".group td { font-weight: bold; padding-top: 0.6rem; } "
    ".what { opacity: 0.7; } "
    ".problem { color: #d02; font-weight: bold; } "
    ".small { font-size: 0.85rem; opacity: 0.75; } "
    ".software { margin-top: 1.25rem; font-size: 0.85rem; opacity: 0.75; "
    "max-width: 110ch; }"
)


def _sentence(error):
    return f"{type(error).__name__}: {error}"


def _gerbers(doc, tag, text):
    with tag("div", name="gerbers", klass="option"):
        with tag("h2"):
            text("1. Download the PCB production Gerbers")
        with tag("p"):
            text(
                "For PCBWay or JLCPCB. One download holding a ready-to-upload "
                "zip for each board, the layer count and size each order "
                "form asks for, and what to read before ordering."
            )

        try:
            boards = gerbers.load()
            problems = {board.id: gerbers.problems(board) for board in boards}
        except Exception as error:  # noqa: BLE001 - this page must not raise
            said = str(error) if isinstance(error, gerbers.PackageError) else _sentence(error)
            with tag("p", klass="problem"):
                text(f"Not available: {said}.")
            return

        with tag("p"):
            with tag("a", klass="button", href="/download/gerbers"):
                text(f"download the Gerbers ({len(boards)} boards)")

        with tag("table"):
            with tag("tr"):
                for heading in ("board", "layers", "size", "needed", ""):
                    with tag("th"):
                        text(heading)
            group = None
            for board in boards:
                if board.group != group:
                    group = board.group
                    with tag("tr", klass="group"):
                        with tag("td", colspan="5"):
                            text(group)
                with tag("tr"):
                    with tag("td"):
                        text(board.title)
                        with tag("div", klass="what"):
                            text(board.what)
                        for problem in problems[board.id]:
                            with tag("div", klass="problem"):
                                text(problem)
                    with tag("td"):
                        text(str(board.copper_layers))
                    with tag("td"):
                        text(board.size)
                    with tag("td"):
                        text(str(board.quantity))
                    with tag("td"):
                        with tag("a", href=f"/download/gerbers/{board.id}"):
                            text("this board only")

        plotted = sorted(board.exported_at for board in boards if board.exported_at)
        if plotted:
            with tag("p", klass="small"):
                text(
                    f"Plotted {plotted[-1][:10]} from the boards in this "
                    "checkout, each after passing KiCad's design rule check. "
                    "A plot is not a release: the README inside the download "
                    "says which physical checks each design still lists as open."
                )


def _kicad(doc, tag, text, colloquy):
    with tag("div", name="kicad", klass="option"):
        with tag("h2"):
            text("2. Download the full KiCad projects")

        try:
            counted = kicad_projects.summary(colloquy.repository.git.tracked)
            size = (
                f"{counted.count} files, {counted.megabytes} MB before "
                "compression"
            )
        except Exception as error:  # noqa: BLE001 - this page must not raise
            size = f"size unknown ({_sentence(error)})"

        with tag("p"):
            text(
                "Everything under CAD/KiCad as this checkout has it - "
                "schematics, boards, libraries, 3D models and the Gerbers "
                f"above: {size}. Opens in KiCad 9."
            )
        with tag("p"):
            with tag("a", klass="button", href="/download/kicad"):
                text("download the KiCad projects")
        with tag("p", klass="small"):
            text(
                "The zip is made on the first press, which takes a few "
                "seconds before the download begins."
            )


def _mount(doc, tag, text):
    with tag("div", name="mount", klass="option"):
        with tag("h2"):
            text("3. The new PCB is mounted")
        with tag("p"):
            text(
                "Press this when the new board is in the rack with both USB "
                "leads connected. It notes the board as mounted and restarts "
                "the server: the Arduino and the U2D2 are opened, the drivers "
                "come back, and so does the usual page."
            )
        with tag("p"):
            text(
                "Nothing starts moving by itself - the piece is started from "
                "the usual page, as before."
            )
        with tag("p"):
            with tag("a", klass="button", href="/mount-main-pcb"):
                text("the new PCB is mounted")


def _software(doc, tag, text, colloquy):
    """What this machine is running and whether it is up to date."""
    try:
        repository = colloquy.repository
        parts = []
        if repository.running:
            parts.append(f"running {repository.running}")
        parts.append(repository.summary)
        parts.append(f"checked {repository.last_checked}")
        if repository.auto_update:
            parts.append(
                "this machine pulls what origin has and restarts onto it by itself"
            )
        else:
            parts.append("automatic updates are off on this machine")
        said = " - ".join(parts)
    except Exception as error:  # noqa: BLE001 - this page must not raise
        said = f"could not be read ({_sentence(error)})"

    with tag("div", name="software", klass="software"):
        text(f"Software: {said}.")


def page(colloquy):
    """The whole front page, as bytes."""
    main_pcb = colloquy.hardware.main_pcb
    since = (main_pcb.unmounted_at or "").replace("T", " ") or "an unrecorded date"

    doc, tag, text = Doc().tagtext()
    doc.asis("<!DOCTYPE html>")
    with tag("html"):
        with tag("head"):
            doc.stag("meta", charset="utf-8")
            with tag("title"):
                text("Colloquy of Mobiles - main PCB out")
            with tag("style"):
                doc.asis(STYLE)
        with tag("body"):
            with tag("div", name="server commands", klass="furniture"):
                with tag("a", href="/shutdown"):
                    text("shutdown")
                with tag("a", href="/restart"):
                    text("restart")
                with tag("a", href="/"):
                    text("refresh")

            doc.asis(updates.banner_html(colloquy.repository, back="/"))

            with tag("div", klass="piece"):
                text("Colloquy of Mobiles")
            with tag("h1"):
                text("The main PCB is out")
            with tag("p", klass="lede"):
                text(
                    f"Noted as unmounted since {since}. The Arduino and the "
                    "U2D2 are not opened and the drivers are off: nothing can "
                    "move or light up, and nothing on this page can start it. "
                    "The usual page returns when a board is noted as mounted."
                )

            _gerbers(doc, tag, text)
            _kicad(doc, tag, text, colloquy)
            _mount(doc, tag, text)
            _software(doc, tag, text, colloquy)

            doc.asis(updates.script_html(colloquy.repository))

    return doc.getvalue().encode("utf-8")


def restarting_page(repository, title, lines, back="/"):
    """The page a route answers with when it ends in a restart.

    Says what was done, and comes back by itself: the banner is marked
    sticky and the script reloads onto `back` once a new process answers.
    The plain link is for a browser with no script, and for anybody who
    would rather press something.
    """
    doc, tag, text = Doc().tagtext()
    doc.asis("<!DOCTYPE html>")
    with tag("html"):
        with tag("head"):
            doc.stag("meta", charset="utf-8")
            with tag("title"):
                text(title)
            with tag("style"):
                doc.asis(STYLE)
        with tag("body"):
            with tag("h1"):
                text(title)
            for line in lines:
                with tag("p", klass="lede"):
                    text(line)
            doc.asis(
                updates.banner_html(
                    repository,
                    back=back,
                    phase="restarting",
                    text="Restarting. This page comes back by itself.",
                )
            )
            with tag("p"):
                with tag("a", href=back):
                    text("reload")
            doc.asis(updates.script_html())

    return doc.getvalue().encode("utf-8")
