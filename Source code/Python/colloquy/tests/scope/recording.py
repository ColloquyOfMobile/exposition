# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/scope/recording.py

"""One run on the disk: the clock, and every channel's counts.

**It kept nothing at first, and that was wrong for the reason the
Goertzel ear's was.** The argument was that a scope trace is looked at
now, at a wire, with a probe still in your hand, and that filing a
hundred thousand samples would keep the half nobody wants. The half
nobody wants turned out to be the half somebody asks for first: the
moment two microphones are being compared, the questions are all *between*
runs - is A1 still quiet after I reseated it, was it this bad before I
moved it, does the difference follow the lead when I swap the two - and
not one of them can be answered from the single run that happens to be in
memory, which is all there ever is, since `setup()` clears the recording
and a restart takes it anyway.

It is also the only way the run can leave this machine. A picture on a
page cannot be sent to anybody; a file can.

**The format is one row per pair**, the clock in seconds from the start of
the run and one column per channel, with the channel names in the header.
Read back out of the header rather than out of the code, exactly as the
ear reads its pitches: a channel list that changes later must not be able
to relabel a measurement somebody already took.

Six decimals on the clock because samples are about 104 us apart - three
would put a whole run's samples into eleven distinct timestamps and draw a
staircase.

**The gaps are in the file and nothing marks them.** A row is a moment,
the rows are in order, and two consecutive rows may be 104 us or 40 ms
apart; that is the recording, and it is why `trace.py` places captures
where they fell. Anything reading this back must not assume a fixed
interval between rows - which is why the clock is a column rather than
implied by the row number.
"""
import csv

CLOCK = "seconds"


def write(trace, path):
    """Put the recording on the disk, and say where it went.

    Written at the end from what is in memory rather than a row at a time
    as captures arrive - a press lands on the request thread while the
    captures are read on the loop thread, and two threads on one file
    handle is a real hazard where losing the last quarter second of a
    killed run is not. `setdown` runs in `_run_in_context`'s `finally`,
    so a stop, an error and a refusal all reach it.
    """
    lines = trace.series()
    names = list(trace.names)
    columns = [lines[name] for name in names]

    with open(path, "w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow([CLOCK] + names)
        for index in range(len(trace)):
            seconds, _ = columns[0][index]
            writer.writerow(
                [f"{seconds:.6f}"] + [str(column[index][1]) for column in columns]
            )
    return path


def read(path):
    """A written run back as `{name: [(seconds, count), ...]}`.

    Channel names off the header, so a file outlives the code that made
    it. A row that cannot be read is skipped rather than raising: a run
    killed mid-write leaves a half line at the end, and losing it is not
    worth losing the hour before it.
    """
    series = {}
    with open(path, newline="", encoding="utf-8") as handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration:
            return series

        names = header[1:]
        columns = [[] for _ in names]
        for row in reader:
            if len(row) != len(names) + 1:
                continue
            try:
                seconds = float(row[0])
                values = [int(value) for value in row[1:]]
            except ValueError:
                continue
            for column, value in zip(columns, values):
                column.append((seconds, value))
        series = dict(zip(names, columns))
    return series


def describe(path):
    """What is in a file, without reading all of it.

    The size, because a run of a few minutes is tens of megabytes and
    that is worth knowing before opening one - and because it is the one
    fact about a recording that a listing can give away for nothing.
    """
    size = path.stat().st_size
    if size >= 1024 * 1024:
        return f"{size / (1024 * 1024):.1f} MB"
    return f"{size / 1024:.0f} kB"
