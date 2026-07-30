from time import time
from collections import deque
import csv
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
from io import StringIO
from pathlib import Path


threshold = 310
FEMALE_COLUMNS = ("female1", "female2", "female3")
FEMALE_COLORS = ("tab:blue", "tab:orange", "tab:green")


def _decimate_min_max(x, y, max_points=2000):
    """Bucket (x, y) into at most `max_points` points, keeping each bucket's
    min and max y so brief pulses survive downsampling (unlike plain
    every-Nth-point striding, which can hide short spikes entirely)."""
    x = np.asarray(x)
    y = np.asarray(y)
    n = len(x)
    if n <= max_points:
        return x, y

    buckets = max(1, max_points // 2)
    edges = np.linspace(0, n, buckets + 1).astype(int)

    xs, ys = [], []
    for i in range(buckets):
        lo, hi = edges[i], edges[i + 1]
        if hi <= lo:
            continue
        chunk_x = x[lo:hi]
        chunk_y = y[lo:hi]
        i_min = int(np.argmin(chunk_y))
        i_max = int(np.argmax(chunk_y))
        pair = sorted((i_min, i_max))
        for i in pair:
            xs.append(chunk_x[i])
            ys.append(chunk_y[i])

    return np.array(xs), np.array(ys)


def compute_pulses(df, column, window_size=5):
    """Smooth `column`, detect threshold crossings, return the smoothed
    series, the clamped-to-threshold "logic" series, and the duration of
    every above-threshold pulse plus their complementary cumulative counts.
    """
    filtered = df[column].rolling(window=window_size, min_periods=1).mean()
    logic = filtered.where(filtered > threshold, 0)

    high = filtered > threshold
    rising_edge = high & ~high.shift(fill_value=False)
    falling_edge = ~high & high.shift(fill_value=False)

    start_times = df.loc[rising_edge, "seconds"].to_numpy()
    stop_times = df.loc[falling_edge, "seconds"].to_numpy()
    durations = stop_times[: len(start_times)] - start_times[: len(stop_times)]

    if len(durations) == 0:
        counts = np.array([])
    else:
        seconds = np.arange(int(np.ceil(durations.max())) + 1)
        counts = (durations[:, None] >= seconds).sum(axis=0)

    return filtered, logic, durations, counts


def post_process(file, output=None, window_size=5):
    """Read a raw sensor-log CSV and compute pulse durations for all three
    females (previously this only ever analyzed `female1`, silently
    ignoring female2/female3 no matter which one the data was about).
    Returns (output_path, results) where results is
    {"female1": {"durations": ..., "counts": ...}, "female2": ..., ...}.
    """
    file = Path(file)

    if output is None:
        output = file.with_name(f"post process {file.stem}.csv")

    df = pd.read_csv(file)
    df.columns = df.columns.str.strip()

    results = {}
    for column in FEMALE_COLUMNS:
        prefix = column.replace("female", "f")
        filtered, logic, durations, counts = compute_pulses(df, column, window_size)
        df[f"{prefix} unfiltered"] = df[column]
        df[f"{prefix} filtered"] = filtered
        df[f"{prefix} logic"] = logic
        results[column] = {"durations": durations, "counts": counts}

    df.to_csv(output, index=False)
    return output, results


def read_and_store(start_time, file, duration, stop, sensors_read, result_rows=None):
    timestamp = time() - start_time
    tokens = [str(timestamp)]
    tokens.extend(read() for read in sensors_read)

    if result_rows is not None:
        result_rows.append(tokens)

    line = ", ".join(str(token) for token in tokens)

    file.write(line + "\n")
    if timestamp > duration:
        stop()


def plot_duration_histogram_as_svg(output, durations):
    if len(durations) == 0:
        return None

    # Plot histogram
    plt.figure(figsize=(8, 4))

    plt.hist(
        durations,
        bins=20,
    )

    plt.xlabel("Pulse duration (s)")
    plt.ylabel("Number of pulses")
    plt.title("Pulse duration distribution")

    plt.grid(True)

    # Add statistics
    mean = durations.mean()
    median = pd.Series(durations).median()

    plt.axvline(
        mean,
        linestyle="--",
        label=f"Mean: {mean:.3f}s",
    )

    plt.axvline(
        median,
        linestyle=":",
        label=f"Median: {median:.3f}s",
    )

    plt.legend()

    plt.savefig(
        output,
        format="svg",
        bbox_inches="tight",
    )
    plt.close()

    return output


def plot_counts_as_svg(output, counts, title):
    """
    Plot the complementary cumulative histogram.

    Parameters
    ----------
    output : Path, str, or writable buffer (e.g. io.StringIO)
        Where to save the SVG.
    counts : array-like
        counts[i] = number of pulses lasting at least i seconds.
    title : str
        Plot title.
    """
    if len(counts) == 0:
        return None

    seconds = np.arange(len(counts))

    fig, ax = plt.subplots(figsize=(10, 5))

    ax.step(seconds, counts, where="post", linewidth=2)
    ax.set_xlabel("Pulse duration (s)")
    ax.set_ylabel("Number of pulses ≥ duration")
    ax.set_title(title)

    ax.grid(True, alpha=0.3)

    fig.tight_layout()
    fig.savefig(output, format="svg")
    plt.close(fig)

    return output


def plot_full_measurement_as_svg(output, df, max_points=2000):
    """Plot every female's smoothed signal + threshold-logic step, from a
    dataframe already processed by `post_process`/`compute_pulses` (i.e. it
    has "f1/f2/f3 filtered" and "f1/f2/f3 logic" columns). The series are
    decimated (min/max per bucket, so short pulses survive) to keep the SVG
    small regardless of how long the run was: an unfiltered ~19,000-row run
    produces a ~700KB inline SVG, which is heavy to embed in a web page and
    slow for a single-threaded server to render; capped at `max_points` per
    line it stays on the order of tens of KB no matter the run length.
    """
    fig, ax1 = plt.subplots(figsize=(10, 5))
    seconds = df["seconds"].to_numpy()

    for column, color in zip(FEMALE_COLUMNS, FEMALE_COLORS):
        prefix = column.replace("female", "f")
        x, y = _decimate_min_max(
            seconds, df[f"{prefix} filtered"].to_numpy(), max_points
        )
        ax1.plot(x, y, label=column, linewidth=2, color=color)

    ax1.axhline(
        y=threshold, label=f"threshold ({threshold})", linewidth=2, color="black"
    )
    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Sensor value")
    ax1.grid(True)
    ax1.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))

    ax2 = ax1.twinx()
    for column, color in zip(FEMALE_COLUMNS, FEMALE_COLORS):
        prefix = column.replace("female", "f")
        x, y = _decimate_min_max(seconds, df[f"{prefix} logic"].to_numpy(), max_points)
        ax2.step(x, y, label=f"{prefix} logic", linewidth=1, alpha=0.5, color=color)
    ax2.set_ylabel("Logic")
    ax2.set_ylim(-0.1, 1.1)

    lines = ax1.get_lines() + ax2.get_lines()
    labels = [line.get_label() for line in lines]
    ax1.legend(lines, labels, fontsize="small")

    plt.title("Sensor Data")
    plt.tight_layout()
    fig.savefig(output, format="svg")
    plt.close(fig)

    return output


