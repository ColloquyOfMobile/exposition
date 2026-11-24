"""`installation PCB solution 2`: the steps, the record, and the branch it
is shared on.

The git half runs against a real, throwaway origin in tmp_path: plumbing
is easy to get subtly wrong, and only git can say a commit is right. No
port is opened and nothing is started.
"""
import re
import subprocess

import pytest

from colloquy.repository.git import Git
from colloquy.tests.installation_sol2 import InstallationSol2, progress, shared, steps


# --- the steps -----------------------------------------------------------


def test_every_key_is_unique_and_the_first_checks_the_present_state():
    assert len(set(steps.KEYS)) == len(steps.KEYS)
    assert steps.KEYS[0] == "check the present state"
    assert steps.KEYS[-1] == "firmware 5"


def test_every_body_is_plugged_in_by_a_step_of_its_own():
    for body in ("female1", "female2", "female3"):
        assert f"plug in {body}" in steps.KEYS
    for body in ("male1", "male2"):
        assert f"mount and plug in {body}" in steps.KEYS


def test_every_power_step_warns_against_12v_on_the_5v_jack():
    text = dict((s.key, s.text) for s in steps.STEPS)["power the bare backplane"]
    assert "Never 12 V into `J2`" in text


def test_the_amplifier_limit_quoted_is_the_recorded_one():
    from colloquy.params import DEFAULTS

    limit = DEFAULTS["audio"]["amplifier max supply volts"]
    assert f"{limit:.1f} V maximum" in steps.NEVER_12V_ON_J2


def test_every_link_points_at_a_tree_path():
    for step in steps.STEPS:
        for target in re.findall(r"\]\((/app/[^)]*)\)", step.text):
            assert " " not in target, target


# --- the record ----------------------------------------------------------


def test_a_record_round_trips_and_is_ascii():
    record = {"a": progress.Entry(True, "2026-11-24T10:00:00", "câble réparé", "2026-11-24T10:01:00")}
    text = progress.dump(record)

    assert text.isascii()
    assert progress.parse(text) == record


def test_nonsense_reads_as_an_empty_record():
    assert progress.parse("") == {}
    assert progress.parse("not json") == {}
    assert progress.parse('{"steps": []}') == {}
    assert progress.parse('{"steps": {"a": 3, "b": {"done": "yes"}}}') == {"b": progress.Entry()}


def test_the_later_word_wins_half_by_half():
    ticked = progress.mark({}, "a", True, "2026-11-24T10:00:00")
    noted = progress.annotate({}, "a", "loose screw", "2026-11-24T09:00:00")
    unticked = progress.mark({}, "a", False, "2026-11-24T11:00:00")

    merged = progress.merge(ticked, noted)
    assert merged["a"].done and merged["a"].note == "loose screw"
    merged = progress.merge(merged, unticked)
    assert not merged["a"].done and merged["a"].note == "loose screw"
    # Order of the copies does not matter.
    assert progress.merge(unticked, noted, ticked) == merged


def test_the_next_step_is_the_first_not_done():
    record = progress.mark({}, steps.KEYS[0], True, "2026-11-24T10:00:00")
    assert progress.next_step(record, steps.KEYS) == steps.KEYS[1]
    assert progress.next_step({}, steps.KEYS) == steps.KEYS[0]


# --- the branch ----------------------------------------------------------


def git(folder, *args):
    return subprocess.run(
        ("git", *args), cwd=folder, capture_output=True, text=True, check=True
    ).stdout.strip()


@pytest.fixture
def checkouts(tmp_path):
    """A bare origin and two clones: the laptop and the bench."""
    origin = tmp_path / "origin.git"
    git(tmp_path, "init", "--bare", "--quiet", str(origin))
    folders = []
    for name in ("laptop", "bench"):
        folder = tmp_path / name
        git(tmp_path, "clone", "--quiet", str(origin), str(folder))
        git(folder, "config", "user.name", "test")
        git(folder, "config", "user.email", "test@example.invalid")
        folders.append(folder)
    return origin, folders[0], folders[1]


def test_the_laptop_pushes_and_the_bench_reads_it(checkouts):
    _, laptop_folder, bench_folder = checkouts
    laptop = shared.SharedRecord(git=Git(laptop_folder), writer=True)
    bench = shared.SharedRecord(git=Git(bench_folder), writer=False)

    record = progress.mark({}, "check the present state", True, "2026-11-24T10:00:00")
    report = laptop.publish(record, "'check the present state' done")
    assert report.startswith("recorded and pushed"), report

    git(bench_folder, "fetch", "--quiet")
    assert bench.read()["check the present state"].done
    assert "as on origin" in bench.where()
    # The laptop's checkout was never touched: no branch moved, nothing dirty.
    assert git(laptop_folder, "status", "--porcelain") == ""
    assert git(laptop_folder, "log", "--oneline", "-1", shared.BRANCH).endswith(
        "Installation sol2: 'check the present state' done"
    )


