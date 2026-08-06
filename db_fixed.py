"""
Database Module for Mill Management System
Matches your existing MySQL schema exactly
"""

import mysql.connector
from contextlib import contextmanager
import os

# MySQL Database configuration
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "milluser"),
    "password": os.environ.get("DB_PASSWORD", "millpass"),
    "database": os.environ.get("DB_NAME", "mill"),
    "charset": "utf8mb4",
    "use_unicode": True
}

@contextmanager
def get_db():
    """Context manager for database connections to ensure proper cleanup"""
    conn = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        yield conn
    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        if conn:
            conn.rollback()
        raise
    finally:
        if conn and conn.is_connected():
            conn.close()

def init_db():
    """
    Initialize database with YOUR exact schema
    Note: Run the SQL file first, this just adds missing tables
    """
    try:
        with get_db() as conn:
            cur = conn.cursor()

            # Add conditioning table (missing from your schema)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS conditioning (
                id INT AUTO_INCREMENT PRIMARY KEY,
                intake_id INT,
                initial_moisture DECIMAL(5,2),
                target_moisture DECIMAL(5,2),
                added_water_liters DECIMAL(10,2),
                tempering_hours DECIMAL(5,2),
                captured_by VARCHAR(50),
                captured_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (intake_id) REFERENCES intake(id) ON DELETE SET NULL
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            # Add packing_sessions table (missing from your schema)
            cur.execute("""
            CREATE TABLE IF NOT EXISTS packing_sessions (
                id INT AUTO_INCREMENT PRIMARY KEY,
                line VARCHAR(20),
                product VARCHAR(50),
                bags INT,
                bag_weight DECIMAL(5,2),
                total_weight DECIMAL(10,2),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
            """)

            conn.commit()
            print("✅ Additional tables created successfully!")
            
    except mysql.connector.Error as err:
        print(f"❌ Database initialization error: {err}")
        raise

def check_admin_password():
    """Check if admin password needs hashing"""
    try:
        with get_db() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT password_hash FROM users WHERE username='admin'")
            row = cur.fetchone()
            
            if row and row['password_hash'] == 'admin123':
                print("⚠️  WARNING: Admin password is still plain text!")
                print("   Your SQL schema has 'admin123' in plain text")
                print("   The app expects hashed passwords")
                print()
                
                response = input("   Hash the admin password now? (yes/no): ")
                if response.lower() == 'yes':
                    from werkzeug.security import generate_password_hash
                    hashed = generate_password_hash('admin123')
                    cur = conn.cursor()
                    cur.execute("UPDATE users SET password_hash = %s WHERE username = 'admin'", (hashed,))
                    conn.commit()
                    print("   ✅ Admin password hashed!")
                    print("   Login: username='admin' password='admin123'")
                else:
                    print("   ⚠️  Password NOT hashed. Login may fail!")
                    
    except mysql.connector.Error as err:
        print(f"❌ Error checking password: {err}")

def add_demo_data():
    """Add some demo vendors"""
    try:
        with get_db() as conn:
            cur = conn.cursor()
            
            # Check if vendors exist
            cur.execute("SELECT COUNT(*) as count FROM vendors")
            if cur.fetchone()[0] > 0:
                print("Vendors already exist. Skipping...")
                return
            
            # Add demo vendors
            vendors = [
                ("Al-Nour Trading", "+20123456789", "Reliable supplier"),
                ("Delta Wheat Co.", "+20198765432", "Large capacity"),
                ("Upper Egypt Grains", "+20111222333", "Good quality")
            ]
            
            for name, phone, notes in vendors:
                cur.execute("""
                    INSERT INTO vendors (name, phone, notes)
                    VALUES (%s, %s, %s)
                """, (name, phone, notes))
            
            conn.commit()
            print("✅ Demo vendors added!")
            
    except mysql.connector.Error as err:
        print(f"❌ Error adding demo data: {err}")

if __name__ == "__main__":
    print("=" * 60)
    print("Mill Management System - Database Setup")
    print("=" * 60)
    print()
    print("IMPORTANT: Run your SQL schema first!")
    print("This script only adds missing tables to your existing schema")
    print()
    
    try:
        print("Checking database...")
        init_db()
        
        print()
        check_admin_password()
        
        print()
        response = input("\nAdd demo vendors? (yes/no): ")
        if response.lower() == 'yes':
            add_demo_data()
        
        print("\n" + "=" * 60)
        print("✅ Database setup complete!")
        print("=" * 60)
        print("\n📝 Your login credentials:")
        print("   Username: admin")
        print("   Password: admin123")
        print()
        
    except Exception as e:
        print(f"\n❌ Setup failed: {e}")
        print("Make sure you've run the SQL schema file first!")
