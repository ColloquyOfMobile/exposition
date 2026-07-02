import serial
import matplotlib.pyplot as plt
from collections import deque
from matplotlib.animation import FuncAnimation

# -------------------------
# Configuration
# -------------------------
PORT = "COM4"          # Change to your Arduino port
BAUDRATE = 57600
HISTORY = 200          # Number of samples displayed

# -------------------------
# Serial
# -------------------------
ser = serial.Serial(PORT, BAUDRATE, timeout=1)

# Skip header
line = ser.readline()
print(*line)

# One deque per analog channel
data = [deque([0] * HISTORY, maxlen=HISTORY) for _ in range(16)]

# -------------------------
# Figure
# -------------------------
fig, ax = plt.subplots(figsize=(12, 6))

lines = []
for i in range(16):
    line, = ax.plot(data[i], label=f"A{i}")
    lines.append(line)

ax.set_ylim(0, 1023)
ax.set_xlim(0, HISTORY)
ax.set_xlabel("Samples")
ax.set_ylabel("ADC Value")
ax.grid(True)
ax.legend(ncol=4)


# -------------------------
# Update function
# -------------------------
def update(frame):
    line = ser.readline().decode(errors="ignore").strip()
    print(*line)

    if not line:
        return lines

    try:
        values = list(map(int, line.split(",")))

        if len(values) != 16:
            return lines

        for i, value in enumerate(values):
            data[i].append(value)
            lines[i].set_ydata(data[i])

    except ValueError:
        pass

    return lines


ani = FuncAnimation(fig, update, interval=20, blit=False)

plt.tight_layout()
plt.show()

ser.close()