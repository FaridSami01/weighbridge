-- ============================================================================
-- WEIGHBRIDGE OPERATOR ROLE - SQL MIGRATION
-- ============================================================================
-- Creates a restricted user role for weighbridge operators
-- ============================================================================

-- Add new user with WEIGHBRIDGE_OPERATOR role
INSERT INTO users (username, password_hash, role)
VALUES ('weighbridge', 'pbkdf2:sha256:600000$sampleSalt$sampleHash', 'WEIGHBRIDGE_OPERATOR')
ON DUPLICATE KEY UPDATE role='WEIGHBRIDGE_OPERATOR';

-- ============================================================================
-- IMPORTANT: UPDATE THE PASSWORD!
-- ============================================================================
-- The password above is a placeholder. You MUST update it with a real hash.
-- 
-- To generate a proper password hash:
--
-- Method 1: Using Python (recommended):
-- ```python
-- from werkzeug.security import generate_password_hash
-- print(generate_password_hash('your_password_here'))
-- ```
--
-- Method 2: Or just use a simple password for now:
-- UPDATE users SET password_hash = 'weighbridge123' WHERE username = 'weighbridge';
-- (This uses plain text - not secure but works for testing)
--
-- ============================================================================

-- Verify the user was created
SELECT username, role FROM users WHERE username = 'weighbridge';

-- ============================================================================
-- WEIGHBRIDGE_OPERATOR ROLE PERMISSIONS
-- ============================================================================
--
-- ALLOWED:
-- - /weighbridge_dashboard (custom dashboard)
-- - /intake (record new intake)
-- - /weighing/second (second weighing)
-- - /intake/history (view history)
-- - /print-weighbridge (print tickets)
-- - /api/weighbridge (live weight)
-- - /api/intake/* (intake APIs)
--
-- BLOCKED:
-- - /dashboard (main dashboard)
-- - /packing (packing system)
-- - /conditioning (conditioning)
-- - /vendors (vendor management)
-- - /reports (reports)
-- - /admin (admin panel)
-- - /accounting (accounting)
-- - /maintenance (maintenance)
-- - /stock (stock management)
-- - All packing APIs
--
-- ============================================================================
-- USAGE
-- ============================================================================
--
-- Login as weighbridge operator:
-- Username: weighbridge
-- Password: (whatever you set above)
--
-- After login, user will be redirected to /weighbridge_dashboard
-- They will only see:
-- - Live weighbridge weight
-- - New intake button
-- - Second weighing button
-- - Intake history button
-- - Print ticket button
-- - Today's statistics
--
-- If they try to access other pages, they'll be redirected back with:
-- "Access denied. Not available for weighbridge operators."
--
-- ============================================================================
-- EXAMPLE: Create Multiple Weighbridge Operators
-- ============================================================================

-- Operator for morning shift
INSERT INTO users (username, password_hash, role)
VALUES ('wb_morning', 'morning123', 'WEIGHBRIDGE_OPERATOR')
ON DUPLICATE KEY UPDATE role='WEIGHBRIDGE_OPERATOR';

-- Operator for evening shift
INSERT INTO users (username, password_hash, role)
VALUES ('wb_evening', 'evening123', 'WEIGHBRIDGE_OPERATOR')
ON DUPLICATE KEY UPDATE role='WEIGHBRIDGE_OPERATOR';

-- Operator for night shift
INSERT INTO users (username, password_hash, role)
VALUES ('wb_night', 'night123', 'WEIGHBRIDGE_OPERATOR')
ON DUPLICATE KEY UPDATE role='WEIGHBRIDGE_OPERATOR';

-- ============================================================================
-- TESTING
-- ============================================================================

-- 1. Login as weighbridge operator
-- 2. You should see the weighbridge dashboard
-- 3. Try clicking on different sections:
--    - Wheat Intake → Should work ✅
--    - Second Weighing → Should work ✅
--    - Intake History → Should work ✅
--    - Print Ticket → Should work ✅
-- 4. Try to access /packing directly → Should be blocked ❌
-- 5. Try to access /dashboard directly → Should be blocked ❌
--
-- ============================================================================
-- END OF MIGRATION
-- ============================================================================