def test_the_bench_cannot_write(checkouts):
    _, _, bench_folder = checkouts
    bench = shared.SharedRecord(git=Git(bench_folder), writer=False)

    assert bench.write({}, "x").startswith("refused")


def test_a_rejected_push_is_merged_and_pushed_again(checkouts):
    origin, laptop_folder, bench_folder = checkouts
    first = shared.SharedRecord(git=Git(laptop_folder), writer=True)
    first.publish(progress.mark({}, "a", True, "2026-11-24T10:00:00"), "a")

    # Another writer (an older laptop clone) pushes a note meanwhile.
    other = shared.SharedRecord(git=Git(bench_folder), writer=True)
    git(bench_folder, "fetch", "--quiet")
    other.publish(progress.annotate({}, "b", "broken wire", "2026-11-24T10:05:00"), "b")

    report = first.publish(progress.mark({}, "c", True, "2026-11-24T10:10:00"), "c")
    assert report.startswith("recorded and pushed"), report

    text = git(origin, "show", f"{shared.BRANCH}:{progress.FILE_NAME}")
    record = progress.parse(text)
    assert record["a"].done and record["c"].done and record["b"].note == "broken wire"


def test_an_unchanged_record_makes_no_commit(checkouts):
    _, laptop_folder, _ = checkouts
    laptop = shared.SharedRecord(git=Git(laptop_folder), writer=True)
    record = progress.mark({}, "a", True, "2026-11-24T10:00:00")
    laptop.publish(record, "a")
    before = git(laptop_folder, "rev-parse", shared.BRANCH)

    assert "nothing new" in laptop.publish(record, "a again")
    assert git(laptop_folder, "rev-parse", shared.BRANCH) == before


def test_offline_the_record_stays_on_the_laptop(checkouts, tmp_path):
    _, laptop_folder, _ = checkouts
    git(laptop_folder, "remote", "set-url", "origin", str(tmp_path / "nowhere.git"))
    laptop = shared.SharedRecord(git=Git(laptop_folder), writer=True)

    report = laptop.publish(progress.mark({}, "a", True, "2026-11-24T10:00:00"), "a")

    assert report.startswith("recorded on this laptop, not pushed")
    assert laptop.read()["a"].done
    assert "not pushed yet" in laptop.where()


def test_nothing_raises_outside_a_repository(tmp_path):
    record = shared.SharedRecord(git=Git(tmp_path), writer=True)

    assert record.read() == {}
    assert record.publish({}, "x").startswith("not recorded")
    assert "nothing on origin" in record.where()


# --- the page ------------------------------------------------------------


class FakeShared:
    def __init__(self, writer=True):
        self.is_writer = writer
        self.record = {}
        self.report = None
        self.written = []

    def read(self):
        return self.record

    def where(self):
        return "here"

    def write(self, record, summary):
        self.record = record
        self.written.append(summary)


def node(writer=True):
    from pathlib import Path
    from types import SimpleNamespace

    owner = SimpleNamespace(
        owners=[], name="manual tests", is_simulated=True, path=Path("tests/manual tests")
    )
    return InstallationSol2(owner=owner, shared=FakeShared(writer))


FIRST = "01 check the present state"


def where_you_left_off(guide):
    return guide._snapshot_if_opened(())["where you left off"]["html"]


def test_the_guide_opens_on_the_first_step_not_done():
    guide = node()
    states = guide._snapshot_if_opened(())

    assert states["progress"]["value"] == f"0 of {len(steps.KEYS)} steps done"
    assert FIRST in where_you_left_off(guide)
    assert "done: next step" in guide.snapshot_children
    # Read first, press after: the step is drawn above its button.
    keys = list(states)
    assert keys.index("where you left off") < keys.index("done: next step") < keys.index("steps")


def test_done_goes_on_to_the_next_step_and_back_one_returns():
    guide = node()

    guide.done_current()
    assert guide.shared.record["check the present state"].done
    assert "02 record the configuration" in where_you_left_off(guide)
    table = guide._snapshot_if_opened(())["steps"]["html"]
    assert "&#10003;</td><td><a href='/app/tests/manual%20tests/installation%20PCB%20solution%202/all%20steps/01%20check" in table
    assert "&#8594;</td><td><a" in table and "<strong>02 record the configuration</strong>" in table

    guide.back_one()
    assert FIRST in where_you_left_off(guide)


