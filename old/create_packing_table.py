"""
Automatic Packing Table Creator
Run this to create the packing table in your database
"""

import mysql.connector

print("=" * 60)
print("  PACKING TABLE CREATOR")
print("=" * 60)
print()

# Database configuration
DB_CONFIG = {
    "host": input("MySQL Host (default: localhost): ") or "localhost",
    "user": input("MySQL User (default: milluser): ") or "milluser",
    "password": input("MySQL Password: "),
    "database": input("Database Name (default: mill): ") or "mill",
}

print()
print("Connecting to database...")

try:
    # Connect to database
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("✅ Connected!")
    print()
    print("Creating packing table...")
    
    # Create table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS packing (
            id INT AUTO_INCREMENT PRIMARY KEY,
            product_type VARCHAR(100) NOT NULL COMMENT 'Flour 72%, Flour 82%, Bran, etc.',
            bag_weight DECIMAL(10,2) NOT NULL COMMENT 'Weight per bag in kg',
            bag_count INT NOT NULL COMMENT 'Number of bags',
            total_weight DECIMAL(10,2) NOT NULL COMMENT 'Total weight (bag_weight × bag_count)',
            production_line VARCHAR(50) DEFAULT 'Line 1' COMMENT 'Production line identifier',
            shift VARCHAR(50) DEFAULT 'Morning' COMMENT 'Morning, Evening, Night',
            operator VARCHAR(100) COMMENT 'Operator name',
            notes TEXT COMMENT 'Optional notes',
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(100),
            
            INDEX idx_product (product_type),
            INDEX idx_date (created_at),
            INDEX idx_line (production_line),
            INDEX idx_shift (shift)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
        COMMENT='Packing production records'
    """)
    
    print("✅ Table created successfully!")
    print()
    
    # Insert sample data
    print("Adding sample data...")
    cursor.execute("""
        INSERT INTO packing (product_type, bag_weight, bag_count, total_weight, 
                           production_line, shift, operator, created_by)
        VALUES 
            ('Flour 72%', 25, 40, 1000, 'Line 1', 'Morning', 'Ahmed', 'admin'),
            ('Flour 82%', 50, 20, 1000, 'Line 2', 'Morning', 'Mohammed', 'admin'),
            ('Bran', 25, 30, 750, 'Line 1', 'Evening', 'Ali', 'admin'),
            ('Semolina', 25, 50, 1250, 'Line 3', 'Morning', 'Hassan', 'admin')
    """)
    
    conn.commit()
    print("✅ Sample data added!")
    print()
    
    # Verify
    cursor.execute("SELECT COUNT(*) FROM packing")
    count = cursor.fetchone()[0]
    
    print("=" * 60)
    print(f"✅ SUCCESS! Packing table created with {count} sample records")
    print("=" * 60)
    print()
    print("You can now:")
    print("  1. Run your app: python app.py")
    print("  2. Visit: http://localhost:5000/packing")
    print("  3. Start recording production!")
    print()
    
    cursor.close()
    conn.close()
    
except mysql.connector.Error as err:
    print(f"❌ Database Error: {err}")
    print()
    print("Common issues:")
    print("  - Wrong password")
    print("  - Database 'mill' doesn't exist")
    print("  - User doesn't have permissions")
    print()

except Exception as e:
    print(f"❌ Error: {e}")

input("Press Enter to exit...")
