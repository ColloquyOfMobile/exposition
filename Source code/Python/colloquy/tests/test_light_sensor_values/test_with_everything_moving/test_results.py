# -*- coding: utf-8 -*-
# colloquy/tests/test_light_sensor_values/test_with_everything_moving/test_results.py
import io

import pandas as pd

from colloquy.base import Base
from ..utils import (
    FEMALE_COLUMNS,
    compute_pulses,
    plot_counts_as_svg,
)
from colloquy.ui import leaves
from colloquy.ui.graph_view import Columns, GraphView


class TestResults(Base):
    def __init__(self, owner, result_rows):
        super().__init__(owner=owner)

        columns = ["seconds"] + list(FEMALE_COLUMNS)
        self._data_frame = df = pd.DataFrame(result_rows, columns=columns)
        df.columns = df.columns.str.strip()

        self._results = {}
        self._post_process()

        # The run's raw reading, drawn by the server. A node rather than
        # a leaf because it has controls - the density, the page size and
        # which page - and that is how the tree draws a thing you can act
        # on. `Columns` is a view over the dataframe's own arrays, not a
        # copy of them: a forty-minute run is a hundred thousand rows and
        # there is no reason to hold it twice to draw four hundred of it.
        # See colloquy/ui/graph_view.py.
        self._graph = GraphView(
            owner=self,
            series=[(column, self._column_view(column)) for column in FEMALE_COLUMNS],
            name="full measurement",
        )

    @property
    def name(self):
        return "test results"

    def _post_process(self, window_size=5):
        df = self._data_frame
        for column in FEMALE_COLUMNS:
            prefix = column.replace("female", "f")
            filtered, logic, durations, counts = compute_pulses(df, column, window_size)
            df[f"{prefix} filtered"] = filtered
            df[f"{prefix} logic"] = logic
            self._results[column] = {"durations": durations, "counts": counts}

    def _column_view(self, column):
        """One female's reading as (seconds, value) pairs, unmaterialised."""
        df = self._data_frame
        return Columns(
            df["seconds"].to_numpy(dtype=float, copy=False),
            df[column].to_numpy(dtype=float, copy=False),
        )

    def counts_as_svg(self, column):
        svg = io.StringIO()
        plot_counts_as_svg(
            output=svg,
            counts=self._results[column]["counts"],
            title=f"{column} pulse complementary cumulative histogram",
        )
        return svg.getvalue()

    def _snapshot_if_opened(self, path):
        states = {}
        for column in FEMALE_COLUMNS:
            if len(self._results[column]["counts"]) == 0:
                continue
            key = f"{column} pulse durations"
            states[key] = leaves.svg(path, key, self.counts_as_svg(column))
        return states

    @property
    def snapshot_children(self):
        return {self._graph.name: self._graph}
