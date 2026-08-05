-- MAINTENANCE MANAGEMENT SYSTEM - DATABASE SCHEMA

-- Table 1: Equipment Registry
CREATE TABLE IF NOT EXISTS equipment (
    id INT AUTO_INCREMENT PRIMARY KEY,
    equipment_code VARCHAR(50) UNIQUE NOT NULL,
    equipment_name VARCHAR(100) NOT NULL,
    equipment_type ENUM('milling_line', 'packing_line', 'weighbridge', 'motor', 'conveyor', 'sifter', 'other') NOT NULL,
    location VARCHAR(100),
    manufacturer VARCHAR(100),
    model_number VARCHAR(100),
    serial_number VARCHAR(100),
    installation_date DATE,
    warranty_expiry DATE,
    status ENUM('active', 'maintenance', 'broken', 'retired') DEFAULT 'active',
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Table 2: Maintenance Schedule (Preventive)
CREATE TABLE IF NOT EXISTS maintenance_schedule (
    id INT AUTO_INCREMENT PRIMARY KEY,
    equipment_id INT NOT NULL,
    task_name VARCHAR(200) NOT NULL,
    task_description TEXT,
    frequency_type ENUM('hours', 'days', 'weeks', 'months') NOT NULL,
    frequency_value INT NOT NULL,
    last_performed_date DATE,
    last_performed_hours INT,
    next_due_date DATE,
    next_due_hours INT,
    priority ENUM('low', 'medium', 'high', 'critical') DEFAULT 'medium',
    estimated_duration_minutes INT,
    required_parts TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    FOREIGN KEY (equipment_id) REFERENCES equipment(id) ON DELETE CASCADE,
    INDEX idx_next_due (next_due_date),
    INDEX idx_equipment (equipment_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Table 3: Maintenance Logs (Completed Work)
CREATE TABLE IF NOT EXISTS maintenance_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    equipment_id INT NOT NULL,
    schedule_id INT,
    log_type ENUM('preventive', 'breakdown', 'inspection', 'calibration') NOT NULL,
    performed_date DATE NOT NULL,
    performed_time TIME,
    performed_by VARCHAR(100) NOT NULL,
    task_description TEXT NOT NULL,
    parts_used TEXT,
    parts_cost DECIMAL(10,2) DEFAULT 0.00,
    labor_hours DECIMAL(5,2),
    labor_cost DECIMAL(10,2) DEFAULT 0.00,
    total_cost DECIMAL(10,2) GENERATED ALWAYS AS (parts_cost + labor_cost) STORED,
    downtime_minutes INT DEFAULT 0,
    status ENUM('completed', 'partial', 'failed') DEFAULT 'completed',
    notes TEXT,
    next_action TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_by VARCHAR(100),
    FOREIGN KEY (equipment_id) REFERENCES equipment(id) ON DELETE CASCADE,
    FOREIGN KEY (schedule_id) REFERENCES maintenance_schedule(id) ON DELETE SET NULL,
    INDEX idx_date (performed_date),
    INDEX idx_equipment (equipment_id),
    INDEX idx_type (log_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Table 4: Spare Parts Inventory
CREATE TABLE IF NOT EXISTS spare_parts (
    id INT AUTO_INCREMENT PRIMARY KEY,
    part_code VARCHAR(50) UNIQUE NOT NULL,
    part_name VARCHAR(200) NOT NULL,
    part_category ENUM('motor', 'belt', 'bearing', 'filter', 'seal', 'electrical', 'other') NOT NULL,
    compatible_equipment TEXT,
    quantity_in_stock INT DEFAULT 0,
    minimum_stock_level INT DEFAULT 0,
    unit_cost DECIMAL(10,2),
    supplier_name VARCHAR(100),
    supplier_contact VARCHAR(100),
    location VARCHAR(100),
    notes TEXT,
    last_ordered_date DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_stock (quantity_in_stock, minimum_stock_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Table 5: Equipment Meter Readings (for hour-based maintenance)
CREATE TABLE IF NOT EXISTS equipment_meters (
    id INT AUTO_INCREMENT PRIMARY KEY,
    equipment_id INT NOT NULL,
    reading_date DATE NOT NULL,
    reading_time TIME,
    hours_reading INT NOT NULL,
    recorded_by VARCHAR(100),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (equipment_id) REFERENCES equipment(id) ON DELETE CASCADE,
    INDEX idx_equipment_date (equipment_id, reading_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Insert Sample Equipment
INSERT INTO equipment (equipment_code, equipment_name, equipment_type, location, status) VALUES
('ML-001', 'Milling Line 1', 'milling_line', 'Production Floor East', 'active'),
('ML-002', 'Milling Line 2', 'milling_line', 'Production Floor Center', 'active'),
('ML-003', 'Milling Line 3', 'milling_line', 'Production Floor West', 'active'),
('PL-001', 'Packing Line 1', 'packing_line', 'Packing Area', 'active'),
('PL-002', 'Packing Line 2', 'packing_line', 'Packing Area', 'active'),
('PL-003', 'Packing Line 3', 'packing_line', 'Packing Area', 'active'),
('WB-001', 'Weighbridge Main', 'weighbridge', 'Entrance', 'active'),
('MT-001', 'Main Motor Line 1', 'motor', 'Production Floor East', 'active'),
('MT-002', 'Main Motor Line 2', 'motor', 'Production Floor Center', 'active'),
('CV-001', 'Wheat Conveyor Belt', 'conveyor', 'Intake Area', 'active');

-- Insert Sample Maintenance Schedule
INSERT INTO maintenance_schedule 
(equipment_id, task_name, task_description, frequency_type, frequency_value, next_due_date, priority) VALUES
(1, 'Belt Inspection & Tension Check', 'Inspect all belts for wear, check tension, replace if needed', 'hours', 500, DATE_ADD(CURDATE(), INTERVAL 3 DAY), 'high'),
(1, 'Oil Change & Lubrication', 'Change motor oil, lubricate all bearings', 'hours', 1000, DATE_ADD(CURDATE(), INTERVAL 7 DAY), 'medium'),
(1, 'Complete Line Inspection', 'Full inspection of all components, clean filters', 'months', 1, DATE_ADD(CURDATE(), INTERVAL 25 DAY), 'high'),
(2, 'Belt Inspection & Tension Check', 'Inspect all belts for wear, check tension, replace if needed', 'hours', 500, DATE_ADD(CURDATE(), INTERVAL 5 DAY), 'high'),
(2, 'Oil Change & Lubrication', 'Change motor oil, lubricate all bearings', 'hours', 1000, DATE_ADD(CURDATE(), INTERVAL 10 DAY), 'medium'),
(3, 'Belt Replacement', 'Replace conveyor belt (scheduled)', 'hours', 2000, DATE_ADD(CURDATE(), INTERVAL 15 DAY), 'medium'),
(7, 'Weighbridge Calibration', 'Professional calibration service', 'months', 6, DATE_ADD(CURDATE(), INTERVAL 90 DAY), 'critical'),
(8, 'Motor Bearing Inspection', 'Check motor bearings for noise/vibration', 'weeks', 2, DATE_ADD(CURDATE(), INTERVAL 10 DAY), 'high'),
(10, 'Conveyor Belt Cleaning', 'Clean wheat residue, check alignment', 'weeks', 1, DATE_ADD(CURDATE(), INTERVAL 2 DAY), 'medium');

-- Insert Sample Spare Parts
INSERT INTO spare_parts 
(part_code, part_name, part_category, quantity_in_stock, minimum_stock_level, unit_cost, supplier_name) VALUES
('BLT-V001', 'V-Belt Type A (Standard)', 'belt', 8, 5, 150.00, 'Industrial Supplies Co.'),
('BLT-V002', 'V-Belt Type B (Heavy Duty)', 'belt', 3, 3, 250.00, 'Industrial Supplies Co.'),
('BRG-001', 'Ball Bearing 6205', 'bearing', 12, 8, 45.00, 'Bearing Warehouse'),
('BRG-002', 'Ball Bearing 6305', 'bearing', 6, 5, 85.00, 'Bearing Warehouse'),
('FLT-001', 'Air Filter 200mm', 'filter', 15, 10, 35.00, 'Filter Express'),
('FLT-002', 'Oil Filter Premium', 'filter', 20, 15, 25.00, 'Filter Express'),
('MTR-OIL', 'Motor Oil SAE 40 (5L)', 'other', 30, 20, 120.00, 'Lubricants Direct'),
('SEL-001', 'Rubber Seal 50mm', 'seal', 25, 15, 18.00, 'Seals & Gaskets Ltd'),
('ELC-001', 'Motor Starter Relay', 'electrical', 4, 3, 350.00, 'Electric Components'),
('ELC-002', 'Emergency Stop Button', 'electrical', 6, 4, 85.00, 'Electric Components');

-- Insert Sample Maintenance Logs
INSERT INTO maintenance_logs 
(equipment_id, schedule_id, log_type, performed_date, performed_by, task_description, parts_used, parts_cost, labor_hours, labor_cost, downtime_minutes, status) VALUES
(1, 1, 'preventive', DATE_SUB(CURDATE(), INTERVAL 10 DAY), 'Ahmed Hassan', 'Inspected and adjusted belt tension on all drives', 'None', 0.00, 1.5, 150.00, 30, 'completed'),
(2, NULL, 'breakdown', DATE_SUB(CURDATE(), INTERVAL 5 DAY), 'Mohamed Ali', 'Replaced broken V-belt on main motor', 'V-Belt Type A x1', 150.00, 2.0, 200.00, 120, 'completed'),
(1, 2, 'preventive', DATE_SUB(CURDATE(), INTERVAL 3 DAY), 'Ahmed Hassan', 'Changed motor oil and lubricated all bearings', 'Motor Oil x2, Grease', 240.00, 3.0, 300.00, 60, 'completed'),
(7, NULL, 'calibration', DATE_SUB(CURDATE(), INTERVAL 15 DAY), 'Calibration Services Co.', 'Professional weighbridge calibration and certification', 'None', 0.00, 0, 800.00, 0, 'completed'),
(10, NULL, 'preventive', DATE_SUB(CURDATE(), INTERVAL 2 DAY), 'Khaled Mahmoud', 'Cleaned conveyor belt and adjusted tracking', 'None', 0.00, 1.0, 100.00, 15, 'completed');

-- Views for reporting
CREATE OR REPLACE VIEW v_maintenance_due_soon AS
SELECT 
    e.equipment_code,
    e.equipment_name,
    e.equipment_type,
    ms.task_name,
    ms.priority,
    ms.next_due_date,
    DATEDIFF(ms.next_due_date, CURDATE()) as days_until_due,
    ms.estimated_duration_minutes,
    CASE 
        WHEN DATEDIFF(ms.next_due_date, CURDATE()) < 0 THEN 'Overdue'
        WHEN DATEDIFF(ms.next_due_date, CURDATE()) <= 3 THEN 'Due Soon'
        ELSE 'Scheduled'
    END as status
FROM maintenance_schedule ms
JOIN equipment e ON ms.equipment_id = e.id
WHERE ms.is_active = TRUE
  AND e.status = 'active'
  AND ms.next_due_date <= DATE_ADD(CURDATE(), INTERVAL 30 DAY)
ORDER BY ms.next_due_date ASC;

CREATE OR REPLACE VIEW v_equipment_maintenance_cost AS
SELECT 
    e.equipment_code,
    e.equipment_name,
    COUNT(ml.id) as maintenance_count,
    SUM(ml.total_cost) as total_maintenance_cost,
    SUM(ml.downtime_minutes) as total_downtime_minutes,
    AVG(ml.total_cost) as avg_cost_per_maintenance
FROM equipment e
LEFT JOIN maintenance_logs ml ON e.id = ml.equipment_id
    AND ml.performed_date >= DATE_SUB(CURDATE(), INTERVAL 12 MONTH)
GROUP BY e.id, e.equipment_code, e.equipment_name
ORDER BY total_maintenance_cost DESC;

CREATE OR REPLACE VIEW v_low_stock_parts AS
SELECT 
    part_code,
    part_name,
    part_category,
    quantity_in_stock,
    minimum_stock_level,
    (minimum_stock_level - quantity_in_stock) as qty_to_order,
    unit_cost,
    supplier_name,
    supplier_contact
FROM spare_parts
WHERE quantity_in_stock <= minimum_stock_level
ORDER BY (minimum_stock_level - quantity_in_stock) DESC;

-- Triggers to update schedule after maintenance
DELIMITER $$

CREATE TRIGGER after_maintenance_update_schedule
AFTER INSERT ON maintenance_logs
FOR EACH ROW
BEGIN
    IF NEW.schedule_id IS NOT NULL THEN
        UPDATE maintenance_schedule
        SET 
            last_performed_date = NEW.performed_date,
            next_due_date = CASE
                WHEN frequency_type = 'days' THEN DATE_ADD(NEW.performed_date, INTERVAL frequency_value DAY)
                WHEN frequency_type = 'weeks' THEN DATE_ADD(NEW.performed_date, INTERVAL frequency_value WEEK)
                WHEN frequency_type = 'months' THEN DATE_ADD(NEW.performed_date, INTERVAL frequency_value MONTH)
                ELSE next_due_date
            END
        WHERE id = NEW.schedule_id;
    END IF;
END$$

DELIMITER ;
