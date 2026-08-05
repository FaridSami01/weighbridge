# packing_scale_multi.py - Triple Machine Support
# Manages 3 Baykon machines simultaneously
from packing_database import PackingDatabaseManager
import serial
import re
import time
import threading
from datetime import datetime

class BaykonMachine:
    """
    Single Baykon machine reader
    Supports multiple data formats with auto-detection
    """
    
    def __init__(self, name, port, baudrate=9600, division=100, 
                 full_threshold=38.0, empty_threshold=2.0, bag_size=40, product="Unknown",
                 on_bag_complete=None):
        self.name = name
        self.port = port
	self.db_manager = db_manager
        self.baudrate = baudrate
        self.division = division
        self.bag_size = bag_size
        self.product = product
        self.on_bag_complete = on_bag_complete  # Callback function for auto-save
        
        # Thresholds
        self.FULL_THRESHOLD = full_threshold
        self.EMPTY_THRESHOLD = empty_threshold
        self.STABLE_TIME = 0.5
        
        # State tracking
        self.bag_count = 0
        self.state = "EMPTY"
        self.full_since = None
        self.last_full_weight = None
        self.current_weight = 0.0
        
        # Session tracking
        self.session_bags = []
        self.session_start = datetime.now()
        
        # Connection
        self.serial = None
        self.is_running = False
        
        # Multiple regex patterns for different formats
        self.patterns = [
            # Format 1: "t01 3990" (BX3 40kg)
            re.compile(r't\d+\s+(\d+)'),
            
            # Format 2: "\x02l80  4009     0\r@" (BXf3 50kg)
            re.compile(r'l\d+\s+(\d+)'),
            
            # Format 3: Just any 4-5 digit number (fallback for BX30)
            re.compile(r'(\d{4,5})'),
        ]
        
        # Auto-detect format
        self.detected_format = None
        self.thread = None
        
        # Start connection
        self.connect()
    
    def connect(self):
        """Connect to Baykon machine"""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.2,
                exclusive=True  # Prevent other programs from using this port
            )
            
            # Clear any stale data
            self.serial.reset_input_buffer()
            self.serial.reset_output_buffer()
            
            self.is_running = True
            
            # Start monitoring thread
            self.thread = threading.Thread(target=self._monitor, daemon=True)
            self.thread.start()
            
            # Give thread time to initialize before next scale opens
            time.sleep(0.1)
            
            print(f"✅ {self.name} connected on {self.port}")
            
        except PermissionError as e:
            print(f"❌ {self.name} on {self.port}: Port is in use by another program!")
            print(f"   Close any programs using {self.port} and restart")
            self.serial = None
            self.is_running = False
            
        except FileNotFoundError as e:
            print(f"❌ {self.name} on {self.port}: Port does not exist")
            print(f"   Check Device Manager for correct COM port number")
            self.serial = None
            self.is_running = False
            
        except Exception as e:
            print(f"❌ {self.name} on {self.port}: {e}")
            self.serial = None
            self.is_running = False
    
    def _monitor(self):
        """Monitor scale data in background thread"""
        reconnect_attempts = 0
        max_consecutive_failures = 5  # Max failures in a row before waiting longer
        last_data_time = time.time()
        health_check_interval = 60  # Check every 60 seconds
        last_health_check = time.time()
        
        while self.is_running:
            try:
                current_time = time.time()
                
                # Periodic health check
                if current_time - last_health_check > health_check_interval:
                    if self.serial and not self.serial.is_open:
                        print(f"⚠️  {self.name}: Health check - port not open, will attempt reconnect")
                        # Force reconnection attempt
                        self.serial = None
                    last_health_check = current_time
                
                # Check if serial port is actually open and working
                if self.serial and self.serial.is_open:
                    if self.serial.in_waiting:
                        raw = self.serial.read(self.serial.in_waiting)
                        
                        # Decode data
                        try:
                            text = raw.decode("ascii", errors="ignore")
                        except:
                            text = raw.decode("utf-8", errors="ignore")
                        
                        # Process each line
                        for line in text.splitlines():
                            if line.strip():
                                self._process_line(line)
                        
                        # Reset reconnect counter on successful read
                        if reconnect_attempts > 0:
                            print(f"✅ {self.name}: Data received, connection stable")
                        reconnect_attempts = 0
                        last_data_time = current_time
                else:
                    # Serial port closed/disconnected - try to reconnect
                    reconnect_attempts += 1
                    
                    # Adaptive delay: longer waits after multiple failures
                    if reconnect_attempts <= 3:
                        wait_time = 2
                        print(f"⚠️  {self.name}: USB disconnected, attempting reconnect {reconnect_attempts}...")
                    elif reconnect_attempts <= max_consecutive_failures:
                        wait_time = 5
                        print(f"⚠️  {self.name}: Reconnect attempt {reconnect_attempts} (waiting {wait_time}s)...")
                    else:
                        wait_time = 10
                        if reconnect_attempts % 6 == 0:  # Print every 6th attempt to reduce spam
                            print(f"⚠️  {self.name}: Still trying to reconnect... (attempt {reconnect_attempts})")
                    
                    time.sleep(wait_time)
                    
                    try:
                        # Try to reconnect
                        self.serial = serial.Serial(
                            port=self.port,
                            baudrate=self.baudrate,
                            timeout=0.2,
                            exclusive=True
                        )
                        self.serial.reset_input_buffer()
                        self.serial.reset_output_buffer()
                        print(f"✅ {self.name}: Reconnected successfully after {reconnect_attempts} attempts!")
                        reconnect_attempts = 0
                        last_data_time = current_time
                    except serial.SerialException as e:
                        # USB still not available
                        if reconnect_attempts <= 3:
                            print(f"   Reconnect failed: {e}")
                    except PermissionError:
                        # Another program using port
                        if reconnect_attempts == 1:
                            print(f"   Port {self.port} in use by another program")
                        time.sleep(5)  # Wait longer for permission issues
                    except FileNotFoundError:
                        # Port doesn't exist yet (USB not enumerated)
                        if reconnect_attempts <= 3:
                            print(f"   Port {self.port} not found yet...")
                    except Exception as e:
                        if reconnect_attempts <= 3:
                            print(f"   Reconnect failed: {e}")
                
                time.sleep(0.01)
                
            except PermissionError as e:
                # Port in use by another program
                print(f"❌ {self.name} permission error: {e}")
                print(f"   Port {self.port} is being used by another program!")
                time.sleep(5)
                # Don't stop, keep trying in case other program releases it
            
            except serial.SerialException as e:
                # USB device disconnected
                print(f"⚠️  {self.name}: USB device error - {e}")
                if self.serial:
                    try:
                        self.serial.close()
                    except:
                        pass
                    self.serial = None
                # Loop will retry connection above
                time.sleep(1)
                
            except Exception as e:
                if self.is_running:  # Only log if still supposed to be running
                    print(f"⚠️  {self.name} error: {e}")
                    # Don't stop on other errors, just log and continue
                time.sleep(1)
    
    def _process_line(self, line):
        """Process incoming data line"""
        weight_kg = None
        
        # Debug: show raw data (only first time for each scale)
        if not hasattr(self, '_first_data_shown'):
            print(f"📡 {self.name}: Receiving data: {repr(line)}")
            self._first_data_shown = True
        
        # Try each pattern
        for i, pattern in enumerate(self.patterns):
            match = pattern.search(line)
            if match:
                try:
                    raw_value = int(match.group(1))
                    weight_kg = raw_value / self.division
                    
                    # Auto-detect format
                    if self.detected_format is None:
                        self.detected_format = i
                        format_names = ["Format 1 (t01 3990)", 
                                      "Format 2 (l80 4009)", 
                                      "Format 3 (fallback)"]
                        print(f"🔍 {self.name}: Detected {format_names[i]}")
                    
                    break
                except (ValueError, IndexError):
                    continue
        
        if weight_kg is None:
            return
        
        self.current_weight = weight_kg
        now = time.time()
        
        # Detect bag FULL
        if weight_kg >= self.FULL_THRESHOLD and self.state == "EMPTY":
            if self.full_since is None:
                self.full_since = now
                self.last_full_weight = weight_kg
            elif now - self.full_since >= self.STABLE_TIME:
                self.state = "FULL"
                print(f"🎯 {self.name}: Bag ready {self.last_full_weight:.2f} kg")
        
        # Update stable weight
        if self.state == "EMPTY" and weight_kg >= self.FULL_THRESHOLD:
            self.last_full_weight = weight_kg
        
        # Detect bag REMOVED
        if weight_kg <= self.EMPTY_THRESHOLD and self.state == "FULL":
            self.bag_count += 1
            self.state = "EMPTY"
            
            bag_info = {
                'bag_number': self.bag_count,
                'weight': self.last_full_weight,
                'timestamp': datetime.now(),
                'machine_name': self.name,
                'bag_size': self.bag_size,
                'product': self.product
            }
            self.session_bags.append(bag_info)
            
            print(f"✅ {self.name}: Bag #{self.bag_count} | {self.last_full_weight:.2f} kg")
            
            # Auto-save to database if callback provided
            if self.on_bag_complete:
                try:
                    self.on_bag_complete(bag_info)
                    print(f"   💾 Saved to database")
                except Exception as e:
                    print(f"   ⚠️  Database save failed: {e}")
            
            self.full_since = None
        
        # Reset if weight drops early
        if weight_kg < self.FULL_THRESHOLD and self.state == "EMPTY":
            self.full_since = None
    
    def get_current_weight(self):
        return self.current_weight
    
    def get_bag_count(self):
        return self.bag_count
    
    def query_scale_counter(self):
        """
        Query the scale's internal bag counter
        Different scales use different commands
        """
        if not self.serial or not self.serial.is_open:
            return None
        
        commands_to_try = [
            b'C\r\n',      # Counter command (common)
            b'?C\r\n',     # Query counter
            b'RC\r\n',     # Read counter
            b'P\r\n',      # Print (might include counter)
            b'\x05',       # ENQ (enquiry)
        ]
        
        for cmd in commands_to_try:
            try:
                # Clear buffer
                self.serial.reset_input_buffer()
                
                # Send command
                self.serial.write(cmd)
                time.sleep(0.3)  # Wait for response
                
                # Read response
                if self.serial.in_waiting:
                    response = self.serial.read(self.serial.in_waiting)
                    decoded = response.decode('ascii', errors='ignore')
                    
                    # Try to extract counter value
                    # Common formats: "C:123", "COUNT:123", "BAGS:123"
                    import re
                    patterns = [
                        r'C[:\s]*(\d+)',       # C:123 or C 123
                        r'COUNT[:\s]*(\d+)',   # COUNT:123
                        r'BAGS[:\s]*(\d+)',    # BAGS:123
                        r'CNT[:\s]*(\d+)',     # CNT:123
                        r'^(\d+)$',            # Just a number
                    ]
                    
                    for pattern in patterns:
                        match = re.search(pattern, decoded, re.IGNORECASE)
                        if match:
                            count = int(match.group(1))
                            print(f"📊 {self.name}: Scale counter = {count} bags")
                            return count
                            
            except Exception as e:
                continue
        
        print(f"⚠️  {self.name}: Could not read scale counter")
        return None
    
    def sync_with_scale_counter(self, db_count):
        """
        Compare scale counter with database count
        Returns number of missing bags
        """
        scale_count = self.query_scale_counter()
        
        if scale_count is None:
            return 0
        
        missing_bags = scale_count - db_count
        
        if missing_bags > 0:
            print(f"⚠️  {self.name}: SYNC NEEDED!")
            print(f"   Scale counter: {scale_count} bags")
            print(f"   Database count: {db_count} bags")
            print(f"   Missing: {missing_bags} bags")
            return missing_bags
        elif missing_bags < 0:
            print(f"⚠️  {self.name}: Database has MORE bags than scale!")
            print(f"   Scale might have been reset")
        else:
            print(f"✅ {self.name}: Counts match ({scale_count} bags)")
        
        return missing_bags
    
    def get_current_weight(self):
        return self.current_weight
    
    def get_bag_count(self):
        return self.bag_count
    
    def get_last_bag_weight(self):
        if self.session_bags:
            return self.session_bags[-1]['weight']
        return 0.0
    
    def get_session_stats(self):
        if not self.session_bags:
            return {
                'total_bags': 0,
                'total_weight': 0.0,
                'average_weight': 0.0,
                'min_weight': 0.0,
                'max_weight': 0.0
            }
        
        weights = [bag['weight'] for bag in self.session_bags]
        
        return {
            'total_bags': self.bag_count,
            'total_weight': sum(weights),
            'average_weight': sum(weights) / len(weights),
            'min_weight': min(weights),
            'max_weight': max(weights)
        }
    
    def get_recent_bags(self, count=10):
        return self.session_bags[-count:]
    
    def reset_session(self):
        self.bag_count = 0
        self.session_bags = []
        self.session_start = datetime.now()
        print(f"📊 {self.name}: Session reset")
    
    def is_online(self):
        """Check if scale is currently online and communicating"""
        try:
            return self.is_running and self.serial is not None and self.serial.is_open
        except:
            return False
    
    def get_status(self):
        return {
            'online': self.is_online(),
            'current_weight': self.current_weight,
            'state': self.state,
            'bag_count': self.bag_count,
            'last_bag_weight': self.get_last_bag_weight(),
            'detected_format': self.detected_format,
            'name': self.name,
            'port': self.port,
            'bag_size': self.bag_size,
            'product': self.product
        }
    
    def close(self):
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
        if self.serial and self.serial.is_open:
            self.serial.close()
        print(f"{self.name} disconnected")


