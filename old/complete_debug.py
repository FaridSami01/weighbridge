"""
Complete System Debug - Check Everything
Run this to see exactly what's happening
"""

print("=" * 70)
print("  COMPLETE SYSTEM DEBUG")
print("=" * 70)
print()

# Test 1: Import weighbridge module
print("TEST 1: Import weighbridge module")
print("-" * 70)
try:
    from weighbridge import WeighbridgeReader
    print("✅ weighbridge module imported successfully")
except Exception as e:
    print(f"❌ Failed to import: {e}")
    exit(1)

print()

# Test 2: Create weighbridge object
print("TEST 2: Create weighbridge object")
print("-" * 70)
try:
    import time
    w = WeighbridgeReader("COM10", 2400)
    print("✅ WeighbridgeReader created")
    print(f"   Port: {w.port}")
    print(f"   Baudrate: {w.baudrate}")
    print(f"   Has serial: {w.ser is not None}")
    if w.ser:
        print(f"   Serial open: {w.ser.is_open}")
    print(f"   _online: {w._online}")
    print()
    print("Waiting 2 seconds for data...")
    time.sleep(2)
    print()
except Exception as e:
    print(f"❌ Failed to create: {e}")
    import traceback
    traceback.print_exc()
    exit(1)

print()

# Test 3: Check methods
print("TEST 3: Check methods")
print("-" * 70)
try:
    weight = w.get_weight()
    online = w.is_online()
    
    print(f"✅ get_weight() = {weight}")
    print(f"✅ is_online() = {online}")
    
    if online:
        print()
        print("🎉 SUCCESS! Weighbridge is ONLINE")
    else:
        print()
        print("⚠️  WARNING: is_online() returns False")
        print()
        print("Checking why:")
        print(f"   w._online = {w._online}")
        print(f"   w.ser = {w.ser}")
        if w.ser:
            print(f"   w.ser.is_open = {w.ser.is_open}")
        print(f"   w.running = {w.running}")
        if hasattr(w, 'thread'):
            print(f"   w.thread.is_alive() = {w.thread.is_alive()}")
        
except Exception as e:
    print(f"❌ Method call failed: {e}")
    import traceback
    traceback.print_exc()

print()

# Test 4: Monitor for 10 seconds
print("TEST 4: Monitor weight for 10 seconds")
print("-" * 70)
print("(Put weight on scale to see if it updates)")
print()

try:
    for i in range(10):
        weight = w.get_weight()
        online = w.is_online()
        status = "🟢 ONLINE" if online else "🔴 OFFLINE"
        print(f"[{i+1}/10] {status} | Weight: {weight:>5} kg")
        time.sleep(1)
except KeyboardInterrupt:
    print("\nStopped by user")
except Exception as e:
    print(f"❌ Error: {e}")

print()

# Test 5: Check Flask environment
print("TEST 5: Check Flask environment simulation")
print("-" * 70)

# Simulate what Flask does
print("Simulating Flask import...")
print()

# Create new instance like Flask does
try:
    w2 = WeighbridgeReader("COM10", 2400)
    print(f"✅ Second instance created")
    print(f"   Immediately after creation:")
    print(f"   - is_online() = {w2.is_online()}")
    print(f"   - get_weight() = {w2.get_weight()}")
    print()
    print("Waiting 2 seconds (like Flask startup)...")
    time.sleep(2)
    print(f"   After 2 seconds:")
    print(f"   - is_online() = {w2.is_online()}")
    print(f"   - get_weight() = {w2.get_weight()}")
    
    w2.stop()
except Exception as e:
    print(f"❌ Flask simulation failed: {e}")

print()

# Cleanup
w.stop()

print("=" * 70)
print("  DEBUG COMPLETE")
print("=" * 70)
print()
print("SUMMARY:")
print()
print("If is_online() = True:")
print("  → Weighbridge code is working")
print("  → Problem is likely in Flask app setup")
print()
print("If is_online() = False:")
print("  → Check the 'Checking why' section above")
print("  → Look at w._online, w.ser.is_open values")
print()

input("Press Enter to exit...")
