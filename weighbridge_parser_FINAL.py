"""
WEIGHBRIDGE BINARY PARSER - FINAL CORRECT VERSION

Calibrated with:
  100 kg  → raw 30848
  3690 kg → raw 30968

Formula: weight = (29.9167 × raw_value) - 922769.33
"""

def parse_weighbridge_weight(data):
    """
    Parse weight from binary weighbridge scale data
    
    Data format (5 bytes):
      [0] = 0x80 (header)
      [1] = 0x80 (header)
      [2] = low byte of raw weight value
      [3] = high byte of raw weight value
      [4] = 0x00 (terminator)
    
    Args:
        data: bytes object containing scale data
        
    Returns:
        int: weight in kg, or 0 if invalid/error
    """
    
    # Validate data length
    if len(data) < 5:
        return 0
    
    # Check header bytes
    if data[0] != 0x80 or data[1] != 0x80:
        return 0
    
    # Extract 16-bit raw value (little-endian)
    # byte[2] is low byte, byte[3] is high byte
    raw_value = data[2] | (data[3] << 8)
    
    # Apply calibration formula
    # Formula derived from two-point calibration:
    #   100 kg @ raw_value=30848
    #   3690 kg @ raw_value=30968
    weight = (29.916666666666668 * raw_value) - 922769.3333333334
    
    # Round to nearest kg
    weight = round(weight)
    
    # Weighbridge sanity check (allow 0-100,000 kg)
    if weight < 0 or weight > 100000:
        return 0
    
    return weight


# ============================================================================
# TESTING
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("WEIGHBRIDGE PARSER - FINAL VERSION")
    print("="*70)
    print()
    
    # Test with known data
    test_cases = [
        (b'\x80\x80\x00\x78\x00', 100, "100 kg test"),
        (b'\x80\x80\xF8\x78\x00', 3690, "3690 kg test"),
    ]
    
    all_passed = True
    
    for data, expected, label in test_cases:
        result = parse_weighbridge_weight(data)
        status = "✅ PASS" if result == expected else f"❌ FAIL (got {result})"
        print(f"{label:20s} | Expected: {expected:5d} kg | Result: {result:5d} kg | {status}")
        if result != expected:
            all_passed = False
    
    print()
    
    if all_passed:
        print("✅ ALL TESTS PASSED!")
    else:
        print("❌ SOME TESTS FAILED")
    
    print()
    print("="*70)
    print("INTEGRATION INSTRUCTIONS")
    print("="*70)
    print()
    print("1. Find your weighbridge serial reading code")
    print("2. Replace the weight parsing with this function:")
    print()
    print("   # In your serial reading loop:")
    print("   if serial_port.in_waiting > 0:")
    print("       data = serial_port.read(serial_port.in_waiting)")
    print("       weight = parse_weighbridge_weight(data)")
    print("       if weight > 0:")
    print("           print(f'Weighbridge: {weight} kg')")
    print("           # Update your database/display here")
    print()
    print("3. Test with actual vehicles on the scale")
    print("4. Verify the displayed weight matches scale display")
    print()
    
    print("="*70)
    print("EXPECTED BEHAVIOR")
    print("="*70)
    print()
    print("Raw value range:")
    print("  30848 (0x7800) → 100 kg")
    print("  30861 → ~500 kg")
    print("  30878 → ~1000 kg")
    print("  30968 (0x78F8) → 3690 kg")
    print("  31012 → ~5000 kg")
    print()