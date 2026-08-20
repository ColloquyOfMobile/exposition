from pathlib import Path

from colloquy.base import Base

from .rendering import render_html
from colloquy.ui import leaves
from colloquy.utils import write_text

SCENARIOS_FOLDER = Path(__file__).resolve().parent.parent / "scenarios"


def scenario_path(name):
    return (SCENARIOS_FOLDER / name).with_suffix(".scenario")


def all_scenario_names():
    """Every scenario on disk, whether or not anything claims it."""
    if not SCENARIOS_FOLDER.exists():
        return ()
    return tuple(sorted(path.stem for path in SCENARIOS_FOLDER.glob("*.scenario")))


class Scenario(Base):
    """One *.scenario file: what the installation does from some starting
    point, second by second, in what is visible in the room.

    Defaults to a rendered view; "edit" switches to a plain-text textarea,
    "save" writes it back to disk and returns to the rendered view - the
    same view/edit shape as the code documentation.
    """

    def __init__(self, owner, file_path):
        super().__init__(owner=owner)
        self._file_path = file_path
        self._mode = "view"
        self["save"] = self.save

    @property
    def name(self):
        return self._file_path.stem

    @property
    def file_path(self):
        return self._file_path

    @property
    def snapshot_children(self):
        return {}

    def read(self):
        try:
            return self._file_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return ""

    def enter_edit(self):
        self._mode = "edit"

    def cancel(self):
        self._mode = "view"

    def save(self, content):
        write_text(self._file_path, content)
        self._mode = "view"
        self.open()

    def _snapshot_if_opened(self, path):
        if self._mode == "edit":
            return {
                "cancel": self.cancel,
                "editor": leaves.editor(path, "editor", self.read()),
            }

        return {
            "edit": self.enter_edit,
            "rendered": leaves.html(path, "rendered", render_html(self.read())),
        }


class Scenarios(Base):
    """The scenarios describing one startable thing, hanging off it.

    A thread names the scenarios that describe it (`BaseThread.
    scenario_names`) and gets this node beside its own "start" - which is
    the rule these are filed by: wherever the page offers to start
    something, it also says what that thing will do.

    The names are of behaviours, not of nodes, so a body's three copies
    share one: female1, female2 and female3 all point their search at
    "female-looking". A thread may name several - one action is not one
    scenario, and the whole-piece ones sit on the root, where they are
    sub-scenarios of the evening it starts.

    A named file that is not on disk is shown as missing rather than
    quietly skipped: a scenario that has been renamed away is a thing to
    notice, not to hide.
    """

    def __init__(self, owner, names):
        super().__init__(owner=owner)
        self._names = tuple(names)
        self._children = {}

    @property
    def name(self):
        return "scenarios"

    @property
    def names(self):
        return self._names

    @property
    def snapshot_children(self):
        found = {}
        for name in self._names:
            found[name] = self._children.get(name) or Scenario(
                owner=self, file_path=scenario_path(name)
            )
        self._children = found
        return dict(self._children)
