-- ============================================================================
-- PACKING BAGS TABLE - AUTO-SAVE MIGRATION
-- ============================================================================
-- Run this SQL in your MySQL database to enable auto-save feature
-- ============================================================================

CREATE TABLE IF NOT EXISTS packing_bags (
    id INT AUTO_INCREMENT PRIMARY KEY,
    bag_date DATE NOT NULL,
    machine_name VARCHAR(100) NOT NULL,
    product_type VARCHAR(100) NOT NULL,
    bag_size INT NOT NULL,
    weight DECIMAL(10,2) NOT NULL,
    bag_number INT NOT NULL,
    created_at DATETIME NOT NULL,
    INDEX idx_date (bag_date),
    INDEX idx_machine (machine_name),
    INDEX idx_product (product_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- ============================================================================
-- DESCRIPTION
-- ============================================================================
-- This table stores every bag counted by the 3 Baykon machines
--
-- Fields:
-- - id: Unique identifier
-- - bag_date: Date bag was produced
-- - machine_name: Which machine (e.g., "BX3 - Bran 40kg")
-- - product_type: Product (e.g., "Coarse Bran", "Flour")
-- - bag_size: Bag size in kg (40, 50)
-- - weight: Actual weight of bag
-- - bag_number: Sequence number from machine
-- - created_at: Exact timestamp when bag completed
--
-- ============================================================================
-- USAGE
-- ============================================================================
--
-- Every time a bag is completed, it's automatically saved:
--
-- Example data:
-- id | bag_date   | machine_name      | product      | size | weight | bag# | created_at
-- ---+------------+-------------------+--------------+------+--------+------+--------------------
--  1 | 2026-02-25 | BX3 - Bran 40kg   | Coarse Bran  | 40   | 39.85  | 1    | 2026-02-25 08:15:23
--  2 | 2026-02-25 | BX3 - Flour 50kg  | Flour        | 50   | 50.12  | 1    | 2026-02-25 08:16:45
--  3 | 2026-02-25 | BX3 - Bran 40kg   | Coarse Bran  | 40   | 40.02  | 2    | 2026-02-25 08:17:10
--
-- ============================================================================
-- QUERIES
-- ============================================================================

-- Get today's production summary
SELECT 
    machine_name,
    product_type,
    COUNT(*) as total_bags,
    SUM(weight) as total_weight,
    AVG(weight) as average_weight
FROM packing_bags
WHERE bag_date = CURDATE()
GROUP BY machine_name, product_type;

-- Get hourly production
SELECT 
    DATE_FORMAT(created_at, '%H:00') as hour,
    machine_name,
    COUNT(*) as bags,
    SUM(weight) as weight
FROM packing_bags
WHERE bag_date = CURDATE()
GROUP BY DATE_FORMAT(created_at, '%H:00'), machine_name
ORDER BY hour, machine_name;

-- Get production by date range
SELECT 
    bag_date,
    machine_name,
    COUNT(*) as bags,
    SUM(weight) / 1000 as tons
FROM packing_bags
WHERE bag_date BETWEEN '2026-02-01' AND '2026-02-28'
GROUP BY bag_date, machine_name
ORDER BY bag_date, machine_name;

-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
