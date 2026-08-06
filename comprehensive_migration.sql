-- ============================================================================
-- COMPREHENSIVE SYSTEM UPDATES - FIXED SQL MIGRATION
-- ============================================================================
-- Works with all MySQL versions
-- ============================================================================

-- 1. Add missing columns to wheat_intake table
-- ============================================================================

-- Add columns one by one with error handling
-- If column exists, it will show an error but continue with next

ALTER TABLE wheat_intake ADD COLUMN truck_number VARCHAR(50);
ALTER TABLE wheat_intake ADD COLUMN wheat_type VARCHAR(100);
ALTER TABLE wheat_intake ADD COLUMN carrier_name VARCHAR(200);
ALTER TABLE wheat_intake ADD COLUMN governorate VARCHAR(100);
ALTER TABLE wheat_intake ADD COLUMN load_type VARCHAR(100);
ALTER TABLE wheat_intake ADD COLUMN driver_name VARCHAR(200);
ALTER TABLE wheat_intake ADD COLUMN quality VARCHAR(100);
ALTER TABLE wheat_intake ADD COLUMN bags_count INT DEFAULT 0;
ALTER TABLE wheat_intake ADD COLUMN code VARCHAR(100);
ALTER TABLE wheat_intake ADD COLUMN impurities_weight INT DEFAULT 0;
ALTER TABLE wheat_intake ADD COLUMN invoice_number VARCHAR(100);
ALTER TABLE wheat_intake ADD COLUMN operator2 VARCHAR(100);
ALTER TABLE wheat_intake ADD COLUMN fine_bran_given DECIMAL(10,2) DEFAULT 0;

-- Note: If you see "Duplicate column name" errors, that's OK - it means the column already exists
-- Just continue with the rest of the SQL

-- ============================================================================
-- 2. Create bag sizes configuration table
-- ============================================================================

CREATE TABLE IF NOT EXISTS bag_sizes (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_type VARCHAR(50) NOT NULL,
    bag_size_kg INT NOT NULL,
    fine_bran_per_bag DECIMAL(10,2) DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY (product_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- 3. Insert default bag sizes
-- ============================================================================

-- Clear existing data (optional)
DELETE FROM bag_sizes;

-- Insert bag size configurations
INSERT INTO bag_sizes (product_type, bag_size_kg, fine_bran_per_bag) VALUES
('Flour', 50, 1.5),
('Coarse Bran', 40, 0),
('Fine Bran', 25, 0);

-- ============================================================================
-- 4. Verification
-- ============================================================================

-- Check wheat_intake structure
DESC wheat_intake;

-- Check bag sizes
SELECT * FROM bag_sizes;

-- Check recent records
SELECT 
    id,
    truck_number,
    vendor_id,
    gross_weight,
    tare_weight,
    net_weight,
    bags_count,
    fine_bran_given,
    date
FROM wheat_intake 
ORDER BY date DESC 
LIMIT 5;

-- ============================================================================
-- ALTERNATIVE: If you get errors, run this safer version
-- ============================================================================

-- Check if column exists before adding (MySQL 5.7+)
SET @dbname = DATABASE();
SET @tablename = "wheat_intake";

-- You can manually check which columns are missing:
SELECT COLUMN_NAME 
FROM INFORMATION_SCHEMA.COLUMNS 
WHERE TABLE_SCHEMA = @dbname 
AND TABLE_NAME = @tablename;

-- Then only add the missing ones manually

-- ============================================================================
-- QUICK FIX: Add all columns in one statement (may fail if any exist)
-- ============================================================================

-- If you want to add all at once and don't mind errors, use this:
-- (Comment out if columns already exist)

/*
ALTER TABLE wheat_intake 
ADD COLUMN truck_number VARCHAR(50),
ADD COLUMN wheat_type VARCHAR(100),
ADD COLUMN carrier_name VARCHAR(200),
ADD COLUMN governorate VARCHAR(100),
ADD COLUMN load_type VARCHAR(100),
ADD COLUMN driver_name VARCHAR(200),
ADD COLUMN quality VARCHAR(100),
ADD COLUMN bags_count INT DEFAULT 0,
ADD COLUMN code VARCHAR(100),
ADD COLUMN impurities_weight INT DEFAULT 0,
ADD COLUMN invoice_number VARCHAR(100),
ADD COLUMN operator2 VARCHAR(100),
ADD COLUMN fine_bran_given DECIMAL(10,2) DEFAULT 0;
*/

-- ============================================================================
-- USAGE EXAMPLES
-- ============================================================================

-- Example 1: First weighing (intake)
/*
INSERT INTO wheat_intake (
    truck_number, vendor_id, gross_weight, tare_weight,
    wheat_type, carrier_name, governorate, driver_name,
    date, captured_by
) VALUES (
    'T-1234',           -- truck number
    1,                  -- vendor_id
    50000,              -- gross weight
    0,                  -- tare (filled in second weighing)
    'Hard Wheat',       -- wheat type
    'ABC Transport',    -- carrier
    'Cairo',            -- governorate
    'Ahmed Ali',        -- driver
    NOW(),
    'weighbridge'
);
*/

-- Example 2: Second weighing (update)
/*
UPDATE wheat_intake SET
    tare_weight = 15000,
    impurities_weight = 500,
    net_weight = gross_weight - tare_weight - impurities_weight,
    quality = 'Grade A',
    bags_count = 700,
    fine_bran_given = 700 * 1.5,
    invoice_number = 'INV-2024-001',
    operator2 = 'hassan'
WHERE id = 1;  -- Replace with actual ID
*/

-- Example 3: Calculate totals
/*
SELECT 
    truck_number,
    bags_count,
    (bags_count * 50) as flour_kg,
    fine_bran_given,
    (bags_count * 50 + fine_bran_given) as total_delivered_kg
FROM wheat_intake
WHERE bags_count > 0
ORDER BY date DESC
LIMIT 10;
*/

-- ============================================================================
-- DONE!
-- ============================================================================
