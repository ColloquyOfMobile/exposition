# -*- coding: utf-8 -*-
# colloquy/base_thread/__init__.py
import traceback
from time import time, sleep
from pathlib import Path
from colloquy.base import Base
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import io
import matplotlib.ticker as mticker


class TestResults(Base):
    def __init__(self, owner, result_rows):
        super().__init__(owner=owner)

        columns = ["seconds"] + [f"female{i + 1}" for i in range(3)]

        self._data_frame = df = pd.DataFrame(result_rows, columns=columns)
        self._threshold = 350
        self._counts = None
        self.post_process()
        # df["seconds"] = df["seconds"].astype(float)

    @property
    def name(self):
        return f"test results"

    def show_full_measurement_in_gui(self):
        df = self._data_frame

        fig, ax1 = plt.subplots(figsize=(10, 5))

        # Main sensor signals
        ax1.plot(df["seconds"], df["female1"], label="female1", linewidth=2)
        ax1.plot(df["seconds"], df["female2"], label="female2", linewidth=2)
        ax1.plot(df["seconds"], df["female3"], label="female3", linewidth=2)
        ax1.axhline(
            y=self._threshold,
            label=f"threshold ({self._threshold})",
            linewidth=2,
        )

        ax1.set_xlabel("Time (s)")
        ax1.set_ylabel("Sensor value")
        # ax1.grid(True)

        ax1.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))

        # Combine legends from both axes
        lines = ax1.get_lines()
        labels = [line.get_label() for line in lines]
        ax1.legend(lines, labels)

        plt.title("Sensor Data")
        plt.tight_layout()

        plt.show()

        plt.close()

        # return svg.getvalue()

    def counts_as_svg(self):
        """
        Plot the complementary cumulative histogram.

        Parameters
        ----------
        output : Path or str
            Output SVG filename.
        counts : array-like
            counts[i] = number of pulses lasting at least i seconds.
        title : str
            Plot title.
        """
        title = f"pulse complementary cumulative histogram."
        counts = self._counts
        seconds = np.arange(len(counts))

        fig, ax = plt.subplots(figsize=(10, 5))

        ax.step(seconds, counts, where="post", linewidth=2)
        ax.set_xlabel("Pulse duration (s)")
        ax.set_ylabel("Number of pulses ≥ duration")
        ax.set_title(title)

        ax.grid(True, alpha=0.3)

        fig.tight_layout()

        svg = io.StringIO()
        fig.savefig(svg, format="svg")
        plt.close(fig)
        return svg.getvalue()

    def post_process(
        self,
    ):
        window_size = 5
        df = self._data_frame

        # Nettoie les noms de colonnes si le CSV contient des espaces
        df.columns = df.columns.str.strip()

        # Moyennes glissantes
        for column in ("female1", "female2", "female3"):
            column_filtered = f"{column} filtered"
            df[column_filtered] = (
                df[column].rolling(window=window_size, min_periods=1).mean()
            )
            df[f"{column} logic"] = df[column_filtered].where(
                df[column_filtered] > self._threshold, 0
            )

            high = df[column_filtered] > self._threshold

            rising_edge = f"{column} rising edge"
            df[rising_edge] = high & ~high.shift(fill_value=False)

            falling_edge = f"{column} falling edge"
            df[falling_edge] = ~high & high.shift(fill_value=False)

            pulse_id = f"{column} pulse id"
            df[pulse_id] = df[rising_edge].cumsum()

            # Set pulse_id to 0 when not inside a pulse
            df[pulse_id] = df[pulse_id].where(high, 0)

            start_times = df.loc[df[rising_edge], "seconds"].to_numpy()
            stop_times = df.loc[df[falling_edge], "seconds"].to_numpy()
            durations = stop_times[: len(start_times)] - start_times[: len(stop_times)]

            if len(durations) == 0:
                self._counts = np.array([])
                continue

            # survival function (or complementary cumulative histogram)
            seconds = np.arange(int(np.ceil(durations.max())) + 1)
            self._counts = (durations[:, None] >= seconds).sum(axis=0)

    # def snapshot(self, path, focus_path):
    # states = super().snapshot(path=path)
    # _path = states["path"]
    # states["show full measurement in GUI"] = self.show_full_measurement_in_gui
    # states["plot"] =  {
    # "path": _path + ("plot", ),
    # "name": "plot",
    # "svg": self.counts_as_svg(),
    # }
    # return states

    def _snapshot_if_opened(self, path):
        states = {}
        states["show full measurement in GUI"] = self.show_full_measurement_in_gui
        states["plot"] = {
            "path": path + ("plot",),
            "name": "plot",
            "svg": self.counts_as_svg(),
        }
        return states

    @property
    def snapshot_children(self):
        return {}

    # @property
    # def snapshot_children(self):
    # children = {}
    # children["show full measurement in GUI"] = self.show_full_measurement_in_gui
    # children["plot"] =  {
    # "path": _path + ("plot", ),
    # "name": "plot",
    # "svg": self.counts_as_svg(),
    # }
    # return children
