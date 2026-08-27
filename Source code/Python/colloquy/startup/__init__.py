# -*- coding: utf-8 -*-
# Source code/Python/colloquy/startup/__init__.py

"""What went wrong while the hardware was being opened, and what to do next.

**Nothing here may stop the server starting.** That is the whole point of
the node. Before it, `main.py` opened the two links and woke every servo
with nothing catching anything, so a board running last month's sketch or
one servo that did not answer ended the process on a traceback - and the
page that would have explained it, and the command that would have fixed
it, both died with it (docs/errors/2026-08-27-01.txt).

An installation that comes up unable to move is worth far more than one
that does not come up. The page still browses, the params are still
editable, the logs are still there, `flash firmware` is still one click
away, and the reader is told plainly which of those to use.

**It is on the front page only when it has something to say.** A clean
start registers no child at all, so its being there *is* the alarm - the
same arrangement as `Repository`'s pull link, which appears only when
origin actually has something and whose appearing is the proposal.

**Every problem carries a remedy**, because "the Arduino did not open" on
its own sends somebody to read a traceback in a log. The remedies come in
two shapes: a link the page can offer for a fault the software can fix
(an old sketch is flashed from `drivers > arduino > flash firmware`), and
a sentence for a fault that needs hands (a lead that is out, a servo that
is not answering). The second kind says which one and what to do, and
that is as far as software can take it.
"""
from colloquy.base import Base
from colloquy.ui import leaves


class Problem:
    """One thing that went wrong, in the three parts a reader needs.

    `what` happened, what it `means` for the installation now, and the
    `remedy`. `remedy_html` is for the case where the fix is a link rather
    than a sentence - see the module docstring.
    """

    def __init__(self, key, what, means, remedy, remedy_html=None):
        self.key = key
        self.what = what
        self.means = means
        self.remedy = remedy
        self.remedy_html = remedy_html


class Startup(Base):
    """The record of how far `open_the_hardware()` got, and what stopped it."""

    def __init__(self, owner):
        super().__init__(owner=owner)
        self._problems = []

    @property
    def name(self):
        return "startup problems"

    @property
    def colloquy(self):
        return self.owner

    @property
    def problems(self):
        return list(self._problems)

    @property
    def has_problems(self):
        return bool(self._problems)

    # --- what main.py reports into ----------------------------------------

    def _add(self, *args, **kwargs):
        problem = Problem(*args, **kwargs)
        self._problems.append(problem)
        # Said on the console too. Somebody watching a start in a terminal
        # should not have to open a browser to find out it half-worked.
        self.log(f"STARTUP PROBLEM - {problem.what} {problem.remedy}")
        return problem

    def arduino_firmware_is_old(self, error):
        """The board answered and its sketch is older than this driver needs.

        The one startup failure with a remedy that is a link: the flasher
        compiles and uploads this repo's own sketch and reopens the port
        afterwards, so the outcome line is the board saying which firmware
        it is now running.
        """
        found = error.found_version
        found = f"firmware {found}" if found is not None else "an older firmware"
        self._add(
            key="arduino firmware",
            what=f"The Arduino is running {found}, which this driver cannot drive.",
            means=(
                "no light, no light sensor and no sound - an old sketch "
                "answers an unknown path with an empty line, so a female "
                "would simply never read a pattern"
            ),
            remedy="Flash this repo's sketch onto the board, then restart.",
            remedy_html=(
                "<p>The board can be flashed from here - it compiles and "
                "uploads this repo's own sketch, and reopens the link "
                "afterwards so the board says in its own words which "
                "firmware it ends up with.</p>"
                '<p><a href="/app/drivers/arduino/flash firmware">'
                "<strong>go to flash firmware</strong></a> "
                "(press <em>compile only</em> first if you have never "
                "flashed from this machine)</p>"
            ),
        )

    def arduino_failed(self, error):
        """The link did not open at all, for a reason nothing here can fix."""
        self._add(
            key="arduino",
            what=f"The Arduino link did not open: {error}",
            means="no light, no light sensor and no sound",
            remedy=(
                "Check the USB lead and which COM port the board is on "
                "(drivers > arduino > com port), then restart."
            ),
        )

    def servo_bus_failed(self, error):
        """The U2D2 did not open, so no servo was reached at all."""
        self._add(
            key="servo bus",
            what=f"The servo bus (U2D2) did not open: {error}",
            means="nothing can move - no body, no mirror, and not the bar",
            remedy=(
                "Check the U2D2's USB lead and its COM port, then restart. "
                "Nothing was left with torque enabled."
            ),
        )

    def servo_failed(self, body_name, dxl, error):
        """One servo did not answer while it was being woken.

        The other five were still initialised: one dead servo is a body
        that cannot move, not an installation that cannot start.
        """
        self._add(
            key=f"servo {body_name}",
            what=f"{body_name} ({dxl.name}) did not answer: {error}",
            means=(
                f"{body_name} will not move, and any behaviour that waits "
                "for it to arrive somewhere will time out"
            ),
            remedy=(
                f"Check {body_name}'s daisy-chain lead and its power, and "
                "that its id is the one it should be. Then restart."
            ),
        )

    # --- the page ----------------------------------------------------------

    @property
    def snapshot_children(self):
        """None. Everything here is a reading or a remedy, and the one
        remedy that is a link goes to a node that already exists."""
        return {}

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)

        if not self.has_problems:
            # Not normally reachable - the root does not offer this node
            # when it is empty - but a node that renders nothing at all if
            # somebody types its URL is worse than one that says so.
            leaf("state", "the hardware opened cleanly")
            return states

        leaf(
            "state",
            f"{len(self._problems)} problem(s) while opening the hardware - "
            "the server started anyway",
        )
        for problem in self._problems:
            leaf(problem.key, problem.what)
            leaf(f"{problem.key}: what that means", problem.means)
            if problem.remedy_html is None:
                leaf(f"{problem.key}: what to do", problem.remedy)
            else:
                # An anchor rather than a command link, because it goes to
                # another node in the tree rather than calling anything.
                # Both renderers drop an html leaf in as it is.
                states[f"{problem.key}: what to do"] = leaves.html(
                    path, f"{problem.key}: what to do", problem.remedy_html
                )
        return states
