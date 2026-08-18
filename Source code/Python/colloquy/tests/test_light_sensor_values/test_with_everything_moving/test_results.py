# -*- coding: utf-8 -*-
# colloquy/tests/test_light_sensor_values/test_with_everything_moving/test_results.py
import io

import pandas as pd

from colloquy.base import Base
from ..utils import (
    FEMALE_COLUMNS,
    compute_pulses,
    dataframe_to_chart_json,
    plot_counts_as_svg,
)
from colloquy.ui import leaves


class TestResults(Base):
    def __init__(self, owner, result_rows):
        super().__init__(owner=owner)

        columns = ["seconds"] + list(FEMALE_COLUMNS)
        self._data_frame = df = pd.DataFrame(result_rows, columns=columns)
        df.columns = df.columns.str.strip()

        self._results = {}
        self._post_process()

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

    def full_measurement_as_chart(self):
        return dataframe_to_chart_json(
            self._data_frame, x_column="seconds", y_columns=FEMALE_COLUMNS
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
        states["full measurement"] = leaves.chart(
            path,
            "full measurement",
            self.full_measurement_as_chart(),
        )
        for column in FEMALE_COLUMNS:
            if len(self._results[column]["counts"]) == 0:
                continue
            key = f"{column} pulse durations"
            states[key] = leaves.svg(path, key, self.counts_as_svg(column))
        return states

    @property
    def snapshot_children(self):
        return {}
