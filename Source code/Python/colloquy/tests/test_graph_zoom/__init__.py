import numpy as np
import pandas as pd

from colloquy.base import Base
from ..test_light_sensor_values.utils import FEMALE_COLUMNS, dataframe_to_chart_json


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

    def _dummy_data_frame(self):
        rng = np.random.default_rng(0)  # fixed seed: same data every view
        n = 2000
        seconds = np.linspace(0, 120, n)
        df = pd.DataFrame({"seconds": seconds})
        for i, column in enumerate(FEMALE_COLUMNS, start=1):
            noise = rng.integers(-8, 8, n)
            wave = 60 * np.sin(seconds / (2 + i)) + 30 * np.sin(seconds * 3 + i)
            df[column] = 300 + wave + noise
        return df

    def _dummy_chart(self):
        return dataframe_to_chart_json(
            self._dummy_data_frame(), x_column="seconds", y_columns=FEMALE_COLUMNS
        )

    def _snapshot_if_opened(self, path):
        states = {}
        states["dummy graph"] = {
            "path": path + ("dummy graph",),
            "name": "dummy graph",
            "chart": self._dummy_chart(),
        }
        return states

    @property
    def snapshot_children(self):
        return {}
