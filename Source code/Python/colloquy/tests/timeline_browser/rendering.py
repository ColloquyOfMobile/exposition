import re
from dataclasses import dataclass, field
from pathlib import Path

from yattag import Doc

from colloquy.utils import timelap_to_string

# One entry per line: "<duration_in_seconds> <description>". Duration 0 is
# an instantaneous event; anything else is an activity spanning that many
# seconds from its start. Blank lines and lines starting with "#" (used for
# a leading title/description block) are ignored.
_ENTRY_RE = re.compile(r"^(\d+(?:\.\d+)?)\s+(\S.*)$")

# "-> <other-timeline>" or "-> <other-timeline> : <label>" starts a child
# thread's own timeline concurrently at this point - see parse_entries.
_INCLUDE_RE = re.compile(r"^->\s*(\S+?)(?:\s*:\s*(.+))?$")

_TIMELINES_FOLDER = Path(__file__).resolve().parent.parent / "timelines"


@dataclass
class TimelineEntry:
    start_seconds: float
    duration_seconds: float
    description: str
    # Populated only for "-> other-timeline" lines: the referenced
    # timeline's own entries (recursively expanded), rendered nested under
    # this one instead of a plain event/activity row.
    children: list = field(default_factory=list)
    is_branch: bool = False
    is_problem: bool = False

    @property
    def is_event(self):
        return self.duration_seconds == 0


def parse_title(content):
    """Leading run of "#" comment lines, stripped of their leading '#'s -
    the timeline's own title/description, shown above its rendered rows."""
    lines = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line:
            if lines:
                break
            continue
        if not line.startswith("#"):
            break
        lines.append(line.lstrip("#").strip())
    return lines


def parse_entries(content, _folder=None, _visited=frozenset()):
    """Entries in file order, each starting where the previous one ended.
    Events (duration 0) don't advance the clock, so consecutive events
    share the same start time - that's how "several things happen at
    once" is expressed in this format.

    "-> other-timeline[: label]" lines are a different kind of entry: they
    don't take any time themselves (a thread starting a child thread is
    instantaneous), and the child's own timeline is parsed recursively and
    attached as .children, to be rendered as a nested, concurrently-running
    sub-timeline - see render_html. _visited guards against include cycles
    (A includes B includes A): the first repeat along a given branch is
    reported instead of recursing forever.
    """
    if _folder is None:
        _folder = _TIMELINES_FOLDER

    entries = []
    elapsed = 0.0
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        include_match = _INCLUDE_RE.match(line)
        if include_match:
            name, label = include_match.group(1), include_match.group(2)
            display = f"{name}" + (f" ({label})" if label else "")

            if name in _visited:
                description = (
                    f"-> {display} - already expanded earlier on this branch, "
                    "stopped here to avoid an include cycle"
                )
                entries.append(
                    TimelineEntry(
                        start_seconds=elapsed,
                        duration_seconds=0.0,
                        description=description,
                        is_branch=True,
                        is_problem=True,
                    )
                )
                continue

            child_path = (_folder / name).with_suffix(".timeline")
            if not child_path.is_file():
                entries.append(
                    TimelineEntry(
                        start_seconds=elapsed,
                        duration_seconds=0.0,
                        description=f"-> {display} - missing file, nothing to expand",
                        is_branch=True,
                        is_problem=True,
                    )
                )
                continue

            child_content = child_path.read_text(encoding="utf-8")
            children = parse_entries(
                child_content, _folder=_folder, _visited=_visited | {name}
            )
            entries.append(
                TimelineEntry(
                    start_seconds=elapsed,
                    duration_seconds=0.0,
                    description=f"-> {display} (starts here, runs concurrently on its own clock)",
                    children=children,
                    is_branch=True,
                )
            )
            continue

        match = _ENTRY_RE.match(line)
        if match is None:
            continue
        duration = float(match.group(1))
        description = match.group(2)
        entries.append(
            TimelineEntry(
                start_seconds=elapsed,
                duration_seconds=duration,
                description=description,
            )
        )
        elapsed += duration

    return entries


def _render_entries(tag, text, entries):
    with tag("div", klass="timeline"):
        for entry in entries:
            start_label = f"t={timelap_to_string(entry.start_seconds)}"

            if entry.is_branch:
                row_klass = "timeline-row timeline-branch"
                if entry.is_problem:
                    row_klass += " timeline-problem"
                with tag("div", klass=row_klass):
                    with tag("div", klass="timeline-time"):
                        text(start_label)
                    with tag("div", klass="timeline-marker"):
                        text("start")
                    with tag("div", klass="timeline-desc"):
                        text(entry.description)
                if entry.children:
                    with tag("div", klass="timeline-nested"):
                        _render_entries(tag, text, entry.children)
                continue

            if entry.is_event:
                marker_label = "event"
                row_klass = "timeline-row timeline-event"
            else:
                marker_label = f"+{timelap_to_string(entry.duration_seconds)}"
                row_klass = "timeline-row timeline-activity"

            with tag("div", klass=row_klass):
                with tag("div", klass="timeline-time"):
                    text(start_label)
                with tag("div", klass="timeline-marker"):
                    text(marker_label)
                with tag("div", klass="timeline-desc"):
                    text(entry.description)


def render_html(content):
    doc, tag, text = Doc().tagtext()

    for line in parse_title(content):
        with tag("p", klass="timeline-title"):
            text(line)

    _render_entries(tag, text, parse_entries(content))

    return doc.getvalue()
