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
    from types import SimpleNamespace

    owner = SimpleNamespace(owners=[], name="manual tests", is_simulated=True)
    return InstallationSol2(owner=owner, shared=FakeShared(writer))


def test_the_page_renders_and_points_at_the_first_step():
    guide = node()
    states = guide._snapshot_if_opened(())

    assert states["progress"]["value"] == f"0 of {len(steps.KEYS)} steps done"
    assert states["next step"]["value"] == "01 check the present state"
    assert "01 check the present state" in guide.snapshot_children


def test_a_step_is_ticked_noted_and_unticked():
    guide = node()
    step = guide["01 check the present state"]

    assert "done" in step.snapshot_children
    step.done()
    assert guide.shared.record["check the present state"].done
    assert "not done after all" in step.snapshot_children
    step.save("J5 cable: pin 7 open at the body end\r\n")
    assert guide.shared.record["check the present state"].note == "J5 cable: pin 7 open at the body end"
    step.undo()
    assert not guide.shared.record["check the present state"].done

    states = guide._snapshot_if_opened(())
    assert states["next step"]["value"] == "01 check the present state"
    assert "editor" in step._snapshot_if_opened(())["note"]


def test_elsewhere_the_page_is_read_only():
    guide = node(writer=False)
    step = guide["01 check the present state"]

    assert step.snapshot_children == {}
    assert "value" in step._snapshot_if_opened(())["note"]
    assert "fetch the record" in guide.snapshot_children


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
