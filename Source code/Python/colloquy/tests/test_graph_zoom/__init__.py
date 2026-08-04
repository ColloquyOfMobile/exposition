import io
import numpy as np
import pandas as pd

from colloquy.base import Base
from ..test_light_sensor_values.utils import (
    FEMALE_COLUMNS,
    compute_pulses,
    plot_full_measurement_as_svg,
)


class TestGraphZoom(Base):
    """Dummy-data demo of the zoom/pan graph tool (see
    server2/wsgi2.py's SVG_ZOOM_SCRIPT), so it can be exercised without
    waiting on a real, multi-minute test_light_sensor_values run.
    Generates a synthetic dataset shaped like the real light-sensor logs
    (same columns, same post-processing) and renders it through the exact
    same plotting path real runs use, so the graph you get here behaves
    identically to the real one.
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

    def _dummy_svg(self):
        df = self._dummy_data_frame()
        for column in FEMALE_COLUMNS:
            prefix = column.replace("female", "f")
            filtered, logic, durations, counts = compute_pulses(
                df, column, window_size=5
            )
            df[f"{prefix} filtered"] = filtered
            df[f"{prefix} logic"] = logic

        svg = io.StringIO()
        plot_full_measurement_as_svg(output=svg, df=df)
        return svg.getvalue()

    def _snapshot_if_opened(self, path):
        states = {}
        states["dummy graph"] = {
            "path": path + ("dummy graph",),
            "name": "dummy graph",
            "svg": self._dummy_svg(),
        }
        return states

    @property
    def snapshot_children(self):
        return {}
