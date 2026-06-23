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

    plt.figure(figsize=(10, 5))

    plt.plot(df["seconds"], df["female1"], label="female1", linewidth=2)
    plt.plot(df["seconds"], df["female2"], label="female2", linewidth=2)
    plt.plot(df["seconds"], df["female3"], label="female3", linewidth=2)
    plt.plot(df["seconds"], df["f1 unfiltered"], label="f1 unfiltered", alpha=0.7)

    plt.xlabel("Time (s)")
    plt.ylabel("Value")
    plt.title("Sensor Data")
    plt.grid(True)
    plt.legend()

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

    df.to_csv(output, index=False)

    return output

def post_process_old(file, output=None):
    if output is None:
        output=file.with_name(f"post process {file.stem}.csv")
        
    window_size = 5
    windows = [
        deque(maxlen=window_size),
        deque(maxlen=window_size),
        deque(maxlen=window_size),
        ]
    with (
        file.open(newline="", encoding="utf-8") as infile,
        output.open("a", newline="", encoding="utf-8") as outfile,
        ):
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
    
        
        for row in reader:
            new_row = []
            if row[0] == "seconds":
                new_row.append("seconds")
                new_row.append("f1 unfiltered")
                new_row.append("female1")
                new_row.append("female2")
                new_row.append("female3")
                writer.writerow(new_row)
                continue
            
            time, *values = row
            
            new_row.append(float(time))
            new_row.append(float(values[0]))
            
            for value, window in zip(values, windows):
                value = float(value)
                window.append(value)
            
                filtered_value = sum(window) / len(window)
            
                new_row.append(filtered_value)
            
            if len(windows[0])<5:
                continue
                
            writer.writerow(new_row)

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