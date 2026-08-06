"""
Accounting Schema Installer for Toll Milling System
Automatically creates all accounting tables, triggers, and sample data
"""

import mysql.connector
import sys
from datetime import datetime

print("=" * 70)
print("  ACCOUNTING SCHEMA INSTALLER")
print("  Al Mohandes Modern Mills - Toll Milling System")
print("=" * 70)
print()

# Database credentials
DB_CONFIG = {
    "host": input("MySQL Host (default: localhost): ") or "localhost",
    "user": input("MySQL User (default: milluser): ") or "milluser",
    "password": input("MySQL Password: "),
    "database": input("Database Name (default: mill): ") or "mill",
}

print()
print("Connecting to database...")
print()

try:
    # Connect to database
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("✅ Connected successfully!")
    print()
    print("=" * 70)
    print("STEP 1: Creating accounting configuration table...")
    print("=" * 70)
    
    # Create accounting_config table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounting_config (
            id INT PRIMARY KEY AUTO_INCREMENT,
            config_key VARCHAR(50) UNIQUE NOT NULL,
            config_value DECIMAL(10,2) NOT NULL,
            unit VARCHAR(20),
            description TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            updated_by VARCHAR(100)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    print("✅ accounting_config table created")
    
    # Insert default rates
    default_rates = [
        ('milling_fee', 770.00, 'LE/ton', 'Milling fee per ton of wheat'),
        ('bran_share_percent', 15.00, '%', 'Percentage share of coarse bran revenue'),
        ('bran_price_per_ton', 11000.00, 'LE/ton', 'Current market price of coarse bran per ton'),
        ('weighbridge_fee', 10.00, 'LE', 'Fee per weighing for non-customers'),
        ('extraction_rate', 87.5, '%', 'Flour extraction rate')
    ]
    
    for key, value, unit, desc in default_rates:
        cursor.execute("""
            INSERT INTO accounting_config (config_key, config_value, unit, description)
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE config_value=VALUES(config_value)
        """, (key, value, unit, desc))
    
    print("✅ Default rates configured:")
    print(f"   - Milling Fee: LE 770/ton")
    print(f"   - Bran Share: 15%")
    print(f"   - Bran Price: LE 11,000/ton")
    print(f"   - Weighbridge Fee: LE 10")
    print(f"   - Extraction Rate: 87.5%")
    print()
    
    print("=" * 70)
    print("STEP 2: Creating revenue tracking table...")
    print("=" * 70)
    
    # Create accounting_revenue table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounting_revenue (
            id INT PRIMARY KEY AUTO_INCREMENT,
            date DATE NOT NULL,
            source_type ENUM('milling', 'bran', 'weighbridge', 'other') NOT NULL,
            description VARCHAR(255),
            quantity DECIMAL(10,2) DEFAULT 0,
            rate DECIMAL(10,2) DEFAULT 0,
            amount DECIMAL(10,2) NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(100),
            
            INDEX idx_date (date),
            INDEX idx_source (source_type),
            INDEX idx_amount (amount)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    print("✅ accounting_revenue table created")
    print()
    
    print("=" * 70)
    print("STEP 3: Creating expenses tracking table...")
    print("=" * 70)
    
    # Create accounting_expenses table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS accounting_expenses (
            id INT PRIMARY KEY AUTO_INCREMENT,
            date DATE NOT NULL,
            category ENUM('labor', 'transport', 'bags', 'electricity', 'water', 'maintenance') NOT NULL,
            description VARCHAR(255) NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            created_by VARCHAR(100),
            
            INDEX idx_date (date),
            INDEX idx_category (category),
            INDEX idx_amount (amount)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    """)
    print("✅ accounting_expenses table created")
    print()
    
    print("=" * 70)
    print("STEP 4: Creating reporting views...")
    print("=" * 70)
    
    # Create daily revenue summary view
    cursor.execute("""
        CREATE OR REPLACE VIEW daily_revenue_summary AS
        SELECT 
            date,
            SUM(CASE WHEN source_type = 'milling' THEN amount ELSE 0 END) as milling_revenue,
            SUM(CASE WHEN source_type = 'bran' THEN amount ELSE 0 END) as bran_revenue,
            SUM(CASE WHEN source_type = 'weighbridge' THEN amount ELSE 0 END) as weighbridge_revenue,
            SUM(CASE WHEN source_type = 'other' THEN amount ELSE 0 END) as other_revenue,
            SUM(amount) as total_revenue
        FROM accounting_revenue
        GROUP BY date
        ORDER BY date DESC
    """)
    print("✅ daily_revenue_summary view created")
    
    # Create daily expense summary view
    cursor.execute("""
        CREATE OR REPLACE VIEW daily_expense_summary AS
        SELECT 
            date,
            SUM(CASE WHEN category = 'labor' THEN amount ELSE 0 END) as labor_expense,
            SUM(CASE WHEN category = 'transport' THEN amount ELSE 0 END) as transport_expense,
            SUM(CASE WHEN category = 'bags' THEN amount ELSE 0 END) as bags_expense,
            SUM(CASE WHEN category = 'electricity' THEN amount ELSE 0 END) as electricity_expense,
            SUM(CASE WHEN category = 'water' THEN amount ELSE 0 END) as water_expense,
            SUM(CASE WHEN category = 'maintenance' THEN amount ELSE 0 END) as maintenance_expense,
            SUM(amount) as total_expenses
        FROM accounting_expenses
        GROUP BY date
        ORDER BY date DESC
    """)
    print("✅ daily_expense_summary view created")
    
    # Create monthly profit/loss view
    cursor.execute("""
        CREATE OR REPLACE VIEW monthly_profit_loss AS
        SELECT 
            DATE_FORMAT(COALESCE(r.date, e.date), '%Y-%m') as month,
            COALESCE(SUM(r.amount), 0) as revenue,
            COALESCE(SUM(e.amount), 0) as expenses,
            COALESCE(SUM(r.amount), 0) - COALESCE(SUM(e.amount), 0) as profit
        FROM accounting_revenue r
        LEFT JOIN accounting_expenses e ON DATE_FORMAT(r.date, '%Y-%m') = DATE_FORMAT(e.date, '%Y-%m')
        GROUP BY DATE_FORMAT(COALESCE(r.date, e.date), '%Y-%m')
        ORDER BY month DESC
    """)
    print("✅ monthly_profit_loss view created")
    print()
    
    print("=" * 70)
    print("STEP 5: Adding sample data for testing...")
    print("=" * 70)
    
    # Add sample expenses
    sample_expenses = [
        ('2026-02-11', 'labor', 'Monthly salaries - February 2026', 85000.00),
        ('2026-02-10', 'electricity', 'Electricity bill - January 2026', 42500.00),
        ('2026-02-09', 'transport', 'Wheat transportation - Week 6', 15000.00),
        ('2026-02-08', 'bags', 'Flour bags - 10,000 pieces', 8500.00),
        ('2026-02-07', 'water', 'Water bill - January 2026', 3200.00),
        ('2026-02-06', 'maintenance', 'Motor bearing replacement', 6800.00)
    ]
    
    for date, category, description, amount in sample_expenses:
        cursor.execute("""
            INSERT INTO accounting_expenses (date, category, description, amount, created_by)
            VALUES (%s, %s, %s, %s, 'admin')
        """, (date, category, description, amount))
    
    print("✅ Sample expenses added:")
    print(f"   - Labor: LE 85,000")
    print(f"   - Electricity: LE 42,500")
    print(f"   - Transport: LE 15,000")
    print(f"   - Bags: LE 8,500")
    print(f"   - Water: LE 3,200")
    print(f"   - Maintenance: LE 6,800")
    print()
    
    # Add sample revenue
    sample_revenue = [
        ('2026-02-11', 'milling', 'Milling fee for 50 tons', 50, 770, 38500),
        ('2026-02-11', 'bran', 'Coarse bran revenue share', 5, 11000, 8250),
        ('2026-02-10', 'weighbridge', 'Weighbridge service - 15 customers', 15, 10, 150),
        ('2026-02-09', 'other', 'Equipment rental fee', 1, 5000, 5000)
    ]
    
    for date, source, desc, qty, rate, amount in sample_revenue:
        cursor.execute("""
            INSERT INTO accounting_revenue (date, source_type, description, quantity, rate, amount, created_by)
            VALUES (%s, %s, %s, %s, %s, %s, 'admin')
        """, (date, source, desc, qty, rate, amount))
    
    print("✅ Sample revenue added:")
    print(f"   - Milling Fee: LE 38,500")
    print(f"   - Bran Revenue: LE 8,250")
    print(f"   - Weighbridge: LE 150")
    print(f"   - Other Revenue: LE 5,000")
    print()
    
    # Commit all changes
    conn.commit()
    
    print("=" * 70)
    print("STEP 6: Verifying installation...")
    print("=" * 70)
    
    # Verify tables
    cursor.execute("SHOW TABLES LIKE 'accounting%'")
    tables = cursor.fetchall()
    print(f"✅ Found {len(tables)} accounting tables:")
    for table in tables:
        print(f"   - {table[0]}")
    print()
    
    # Get configuration
    cursor.execute("SELECT config_key, config_value, unit FROM accounting_config")
    configs = cursor.fetchall()
    print("✅ Configuration loaded:")
    for key, value, unit in configs:
        print(f"   - {key}: {value} {unit}")
    print()
    
    # Get sample data counts
    cursor.execute("SELECT COUNT(*) FROM accounting_revenue")
    revenue_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM accounting_expenses")
    expense_count = cursor.fetchone()[0]
    
    print(f"✅ Sample data loaded:")
    print(f"   - Revenue records: {revenue_count}")
    print(f"   - Expense records: {expense_count}")
    print()
    
    # Calculate totals
    cursor.execute("SELECT SUM(amount) FROM accounting_revenue")
    total_revenue = cursor.fetchone()[0] or 0
    
    cursor.execute("SELECT SUM(amount) FROM accounting_expenses")
    total_expenses = cursor.fetchone()[0] or 0
    
    profit = total_revenue - total_expenses
    
    print("=" * 70)
    print("  INSTALLATION COMPLETE!")
    print("=" * 70)
    print()
    print(f"✅ All accounting tables created successfully")
    print(f"✅ Default rates configured")
    print(f"✅ Sample data loaded for testing")
    print()
    print("📊 Sample Data Summary:")
    print(f"   Total Revenue:  LE {total_revenue:,.2f}")
    print(f"   Total Expenses: LE {total_expenses:,.2f}")
    print(f"   Net Profit:     LE {profit:,.2f}")
    print()
    print("=" * 70)
    print("  NEXT STEPS")
    print("=" * 70)
    print()
    print("1. Add accounting routes to your app.py")
    print("2. Copy accounting.html to templates folder")
    print("3. Add translations to app.py")
    print("4. Restart your Flask app")
    print("5. Visit: http://localhost:5000/accounting")
    print()
    print("🎉 You can now track your mill's finances!")
    print()
    
    cursor.close()
    conn.close()
    
except mysql.connector.Error as err:
    print(f"❌ Database Error: {err}")
    print()
    print("Common issues:")
    print("  - Wrong password")
    print("  - Database 'mill' doesn't exist")
    print("  - User doesn't have CREATE TABLE permissions")
    print()
    sys.exit(1)

except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)

input("Press Enter to exit...")
