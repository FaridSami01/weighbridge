"""
Quick Network Scale Test
Test single RS232-to-Ethernet converter
"""

import socket
import time

print("=" * 60)
print("  QUICK NETWORK SCALE TEST")
print("=" * 60)
print()

# Get configuration
print("Enter your scale configuration:")
ip = input("IP Address (e.g., 192.168.1.101): ")
port = int(input("Port (default: 8899): ") or "8899")

print()
print(f"Testing connection to {ip}:{port}...")
print()

try:
    # Create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    
    # Connect
    print("Connecting...", end=" ")
    sock.connect((ip, int(port)))
    print("✅ Connected!")
    print()
    
    print("Reading data (30 seconds)...")
    print("Put weight on scale to see data")
    print("Press Ctrl+C to stop")
    print("-" * 60)
    print()
    
    # Read data
    sock.settimeout(1)
    start_time = time.time()
    
    while time.time() - start_time < 30:
        try:
            data = sock.recv(1024)
            if data:
                text = data.decode('ascii', errors='ignore')
                text = ''.join(c for c in text if c.isprintable() or c in '\r\n')
                
                if text.strip():
                    print(f"[{time.strftime('%H:%M:%S')}] {text.strip()}")
        
        except socket.timeout:
            pass
        
        time.sleep(0.1)
    
    sock.close()
    print()
    print("✅ Test complete!")
    
except socket.timeout:
    print("❌ Connection timeout")
    print()
    print("Check:")
    print("  - Converter is powered on")
    print("  - Ethernet cable is connected")
    print("  - IP address is correct")
    print("  - Your laptop is on same network")
    
except ConnectionRefusedError:
    print("❌ Connection refused")
    print()
    print("Check:")
    print(f"  - Port {port} is correct")
    print("  - Converter settings allow connections")
    
except Exception as e:
    print(f"❌ Error: {e}")

print()
input("Press Enter to exit...")
