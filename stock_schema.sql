-- STOCK MANAGEMENT SYSTEM - DATABASE SCHEMA

-- Table 1: Stock Products
CREATE TABLE IF NOT EXISTS stock_products (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_code VARCHAR(50) UNIQUE NOT NULL,
    product_name VARCHAR(200) NOT NULL,
    category ENUM('flour', 'bran', 'bags', 'other') NOT NULL,
    unit VARCHAR(20) DEFAULT 'kg',
    quantity DECIMAL(10,2) DEFAULT 0.00,
    min_level DECIMAL(10,2) DEFAULT 0.00,
    max_level DECIMAL(10,2),
    unit_cost DECIMAL(10,2),
    location VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_category (category),
    INDEX idx_quantity (quantity, min_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Table 2: Stock Movements (History)
CREATE TABLE IF NOT EXISTS stock_movements (
    id INT AUTO_INCREMENT PRIMARY KEY,
    product_id INT NOT NULL,
    movement_type ENUM('in', 'out', 'adjustment') NOT NULL,
    quantity DECIMAL(10,2) NOT NULL,
    balance_before DECIMAL(10,2) NOT NULL,
    balance_after DECIMAL(10,2) NOT NULL,
    movement_date DATE NOT NULL,
    movement_time TIME,
    reference_type VARCHAR(50),
    reference_id INT,
    notes TEXT,
    created_by VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES stock_products(id) ON DELETE CASCADE,
    INDEX idx_date (movement_date),
    INDEX idx_product (product_id),
    INDEX idx_type (movement_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Insert Sample Products
INSERT INTO stock_products (product_code, product_name, category, unit, quantity, min_level, max_level, unit_cost) VALUES
('FLOUR-72', 'Flour 72% Extraction', 'flour', 'kg', 5000, 2000, 20000, 8.50),
('FLOUR-82', 'Flour 82% Extraction', 'flour', 'kg', 3000, 1500, 15000, 7.80),
('SEMOLINA', 'Semolina', 'flour', 'kg', 1000, 500, 5000, 12.00),
('BRAN-FINE', 'Fine Bran', 'bran', 'kg', 2000, 800, 10000, 3.50),
('BRAN-COARSE', 'Coarse Bran', 'bran', 'kg', 1500, 600, 8000, 4.20),
('BAG-25KG', 'Bags 25kg (Flour)', 'bags', 'pcs', 5000, 2000, 20000, 0.50),
('BAG-50KG', 'Bags 50kg (Flour)', 'bags', 'pcs', 3000, 1500, 15000, 0.80),
('BAG-BRAN', 'Bags 25kg (Bran)', 'bags', 'pcs', 2000, 1000, 10000, 0.45);

-- Insert Sample Movements
INSERT INTO stock_movements (product_id, movement_type, quantity, balance_before, balance_after, movement_date, notes, created_by) VALUES
(1, 'in', 1000, 4000, 5000, DATE_SUB(CURDATE(), INTERVAL 5 DAY), 'Production from Line 1', 'admin'),
(1, 'out', 500, 5000, 4500, DATE_SUB(CURDATE(), INTERVAL 3 DAY), 'Customer pickup', 'admin'),
(1, 'in', 500, 4500, 5000, DATE_SUB(CURDATE(), INTERVAL 1 DAY), 'Production from Line 2', 'admin'),
(5, 'in', 300, 1200, 1500, DATE_SUB(CURDATE(), INTERVAL 2 DAY), 'Production from Line 3', 'admin'),
(6, 'out', 200, 5200, 5000, DATE_SUB(CURDATE(), INTERVAL 1 DAY), 'Used for packing', 'admin');

-- Views for reporting
CREATE OR REPLACE VIEW v_stock_summary AS
SELECT 
    category,
    COUNT(*) as product_count,
    SUM(quantity) as total_quantity,
    SUM(quantity * unit_cost) as total_value
FROM stock_products
GROUP BY category;

CREATE OR REPLACE VIEW v_low_stock_alerts AS
SELECT 
    id,
    product_code,
    product_name,
    category,
    quantity,
    unit,
    min_level,
    (min_level - quantity) as deficit,
    CASE 
        WHEN quantity <= 0 THEN 'OUT_OF_STOCK'
        WHEN quantity < (min_level * 0.5) THEN 'CRITICAL'
        WHEN quantity < min_level THEN 'LOW'
        ELSE 'OK'
    END as alert_level
FROM stock_products
WHERE quantity < min_level
ORDER BY (min_level - quantity) DESC;

CREATE OR REPLACE VIEW v_stock_value AS
SELECT 
    sp.id,
    sp.product_code,
    sp.product_name,
    sp.category,
    sp.quantity,
    sp.unit,
    sp.unit_cost,
    (sp.quantity * sp.unit_cost) as stock_value
FROM stock_products sp
WHERE sp.quantity > 0
ORDER BY stock_value DESC;

-- Trigger to update stock quantity after movement
DELIMITER $$

CREATE TRIGGER after_stock_movement_insert
AFTER INSERT ON stock_movements
FOR EACH ROW
BEGIN
    DECLARE new_quantity DECIMAL(10,2);
    
    IF NEW.movement_type = 'in' THEN
        SET new_quantity = NEW.balance_before + NEW.quantity;
    ELSEIF NEW.movement_type = 'out' THEN
        SET new_quantity = NEW.balance_before - NEW.quantity;
    ELSE
        SET new_quantity = NEW.balance_after;
    END IF;
    
    UPDATE stock_products
    SET quantity = new_quantity
    WHERE id = NEW.product_id;
END$$

DELIMITER ;
