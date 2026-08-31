# -*- coding: utf-8 -*-
# Source code/Python/colloquy/tests/group.py

"""The two kinds of hardware test, and the line between them.

`colloquy/tests/` had grown to fourteen entries in one flat list, and a
flat list says the only thing that matters about a test is its name. It
is not: the first thing anybody wants to know, standing in front of the
rack with twenty minutes, is **whether they have to stay for it**.

So there are two groups, and the rule they are filed by is one question:

> Does this run reach its answer on its own, or is a person the
> measuring instrument?

- **autotests** press start and write the answer down - a CSV, an SVG, a
  grid of verdicts, a diagnosis. You can walk away from one and read it
  afterwards, and several of them run for forty minutes precisely
  because you can.
- **manual tests** produce nothing a file could hold. What they make is
  light, or sound, or a servo moving, and the instrument that records it
  is somebody's eye, ear or hand. `test neopixels` cycles every segment
  so a person can see the right one light; `test sensors` waits for a
  hand over a photodiode; `test audio at 12v` cannot even *begin* its
  second half until somebody has moved a supply lead.

The line is not about how long a test runs or how much hardware it
touches, and it is deliberately not about whether the code happens to
open a results file. It is about who does the perceiving. That is the
distinction that changes what you do next, and none of the others do.

**Two things stay outside both groups**, as direct children of `tests`:
the uPlot demo and `test graph without script`. They are not tests of
the piece at all - they draw the same dummy numbers two ways so the two
ways can be compared - and filing them under either heading would make
the heading mean less. See tests/__init__.py.
"""
from colloquy.base import Base
from colloquy.ui import leaves


class TestGroup(Base):
    """One heading, and the tests filed under it.

    A single class rather than an `Autotests` and a `ManualTests`: what
    differs between the two is a name, a sentence, and a list, and two
    near-identical classes would have been the fourth place in this repo
    where the same dispatch was written out again.

    It forwards `colloquy`, `drivers` and `params` to its owner, because
    inserting a node between `Tests` and a test must not change what a
    test can reach: `test_light_sensor_values` asks its owner for both
    `params` and `drivers` by name, and `BaseThread.colloquy` walks the
    owner chain a link at a time.
    """

    def __init__(self, owner, name, summary):
        super().__init__(owner=owner)
        self._name = name
        self._summary = summary
        self._tests = []
        # Tests that want hardware the installation will never have -
        # Thomas's boards live on an office desk. Offering one in the
        # gallery is offering a run that can only refuse. The gate is
        # `is_simulated`, so it hides on the installation and shows
        # everywhere else, the bench included.
        self._bench_only = set()

    def fill(self, tests, bench_only=()):
        """Adopt these tests, after they have been built.

        Two steps rather than one because of the chicken and egg in the
        owner pointer: a test is constructed with its group as `owner`,
        so the group has to exist before any of them do, and cannot be
        handed them in its own constructor.

        `bench_only` is a set of **names**, not of objects. Identity
        would work on the real tree - every test is one object built
        once - and would quietly stop working the moment anything was
        rebuilt or doubled, which is exactly what a test of this file
        does.
        """
        self._tests = list(tests)
        self._bench_only = set(bench_only)
        for test in self._tests:
            self[test.name] = test
        return self

    @property
    def name(self):
        return self._name

    @property
    def summary(self):
        return self._summary

    @property
    def tests(self):
        return list(self._tests)

    # --- what a test reaches through its owner ----------------------------

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def drivers(self):
        return self.owner.drivers

    @property
    def params(self):
        return self.owner.params

    @property
    def workspace(self):
        return self.owner.workspace

    # --- the page ---------------------------------------------------------

    @property
    def snapshot_children(self):
        return {
            test.name: test
            for test in self._tests
            if not (test.name in self._bench_only and not self.is_simulated)
        }

    def _snapshot_if_opened(self, path):
        states = super()._snapshot_if_opened(path)
        leaf = leaves.into(states, path)
        leaf("what these are", self._summary)

        running = sorted(test.name for test in self._tests if test.is_started)
        if running:
            leaf("running now", ", ".join(running))
        return states