def test_the_note_box_writes_the_current_steps_note():
    guide = node()
    guide.save("Cable broken between the microphone and the female1 base\r\n")

    assert guide.shared.record["check the present state"].note == (
        "Cable broken between the microphone and the female1 base"
    )


def test_a_step_page_ticks_unticks_and_then_points_on():
    guide = node()
    step = guide["all steps"][FIRST]

    assert "done" in step.snapshot_children
    step.done()
    assert "not done after all" in step.snapshot_children
    go_on = step._snapshot_if_opened(())["go on"]["html"]
    assert "02%20record%20the%20configuration" in go_on and "resume where you left off" in go_on
    step.undo()
    assert not guide.shared.record["check the present state"].done
    assert "editor" in step._snapshot_if_opened(())["note"]


def test_when_every_step_is_done_the_guide_says_so():
    guide = node()
    for key in steps.KEYS:
        guide.shared.record = progress.mark(guide.shared.record, key, True, "2026-11-24T10:00:00")

    assert "Every step is done" in where_you_left_off(guide)
    assert "done: next step" not in guide.snapshot_children
    assert guide.done_current() == "every step is done"


def test_elsewhere_the_page_is_read_only():
    guide = node(writer=False)
    step = guide["all steps"][FIRST]

    assert step.snapshot_children == {}
    assert "value" in step._snapshot_if_opened(())["note"]
    assert "done: next step" not in guide.snapshot_children
    assert "fetch the record" in guide.snapshot_children


def test_every_picture_is_well_formed_svg():
    from xml.dom import minidom

    from colloquy.tests.installation_sol2 import pictures

    for key in pictures.PICTURES:
        assert key in steps.KEYS, key
        minidom.parseString("<r>" + pictures.picture(key) + "</r>")
    assert pictures.picture("firmware 5") == ""


def test_a_press_is_shown_at_once_and_pushed_by_the_worker(checkouts):
    _, laptop_folder, _ = checkouts
    laptop = shared.SharedRecord(git=Git(laptop_folder), writer=True)

    assert laptop.write(progress.mark({}, "a", True, "2026-11-24T10:00:00"), "a") is None
    assert laptop.read()["a"].done
    laptop._worker.join(30)

    assert laptop.report.startswith("recorded and pushed"), laptop.report
    assert "as on origin" in laptop.where()


def test_its_group_page_renders_with_it_in():
    """The group asks every test whether it is running (2026-11-24: the
    guide had no `is_started`, and opening `manual tests` stopped the
    server)."""
    from types import SimpleNamespace

    from colloquy.tests.group import TestGroup

    group = TestGroup(
        owner=SimpleNamespace(owners=[], name="tests", is_simulated=True),
        name="manual tests",
        summary="...",
    )
    group.fill([InstallationSol2(owner=group, shared=FakeShared())])

    states = group._snapshot_if_opened(("tests", "manual tests"))

    assert "running now" not in states


def test_the_board_plot_is_the_backplane_as_it_is_now():
    """`export_backplane_front.py` writes the plot and its points with the
    `.kicad_pcb`'s digest; a board changed since is a stale plot. Re-run
    the generator (it needs KiCad)."""
    import json

    from colloquy.hardware.pcb_files.gerbers import REPO_FOLDER, digest
    from colloquy.tests.installation_sol2 import pictures

    record = json.loads((pictures.HARDWARE / "backplane-front.json").read_text(encoding="utf-8"))
    assert (pictures.HARDWARE / "backplane-front.svg").is_file()
    assert record["source sha256"] == digest(REPO_FOLDER / record["source"]), (
        "backplane.kicad_pcb changed: run `py export_backplane_front.py`"
    )


def test_every_board_view_names_parts_that_are_on_the_board():
    from colloquy.tests.installation_sol2 import pictures

    parts = pictures._plot()["parts"]
    for key, make in pictures.BOARD_VIEWS.items():
        assert key in steps.KEYS, key
        drawn = make()
        assert pictures.PLOT_URL in drawn, key
    for refs, _ in (
        pictures.POWER_ROW_MARKS + pictures.POWER_LEDS + pictures.TONE_LEDS + pictures.NOT_HERE
    ):
        assert refs in parts, refs


def test_the_power_row_is_where_the_silkscreen_says():
    """The 2026-11-24 mix-up: MEGA 5V's test pin is TPUSB in the power row,
    and TP32 is a bare pad beside JP1, the AGND-GND bond."""
    from colloquy.tests.installation_sol2 import pictures

    parts = pictures._plot()["parts"]
    assert parts["TPUSB"]["pin"] and parts["TP34"]["pin"]
    assert not parts["TP32"]["pin"]
    assert "**`5V`, `12V`, `USB`, `GND`**" in steps.POWER_ROW
