@echo off
REM Quick Start Script for Mill Management System (Windows)
chcp 65001 >nul

echo ==========================================
echo   Al Mohandes Modern Mills
echo   مطاحن المهندس الحديثة
echo   Quick Setup Script (Windows)
echo ==========================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python is not installed. Please install Python 3.7+
    pause
    exit /b 1
)

echo ✅ Python found
python --version
echo.

REM Install dependencies
echo 📦 Installing Python packages...
pip install flask mysql-connector-python werkzeug pyserial

if errorlevel 1 (
    echo ❌ Failed to install packages
    pause
    exit /b 1
)

echo ✅ Packages installed successfully
echo.

echo 🗄️  Database Setup
echo -------------------
echo This script will now set up the MySQL database.
echo.
echo Have you created the MySQL database 'mill'? (yes/no)
set /p db_exists=

if not "%db_exists%"=="yes" (
    echo.
    echo Please create the database first:
    echo.
    echo   mysql -u root -p
    echo   CREATE DATABASE mill CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    echo   CREATE USER 'milluser'@'localhost' IDENTIFIED BY 'millpass';
    echo   GRANT ALL PRIVILEGES ON mill.* TO 'milluser'@'localhost';
    echo   FLUSH PRIVILEGES;
    echo   EXIT;
    echo.
    pause
)

echo.
echo 🔧 Initializing database tables...
echo yes| python db_fixed.py

echo.
echo ==========================================
echo   ✅ SETUP COMPLETE!
echo ==========================================
echo.
echo 📝 Login Credentials:
echo    Admin:    username='admin'    password='admin123'
echo    Operator: username='operator' password='op123'
echo.
echo 🚀 To start the server, run:
echo    python app.py
echo.
echo 🌐 Then visit: http://localhost:5000
echo.
echo ⚠️  IMPORTANT: Change default passwords in production!
echo.
pause
