import numpy as np
import pandas as pd

from colloquy.base import Base
from ..test_light_sensor_values.utils import FEMALE_COLUMNS, dataframe_to_chart_json
from colloquy.ui import leaves


def dummy_data_frame():
    """The demo dataset, shaped like a light-sensor log.

    A module function rather than a method because there are two views of
    it now - this one and `test graph without script`, which draws the
    same numbers with no JavaScript at all. The comparison is only worth
    anything if it is the same data, so there is one place it comes from.
    """
    rng = np.random.default_rng(0)  # fixed seed: same data every view
    n = 2000
    seconds = np.linspace(0, 120, n)
    df = pd.DataFrame({"seconds": seconds})
    for i, column in enumerate(FEMALE_COLUMNS, start=1):
        noise = rng.integers(-8, 8, n)
        wave = 60 * np.sin(seconds / (2 + i)) + 30 * np.sin(seconds * 3 + i)
        df[column] = 300 + wave + noise
    return df


def dummy_points(column=None):
    """One column of it as (seconds, value) pairs - what `GraphView` takes."""
    frame = dummy_data_frame()
    column = column or FEMALE_COLUMNS[0]
    return list(zip(frame["seconds"].tolist(), frame[column].tolist()))


class TestGraphZoom(Base):
    """Dummy-data demo of the interactive graph tool (see
    server2/wsgi2.py's UPLOT_INIT_SCRIPT), so it can be exercised without
    waiting on a real, multi-minute test_light_sensor_values run.
    Generates a synthetic dataset shaped like the real light-sensor logs
    (same columns) and renders it through the exact same chart path real
    runs use, so this behaves identically to the real one.
    """

    def __init__(self, owner):
        super().__init__(owner=owner)

    @property
    def name(self):
        return "test graph zoom"

    def _dummy_chart(self):
        return dataframe_to_chart_json(
            dummy_data_frame(), x_column="seconds", y_columns=FEMALE_COLUMNS
        )

    def _snapshot_if_opened(self, path):
        states = {}
        states["dummy graph"] = leaves.chart(path, "dummy graph", self._dummy_chart())
        return states

    @property
    def snapshot_children(self):
        return {}
