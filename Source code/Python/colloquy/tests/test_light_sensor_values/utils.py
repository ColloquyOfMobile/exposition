from time import time
from collections import deque
import csv


def post_process(file):
    window_size = 5
    window = deque(maxlen=window_size)
    output = file.with_name(f"post process {file.stem}.csv")
    # files = (
        # file.open(newline="", encoding="utf-8"),
        # file.open("a", newline="", encoding="utf-8")
    # )
    with (
        file.open(newline="", encoding="utf-8") as infile,
        output.open("a", newline="", encoding="utf-8") as outfile,
        ):
        reader = csv.reader(infile)
        writer = csv.writer(outfile)
    
        
        for row in reader:
            if row[0] == "seconds":
                row.append("filtered")
                writer.writerow(row)
                continue
            
            time, value, *_ = row
            
            value = float(value)  # ou int(value)
            window.append(value)
            
            filtered_value = sum(window) / len(window)
            
            row.append(filtered_value)
            writer.writerow(row)

def read_and_store(start_time, file, duration, stop, sensors_read):
	timestamp = time() - start_time
	tokens = [str(timestamp)]
	tokens.extend(read() for read in sensors_read)
	line = ", ".join(str(token) for token in tokens)
	
	file.write(line + "\n")
	if timestamp > duration:
		stop()