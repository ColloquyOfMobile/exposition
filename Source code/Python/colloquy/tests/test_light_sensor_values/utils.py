from time import time
from collections import deque
import csv
import pandas as pd
import matplotlib.pyplot as plt
from io import StringIO
from pathlib import Path


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
    # plt.show()
    
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
    
    threashold = 310
    df["f1 logic"] = df["female1"].where(df["female1"] > threshold, 0)
    
    high = df["female1"] > threshold

    df["rising_edge"] = high & ~high.shift(fill_value=False)
    df["pulse_id"] = df["rising_edge"].cumsum()

    # Set pulse_id to 0 when not inside a pulse
    df["pulse_id"] = df["pulse_id"].where(high, 0)

    df.to_csv(output, index=False)
    return output


def read_and_store(start_time, file, duration, stop, sensors_read):
	timestamp = time() - start_time
	tokens = [str(timestamp)]
	tokens.extend(read() for read in sensors_read)
	line = ", ".join(str(token) for token in tokens)
	
	file.write(line + "\n")
	if timestamp > duration:
		stop()

if __name__ == "__main__":
    plot(path="docs/test_results/week24/test with female male and bar moving for 30s/post process 2026_06_16_17h_43min_26s.csv")