def plot_as_svg(path, max_points=2000):
    """Disk-file entry point used by the test scenarios' `.plot()`: reads a
    post-processed CSV (see `post_process`) and writes the full-measurement
    SVG next to it."""
    if isinstance(path, str):
        path = Path(path)
    df = pd.read_csv(path, skipinitialspace=True)
    return plot_full_measurement_as_svg(
        output=path.with_suffix(".svg"), df=df, max_points=max_points
    )


def plot(path):
    """Local dev helper: pop up an interactive window with the raw signal.
    Not used by the web app (which renders SVG inline instead, see
    `plot_full_measurement_as_svg`) - only run this at the machine."""
    if isinstance(path, str):
        path = Path(path)
    df = pd.read_csv(path, skipinitialspace=True)

    fig, ax1 = plt.subplots(figsize=(10, 5))

    for column in FEMALE_COLUMNS:
        ax1.plot(df["seconds"], df[column], label=column, linewidth=2)
    ax1.axhline(
        y=threshold,
        label=f"threshold ({threshold})",
        linewidth=2,
    )

    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Sensor value")
    ax1.grid(True)

    lines = ax1.get_lines()
    labels = [line.get_label() for line in lines]
    ax1.legend(lines, labels)

    plt.title("Sensor Data")
    plt.tight_layout()
    plt.show()
    plt.close()


if __name__ == "__main__":
    plot(
        path=r"C:\workspace\workspace2\Colloquy\exposition\docs\test_results\week26\2026_07_02_12h_08min_04s.csv"
    )
