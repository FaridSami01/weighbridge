# packing_scale.py - Multi-Format Baykon Support
# Supports both BX3 data formats

import serial
import re
import time
import threading
from datetime import datetime

class PackingScaleReader:
    """
    Multi-Format Baykon Reader
    Supports:
    - BX3 Format 1: "t01 3990" (40kg bran machine)
    - BX3 Format 2: "\x02l80  4009     0\r@" (50kg flour machine)
    """
    
    def __init__(self, port="COM3", baudrate=9600, division=100, 
                 full_threshold=38.0, empty_threshold=2.0):
        self.port = port
        self.baudrate = baudrate
        self.division = division
        
        # Thresholds (can be adjusted per machine)
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
            # Format 1: "t01 3990" (40kg BX3)
            re.compile(r't\d+\s+(\d+)'),
            
            # Format 2: "\x02l80  4009     0\r@" (50kg BX3)
            # Extracts the number after "l80  "
            re.compile(r'l\d+\s+(\d+)'),
            
            # Format 3: Just any 4-5 digit number (fallback)
            re.compile(r'(\d{4,5})'),
        ]
        
        # Thread
        self.thread = None
        
        # Auto-detect format
        self.detected_format = None
        
        # Start connection
        self.connect()
    
    def connect(self):
        """Connect to Baykon machine"""
        try:
            self.serial = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                timeout=0.2
            )
            self.is_running = True
            
            # Start monitoring thread
            self.thread = threading.Thread(target=self._monitor, daemon=True)
            self.thread.start()
            
            print(f"✅ Baykon connected on {self.port}")
            
        except Exception as e:
            print(f"❌ Baykon connection failed on {self.port}: {e}")
            self.is_running = False
    
    def _monitor(self):
        """Monitor scale data in background thread"""
        while self.is_running:
            try:
                if self.serial and self.serial.in_waiting:
                    raw = self.serial.read(self.serial.in_waiting)
                    
                    # Try to decode (handles both ASCII and binary data)
                    try:
                        text = raw.decode("ascii", errors="ignore")
                    except:
                        text = raw.decode("utf-8", errors="ignore")
                    
                    # Process each line
                    for line in text.splitlines():
                        if line.strip():
                            self._process_line(line)
                
                time.sleep(0.01)
                
            except Exception as e:
                print(f"Baykon monitoring error: {e}")
                time.sleep(1)
    
    def _process_line(self, line):
        """Process incoming data line with multiple format support"""
        # Try each pattern until one matches
        weight_kg = None
        
        for i, pattern in enumerate(self.patterns):
            match = pattern.search(line)
            if match:
                try:
                    raw_value = int(match.group(1))
                    weight_kg = raw_value / self.division
                    
                    # Auto-detect format on first successful parse
                    if self.detected_format is None:
                        self.detected_format = i
                        format_names = ["Format 1 (t01 3990)", 
                                      "Format 2 (l80 4009)", 
                                      "Format 3 (fallback)"]
                        print(f"🔍 Auto-detected data format: {format_names[i]}")
                    
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
                print(f"🎯 Bag ready: {self.last_full_weight:.2f} kg")
        
        # Update stable full weight
        if self.state == "EMPTY" and weight_kg >= self.FULL_THRESHOLD:
            self.last_full_weight = weight_kg
        
        # Detect bag REMOVED (completed)
        if weight_kg <= self.EMPTY_THRESHOLD and self.state == "FULL":
            self.bag_count += 1
            self.state = "EMPTY"
            
            # Record bag
            bag_info = {
                'bag_number': self.bag_count,
                'weight': self.last_full_weight,
                'timestamp': datetime.now()
            }
            self.session_bags.append(bag_info)
            
            print(f"✅ Bag #{self.bag_count} completed | Weight: {self.last_full_weight:.2f} kg")
            
            self.full_since = None
        
        # Reset if weight drops early
        if weight_kg < self.FULL_THRESHOLD and self.state == "EMPTY":
            self.full_since = None
    
    def get_current_weight(self):
        """Get current scale reading"""
        return self.current_weight
    
    def get_bag_count(self):
        """Get total bags counted this session"""
        return self.bag_count
    
    def get_last_bag_weight(self):
        """Get weight of last completed bag"""
        if self.session_bags:
            return self.session_bags[-1]['weight']
        return 0.0
    
    def get_session_stats(self):
        """Get statistics for current session"""
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
        """Get recent bag data"""
        return self.session_bags[-count:]
    
    def reset_session(self):
        """Reset session counters (call at start of shift)"""
        self.bag_count = 0
        self.session_bags = []
        self.session_start = datetime.now()
        print("📊 Session reset")
    
    def is_online(self):
        """Check if scale is connected"""
        return self.is_running and self.serial and self.serial.is_open
    
    def get_status(self):
        """Get current status"""
        return {
            'online': self.is_online(),
            'current_weight': self.current_weight,
            'state': self.state,
            'bag_count': self.bag_count,
            'last_bag_weight': self.get_last_bag_weight(),
            'detected_format': self.detected_format
        }
    
    def close(self):
        """Close connection"""
        self.is_running = False
        if self.thread:
            self.thread.join(timeout=2)
        if self.serial and self.serial.is_open:
            self.serial.close()
        print(f"Baykon on {self.port} disconnected")


