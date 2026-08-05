"""
PACKING SCALE MANAGER WITH DATABASE STORAGE
Modified to save every bag to MySQL database
"""

import mysql.connector
from datetime import datetime, date

class PackingDatabaseManager:
    """
    Handles saving packing data to database
    """
    
    def __init__(self, db_config):
        """
        Initialize with database configuration
        
        Args:
            db_config: dict with host, user, password, database
        """
        self.db_config = db_config
    
    def save_bag(self, machine_id, machine_name, bag_number, weight_kg, operator=None):
        """
        Save a packed bag to database
        
        Args:
            machine_id: e.g., 'bran_40kg'
            machine_name: e.g., 'BX3 - Bran 40kg'
            bag_number: Sequential number for the day
            weight_kg: Weight in kilograms
            operator: Username of operator (optional)
        
        Returns:
            bool: True if saved successfully
        """
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO packing_data 
                (machine_id, machine_name, bag_number, weight_kg, packed_date, operator)
                VALUES (%s, %s, %s, %s, CURDATE(), %s)
            """, (machine_id, machine_name, bag_number, weight_kg, operator))
            
            conn.commit()
            cursor.close()
            conn.close()
            
            print(f"✅ Saved to DB: {machine_name} Bag #{bag_number} - {weight_kg} kg")
            return True
            
        except Exception as e:
            print(f"❌ Database save error: {e}")
            return False
    
    def get_today_stats(self, machine_id):
        """
        Get today's statistics for a machine
        
        Returns:
            dict: {bag_count, total_weight, avg_weight, bags: [list of bags]}
        """
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor(dictionary=True)
            
            # Get today's bags
            cursor.execute("""
                SELECT bag_number, weight_kg, packed_at
                FROM packing_data
                WHERE machine_id = %s 
                  AND packed_date = CURDATE()
                ORDER BY bag_number
            """, (machine_id,))
            
            bags = cursor.fetchall()
            
            # Calculate stats and format time in Python
            formatted_bags = []
            if bags:
                bag_count = len(bags)
                total_weight = sum(float(b['weight_kg']) for b in bags)
                avg_weight = total_weight / bag_count
                
                # Format each bag's time in Python
                for bag in bags:
                    time_str = ''
                    if bag.get('packed_at'):
                        try:
                            time_str = bag['packed_at'].strftime('%H:%M:%S')
                        except:
                            time_str = str(bag['packed_at'])
                    
                    formatted_bags.append({
                        'bag_number': bag['bag_number'],
                        'weight_kg': float(bag['weight_kg']),
                        'time': time_str
                    })
            else:
                bag_count = 0
                total_weight = 0
                avg_weight = 0
            
            cursor.close()
            conn.close()
            
            return {
                'bag_count': bag_count,
                'total_weight': total_weight,
                'avg_weight': avg_weight,
                'bags': formatted_bags
            }
            
        except Exception as e:
            print(f"❌ Database read error: {e}")
            return {'bag_count': 0, 'total_weight': 0, 'avg_weight': 0, 'bags': []}
    
    def get_date_range_stats(self, start_date, end_date, machine_id=None):
        """
        Get statistics for a date range
        
        Args:
            start_date: 'YYYY-MM-DD'
            end_date: 'YYYY-MM-DD'
            machine_id: Optional filter by machine
        
        Returns:
            list of daily statistics
        """
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor(dictionary=True)
            
            if machine_id:
                cursor.execute("""
                    SELECT 
                        packed_date,
                        machine_name,
                        COUNT(*) as bag_count,
                        SUM(weight_kg) as total_weight,
                        AVG(weight_kg) as avg_weight,
                        MIN(weight_kg) as min_weight,
                        MAX(weight_kg) as max_weight
                    FROM packing_data
                    WHERE machine_id = %s
                      AND packed_date BETWEEN %s AND %s
                    GROUP BY packed_date, machine_id, machine_name
                    ORDER BY packed_date DESC
                """, (machine_id, start_date, end_date))
            else:
                cursor.execute("""
                    SELECT 
                        packed_date,
                        machine_id,
                        machine_name,
                        COUNT(*) as bag_count,
                        SUM(weight_kg) as total_weight,
                        AVG(weight_kg) as avg_weight
                    FROM packing_data
                    WHERE packed_date BETWEEN %s AND %s
                    GROUP BY packed_date, machine_id, machine_name
                    ORDER BY packed_date DESC, machine_id
                """, (start_date, end_date))
            
            results = cursor.fetchall()
            cursor.close()
            conn.close()
            
            return results
            
        except Exception as e:
            print(f"❌ Database query error: {e}")
            return []


# ============================================================================
# MODIFICATION TO BaykonMachine CLASS
# ============================================================================

# Add this to your existing BaykonMachine class in packing_scale_multi.py

class BaykonMachine:
    """
    Modified to save to database
    """
    
    def __init__(self, name, port, baudrate=9600, db_manager=None):
        self.name = name
        self.port = port
        self.baudrate = baudrate
        self.db_manager = db_manager  # ← Add database manager
        
        # ... existing initialization code ...
    
    def _on_bag_complete(self, weight):
        """
        Called when a bag is complete (MODIFIED to save to DB)
        """
        self.bag_count += 1
        self.total_weight += weight
        
        # Calculate average
        self.avg_weight = self.total_weight / self.bag_count
        
        # Add to bags list
        self.bags_today.append({
            'number': self.bag_count,
            'weight': weight,
            'time': datetime.now().strftime('%H:%M:%S')
        })
        
        # ✅ SAVE TO DATABASE
        if self.db_manager:
            self.db_manager.save_bag(
                machine_id=self.machine_id,
                machine_name=self.name,
                bag_number=self.bag_count,
                weight_kg=weight,
                operator='SYSTEM'  # Or get from session
            )
        
        print(f"✅ {self.name}: Bag #{self.bag_count} | {weight:.2f} kg")
    
    def load_today_stats(self):
        """
        Load today's stats from database on startup
        """
        if self.db_manager:
            stats = self.db_manager.get_today_stats(self.machine_id)
            
            self.bag_count = stats['bag_count']
            self.total_weight = stats['total_weight']
            self.avg_weight = stats['avg_weight']
            self.bags_today = stats['bags']
            
            print(f"📊 {self.name}: Loaded {self.bag_count} bags from database")


# ============================================================================
# USAGE IN YOUR APP
# ============================================================================

"""
# In app.py, initialize the packing manager with database:

from packing_database import PackingDatabaseManager

# Database config
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': 'admin123',
    'database': 'mill'
}

# Create database manager
db_manager = PackingDatabaseManager(DB_CONFIG)

# Initialize machines with database support
machines = {
    'bran_40kg': BaykonMachine(
        name='BX3 - Bran 40kg',
        port='COM3',
        db_manager=db_manager  # ← Pass database manager
    ),
    'flour_50kg_bxf3': BaykonMachine(
        name='BXf3 - Flour 50kg',
        port='COM9',
        db_manager=db_manager
    ),
    'flour_50kg_bx30': BaykonMachine(
        name='BX30 - Flour 50kg',
        port='COM5',
        db_manager=db_manager
    )
}

# Load today's stats from database
for machine in machines.values():
    machine.load_today_stats()
"""
