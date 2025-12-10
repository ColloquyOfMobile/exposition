import serial
import time

# Adjust this to your Arduino serial port:
PORT = "COM3"   # Windows example
# PORT = "/dev/ttyACM0"  # Linux example
BAUD = 115200

# Map logical names to Arduino pin numbers
PIN_MAP = {
    "female1": 11,
    "female2": 12,
    "female3": 13,
    "male1": 22,
    "male2": 23,
}

ser = serial.Serial(PORT, BAUD, timeout=1)

# --- Wait for Arduino to say it's ready ---
print("Waiting for Arduino...")
while True:
    line = ser.readline().decode().strip()
    if line:
        print("Arduino:", line)
        break

print("Interactive pin control")
print("Usage:")
print("  <name> <on/off>   (e.g. 'female1 on')")
print("  <pin> <0/1>       (e.g. '11 1')")
print("  q                 quit")
print("Available pins:", ", ".join(PIN_MAP.keys()))

def send_command(pin, state):
    cmd = f"{pin} {state}"
    ser.write(cmd.encode())
    response = ser.readline().decode().strip()

    if response:
        print(response)

try:
    while True:
        cmd = input(">> ").strip().lower()
        if cmd in ("q", "quit", "exit"):
            break
        if not cmd:
            continue

        parts = cmd.split()
        if len(parts) != 2:
            print("Invalid command. Example: 'female1 on' or '11 1'")
            continue

        target, state_str = parts

        # convert state
        if state_str in ("1", "on", "high"):
            state = 1
        elif state_str in ("0", "off", "low"):
            state = 0
        else:
            print("State must be on/off or 1/0")
            continue

        # convert target to pin
        if target in PIN_MAP:
            pin = PIN_MAP[target]
        elif target.isdigit():
            pin = int(target)
        else:
            print("Unknown pin name. Available:", ", ".join(PIN_MAP.keys()))
            continue

        send_command(pin, state)

finally:
    ser.close()
    print("Connection closed.")