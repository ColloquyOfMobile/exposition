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
    # timeline's own entries (recursively expanded) and its optional
    # ": label" (e.g. "O drive", "male1") - see flatten_entries, which
    # carries the label into every descendant's description as context
    # instead of just dropping it.
    children: list = field(default_factory=list)
    label: str = None
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
                    label=label,
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


def flatten_entries(entries, offset=0.0, context=()):
    """Resolve every "-> other-timeline" branch into one flat, chronologically
    sorted sequence of what actually happens - a black-box view that doesn't
    expose which entries came from a child thread being started. A normal
    include vanishes, replaced in place by its own (recursively flattened)
    entries, offset to start at the including line's own absolute time; only
    a genuine problem (missing include / cycle) survives as its own row,
    since that's a defect in the timeline itself, not an implementation
    detail worth hiding.

    Dropping a branch entirely would also drop its ": label" (e.g. "O
    drive" vs "P drive", "male1" vs "male2") - the only thing that told two
    otherwise-identical included timelines apart. Instead, every labelled
    branch's label is carried in `context` and stamped as a "[label / ...]"
    prefix onto each of its descendants' descriptions, so e.g. two Drive
    threads merged under one Male read as distinguishable events rather
    than identical-looking duplicates.
    """
    flat = []
    for entry in entries:
        absolute_start = entry.start_seconds + offset
        prefix = f"[{' / '.join(context)}] " if context else ""

        if entry.is_branch:
            if entry.is_problem:
                flat.append(
                    TimelineEntry(
                        start_seconds=absolute_start,
                        duration_seconds=0.0,
                        description=prefix + entry.description,
                        is_problem=True,
                    )
                )
            else:
                child_context = context + (entry.label,) if entry.label else context
                flat.extend(
                    flatten_entries(
                        entry.children, offset=absolute_start, context=child_context
                    )
                )
            continue

        flat.append(
            TimelineEntry(
                start_seconds=absolute_start,
                duration_seconds=entry.duration_seconds,
                description=prefix + entry.description,
            )
        )
    return flat


def render_html(content):
    doc, tag, text = Doc().tagtext()

    for line in parse_title(content):
        with tag("p", klass="timeline-title"):
            text(line)

    flat = sorted(
        flatten_entries(parse_entries(content)), key=lambda entry: entry.start_seconds
    )

    with tag("div", klass="timeline"):
        for entry in flat:
            start_label = f"t={timelap_to_string(entry.start_seconds)}"

            if entry.is_problem:
                marker_label = "!"
                row_klass = "timeline-row timeline-problem"
            elif entry.is_event:
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

    return doc.getvalue()
