import csv
from pathlib import Path
from collections import deque

p1 = r"C:\workspace\workspace2\Colloquy\exposition\docs\female_only_10min.csv"
p2 =  r"C:\workspace\workspace2\Colloquy\exposition\docs\female_and_male_10min.csv"

path = Path(p2)



window_size = 5

with path.open(newline="", encoding="utf-8") as f:
    reader = csv.reader(f)

    rows = []
    window = deque(maxlen=window_size)

    for row in reader:
        if row[0] == "seconds":
            continue

        seconds = row[0]
        value = 0 if row[1].strip() == "False" else 1

        window.append((seconds, value))

        if len(window) < window_size:
            continue

        total = sum(value for _, value in window)

        # majorité
        final_value = 1 if total >= (window_size / 2) else 0

        # temps du milieu de la fenêtre
        center_index = window_size // 2
        final_seconds = window[center_index][0]
        
        rows.append((final_seconds, final_value))
        

output = path.parent / f"{path.stem}_averaged.csv"
with output.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerows(rows)