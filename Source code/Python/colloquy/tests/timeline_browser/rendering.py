import re
from dataclasses import dataclass

from yattag import Doc

from colloquy.utils import timelap_to_string

# One entry per line: "<duration_in_seconds> <description>". Duration 0 is
# an instantaneous event; anything else is an activity spanning that many
# seconds from its start. Blank lines and lines starting with "#" (used for
# a leading title/description block) are ignored.
_ENTRY_RE = re.compile(r"^(\d+(?:\.\d+)?)\s+(\S.*)$")


@dataclass
class TimelineEntry:
    start_seconds: float
    duration_seconds: float
    description: str

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


def parse_entries(content):
    """Entries in file order, each starting where the previous one ended.
    Events (duration 0) don't advance the clock, so consecutive events
    share the same start time - that's how "several things happen at
    once" is expressed in this format."""
    entries = []
    elapsed = 0.0
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
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


def render_html(content):
    doc, tag, text = Doc().tagtext()

    for line in parse_title(content):
        with tag("p", klass="timeline-title"):
            text(line)

    with tag("div", klass="timeline"):
        for entry in parse_entries(content):
            start_label = f"t={timelap_to_string(entry.start_seconds)}"
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

    return doc.getvalue()
