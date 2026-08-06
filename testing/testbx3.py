import serial
import re
import time

PORT = "COM9"
BAUD = 9600
DIVISION = 100

FULL_THRESHOLD  = 48.0   # kg (closer to your 40kg target)
EMPTY_THRESHOLD = 2.0    # kg
STABLE_TIME     = 0.5    # seconds

ser = serial.Serial(PORT, BAUD, timeout=0.2)
pattern = re.compile(r't\d+\s+(\d+)')

bag_count = 0
state = "EMPTY"
full_since = None
last_full_weight = None

print("Bag counter running...")

while True:
    if ser.in_waiting:
        raw = ser.read(ser.in_waiting)
        text = raw.decode("ascii", errors="ignore")

        for line in text.splitlines():
            m = pattern.search(line)
            if not m:
                continue

            weight_kg = int(m.group(1)) / DIVISION
            now = time.time()

            # Detect potential FULL
            if weight_kg >= FULL_THRESHOLD and state == "EMPTY":
                if full_since is None:
                    full_since = now
                    last_full_weight = weight_kg
                elif now - full_since >= STABLE_TIME:
                    state = "FULL"
                    print(f"Bag ready: {last_full_weight:.2f} kg")

            # Update last stable full weight
            if state == "EMPTY" and weight_kg >= FULL_THRESHOLD:
                last_full_weight = weight_kg

            # Detect bag removal
            if weight_kg <= EMPTY_THRESHOLD and state == "FULL":
                bag_count += 1
                state = "EMPTY"
                full_since = None
                print(
                    f"Bag completed ✅ | "
                    f"Weight: {last_full_weight:.2f} kg | "
                    f"TOTAL BAGS = {bag_count}"
                )

            # Reset if weight drops early
            if weight_kg < FULL_THRESHOLD and state == "EMPTY":
                full_since = None