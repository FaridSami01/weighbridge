"""
Packing Scale Cable Detector
Automatically finds which COM port your packing scales are connected to
"""

import serial
import serial.tools.list_ports
import time
import sys

print("=" * 70)
print("  PACKING SCALE CABLE DETECTOR")
print("=" * 70)
print()

# Step 1: List all available COM ports
print("STEP 1: Scanning for COM ports...")
print("-" * 70)

available_ports = []
for port in serial.tools.list_ports.comports():
    available_ports.append(port.device)
    print(f"✅ Found: {port.device}")
    print(f"   Description: {port.description}")
    print(f"   Hardware ID: {port.hwid}")
    print()

if not available_ports:
    print("❌ No COM ports found!")
    print()
    print("Possible reasons:")
    print("  1. Scale not connected")
    print("  2. USB adapter not plugged in")
    print("  3. Driver not installed")
    print()
    input("Press Enter to exit...")
    sys.exit(1)

print(f"Total ports found: {len(available_ports)}")
print()

# Step 2: Test each port with different baud rates
print("STEP 2: Testing each port for packing scale data...")
print("-" * 70)

common_bauds = [9600, 4800, 19200, 2400, 1200]
test_duration = 3  # seconds

detected_scales = []

for port in available_ports:
    print(f"\n🔍 Testing {port}...")
    
    for baud in common_bauds:
        try:
            print(f"   Trying {baud} baud...", end=" ")
            
            # Open port
            ser = serial.Serial(
                port=port,
                baudrate=baud,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            
            # Read for a few seconds
            data_received = False
            weight_found = False
            count_found = False
            sample_data = ""
            
            start_time = time.time()
            while time.time() - start_time < test_duration:
                if ser.in_waiting > 0:
                    try:
                        chunk = ser.read(ser.in_waiting)
                        text = chunk.decode('ascii', errors='ignore')
                        
                        # Filter printable characters
                        text = ''.join(c for c in text if c.isprintable() or c in '\r\n')
                        
                        if text.strip():
                            data_received = True
                            sample_data += text[:100]  # Keep sample
                            
                            # Check for weight patterns
                            if any(word in text.lower() for word in ['kg', 'weight', 'w:', 'wt']):
                                weight_found = True
                            
                            # Check for count patterns
                            if any(word in text.lower() for word in ['count', 'cnt', 'c:', 'bags']):
                                count_found = True
                    except:
                        pass
                
                time.sleep(0.1)
            
            ser.close()
            
            if data_received:
                print("✅ DATA RECEIVED!")
                print(f"      Weight indicators: {'YES ✅' if weight_found else 'NO'}")
                print(f"      Count indicators: {'YES ✅' if count_found else 'NO'}")
                print(f"      Sample: {sample_data[:50]}")
                
                detected_scales.append({
                    'port': port,
                    'baud': baud,
                    'has_weight': weight_found,
                    'has_count': count_found,
                    'sample': sample_data[:100]
                })
            else:
                print("No data")
        
        except serial.SerialException as e:
            print(f"❌ Error: {e}")
            break
        except Exception as e:
            print(f"⚠️  {e}")
            continue

print()
print("=" * 70)
print("  DETECTION RESULTS")
print("=" * 70)
print()

if not detected_scales:
    print("❌ No packing scales detected!")
    print()
    print("Troubleshooting:")
    print("  1. Make sure scale is powered on")
    print("  2. Check cable connections")
    print("  3. Put weight on scale to trigger data transmission")
    print("  4. Some scales only send data when weight changes")
    print()
    print("Try this:")
    print("  - Put a bag on the scale")
    print("  - Run this script again")
    print()
else:
    print(f"✅ Found {len(detected_scales)} scale(s)!")
    print()
    
    for i, scale in enumerate(detected_scales, 1):
        print(f"SCALE {i}:")
        print(f"  Port: {scale['port']}")
        print(f"  Baud Rate: {scale['baud']}")
        print(f"  Has Weight: {'✅ YES' if scale['has_weight'] else '⚠️  NO'}")
        print(f"  Has Count: {'✅ YES' if scale['has_count'] else '⚠️  NO'}")
        print(f"  Sample Data: {scale['sample'][:60]}")
        print()
    
    print("=" * 70)
    print("  RECOMMENDED CONFIGURATION")
    print("=" * 70)
    print()
    
    for i, scale in enumerate(detected_scales, 1):
        print(f"# Scale {i} (Packing Line {i})")
        print(f"scale_{i} = PackingScaleReader('{scale['port']}', {scale['baud']})")
        print()
    
    print("=" * 70)
    print("  NEXT STEPS")
    print("=" * 70)
    print()
    print("1. Note the COM port and baud rate above")
    print("2. Update your app.py with these settings")
    print("3. Test with: python packing_scale.py COM# BAUD")
    print()
    print(f"Example: python packing_scale.py {detected_scales[0]['port']} {detected_scales[0]['baud']}")
    print()

# Step 3: Live monitoring option
if detected_scales:
    print()
    choice = input("Want to monitor live data from detected scales? (y/n): ")
    
    if choice.lower() == 'y':
        print()
        print("=" * 70)
        print("  LIVE MONITORING")
        print("=" * 70)
        print("Press Ctrl+C to stop")
        print()
        
        # Open all detected scales
        open_scales = []
        for scale in detected_scales:
            try:
                ser = serial.Serial(
                    port=scale['port'],
                    baudrate=scale['baud'],
                    timeout=1
                )
                open_scales.append({
                    'port': scale['port'],
                    'ser': ser
                })
                print(f"✅ Monitoring {scale['port']} @ {scale['baud']} baud")
            except Exception as e:
                print(f"❌ Failed to open {scale['port']}: {e}")
        
        print()
        print("-" * 70)
        
        try:
            while True:
                for scale in open_scales:
                    if scale['ser'].in_waiting > 0:
                        try:
                            data = scale['ser'].read(scale['ser'].in_waiting)
                            text = data.decode('ascii', errors='ignore')
                            text = ''.join(c for c in text if c.isprintable() or c in '\r\n')
                            
                            if text.strip():
                                print(f"[{scale['port']}] {text.strip()}")
                        except:
                            pass
                
                time.sleep(0.1)
        
        except KeyboardInterrupt:
            print("\n\nStopped by user")
        
        finally:
            for scale in open_scales:
                scale['ser'].close()

print()
print("=" * 70)
print("Script complete!")
print("=" * 70)
print()

input("Press Enter to exit...")
