"""
Quick Packing Scale Test
Simple script to quickly test if packing scale is connected
"""

import serial.tools.list_ports

print("=" * 60)
print("  QUICK PACKING SCALE CABLE TEST")
print("=" * 60)
print()

# List all COM ports
print("Available COM Ports:")
print("-" * 60)

ports = list(serial.tools.list_ports.comports())

if not ports:
    print("❌ No COM ports found!")
    print()
    print("Check:")
    print("  - Is the USB cable plugged in?")
    print("  - Is the scale powered on?")
    print("  - Are drivers installed?")
else:
    for i, port in enumerate(ports, 1):
        print(f"\n{i}. {port.device}")
        print(f"   Name: {port.description}")
        
        # Identify likely packing scale
        desc_lower = port.description.lower()
        if any(word in desc_lower for word in ['usb', 'serial', 'prolific', 'ftdi', 'ch340']):
            print(f"   ⭐ LIKELY PACKING SCALE ADAPTER!")
        
        if port.hwid:
            print(f"   ID: {port.hwid}")

print()
print("=" * 60)
print()

if ports:
    print(f"✅ Found {len(ports)} port(s)")
    print()
    print("NEXT STEP:")
    print("Run the full detector to test which port has your scale:")
    print()
    print("  python detect_packing_scales.py")
    print()
else:
    print("❌ No ports found")
    print()
    print("TROUBLESHOOTING:")
    print("  1. Plug in USB-to-Serial adapter")
    print("  2. Wait 5 seconds for Windows to detect")
    print("  3. Check Device Manager:")
    print("     Win+X → Device Manager → Ports (COM & LPT)")
    print("  4. Run this script again")

print()
input("Press Enter to exit...")