# ============================================================================
# MULTI-MACHINE SUPPORT
# ============================================================================

class MultiMachineManager:
    """
    Manage multiple Baykon machines simultaneously
    """
    
    def __init__(self):
        self.machines = {}
    
    def add_machine(self, name, port, baudrate=9600, full_threshold=38.0):
        """Add a machine to the system"""
        machine = PackingScaleReader(
            port=port,
            baudrate=baudrate,
            full_threshold=full_threshold
        )
        self.machines[name] = machine
        return machine
    
    def get_machine(self, name):
        """Get a specific machine"""
        return self.machines.get(name)
    
    def get_all_stats(self):
        """Get stats from all machines"""
        return {
            name: machine.get_session_stats()
            for name, machine in self.machines.items()
        }
    
    def get_all_status(self):
        """Get status from all machines"""
        return {
            name: machine.get_status()
            for name, machine in self.machines.items()
        }
    
    def reset_all(self):
        """Reset all machine counters"""
        for machine in self.machines.values():
            machine.reset_session()
    
    def close_all(self):
        """Close all connections"""
        for machine in self.machines.values():
            machine.close()


# For standalone testing
if __name__ == "__main__":
    print("Testing Multi-Format Baykon Reader...")
    print("Press Ctrl+C to stop")
    print("-" * 50)
    
    # Test with current port (adjust as needed)
    scale = PackingScaleReader(port="COM3", baudrate=9600, full_threshold=38.0)
    
    try:
        while True:
            stats = scale.get_session_stats()
            status = scale.get_status()
            
            format_name = "Unknown"
            if status['detected_format'] == 0:
                format_name = "Format 1 (t01 3990)"
            elif status['detected_format'] == 1:
                format_name = "Format 2 (l80 4009)"
            elif status['detected_format'] == 2:
                format_name = "Format 3 (fallback)"
            
            print(f"\rBags: {stats['total_bags']} | "
                  f"Weight: {status['current_weight']:.2f} kg | "
                  f"State: {status['state']} | "
                  f"Avg: {stats['average_weight']:.2f} kg | "
                  f"Format: {format_name}",
                  end='', flush=True)
            
            time.sleep(0.5)
            
    except KeyboardInterrupt:
        print("\n\nStopping...")
        scale.close()
        print(f"\nFinal Stats:")
        print(f"Total Bags: {scale.bag_count}")
        stats = scale.get_session_stats()
        print(f"Total Weight: {stats['total_weight']:.2f} kg")
        print(f"Average: {stats['average_weight']:.2f} kg")
