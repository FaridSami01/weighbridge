import serial
import re

PORT = "COM9"
BAUD = 9600
DIVISION = 100      # 3087 -> 30.87 kg (adjust if needed)

EMPTY_THRESHOLD = 2.0     # kg
FULL_THRESHOLD  = 48.0    # kg

ser = serial.Serial(PORT, BAUD, timeout=0.5)

# Accept BX3 continuous formats: t00 and l00
pattern = re.compile(r'[tl]\d+\s+(\d+)')

state = "WAIT_ZERO"   # WAIT_ZERO -> WAIT_FULL
bag_count = 0

print("50kg BX3 bag counter (quiet mode) running...")

while True:
    if ser.in_waiting:
        raw = ser.read(ser.in_waiting)
        text = raw.decode("ascii", errors="ignore")

        for line in text.splitlines():
            m = pattern.search(line)
            if not m:
                continue

            weight_kg = int(m.group(1)) / DIVISION

            # 1️⃣ Detect empty scale
            if state == "WAIT_ZERO" and weight_kg <= EMPTY_THRESHOLD:
                state = "WAIT_FULL"
                print("🟢 Scale empty (≈0 kg) → waiting for bag fill")

            # 2️⃣ Detect full bag → count
            elif state == "WAIT_FULL" and weight_kg >= FULL_THRESHOLD:
                bag_count += 1
                print(f"✅ Bag completed → TOTAL BAGS = {bag_count}")
                state = "WAIT_ZERO"