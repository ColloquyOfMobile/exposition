from time import time
from collections import deque
import csv
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from io import StringIO
from pathlib import Path

    
threshold = 310

def plot_as_svg(path):
    if isinstance(path, str):
        path = Path(path)
    df = pd.read_csv(path, skipinitialspace=True)

    fig, ax1 = plt.subplots(figsize=(10, 5))
    
    # Main sensor signals
    ax1.plot(df["seconds"], df["female1"], label="female1", linewidth=2)
    ax1.plot(df["seconds"], df["female2"], label="female2", linewidth=2)
    ax1.plot(df["seconds"], df["female3"], label="female3", linewidth=2)
    ax1.plot(df["seconds"], df["f1 unfiltered"], label="f1 unfiltered", alpha=0.7)
    ax1.axhline(
        y=threshold,
        label=f"threshold ({threshold})",
        linewidth=2,
    )

    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Sensor value")
    ax1.grid(True)

    # Secondary axis for logic signal
    ax2 = ax1.twinx()
    ax2.step(
        df["seconds"],
        df["f1 logic"],
        label="f1 logic",
        linewidth=2,
    )
    ax2.set_ylabel("Logic")
    ax2.set_ylim(-0.1, 1.1)
    
    # Combine legends from both axes
    lines = ax1.get_lines() + ax2.get_lines()
    labels = [line.get_label() for line in lines]
    ax1.legend(lines, labels)

    plt.title("Sensor Data")
    plt.tight_layout()
    plt.savefig(path.with_suffix(".svg"), format="svg")
    plt.close()
    
    
    
def post_process(file, output=None, window_size=5):
    file = Path(file)

    if output is None:
        output = file.with_name(f"post process {file.stem}.csv")

    df = pd.read_csv(file)

    # Nettoie les noms de colonnes si le CSV contient des espaces
    df.columns = df.columns.str.strip()

    # Sauvegarde la valeur brute de female1
    df.insert(
        df.columns.get_loc("female1"),
        "f1 unfiltered",
        df["female1"],
    )

    # Moyennes glissantes
    for column in ("female1", "female2", "female3"):
        df[column] = (
            df[column]
            .rolling(window=window_size, min_periods=1)
            .mean()
        )
    df["f1 logic"] = df["female1"].where(df["female1"] > threshold, 0)
    
    high = df["female1"] > threshold

    df["rising_edge"] = high & ~high.shift(fill_value=False)
    df["falling_edge"] = ~high & high.shift(fill_value=False)
    df["pulse_id"] = df["rising_edge"].cumsum()

    # Set pulse_id to 0 when not inside a pulse
    df["pulse_id"] = df["pulse_id"].where(high, 0)
    df.to_csv(output, index=False)
    
    start_times = df.loc[df["rising_edge"], "seconds"].to_numpy()
    stop_times = df.loc[df["falling_edge"], "seconds"].to_numpy()
    durations = stop_times[:len(start_times)] - start_times[:len(stop_times)]
    
    # survival function (or complementary cumulative histogram)
    seconds = np.arange(int(np.ceil(durations.max())) + 1)
    counts = (durations[:, None] >= seconds).sum(axis=0)
    
    return output, durations, counts


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
    output : Path or str
        Output SVG filename.
    counts : array-like
        counts[i] = number of pulses lasting at least i seconds.
    title : str
        Plot title.
    """
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




def plot(path):
    if isinstance(path, str):
        path = Path(path)
    df = pd.read_csv(path, skipinitialspace=True)

    fig, ax1 = plt.subplots(figsize=(10, 5))
    
    # Main sensor signals
    ax1.plot(df["seconds"], df["female1"], label="female1", linewidth=2)
    ax1.plot(df["seconds"], df["female2"], label="female2", linewidth=2)
    ax1.plot(df["seconds"], df["female3"], label="female3", linewidth=2)
    ax1.axhline(
        y=threshold,
        label=f"threshold ({threshold})",
        linewidth=2,
    )

    ax1.set_xlabel("Time (s)")
    ax1.set_ylabel("Sensor value")
    ax1.grid(True)
    
    # Combine legends from both axes
    lines = ax1.get_lines()
    labels = [line.get_label() for line in lines]
    ax1.legend(lines, labels)

    plt.title("Sensor Data")
    plt.tight_layout()
    plt.show()
    plt.close()
    
if __name__ == "__main__":
    plot(path=r"C:\workspace\workspace2\Colloquy\exposition\docs\test_results\week26\2026_07_02_12h_08min_04s.csv")