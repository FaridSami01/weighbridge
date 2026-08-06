# test_all_baykon_machines.py
# Test all 3 Baykon machines to see their data formats

import serial
import time
import re

# Machine configurations
MACHINES = {
    "BX3_BRAN_40KG": {
        "port": "COM3",
        "baudrate": 9600,
        "description": "BX3 - Bran 40kg (WORKING)"
    },
    "BX3_FLOUR_50KG": {
        "port": "COM9",  # Change to actual port!
        "baudrate": 9600,
        "description": "BX3 - Flour 50kg (NOT WORKING)"
    },
    "BX30_FLOUR_50KG": {
        "port": "COM6",  # Change to actual port!
        "baudrate": 9600,
        "description": "BX30 - Flour 50kg"
    }
}

def test_machine(name, config):
    """Test a single machine"""
    print("\n" + "="*70)
    print(f"Testing: {name}")
    print(f"Description: {config['description']}")
    print(f"Port: {config['port']} @ {config['baudrate']} baud")
    print("="*70)
    
    try:
        ser = serial.Serial(
            port=config['port'],
            baudrate=config['baudrate'],
            timeout=1
        )
        
        print(f"✅ Port {config['port']} opened successfully!")
        print(f"\nListening for 30 seconds...")
        print(f"Put a bag on the scale and complete it!\n")
        
        start_time = time.time()
        data_received = False
        
        while time.time() - start_time < 30:
            if ser.in_waiting > 0:
                raw = ser.read(ser.in_waiting)
                data_received = True
                
                print("\n" + "-"*70)
                print(f"📡 RAW DATA RECEIVED:")
                print("-"*70)
                print(f"Bytes: {raw}")
                print(f"Hex:   {raw.hex()}")
                
                try:
                    text = raw.decode('utf-8', errors='ignore')
                    print(f"UTF-8: {repr(text)}")
                except:
                    try:
                        text = raw.decode('ascii', errors='ignore')
                        print(f"ASCII: {repr(text)}")
                    except:
                        print("Could not decode as text")
                
                # Try to parse with different patterns
                print("\n🔍 PARSING ATTEMPTS:")
                
                # Pattern 1: t\d+\s+(\d+) - Known working for 40kg BX3
                pattern1 = re.compile(r't\d+\s+(\d+)')
                match1 = pattern1.search(text)
                if match1:
                    weight = int(match1.group(1)) / 100
                    print(f"  ✅ Pattern 1 (t\\d+\\s+(\\d+)): {weight} kg")
                else:
                    print(f"  ❌ Pattern 1: No match")
                
                # Pattern 2: Just numbers
                pattern2 = re.compile(r'(\d{4,5})')
                match2 = pattern2.search(text)
                if match2:
                    weight = int(match2.group(1)) / 100
                    print(f"  ⚠️  Pattern 2 (\\d{{4,5}}): {weight} kg")
                else:
                    print(f"  ❌ Pattern 2: No match")
                
                # Pattern 3: Weight with decimal
                pattern3 = re.compile(r'(\d+\.\d+)')
                match3 = pattern3.search(text)
                if match3:
                    weight = float(match3.group(1))
                    print(f"  ⚠️  Pattern 3 (\\d+\\.\\d+): {weight} kg")
                else:
                    print(f"  ❌ Pattern 3: No match")
                
                print("-"*70)
            
            time.sleep(0.1)
        
        if not data_received:
            print("\n❌ NO DATA RECEIVED IN 30 SECONDS!")
            print("\nPossible issues:")
            print("  1. Wrong COM port")
            print("  2. Machine communication disabled")
            print("  3. Different baudrate needed")
            print("  4. Need to press PRINT button manually")
            print("  5. Machine in wrong mode")
        
        ser.close()
        
    except serial.SerialException as e:
        print(f"\n❌ ERROR: {e}")
        print(f"\nPossible issues:")
        print(f"  1. Wrong COM port (check Device Manager)")
        print(f"  2. Port already in use")
        print(f"  3. Cable not connected")
    
    except Exception as e:
        print(f"\n❌ UNEXPECTED ERROR: {e}")
    
    print("\n")


def main():
    """Test all machines"""
    print("""
╔══════════════════════════════════════════════════════════════════╗
║  BAYKON MULTI-MACHINE TEST                                       ║
║  Testing all 3 bagging machines for data format                  ║
╚══════════════════════════════════════════════════════════════════╝

INSTRUCTIONS:
1. Make sure only ONE machine is connected at a time
2. Update the COM port numbers below if needed
3. Complete ONE bag on each machine during the test
4. Watch the output to see data format differences

Press Ctrl+C to stop at any time
""")
    
    print("\nWhich machine do you want to test?")
    print("1. BX3 - Bran 40kg (Working) - COM3")
    print("2. BX3 - Flour 50kg (Not working) - COM?")
    print("3. BX30 - Flour 50kg - COM?")
    print("4. Test all (one by one)")
    
    choice = input("\nEnter choice (1-4): ").strip()
    
    if choice == "1":
        test_machine("BX3_BRAN_40KG", MACHINES["BX3_BRAN_40KG"])
    elif choice == "2":
        port = input("Enter COM port for 50kg BX3 (e.g., COM5): ").strip()
        MACHINES["BX3_FLOUR_50KG"]["port"] = port
        test_machine("BX3_FLOUR_50KG", MACHINES["BX3_FLOUR_50KG"])
    elif choice == "3":
        port = input("Enter COM port for BX30 (e.g., COM6): ").strip()
        MACHINES["BX30_FLOUR_50KG"]["port"] = port
        test_machine("BX30_FLOUR_50KG", MACHINES["BX30_FLOUR_50KG"])
    elif choice == "4":
        print("\n⚠️  Testing all machines one by one...")
        print("Complete one bag on each machine when prompted!\n")
        input("Connect 40kg BX3 to COM3, then press Enter...")
        test_machine("BX3_BRAN_40KG", MACHINES["BX3_BRAN_40KG"])
        
        port = input("\nEnter COM port for 50kg BX3, then press Enter: ").strip()
        MACHINES["BX3_FLOUR_50KG"]["port"] = port
        test_machine("BX3_FLOUR_50KG", MACHINES["BX3_FLOUR_50KG"])
        
        port = input("\nEnter COM port for BX30, then press Enter: ").strip()
        MACHINES["BX30_FLOUR_50KG"]["port"] = port
        test_machine("BX30_FLOUR_50KG", MACHINES["BX30_FLOUR_50KG"])
    else:
        print("Invalid choice!")
        return
    
    print("\n" + "="*70)
    print("TESTING COMPLETE!")
    print("="*70)
    print("\nNext steps:")
    print("1. Review the data format from each machine")
    print("2. Note any differences in patterns")
    print("3. Share the output with me")
    print("4. I'll update packing_scale.py to support all formats")
    print("\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nTest stopped by user.")
    except Exception as e:
        print(f"\nError: {e}")