# ============================================================================
# MULTI-MACHINE MANAGER
# ============================================================================

class MultiMachineManager:
    """
    Manages all 3 Baykon machines simultaneously
    """
    
    def __init__(self, on_bag_complete=None):
        self.machines = {}
        self.on_bag_complete = on_bag_complete  # Callback for auto-save
        self._initialize_machines()
    
    def _initialize_machines(self):
        """Initialize all 3 machines"""
        
        print("\n" + "="*70)
        print("INITIALIZING 3 BAYKON MACHINES")
        print("="*70)
        
        # Get COM ports from environment or use defaults
        import os
        port_bran = os.environ.get("PACKING_PORT_BRAN", "COM3")     # BX3 Bran 40kg
        port_flour1 = os.environ.get("PACKING_PORT_FLOUR1", "COM9")  # BXf3 Flour 50kg
        port_flour2 = os.environ.get("PACKING_PORT_FLOUR2", "COM5") # BX30 Flour 50kg
        
        print(f"Looking for scales on:")
        print(f"  • Bran 40kg:   {port_bran}")
        print(f"  • Flour 50kg:  {port_flour1}")
        print(f"  • Flour 50kg:  {port_flour2}")
        print()
        
        # Machine 1: BX3 40kg Bran
        try:
            self.machines['bran_40kg'] = BaykonMachine(
                name="BX3 - Bran 40kg",
                port=port_bran,
                baudrate=9600,
                full_threshold=38.0,
                bag_size=40,
                product="Coarse Bran",
                on_bag_complete=self.on_bag_complete
            )
            time.sleep(0.5)  # Wait for thread to stabilize
        except Exception as e:
            print(f"❌ BX3 Bran 40kg on {port_bran}: {e}")
            self.machines['bran_40kg'] = None
        
        # Machine 2: BXf3 50kg Flour
        try:
            self.machines['flour_50kg_bxf3'] = BaykonMachine(
                name="BXf3 - Flour 50kg",
                port=port_flour1,
                baudrate=9600,
                full_threshold=48.0,
                bag_size=50,
                product="Flour",
                on_bag_complete=self.on_bag_complete
            )
            time.sleep(0.5)  # Wait for thread to stabilize
        except Exception as e:
            print(f"❌ BXf3 Flour 50kg on {port_flour1}: {e}")
            self.machines['flour_50kg_bxf3'] = None
        
        # Machine 3: BX30 50kg Flour
        try:
            self.machines['flour_50kg_bx30'] = BaykonMachine(
                name="BX30 - Flour 50kg",
                port=port_flour2,
                baudrate=9600,
                full_threshold=48.0,
                bag_size=50,
                product="Flour",
                on_bag_complete=self.on_bag_complete
            )
            time.sleep(0.5)  # Wait for thread to stabilize
        except Exception as e:
            print(f"❌ BX30 Flour 50kg on {port_flour2}: {e}")
            self.machines['flour_50kg_bx30'] = None
        
        print("="*70 + "\n")
        
        # Summary
        online_count = sum(1 for m in self.machines.values() if m and m.is_online())
        print(f"📊 Machines online: {online_count}/3")
        
        if online_count == 0:
            print()
            print("⚠️  NO PACKING SCALES CONNECTED!")
            print("   Check:")
            print("   1. USB cables are plugged in")
            print("   2. Scales are powered on")
            print("   3. Run 'python find_com_ports.py' to find correct ports")
            print("   4. Update COM ports in this file or set environment variables")
            print()
    
    def get_machine(self, machine_id):
        """Get specific machine"""
        return self.machines.get(machine_id)
    
    def get_all_status(self):
        """Get status from all machines"""
        status = {}
        for machine_id, machine in self.machines.items():
            if machine and machine.is_online():
                status[machine_id] = machine.get_status()
            else:
                status[machine_id] = {
                    'online': False,
                    'current_weight': 0.0,
                    'state': 'OFFLINE',
                    'bag_count': 0,
                    'last_bag_weight': 0.0,
                    'name': f"Machine {machine_id}",
                    'bag_size': 0,
                    'product': 'Unknown'
                }
        return status
    
    def get_all_stats(self):
        """Get stats from all machines"""
        stats = {}
        for machine_id, machine in self.machines.items():
            if machine:
                stats[machine_id] = machine.get_session_stats()
            else:
                stats[machine_id] = {
                    'total_bags': 0,
                    'total_weight': 0.0,
                    'average_weight': 0.0,
                    'min_weight': 0.0,
                    'max_weight': 0.0
                }
        return stats
    
    def get_recent_bags(self, machine_id, count=10):
        """Get recent bags from specific machine"""
        machine = self.machines.get(machine_id)
        if machine:
            return machine.get_recent_bags(count)
        return []
    
    def reset_machine(self, machine_id):
        """Reset specific machine"""
        machine = self.machines.get(machine_id)
        if machine:
            machine.reset_session()
            return True
        return False
    
    def reset_all(self):
        """Reset all machines"""
        for machine in self.machines.values():
            if machine:
                machine.reset_session()
    
    def sync_all_counters(self, db_counts):
        """
        Sync all scale counters with database
        db_counts: dict like {'bran_40kg': 150, 'flour_50kg_bxf3': 200, ...}
        Returns: dict of missing bags per machine
        """
        missing = {}
        for machine_id, machine in self.machines.items():
            if machine and machine.is_online():
                db_count = db_counts.get(machine_id, 0)
                missing_bags = machine.sync_with_scale_counter(db_count)
                if missing_bags > 0:
                    missing[machine_id] = missing_bags
        return missing
    
    def query_all_counters(self):
        """
        Query counters from all online scales
        Returns: dict like {'bran_40kg': 150, 'flour_50kg_bxf3': 200, ...}
        """
        counters = {}
        for machine_id, machine in self.machines.items():
            if machine and machine.is_online():
                count = machine.query_scale_counter()
                if count is not None:
                    counters[machine_id] = count
        return counters
    
    def close_all(self):
        """Close all connections"""
        for machine in self.machines.values():
            if machine:
                machine.close()


# For standalone testing
if __name__ == "__main__":
    print("Testing Multi-Machine Manager...")
    print("Press Ctrl+C to stop")
    print("-" * 70)
    
    manager = MultiMachineManager()
    
    try:
        while True:
            all_status = manager.get_all_status()
            
            print("\r", end='')
            for machine_id, status in all_status.items():
                if status['online']:
                    print(f"{status['name']}: {status['bag_count']} bags ({status['current_weight']:.1f}kg) | ", end='')
                else:
                    print(f"{machine_id}: OFFLINE | ", end='')
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\n\nStopping...")
        manager.close_all()
        print("\nFinal Stats:")
        stats = manager.get_all_stats()
        for machine_id, stat in stats.items():
            print(f"{machine_id}: {stat['total_bags']} bags, {stat['total_weight']:.2f} kg")
