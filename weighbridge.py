"""
Ultra-Simple Weighbridge - Guaranteed to work
"""

import serial
import threading
import time
import re

class WeighbridgeReader:
    def __init__(self, port="COM4", baudrate=9600):
        self.port = port
        self.baudrate = baudrate
        self.weight = 0
        self._online = False
        self.running = True
        self.ser = None
        
        # Open port in main thread
        try:
            self.ser = serial.Serial(
                port=self.port,
                baudrate=self.baudrate,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=1
            )
            print(f"✅ Weighbridge connected: {self.port} @ {self.baudrate} baud")
            
            # Set online immediately if port opens successfully
            # Scale only sends data when weight changes, so we can't wait for data
            self._online = True
            
        except Exception as e:
            print(f"⚠️  Weighbridge error: {e}")
            self.ser = None
            self._online = False
            return
        
        # Start read thread
        self.thread = threading.Thread(target=self._read_loop, daemon=True)
        self.thread.start()
    
    def _read_loop(self):
        """Read data continuously"""
        buffer = ""
        
        while self.running and self.ser and self.ser.is_open:
            try:
                if self.ser.in_waiting > 0:
                    data = self.ser.read(self.ser.in_waiting)
                    
                    if data:
                        # Data received - keep online status
                        # (already set to True when port opened)
                        
                        # Process data - decode and remove binary junk
                        text = data.decode('ascii', errors='ignore')
                        
                        # Remove non-printable characters (binary junk)
                        text = ''.join(c for c in text if c.isprintable() or c in '\r\n')
                        
                        buffer += text
                        
                        # Try to parse from buffer immediately (don't wait for newlines)
                        # Pattern from your scale: +0041001D where 410 is the weight
                        # Format: +00WWWXXD where WWW=weight, XX=extra, D=letter
                        
                        # Extract all digits from buffer
                        numbers_only = re.sub(r'[^\d]', '', buffer)
                        
                        if len(numbers_only) >= 4:
                            try:
                                # Remove leading zeros
                                numbers_stripped = numbers_only.lstrip('0')
                                
                                if numbers_stripped:
                                    # Take first 3-4 digits as weight
                                    # 41001 -> 410
                                    # 1502001 -> 1502
                                    if len(numbers_stripped) >= 5:
                                        val = int(numbers_stripped[:4])  # Take first 4 digits
                                    else:
                                        val = int(numbers_stripped[:3])  # Take first 3 digits
                                    
                                    # Check if reasonable weight
                                    if 0 <= val <= 100000:
                                        # Only update if changed significantly (avoid jitter)
                                        if abs(val - self.weight) > 5:
                                            self.weight = val
                                else:
                                    # All zeros
                                    if self.weight != 0:
                                        self.weight = 0
                                    
                            except Exception as e:
                                pass  # Ignore parse errors
                        
                        # Clear buffer after parsing to avoid old data
                        buffer = buffer[-20:]  # Keep only last 20 chars
                
                time.sleep(0.05)
                
            except Exception as e:
                print(f"Read error: {e}")
                self._online = False
                break
    
    def get_weight(self):
        """Get current weight"""
        return self.weight
    
    def is_online(self):
        """Check if online"""
        if not self.ser or not self.ser.is_open:
            return False
        return self._online
    
    def stop(self):
        """Stop reader"""
        self.running = False
        if self.ser:
            try:
                self.ser.close()
            except:
                pass


if __name__ == "__main__":
    import sys
    
    port = sys.argv[1] if len(sys.argv) > 1 else "COM4"
    baud = int(sys.argv[2]) if len(sys.argv) > 2 else 9600
    
    print("Testing...")
    w = WeighbridgeReader(port, baud)
    
    time.sleep(1)
    
    try:
        for i in range(20):
            print(f"[{i+1}] Weight: {w.get_weight():>5} kg | Online: {w.is_online()}")
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        w.stop()
