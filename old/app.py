from flask import Flask, request, jsonify, render_template, redirect, url_for, session, make_response, flash
from io import BytesIO
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT



import mysql.connector
from functools import wraps

from werkzeug.security import generate_password_hash, check_password_hash
import os
from contextlib import contextmanager

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "CHANGE_THIS_IN_PRODUCTION_" + os.urandom(24).hex())

# DATABASE CONFIG - Matches YOUR schema
DB_CONFIG = {
    "host": os.environ.get("DB_HOST", "localhost"),
    "user": os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", "root"),
    "database": os.environ.get("DB_NAME", "mill"),
    "charset": "utf8mb4",
    "use_unicode": True
}
@contextmanager
def get_db():
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

# WEIGHBRIDGE INTEGRATION
# WEIGHBRIDGE INTEGRATION
try:
    from weighbridge import WeighbridgeReader
    import time
    
    port = os.environ.get("WEIGHBRIDGE_PORT", "COM4" if os.name == 'nt' else "/dev/ttyUSB0")
    baudrate = int(os.environ.get("WEIGHBRIDGE_BAUD", "9600"))
    
    weighbridge = WeighbridgeReader(port=port, baudrate=baudrate)
    
    # CRITICAL: Wait until we actually receive data
    print(f"✅ Weighbridge initialized on {port} @ {baudrate} baud")
    print(f"   Waiting for data from scale...")
    
    # Wait up to 10 seconds for first data
    waited = 0
    while waited < 10:
        if weighbridge.is_online():
            print(f"   ✅ Weighbridge ONLINE after {waited} seconds")
            break
        time.sleep(0.5)
        waited += 0.5
    
    if not weighbridge.is_online():
        print(f"   ⚠️  WARNING: No data received after 10 seconds")
        print(f"   Scale may not be sending data continuously")
        print(f"   App will start anyway - scale might come online later")
    
    WEIGHBRIDGE_AVAILABLE = True
    
except Exception as e:
    weighbridge = None
    WEIGHBRIDGE_AVAILABLE = False
    print(f"⚠️  Weighbridge not available: {e}")

# ============================================================================
# TRIPLE BAYKON MACHINE SYSTEM
# ============================================================================
# Manages 3 machines simultaneously:
# - COM3: BX3 40kg Coarse Bran
# - COM9: BXf3 50kg Flour
# - COM5: BX30 50kg Flour
# ============================================================================

from packing_scale_multi import MultiMachineManager
from packing_database import PackingDatabaseManager

# Auto-save function for bags
def save_bag_to_database(bag_info):
    """Auto-save each bag to database"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO packing_bags
                (bag_date, machine_name, product_type, bag_size, weight, bag_number, created_at)
                VALUES (CURDATE(), %s, %s, %s, %s, %s, %s)
            """, (
                bag_info['machine_name'],
                bag_info['product'],
                bag_info['bag_size'],
                bag_info['weight'],
                bag_info['bag_number'],
                bag_info['timestamp']
            ))
            conn.commit()
    except Exception as e:
        print(f"Database save error: {e}")
        # Don't raise - we don't want to break the counting if DB fails

# Create packing database manager
packing_db_manager = PackingDatabaseManager(DB_CONFIG)

# Initialize multi-machine manager with auto-save
packing_manager = MultiMachineManager(on_bag_complete=save_bag_to_database)

# Manually add database manager to each machine
for machine_id, machine in packing_manager.machines.items():
    if machine:
        machine.machine_id = machine_id
        machine.db_manager = packing_db_manager
        # Load today's stats
        machine.load_today_stats()

PACKING_SCALE_AVAILABLE = True

# For backwards compatibility
bx3_scale = packing_manager  # Some routes might reference this

# AUTH DECORATORS
def login_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            flash("Please log in to access this page", "warning")
            return redirect("/login")
        return f(*args, **kwargs)
    return wrapper

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return redirect("/login")
        if session.get("role") != "ADMIN":
            flash("Access denied. Admin privileges required.", "danger")
            return redirect("/dashboard")
        return f(*args, **kwargs)
    return wrapper

def weighbridge_operator_access(f):
    """Allow access only to weighbridge operators and admins"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return redirect("/login")
        role = session.get("role")
        if role not in ["ADMIN", "OPERATOR"]:
            flash("Access denied. Weighbridge access only.", "danger")
            return redirect("/weighbridge_dashboard")
        return f(*args, **kwargs)
    return wrapper

def block_weighbridge_operator(f):
    """Block weighbridge operators from accessing this page"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("user"):
            return redirect("/login")
        if session.get("role") == "OPERATOR":
            flash("Access denied. Not available for weighbridge operators.", "danger")
            return redirect("/weighbridge_dashboard")
        return f(*args, **kwargs)
    return wrapper

# COMPLETE TRANSLATIONS
TRANSLATIONS = {
    "en": {
        "mill_name": "Al Mohandes Modern Mills", "mill_name_ar": "مطاحن المهندس الحديثة",
        "dashboard": "Dashboard", "wheat_intake": "Wheat Intake", "intake_history": "Intake History",
        "conditioning": "Conditioning", "conditioning_history": "Conditioning History", "vendors": "Vendors",
        "packing": "Packing", "stock": "Stock", "reports": "Reports", "admin": "Admin", "logout": "Logout",
        "milling": "Milling", "enter_system": "Enter System", "login": "Login", "username": "Username",
        "password": "Password", "add": "Add", "save": "Save", "update": "Update", "delete": "Delete",
        "edit": "Edit", "cancel": "Cancel", "admin_panel": "Admin Panel", "manage_vendors": "Manage Vendors",
        "manage_stock": "Manage Stock", "stock_control": "Stock Control",
        "intake_packing_edit_note": "Intake & Packing can be edited from their respective pages",
        "truck_number": "Truck Number", "vendor": "Vendor", "vendor_name": "Vendor Name",
        "gross_weight": "Gross Weight", "tare_weight": "Tare Weight", "net_weight": "Net Weight",
        "moisture": "Moisture %", "protein": "Protein %", "impurities": "Impurities %",
        "save_intake": "Save Intake", "example_vendor_1": "Al-Nour Trading",
        "example_vendor_2": "Delta Wheat Co.", "new_vendor": "New Vendor", "edit_vendor": "Edit Vendor",
        "related_intake_optional": "Related Intake (Optional)", "not_linked": "Not Linked",
        "intake": "Intake", "initial_moisture": "Initial Moisture %", "target_moisture": "Target Moisture %",
        "added_water": "Added Water (L)", "tempering_hours": "Tempering Hours",
        "save_conditioning_log": "Save Conditioning Log", "packing_line": "Packing Line",
        "packing_lines": "Packing Lines", "product": "Product", "bag_size": "Bag Size (kg)",
        "bag_count": "Bag Count", "bag_weight": "Bag Weight", "record_packing": "Record Packing",
        "save_packing": "Save Packing", "new_packing_session": "New Packing Session",
        "flour": "Flour", "bran": "Bran", "milling_lines": "Milling Lines",
        "milling_line": "Milling Line", "wheat_used": "Wheat Used", "extraction_rate": "Extraction Rate",
        "quantity": "Quantity", "from_date": "From Date", "to_date": "To Date",
        "generate_report": "Generate Report", "date": "Date", "live_weighbridge": "Live Weighbridge",
        "current_weight": "Current Weight", "weighbridge": "Weighbridge", "daily_capacity": "Daily Capacity",
        "system_status": "System Status", "operational": "Operational", "tons_day": "Tons/Day",
        "online": "Online", "offline": "Offline", "kg": "kg", "operator": "Operator",
        "role": "Role", "created_at": "Created At",
        # Packing production translations
        "packing_production": "Packing Production", "live_packing_scale": "Live Packing Scale",
        "checking": "Checking", "total_weight": "Total Weight", "bags": "bags",
        "record_production": "Record Production", "product_type": "Product Type",
        "select_product": "Select Product", "flour_72": "Flour 72%", "flour_82": "Flour 82%",
        "semolina": "Semolina", "fine_bran": "Fine Bran", "coarse_bran": "Coarse Bran",
        "auto_captured": "Auto-captured from scale", "calculated_auto": "Calculated automatically",
        "production_line": "Production Line", "line_1": "Line 1", "line_2": "Line 2",
        "shift": "Shift", "morning": "Morning", "evening": "Evening", "night": "Night",
        "operator_name": "Operator Name", "notes": "Notes", "optional_notes": "Optional notes",
        "reset": "Reset", "save_production": "Save Production",
        # Accounting - Toll Milling
        "accounting": "Accounting", "pricing_configuration": "Pricing Configuration",
        "milling_fee": "Milling Fee", "coarse_bran_share": "Coarse Bran Revenue Share",
        "coarse_bran_price": "Coarse Bran Price", "weighbridge_fee": "Weighbridge Fee (Non-customers)",
        "save_rates": "Save Rates", "rates_saved": "Rates saved successfully!",
        "revenue_sources": "Revenue Sources", "revenue_source": "Revenue Source",
        "revenue_breakdown": "Revenue Breakdown", "expense_breakdown": "Expense Breakdown",
        "monthly_trend": "Monthly Trend", "profit_analysis": "Profit Analysis",
        "milled_today": "Milled Today", "tons": "Tons", "ton": "Ton", "weighing": "Weighing",
        "this_month": "This Month", "add_other_revenue": "Add Other Revenue",
        "revenue_description_placeholder": "e.g., Equipment rental, consultation fee",
        "milling_revenue": "Milling Fee Revenue", "bran_revenue": "Coarse Bran Revenue",
        "weighbridge_revenue": "Weighbridge Revenue", "other_revenue": "Other Revenue",
        "labor": "Labor & Salaries", "wheat_transport": "Wheat Transportation",
        "bags": "Flour & Bran Bags", "electricity": "Electricity", "water": "Water",
        "maintenance": "Maintenance & Repairs", "select_category": "Select Category...",
        "confirm_delete": "Are you sure you want to delete this expense?",
        "rate": "Rate", "amount": "Amount", "percentage": "Percentage",
        "category": "Category", "description": "Description", "actions": "Actions",
        "apply": "Apply", "all": "All", "total": "Total", "add_expense": "Add Expense",
        "print": "Print", "export_excel": "Export to Excel", "profit": "Profit",
        "revenue": "Revenue", "expenses": "Expenses", "net_profit": "Net Profit",
        "total_revenue": "Total Revenue", "total_expenses": "Total Expenses",
        "filters": "Filters", "invoices": "invoices", "price": "Price",
        "customer": "Customer", "invoice_number": "Invoice Number",
        # Maintenance System
        "maintenance_system": "Maintenance", "system": "System", "maintenance_schedule": "Maintenance Schedule",
        "maintenance_history": "Maintenance History", "maintenance_logs": "Maintenance Logs",
        "maintenance_tasks": "Maintenance Tasks", "equipment": "Equipment",
        "equipment_registry": "Equipment Registry", "spare_parts": "Spare Parts",
        "spare_parts_inventory": "Spare Parts Inventory", "overdue": "Overdue",
        "due_soon": "Due Soon", "low_stock": "Low Stock", "upcoming": "Upcoming",
        "within_7_days": "Within 7 Days", "next_30_days": "Next 30 Days",
        "scheduled_maintenance": "Scheduled Maintenance", "add_schedule": "Add Schedule",
        "log": "Log", "logged_successfully": "Logged Successfully",
        "task": "Task", "task_description": "Task Description",
        "performed_by": "Performed By", "parts_used": "Parts Used",
        "parts_cost": "Parts Cost", "labor_hours": "Labor Hours",
        "labor_cost": "Labor Cost", "downtime": "Downtime",
        "minutes": "Minutes", "next_due": "Next Due",
        "duration": "Duration", "complete": "Complete",
        "log_type": "Log Type", "preventive": "Preventive",
        "breakdown": "Breakdown", "inspection": "Inspection",
        "calibration": "Calibration", "records": "Records",
        "total_cost": "Total Cost", "total_downtime": "Total Downtime",
        "equipment_type": "Equipment Type", "milling_line": "Milling Line",
        "packing_line": "Packing Line", "weighbridge": "Weighbridge",
        "motor": "Motor", "conveyor": "Conveyor",
        "critical": "Critical", "high": "High", "medium": "Medium", "low": "Low",
        "code": "Code", "type": "Type", "location": "Location",
        "view_details": "View Details", "part_code": "Part Code",
        "part_name": "Part Name", "stock": "Stock",
        "min_stock": "Min Stock", "unit_cost": "Unit Cost",
        "supplier": "Supplier", "add_equipment": "Add Equipment",
        "add_part": "Add Part", "adjust_stock": "Adjust Stock",
        "ok": "OK", "summary": "Summary", "select": "Select",
        "days": "Days",
        # Stock Management
        "stock_control": "Stock Control", "total_flour": "Total Flour",
        "total_bran": "Total Bran", "total_bags": "Total Bags",
        "items": "Items", "products_stock": "Products Stock",
        "stock_movements": "Stock Movements", "low_stock_alerts": "Low Stock Alerts",
        "current_stock": "Current Stock", "product_type": "Product Type",
        "recent_movements": "Recent Movements", "movement_type": "Movement Type",
        "stock_in": "Stock In", "stock_out": "Stock Out",
        "adjustment": "Adjustment", "balance": "Balance",
        "items_running_low": "Items Running Low", "minimum_level": "Minimum Level",
        "deficit": "Deficit", "restock": "Restock",
        "all_stock_good": "All stock levels are good!",
        "stock_adjusted_successfully": "Stock adjusted successfully",
        "minimum": "Minimum", "movement": "Movement",
        "after": "After", "before": "Before",
        # Packing BX-3
        "record_production": "Record Production", "reset_session": "Reset Session",
        "bags_today": "Bags Today", "last_bag": "Last Bag",
        "recent_bags": "Recent Bags", "no_bags_yet": "No bags completed yet",
        "underweight": "Underweight", "overweight": "Overweight",
        "confirm_record_production": "Save this production batch to database?",
        "production_recorded": "Production Recorded",
        "confirm_reset_session": "Reset bag counter for new session?",
        "session_reset": "Session Reset Successfully"
    },
    "ar": {
        "mill_name": "Al Mohandes Modern Mills", "mill_name_ar": "مطاحن المهندس الحديثة",
        "dashboard": "لوحة التحكم", "wheat_intake": "استلام القمح", "intake_history": "سجل الاستلام",
        "conditioning": "الترطيب", "conditioning_history": "سجل الترطيب", "vendors": "الموردين",
        "packing": "التعبئة", "stock": "المخزون", "reports": "التقارير", "admin": "الإدارة",
        "logout": "تسجيل الخروج", "milling": "الطحن", "enter_system": "دخول النظام",
        "login": "تسجيل الدخول", "username": "اسم المستخدم", "password": "كلمة المرور",
        "add": "إضافة", "save": "حفظ", "update": "تحديث", "delete": "حذف", "edit": "تعديل",
        "cancel": "إلغاء", "admin_panel": "لوحة الإدارة", "manage_vendors": "إدارة الموردين",
        "manage_stock": "إدارة المخزون", "stock_control": "التحكم في المخزون",
        "intake_packing_edit_note": "يمكن تعديل الاستلام والتعبئة من صفحاتها الخاصة",
        "truck_number": "رقم الشاحنة", "vendor": "المورد", "vendor_name": "اسم المورد",
        "gross_weight": "الوزن الإجمالي", "tare_weight": "وزن الفارغ", "net_weight": "الوزن الصافي",
        "moisture": "نسبة الرطوبة %", "protein": "نسبة البروتين %", "impurities": "نسبة الشوائب %",
        "save_intake": "حفظ الاستلام", "example_vendor_1": "تجارة النور",
        "example_vendor_2": "شركة قمح الدلتا", "new_vendor": "مورد جديد", "edit_vendor": "تعديل المورد",
        "related_intake_optional": "استلام مرتبط (اختياري)", "not_linked": "غير مرتبط",
        "intake": "استلام", "initial_moisture": "الرطوبة الأولية %", "target_moisture": "الرطوبة المستهدفة %",
        "added_water": "الماء المضاف (لتر)", "tempering_hours": "ساعات الترطيب",
        "save_conditioning_log": "حفظ سجل الترطيب", "packing_line": "خط التعبئة",
        "packing_lines": "خطوط التعبئة", "product": "المنتج", "bag_size": "حجم الكيس (كجم)",
        "bag_count": "عدد الأكياس", "bag_weight": "وزن الكيس", "record_packing": "تسجيل التعبئة",
        "save_packing": "حفظ التعبئة", "new_packing_session": "جلسة تعبئة جديدة",
        "flour": "دقيق", "bran": "نخالة", "milling_lines": "خطوط الطحن",
        "milling_line": "خط الطحن", "wheat_used": "القمح المستخدم", "extraction_rate": "معدل الاستخلاص",
        "quantity": "الكمية", "from_date": "من تاريخ", "to_date": "إلى تاريخ",
        "generate_report": "إنشاء التقرير", "date": "التاريخ", "live_weighbridge": "الميزان المباشر",
        "current_weight": "الوزن الحالي", "weighbridge": "الميزان", "daily_capacity": "الطاقة اليومية",
        "system_status": "حالة النظام", "operational": "يعمل", "tons_day": "طن/يوم",
        "online": "متصل", "offline": "غير متصل", "kg": "كجم", "operator": "المشغل",
        "role": "الدور", "created_at": "تاريخ الإنشاء",
        # Packing production translations (Arabic)
        "packing_production": "إنتاج التعبئة", "live_packing_scale": "ميزان التعبئة المباشر",
        "checking": "جاري الفحص", "total_weight": "الوزن الإجمالي", "bags": "كيس",
        "record_production": "تسجيل الإنتاج", "product_type": "نوع المنتج",
        "select_product": "اختر المنتج", "flour_72": "دقيق ٧٢٪", "flour_82": "دقيق ٨٢٪",
        "semolina": "سميد", "fine_bran": "نخالة ناعمة", "coarse_bran": "نخالة خشنة",
        "auto_captured": "يتم التقاطه تلقائياً من الميزان", "calculated_auto": "يتم حسابه تلقائياً",
        "production_line": "خط الإنتاج", "line_1": "الخط ١", "line_2": "الخط ٢",
        "shift": "الوردية", "morning": "صباحية", "evening": "مسائية", "night": "ليلية",
        "operator_name": "اسم المشغل", "notes": "ملاحظات", "optional_notes": "ملاحظات اختيارية",
        "reset": "إعادة تعيين", "save_production": "حفظ الإنتاج",
        # Accounting - Toll Milling (Arabic)
        "accounting": "المحاسبة", "pricing_configuration": "إعدادات التسعير",
        "milling_fee": "رسوم الطحن", "coarse_bran_share": "حصة إيرادات النخالة الخشنة",
        "coarse_bran_price": "سعر النخالة الخشنة", "weighbridge_fee": "رسوم الميزان (العملاء الخارجيين)",
        "save_rates": "حفظ الأسعار", "rates_saved": "تم حفظ الأسعار بنجاح!",
        "revenue_sources": "مصادر الإيرادات", "revenue_source": "مصدر الإيراد",
        "revenue_breakdown": "تفصيل الإيرادات", "expense_breakdown": "تفصيل المصروفات",
        "monthly_trend": "الاتجاه الشهري", "profit_analysis": "تحليل الأرباح",
        "milled_today": "الطحن اليوم", "tons": "طن", "ton": "طن", "weighing": "وزنة",
        "this_month": "هذا الشهر", "add_other_revenue": "إضافة إيراد آخر",
        "revenue_description_placeholder": "مثال: إيجار معدات، رسوم استشارات",
        "milling_revenue": "إيرادات رسوم الطحن", "bran_revenue": "إيرادات النخالة الخشنة",
        "weighbridge_revenue": "إيرادات الميزان", "other_revenue": "إيرادات أخرى",
        "labor": "العمالة والرواتب", "wheat_transport": "نقل القمح",
        "bags": "أكياس الدقيق والنخالة", "electricity": "كهرباء", "water": "مياه",
        "maintenance": "صيانة وإصلاحات", "select_category": "اختر الفئة...",
        "confirm_delete": "هل أنت متأكد من حذف هذا المصروف؟",
        "rate": "السعر", "amount": "المبلغ", "percentage": "النسبة",
        "category": "الفئة", "description": "الوصف", "actions": "الإجراءات",
        "apply": "تطبيق", "all": "الكل", "total": "الإجمالي", "add_expense": "إضافة مصروف",
        "print": "طباعة", "export_excel": "تصدير إلى إكسل", "profit": "الربح",
        "revenue": "الإيرادات", "expenses": "المصروفات", "net_profit": "صافي الربح",
        "total_revenue": "إجمالي الإيرادات", "total_expenses": "إجمالي المصروفات",
        "filters": "الفلاتر", "invoices": "فواتير", "price": "السعر",
        "customer": "العميل", "invoice_number": "رقم الفاتورة",
        # Maintenance System (Arabic)
        "maintenance_system": "الصيانة", "system": "النظام", "maintenance_schedule": "جدول الصيانة",
        "maintenance_history": "سجل الصيانة", "maintenance_logs": "سجلات الصيانة",
        "maintenance_tasks": "مهام الصيانة", "equipment": "المعدات",
        "equipment_registry": "سجل المعدات", "spare_parts": "قطع الغيار",
        "spare_parts_inventory": "مخزون قطع الغيار", "overdue": "متأخرة",
        "due_soon": "قريبة الموعد", "low_stock": "مخزون منخفض", "upcoming": "قادمة",
        "within_7_days": "خلال 7 أيام", "next_30_days": "خلال 30 يوم",
        "scheduled_maintenance": "الصيانة المجدولة", "add_schedule": "إضافة جدولة",
        "log": "تسجيل", "logged_successfully": "تم التسجيل بنجاح",
        "task": "المهمة", "task_description": "وصف المهمة",
        "performed_by": "تم بواسطة", "parts_used": "القطع المستخدمة",
        "parts_cost": "تكلفة القطع", "labor_hours": "ساعات العمل",
        "labor_cost": "تكلفة العمالة", "downtime": "وقت التوقف",
        "minutes": "دقيقة", "next_due": "الموعد القادم",
        "duration": "المدة", "complete": "إكمال",
        "log_type": "نوع السجل", "preventive": "صيانة وقائية",
        "breakdown": "عطل", "inspection": "فحص",
        "calibration": "معايرة", "records": "سجلات",
        "total_cost": "التكلفة الإجمالية", "total_downtime": "إجمالي وقت التوقف",
        "equipment_type": "نوع المعدة", "milling_line": "خط الطحن",
        "packing_line": "خط التعبئة", "weighbridge": "الميزان",
        "motor": "محرك", "conveyor": "سير ناقل",
        "critical": "حرج", "high": "عالي", "medium": "متوسط", "low": "منخفض",
        "code": "الكود", "type": "النوع", "location": "الموقع",
        "view_details": "عرض التفاصيل", "part_code": "كود القطعة",
        "part_name": "اسم القطعة", "stock": "المخزون",
        "min_stock": "الحد الأدنى", "unit_cost": "تكلفة الوحدة",
        "supplier": "المورد", "add_equipment": "إضافة معدة",
        "add_part": "إضافة قطعة", "adjust_stock": "تعديل المخزون",
        "ok": "جيد", "summary": "الملخص", "select": "اختر",
        "days": "أيام",
        # Stock Management (Arabic)
        "stock_control": "التحكم في المخزون", "total_flour": "إجمالي الدقيق",
        "total_bran": "إجمالي النخالة", "total_bags": "إجمالي الأكياس",
        "items": "عنصر", "products_stock": "مخزون المنتجات",
        "stock_movements": "حركة المخزون", "low_stock_alerts": "تنبيهات نفاد المخزون",
        "current_stock": "المخزون الحالي", "product_type": "نوع المنتج",
        "recent_movements": "الحركات الأخيرة", "movement_type": "نوع الحركة",
        "stock_in": "إدخال", "stock_out": "إخراج",
        "adjustment": "تعديل", "balance": "الرصيد",
        "items_running_low": "أصناف قاربت على النفاد", "minimum_level": "الحد الأدنى",
        "deficit": "العجز", "restock": "إعادة تخزين",
        "all_stock_good": "جميع مستويات المخزون جيدة!",
        "stock_adjusted_successfully": "تم تعديل المخزون بنجاح",
        "minimum": "الحد الأدنى", "movement": "حركة",
        "after": "بعد", "before": "قبل",
        # Packing BX-3 (Arabic)
        "record_production": "تسجيل الإنتاج", "reset_session": "إعادة تعيين الجلسة",
        "bags_today": "الأكياس اليوم", "last_bag": "آخر كيس",
        "recent_bags": "الأكياس الأخيرة", "no_bags_yet": "لم يتم إكمال أي أكياس بعد",
        "underweight": "وزن ناقص", "overweight": "وزن زائد",
        "confirm_record_production": "حفظ هذه الدفعة الإنتاجية في قاعدة البيانات؟",
        "production_recorded": "تم تسجيل الإنتاج",
        "confirm_reset_session": "إعادة تعيين عداد الأكياس لجلسة جديدة؟",
        "session_reset": "تم إعادة تعيين الجلسة بنجاح"
    }
}

@app.context_processor
def inject_lang():
    lang = session.get("lang", "en")
    return {"lang": lang, "t": TRANSLATIONS.get(lang, TRANSLATIONS["en"])}

@app.route("/lang/<code>")
def change_lang(code):
    if code in ["en", "ar"]:
        session["lang"] = code
    return redirect(request.referrer or "/")

# ROUTES
@app.route("/api/packing/pdf-range")
@login_required
def generate_packing_pdf_range():
    """
    Generate PDF report for packing data over a date range
    
    Query params:
        start_date: YYYY-MM-DD (required)
        end_date: YYYY-MM-DD (required)
        machine_id: Optional machine filter
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        machine_id = request.args.get('machine_id')
        
        if not start_date or not end_date:
            return jsonify({'error': 'Start date and end date are required'}), 400
        
        # Fetch data for date range
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            
            if machine_id:
                cursor.execute("""
                    SELECT 
                        id,
                        machine_id,
                        machine_name,
                        bag_number,
                        weight_kg,
                        packed_at,
                        packed_date,
                        operator
                    FROM packing_data
                    WHERE machine_id = %s
                      AND packed_date BETWEEN %s AND %s
                    ORDER BY packed_date, machine_id, bag_number
                """, (machine_id, start_date, end_date))
            else:
                cursor.execute("""
                    SELECT 
                        id,
                        machine_id,
                        machine_name,
                        bag_number,
                        weight_kg,
                        packed_at,
                        packed_date,
                        operator
                    FROM packing_data
                    WHERE packed_date BETWEEN %s AND %s
                    ORDER BY packed_date, machine_id, bag_number
                """, (start_date, end_date))
            
            bags = cursor.fetchall()
        
        # Create PDF in memory
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4, 
                              topMargin=0.5*inch, bottomMargin=0.5*inch,
                              leftMargin=0.5*inch, rightMargin=0.5*inch)
        elements = []
        
        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1f2d36'),
            spaceAfter=20,
            alignment=TA_CENTER
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2563eb'),
            spaceAfter=12,
        )
        
        # Title
        title = Paragraph("PACKING PRODUCTION REPORT", title_style)
        elements.append(title)
        
        # Date range info
        start_obj = datetime.strptime(start_date, '%Y-%m-%d')
        end_obj = datetime.strptime(end_date, '%Y-%m-%d')
        
        info_text = f"<b>Period:</b> {start_obj.strftime('%B %d, %Y')} to {end_obj.strftime('%B %d, %Y')}<br/>"
        
        # Calculate number of days
        days_diff = (end_obj - start_obj).days + 1
        info_text += f"<b>Duration:</b> {days_diff} day(s)<br/>"
        
        if machine_id:
            machine_names = {
                'bran_40kg': 'BX3 - Bran 40kg',
                'flour_50kg_bxf3': 'BXf3 - Flour 50kg',
                'flour_50kg_bx30': 'BX30 - Flour 50kg'
            }
            info_text += f"<b>Machine:</b> {machine_names.get(machine_id, machine_id)}<br/>"
        else:
            info_text += f"<b>Machines:</b> All<br/>"
        
        info_text += f"<b>Generated:</b> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        info_para = Paragraph(info_text, styles['Normal'])
        elements.append(info_para)
        elements.append(Spacer(1, 20))
        
        # Summary Statistics
        if bags:
            # Group by machine
            machine_stats = {}
            daily_stats = {}
            
            for bag in bags:
                machine = bag['machine_name']
                date = bag['packed_date'].strftime('%Y-%m-%d') if hasattr(bag['packed_date'], 'strftime') else str(bag['packed_date'])
                
                # Machine stats
                if machine not in machine_stats:
                    machine_stats[machine] = {
                        'count': 0,
                        'total_weight': 0,
                        'bags': []
                    }
                machine_stats[machine]['count'] += 1
                machine_stats[machine]['total_weight'] += float(bag['weight_kg'])
                machine_stats[machine]['bags'].append(bag)
                
                # Daily stats
                if date not in daily_stats:
                    daily_stats[date] = {
                        'count': 0,
                        'total_weight': 0
                    }
                daily_stats[date]['count'] += 1
                daily_stats[date]['total_weight'] += float(bag['weight_kg'])
            
            # OVERALL SUMMARY
            summary_heading = Paragraph("OVERALL SUMMARY", heading_style)
            elements.append(summary_heading)
            
            total_bags = len(bags)
            total_weight = sum(float(b['weight_kg']) for b in bags)
            avg_weight = total_weight / total_bags if total_bags > 0 else 0
            daily_avg = total_bags / days_diff if days_diff > 0 else 0
            
            summary_data = [
                ['Metric', 'Value'],
                ['Total Bags Packed', f"{total_bags:,}"],
                ['Total Weight', f"{total_weight:,.2f} kg"],
                ['Average Weight per Bag', f"{avg_weight:.2f} kg"],
                ['Average Bags per Day', f"{daily_avg:.1f}"],
                ['Date Range', f"{days_diff} day(s)"]
            ]
            
            overall_table = Table(summary_data, colWidths=[3*inch, 3*inch])
            overall_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f2d36')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 12),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('FONTNAME', (1, 1), (1, -1), 'Helvetica-Bold'),
            ]))
            
            elements.append(overall_table)
            elements.append(Spacer(1, 20))
            
            # SUMMARY BY MACHINE
            machine_heading = Paragraph("SUMMARY BY MACHINE", heading_style)
            elements.append(machine_heading)
            
            machine_table_data = [['Machine', 'Bags', 'Total Weight (kg)', 'Avg Weight (kg)', '% of Total']]
            
            for machine, stats in sorted(machine_stats.items()):
                avg_weight = stats['total_weight'] / stats['count']
                percent = (stats['count'] / total_bags * 100) if total_bags > 0 else 0
                machine_table_data.append([
                    machine,
                    f"{stats['count']:,}",
                    f"{stats['total_weight']:,.2f}",
                    f"{avg_weight:.2f}",
                    f"{percent:.1f}%"
                ])
            
            machine_table = Table(machine_table_data, colWidths=[2.2*inch, 1.2*inch, 1.5*inch, 1.2*inch, 1.2*inch])
            machine_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f2d36')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ]))
            
            elements.append(machine_table)
            elements.append(Spacer(1, 20))
            
            # SUMMARY BY DAY
            day_heading = Paragraph("DAILY PRODUCTION SUMMARY", heading_style)
            elements.append(day_heading)
            
            daily_table_data = [['Date', 'Bags', 'Total Weight (kg)', 'Avg Weight (kg)']]
            
            for date in sorted(daily_stats.keys()):
                stats = daily_stats[date]
                avg = stats['total_weight'] / stats['count'] if stats['count'] > 0 else 0
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                daily_table_data.append([
                    date_obj.strftime('%b %d, %Y'),
                    f"{stats['count']:,}",
                    f"{stats['total_weight']:,.2f}",
                    f"{avg:.2f}"
                ])
            
            daily_table = Table(daily_table_data, colWidths=[2*inch, 1.5*inch, 2*inch, 1.5*inch])
            daily_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1f2d36')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.grey),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8f9fa')]),
            ]))
            
            elements.append(daily_table)
            
        else:
            # No bags message
            no_data = Paragraph(
                f"<b>No bags were packed between {start_obj.strftime('%B %d, %Y')} and {end_obj.strftime('%B %d, %Y')}</b>",
                styles['Normal']
            )
            elements.append(no_data)
        
        # Build PDF
        doc.build(elements)
        
        # Get PDF data
        pdf_data = buffer.getvalue()
        buffer.close()
        
        # Return PDF
        response = make_response(pdf_data)
        response.headers['Content-Type'] = 'application/pdf'
        response.headers['Content-Disposition'] = f'inline; filename=packing_report_{start_date}_to_{end_date}.pdf'
        
        return response
        
    except Exception as e:
        print(f"Error generating PDF: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e)}), 500

# API endpoint to get a single intake record
@app.route("/intake", methods=["GET", "POST"])
@login_required
def intake():
    """First weighing - All fields editable except weights"""
    if request.method == "POST":
        try:
            # FREE INPUT FIELDS - User can type anything
            vendor_name = request.form.get("vendor_name", "").strip()
            truck = request.form.get("truck", "").strip()
            wheat_type = request.form.get("wheat_type", "")
            carrier_name = request.form.get("carrier_name", "")
            governorate = request.form.get("governorate", "")
            load_type = request.form.get("load_type", "")
            driver = request.form.get("driver", "")
            
            # WEIGHT FIELDS - Auto-captured from weighbridge
            gross = int(request.form.get("gross", 0))
            first_weight = int(request.form.get("first_weight", 0))
            
            # Store additional data in notes or create new columns
            # For now, we'll use existing schema and store extra data
            
            with get_db() as conn:
                cur = conn.cursor()
                
                # Check if vendor exists, if not create
                vendor_id = None
                if vendor_name:
                    cur.execute("SELECT id FROM vendors WHERE name = %s", (vendor_name,))
                    result = cur.fetchone()
                    if result:
                        vendor_id = result[0]
                    else:
                        # Create new vendor
                        cur.execute("INSERT INTO vendors (name) VALUES (%s)", (vendor_name,))
                        vendor_id = cur.lastrowid
                
                # Insert intake record with tare_weight = 0 (first weighing)
                cur.execute("""
                    INSERT INTO intake 
                    (vendor_id, gross_weight, tare_weight, captured_by, captured_at) 
                    VALUES (%s, %s, 0, %s, NOW())
                """, (vendor_id, gross, session.get("user")))
                
                intake_id = cur.lastrowid
                
                # Store additional metadata in a separate table or notes
                # For simplicity, you could add columns: wheat_type, governorate, load_type, driver, carrier
                # Or store as JSON in a notes field
                
                conn.commit()
            
            flash("First weighing saved successfully! Vehicle can leave.", "success")
            return redirect("/intake/history")
            
        except Exception as e:
            print(f"Intake error: {e}")
            flash(f"Error saving intake: {str(e)}", "danger")
    
    # GET request - show form
    try:
        with get_db() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM vendors ORDER BY name")
            vendors = cur.fetchall() or []
        return render_template("intake.html", vendors=vendors)
    except Exception as e:
        print(f"Error loading vendors: {e}")
        return render_template("intake.html", vendors=[])

@app.route("/weighing/second", methods=["GET", "POST"])
@login_required
def second_weighing():
    """Second weighing - First weigh data locked, new fields editable"""
    if request.method == "POST":
        try:
            intake_id = request.form.get("intake_id")
            
            # CAPTURED WEIGHT (locked from weighbridge)
            second_weight = int(request.form.get("second_weight", 0))
            
            # EDITABLE FIELDS (new data in second weighing)
            impurities_weight = int(request.form.get("impurities_weight", 0))
            invoice_number = request.form.get("invoice_number", "")
            quality = request.form.get("quality", "")
            bags_count = request.form.get("bags_count", 0)
            code = request.form.get("code", "")
            driver_name = request.form.get("driver_name", "")
            operator2 = request.form.get("operator2", session.get("user"))
            
            # CALCULATED
            net_weight = int(request.form.get("net_weight", 0))
            total_weight = int(request.form.get("total_weight", 0))
            
            with get_db() as conn:
                cur = conn.cursor()
                
                # Update intake record with tare weight (second weighing)
                cur.execute("""
                    UPDATE intake 
                    SET tare_weight = %s 
                    WHERE id = %s
                """, (second_weight, intake_id))
                
                # Store second weighing metadata
                # You could create a second_weighing table or add columns
                # For now, we'll just update the main record
                
                conn.commit()
            
            flash(f"Second weighing completed! Net weight: {net_weight} kg", "success")
            return redirect("/weighing/second")
            
        except Exception as e:
            print(f"Second weighing error: {e}")
            flash(f"Error saving second weighing: {str(e)}", "danger")
    
    # GET request - show form with pending records
    try:
        with get_db() as conn:
            cur = conn.cursor(dictionary=True)
            # Get records that haven't been weighed second time (tare_weight = 0)
            cur.execute("""
                SELECT i.*, v.name as vendor 
                FROM intake i 
                LEFT JOIN vendors v ON i.vendor_id = v.id 
                WHERE i.tare_weight = 0 
                ORDER BY i.captured_at DESC
                LIMIT 50
            """)
            pending_records = cur.fetchall() or []
        
        return render_template("second_weighing.html", pending_records=pending_records)
    
    except Exception as e:
        print(f"Error loading pending records: {e}")
        return render_template("second_weighing.html", pending_records=[])


# Enhanced API endpoint to get full intake details
@app.route("/api/intake/<int:intake_id>")
@login_required
def api_get_intake(intake_id):
    """Get complete details of a specific intake record"""
    try:
        with get_db() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT i.*, v.name as vendor, v.phone
                FROM intake i 
                LEFT JOIN vendors v ON i.vendor_id = v.id 
                WHERE i.id = %s
            """, (intake_id,))
            record = cur.fetchone()
            
            if record:
                # Add calculated net_weight if not in schema
                if 'net_weight' not in record or record['net_weight'] is None:
                    record['net_weight'] = record['gross_weight'] - record['tare_weight']
                
                return jsonify({"success": True, "record": record})
            else:
                return jsonify({"success": False, "error": "Record not found"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

# Packing scale API endpoint
@app.route("/api/packing-scale")
@login_required
def api_packing_scale():
    """Get live packing scale data - redirects to new BX-3 endpoint"""
    # Redirect to new endpoint
    return redirect(url_for('api_packing_status'))


# Packing page
@app.route("/packing")
@login_required
@block_weighbridge_operator
@block_weighbridge_operator
def packing():
    """Packing production page"""
    return render_template("packing.html")


# Save packing record
@app.route("/api/packing", methods=["POST"])
@login_required
def api_save_packing():
    """Save packing production record"""
    try:
        data = request.get_json()
        
        # Validate required fields
        required = ['product_type', 'bag_weight', 'bag_count']
        for field in required:
            if field not in data or not data[field]:
                return jsonify({"success": False, "error": f"Missing {field}"}), 400
        
        # Calculate total weight
        total_weight = float(data['bag_weight']) * int(data['bag_count'])
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            # Insert packing record
            cursor.execute("""
                INSERT INTO packing 
                (product_type, bag_weight, bag_count, total_weight, 
                 production_line, shift, operator, notes, created_at, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), %s)
            """, (
                data['product_type'],
                data['bag_weight'],
                data['bag_count'],
                total_weight,
                data.get('production_line', 'Line 1'),
                data.get('shift', 'Morning'),
                data.get('operator', ''),
                data.get('notes', ''),
                session.get('username', 'system')
            ))
            
            conn.commit()
            packing_id = cursor.lastrowid
            
            return jsonify({
                "success": True,
                "packing_id": packing_id,
                "total_weight": total_weight
            })
    
    except Exception as e:
        print(f"Error saving packing: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


# Production dashboard with live stats
@app.route("/production-dashboard")
@login_required
@block_weighbridge_operator
def production_dashboard():
    """Production dashboard with live packing stats"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            
            # Today's production summary
            cursor.execute("""
                SELECT 
                    product_type,
                    SUM(bag_count) as total_bags,
                    SUM(total_weight) as total_weight
                FROM packing
                WHERE DATE(created_at) = CURDATE()
                GROUP BY product_type
            """)
            today_production = cursor.fetchall()
            
            # This week's production
            cursor.execute("""
                SELECT 
                    DATE(created_at) as date,
                    SUM(bag_count) as bags,
                    SUM(total_weight) as weight
                FROM packing
                WHERE created_at >= DATE_SUB(CURDATE(), INTERVAL 7 DAY)
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """)
            week_production = cursor.fetchall()
            
            # Production by line today
            cursor.execute("""
                SELECT 
                    production_line,
                    SUM(bag_count) as bags,
                    SUM(total_weight) as weight
                FROM packing
                WHERE DATE(created_at) = CURDATE()
                GROUP BY production_line
            """)
            line_production = cursor.fetchall()
            
            return render_template("production_dashboard.html",
                                 today=today_production,
                                 week=week_production,
                                 lines=line_production)
    
    except Exception as e:
        print(f"Production dashboard error: {e}")
        return render_template("production_dashboard.html",
                             today=[],
                             week=[],
                             lines=[])


# Production reports
@app.route("/production-report")
@login_required
@block_weighbridge_operator
def production_report():
    """Production report page"""
    try:
        start_date = request.args.get('start_date', datetime.now().strftime('%Y-%m-%d'))
        end_date = request.args.get('end_date', datetime.now().strftime('%Y-%m-%d'))
        
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT 
                    id,
                    product_type,
                    bag_weight,
                    bag_count,
                    total_weight,
                    production_line,
                    shift,
                    operator,
                    notes,
                    created_at,
                    created_by
                FROM packing
                WHERE DATE(created_at) BETWEEN %s AND %s
                ORDER BY created_at DESC
            """, (start_date, end_date))
            
            records = cursor.fetchall()
            
            return render_template("production_report.html",
                                 records=records,
                                 start_date=start_date,
                                 end_date=end_date)
    
    except Exception as e:
        print(f"Production report error: {e}")
        return render_template("production_report.html",
                             records=[],
                             start_date=start_date,
                             end_date=end_date)


# Print weighbridge ticket
@app.route("/print-weighbridge/<int:intake_id>")
@login_required
def print_weighbridge(intake_id):
    """Generate printable weighbridge ticket"""
    try:
        with get_db() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("""
                SELECT i.*, v.name as vendor, v.phone
                FROM intake i 
                LEFT JOIN vendors v ON i.vendor_id = v.id 
                WHERE i.id = %s
            """, (intake_id,))
            record = cur.fetchone()
        
        if record:
            return render_template("print_ticket.html", record=record)
        else:
            return "Record not found", 404
            
    except Exception as e:
        return f"Error: {str(e)}", 500

@app.route("/")
@block_weighbridge_operator
def front():
    if session.get("user"):
        return redirect("/dashboard")
    return render_template("front.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = request.form.get("username", "").strip()
        pw = request.form.get("password", "")
        
        if not user or not pw:
            return render_template("login.html", error="Username and password required")
        
        try:
            with get_db() as conn:
                cur = conn.cursor(dictionary=True)
                # YOUR schema uses password_hash column
                cur.execute("SELECT * FROM users WHERE username=%s", (user,))
                row = cur.fetchone()
                
                if row:
                    # Check if password is hashed or plain text
                    stored_password = row["password_hash"]
                    
                    # If it starts with pbkdf2: it's hashed, otherwise plain text
                    if stored_password.startswith("pbkdf2:"):
                        password_valid = check_password_hash(stored_password, pw)
                    else:
                        # WARNING: Plain-text password fallback is insecure.
                        # Migrate all users to hashed passwords and remove this branch.
                        # Use: UPDATE users SET password_hash = <hashed> WHERE username = <user>
                        password_valid = (stored_password == pw)
                    
                    if password_valid:
                        session["user"] = row["username"]
                        session["username"] = row["username"]  # Fix: also store as 'username' key used by accounting/packing routes
                        session["role"] = row["role"]
                        session.permanent = True
                        
                        # Redirect based on role
                        if row["role"] == "OPERATOR":
                            return redirect("/weighbridge_dashboard")
                        else:
                            return redirect("/dashboard")
                
                return render_template("login.html", error="Invalid credentials")
                
        except Exception as e:
            print(f"Login error: {e}")
            return render_template("login.html", error="Login failed")
    
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

@app.route("/dashboard")
@login_required
@block_weighbridge_operator
@block_weighbridge_operator
def dashboard():
    try:
        with get_db() as conn:
            cur = conn.cursor(dictionary=True)
            # Using YOUR schema's net_weight calculated column
            cur.execute("SELECT COUNT(*) as count, COALESCE(SUM(net_weight), 0) as total FROM intake")
            intake_stats = cur.fetchone()
            cur.execute("SELECT COUNT(*) as count FROM vendors")
            vendor_stats = cur.fetchone()
            # YOUR schema uses quantity_kg instead of quantity
            cur.execute("SELECT COUNT(*) as count, COALESCE(SUM(quantity_kg), 0) as total FROM stock")
            stock_stats = cur.fetchone()
            
            stats = {
                "intake_count": intake_stats["count"],
                "intake_total": intake_stats["total"],
                "vendor_count": vendor_stats["count"],
                "stock_count": stock_stats["count"],
                "stock_total": stock_stats["total"]
            }
        return render_template("dashboard.html", stats=stats)
    except Exception as e:
        print(f"Dashboard error: {e}")
        return render_template("dashboard.html", stats={})

@app.route("/weighbridge_dashboard")
@login_required
def weighbridge_dashboard():
    """Simplified dashboard for weighbridge operators - only intake access"""
    return render_template("weighbridge_dashboard.html")

@app.route("/api/weighbridge")
@login_required
def api_weighbridge():
    if WEIGHBRIDGE_AVAILABLE and weighbridge:
        return jsonify({"weight": weighbridge.get_weight(), "online": weighbridge.is_online(),
                       "timestamp": datetime.now().isoformat()})
    import random
    return jsonify({"weight": random.randint(0, 5000) if random.random() > 0.7 else 0,
                   "online": False, "timestamp": datetime.now().isoformat(), "demo_mode": True})


@app.route("/api/next-intake-number")
@login_required
def api_next_intake_number():
    """Get the next intake record number"""
    try:
        with get_db() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT MAX(id) as max_id FROM intake")
            result = cur.fetchone()
            next_number = (result['max_id'] or 0) + 1
            return jsonify({"next_number": next_number})
    except Exception as e:
        print(f"Unhandled error: {e}")
        return jsonify({"next_number": 1})

@app.route("/intake/history")
@login_required
def intake_history():
    try:
        with get_db() as conn:
            cur = conn.cursor(dictionary=True)
            # Join with vendors table using YOUR schema
            cur.execute("""SELECT i.*, v.name as vendor 
                        FROM intake i 
                        LEFT JOIN vendors v ON i.vendor_id = v.id 
                        ORDER BY i.captured_at DESC LIMIT 100""")
            records = cur.fetchall() or []
        return render_template("intake_history.html", records=records)
    except Exception as e:
        print(f"History error: {e}")
        return render_template("intake_history.html", records=[])

@app.route("/conditioning", methods=["GET", "POST"])
@login_required
@block_weighbridge_operator
def conditioning():
    if request.method == "POST":
        try:
            intake_id = request.form.get("intake_id") or None
            initial = request.form.get("initial_moisture")
            target = request.form.get("target_moisture")
            water = request.form.get("added_water")
            hours = request.form.get("tempering_hours")
            
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute("""INSERT INTO conditioning 
                            (intake_id, initial_moisture, target_moisture, added_water_liters, tempering_hours, captured_by, captured_at) 
                            VALUES (%s, %s, %s, %s, %s, %s, NOW())""",
                          (intake_id, initial, target, water, hours, session.get("user")))
                conn.commit()
            
            flash("Conditioning logged!", "success")
            return redirect("/conditioning/history")
        except Exception as e:
            print(f"Conditioning error: {e}")
            return render_template("conditioning.html", intakes=[], error="Error saving")
    
    try:
        with get_db() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM intake ORDER BY captured_at DESC LIMIT 50")
            intakes = cur.fetchall() or []
        return render_template("conditioning.html", intakes=intakes)
    except Exception as e:
        print(f"Unhandled error: {e}")
        return render_template("conditioning.html", intakes=[])

@app.route("/conditioning/history")
@login_required
@block_weighbridge_operator
def conditioning_history():
    try:
        with get_db() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("""SELECT * FROM conditioning 
                        ORDER BY captured_at DESC LIMIT 100""")
            records = cur.fetchall() or []
        return render_template("conditioning_history.html", records=records)
    except Exception as e:
        print(f"Unhandled error: {e}")
        return render_template("conditioning_history.html", records=[])

@app.route("/vendors", methods=["GET", "POST"])
@login_required
@block_weighbridge_operator
def vendors():
    if request.method == "POST":
        try:
            name = request.form.get("name")
            phone = request.form.get("phone", "")
            notes = request.form.get("notes", "")
            
            with get_db() as conn:
                cur = conn.cursor()
                cur.execute("INSERT INTO vendors (name, phone, notes) VALUES (%s, %s, %s)", 
                          (name, phone, notes))
                conn.commit()
            flash("Vendor added!", "success")
        except Exception as e:
            flash("Error adding vendor", "danger")
    
    try:
        with get_db() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM vendors ORDER BY name")
            vendors = cur.fetchall() or []
        return render_template("vendors.html", vendors=vendors)
    except Exception as e:
        print(f"Unhandled error: {e}")
        return render_template("vendors.html", vendors=[])

@app.route("/reports")
@login_required
@block_weighbridge_operator
def reports():
    return render_template("reports.html")

@app.route("/admin")
@login_required
@block_weighbridge_operator
@admin_required
def admin():
    try:
        with get_db() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id, username, role FROM users ORDER BY id")
            users = cur.fetchall() or []
        return render_template("admin.html", users=users)
    except Exception as e:
        print(f"Unhandled error: {e}")
        return render_template("admin.html", users=[])

@app.route("/admin/vendors")
@login_required
@block_weighbridge_operator
@admin_required
def admin_vendors():
    try:
        with get_db() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM vendors ORDER BY name")
            vendors = cur.fetchall() or []
        return render_template("admin_vendors.html", vendors=vendors)
    except Exception as e:
        print(f"Unhandled error: {e}")
        return render_template("admin_vendors.html", vendors=[])

@app.route("/admin/stock", methods=["GET", "POST"])
@login_required
@block_weighbridge_operator
@admin_required
def admin_stock():
    if request.method == "POST":
        try:
            stock_id = request.form.get("id")
            qty = request.form.get("quantity")
            
            with get_db() as conn:
                cur = conn.cursor()
                # YOUR schema uses quantity_kg
                cur.execute("UPDATE stock SET quantity_kg = %s WHERE id = %s", (qty, stock_id))
                conn.commit()
            flash("Stock updated!", "success")
        except Exception as e:
            print(f"Unhandled error: {e}")
            flash("Error updating stock", "danger")
    
    try:
        with get_db() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id, product, quantity_kg as quantity FROM stock")
            stock = cur.fetchall() or []
        return render_template("admin_stock.html", stock=stock)
    except Exception as e:
        print(f"Unhandled error: {e}")
        return render_template("admin_stock.html", stock=[])


# ============================================================================
# ACCOUNTING SYSTEM - TOLL MILLING
# ============================================================================

@app.route("/accounting")
@login_required
@block_weighbridge_operator
def accounting():
    """Accounting dashboard page"""
    return render_template("accounting.html")

@app.route("/api/accounting/summary")
@login_required
def api_accounting_summary():
    """Get accounting summary for dashboard cards"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT COALESCE(SUM(net_weight), 0) / 1000 as milled_today
                FROM intake WHERE DATE(captured_at) = CURDATE()
            """)
            milled_today = cursor.fetchone()['milled_today']
            
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_revenue
                FROM accounting_revenue
                WHERE YEAR(date) = YEAR(CURDATE()) AND MONTH(date) = MONTH(CURDATE())
            """)
            revenue = cursor.fetchone()['total_revenue']
            
            cursor.execute("""
                SELECT COALESCE(SUM(amount), 0) as total_expenses
                FROM accounting_expenses
                WHERE YEAR(date) = YEAR(CURDATE()) AND MONTH(date) = MONTH(CURDATE())
            """)
            expenses = cursor.fetchone()['total_expenses']
            
            return jsonify({
                'milled_today': float(milled_today),
                'revenue': float(revenue),
                'expenses': float(expenses),
                'profit': float(revenue - expenses)
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/accounting/rates", methods=["GET", "POST"])
@login_required
def api_accounting_rates():
    """Get or update accounting rates"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            
            if request.method == "POST":
                data = request.get_json()
                rates = [
                    ('milling_fee', data.get('milling_fee')),
                    ('bran_share_percent', data.get('bran_share')),
                    ('bran_price_per_ton', data.get('bran_price')),
                    ('weighbridge_fee', data.get('weighbridge_fee'))
                ]
                
                for key, value in rates:
                    if value is not None:
                        cursor.execute("""
                            UPDATE accounting_config
                            SET config_value = %s, updated_by = %s, updated_at = NOW()
                            WHERE config_key = %s
                        """, (value, session.get('username'), key))
                
                conn.commit()
                return jsonify({'success': True})
            else:
                cursor.execute("SELECT config_key, config_value FROM accounting_config")
                rates = {row['config_key']: float(row['config_value']) for row in cursor.fetchall()}
                return jsonify(rates)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/accounting/revenue", methods=["GET", "POST"])
@login_required
def api_accounting_revenue():
    """Get revenue breakdown (GET) or add other revenue (POST)"""
    if request.method == "POST":
        # Add other revenue
        try:
            data = request.get_json()
            print(f"DEBUG POST: Received data: {data}")  # DEBUG
            
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO accounting_revenue 
                    (date, source_type, description, amount, notes, created_by)
                    VALUES (%s, 'other', %s, %s, %s, %s)
                """, (data['date'], data['description'], data['amount'],
                      data.get('notes', ''), session.get('username')))
                conn.commit()
                print(f"DEBUG POST: Successfully inserted revenue")  # DEBUG
                return jsonify({'success': True})
        except Exception as e:
            print(f"ERROR POST: {e}")  # DEBUG
            import traceback
            traceback.print_exc()
            return jsonify({'error': str(e)}), 500
 
    # GET - revenue breakdown
    # GET - revenue breakdown (individual entries, not grouped)
    try:
        start_date = request.args.get('start', datetime.now().strftime('%Y-%m-01'))
        end_date = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))
        
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            
            # Get individual revenue entries
            cursor.execute("""
                SELECT 
                    id,
                    date,
                    source_type,
                    description,
                    amount,
                    notes,
                    created_by,
                    created_at
                FROM accounting_revenue
                WHERE date BETWEEN %s AND %s
                ORDER BY date DESC, created_at DESC
            """, (start_date, end_date))
            
            revenue_data = cursor.fetchall()
            total = sum(float(r['amount']) for r in revenue_data if r['amount'])
            
            # Build individual sources list
            sources = []
            for row in revenue_data:
                amount = float(row['amount']) if row['amount'] else 0
                sources.append({
                    'id': row['id'],
                    'date': row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date']),
                    'name': row['description'] or row['source_type'],
                    'quantity': 1,
                    'rate': 'N/A',
                    'amount': amount,
                    'percentage': f"{(amount / total * 100):.1f}" if total > 0 else "0.0"
                })
            
            return jsonify({'sources': sources})
            
    except Exception as e:
        print(f"Error in revenue GET: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'sources': []}), 500

@app.route("/api/accounting/revenue/<int:revenue_id>", methods=["DELETE"])
@login_required
def delete_revenue(revenue_id):
    """Delete a revenue entry"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM accounting_revenue WHERE id = %s", (revenue_id,))
            conn.commit()
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/accounting/expenses", methods=["GET", "POST"])
@login_required
def api_accounting_expenses():
    """Get expenses (GET) or add expense (POST)"""
    if request.method == "POST":
        try:
            data = request.get_json()
            with get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO accounting_expenses 
                    (date, category, description, amount, notes, created_by)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (data['date'], data['category'], data['description'],
                      data['amount'], data.get('notes', ''), session.get('username')))
                conn.commit()
                return jsonify({'success': True})
        except Exception as e:
            return jsonify({'error': str(e)}), 500

    # GET - expenses list
    try:
        start_date = request.args.get('start', datetime.now().strftime('%Y-%m-01'))
        end_date = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))
        category = request.args.get('category', '')
        
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            query = """
                SELECT id, date, category, description, amount, notes
                FROM accounting_expenses WHERE date BETWEEN %s AND %s
            """
            params = [start_date, end_date]
            if category:
                query += " AND category = %s"
                params.append(category)
            query += " ORDER BY date DESC"
            
            cursor.execute(query, params)
            expenses = cursor.fetchall()
            
            for expense in expenses:
                expense['date'] = expense['date'].strftime('%Y-%m-%d')
                expense['amount'] = float(expense['amount'])
            
            return jsonify({'expenses': expenses})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/accounting/expenses/<int:expense_id>", methods=["DELETE"])
@login_required
def api_delete_expense(expense_id):
    """Delete expense"""
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM accounting_expenses WHERE id = %s", (expense_id,))
            conn.commit()
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/accounting/charts/revenue")
@login_required
def api_charts_revenue():
    """Get revenue chart data"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT source_type, SUM(amount) as total
                FROM accounting_revenue
                WHERE YEAR(date) = YEAR(CURDATE()) AND MONTH(date) = MONTH(CURDATE())
                GROUP BY source_type
            """)
            data = cursor.fetchall()
            
            source_names = {
                'milling': 'Milling Fee' if session.get('lang') != 'ar' else 'رسوم الطحن',
                'bran': 'Coarse Bran' if session.get('lang') != 'ar' else 'النخالة الخشنة',
                'weighbridge': 'Weighbridge' if session.get('lang') != 'ar' else 'الميزان',
                'other': 'Other' if session.get('lang') != 'ar' else 'أخرى'
            }
            
            labels = [source_names.get(row['source_type'], row['source_type']) for row in data]
            values = [float(row['total']) for row in data]
            return jsonify({'labels': labels, 'values': values})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/accounting/charts/expenses")
@login_required
def api_charts_expenses():
    """Get expense chart data"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT category, SUM(amount) as total
                FROM accounting_expenses
                WHERE YEAR(date) = YEAR(CURDATE()) AND MONTH(date) = MONTH(CURDATE())
                GROUP BY category
            """)
            data = cursor.fetchall()
            
            category_names = {
                'labor': 'Labor' if session.get('lang') != 'ar' else 'العمالة',
                'transport': 'Transport' if session.get('lang') != 'ar' else 'النقل',
                'bags': 'Bags' if session.get('lang') != 'ar' else 'الأكياس',
                'electricity': 'Electricity' if session.get('lang') != 'ar' else 'الكهرباء',
                'water': 'Water' if session.get('lang') != 'ar' else 'المياه',
                'maintenance': 'Maintenance' if session.get('lang') != 'ar' else 'الصيانة'
            }
            
            labels = [category_names.get(row['category'], row['category']) for row in data]
            values = [float(row['total']) for row in data]
            return jsonify({'labels': labels, 'values': values})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/accounting/charts/trend")
@login_required
def api_charts_trend():
    """Get monthly trend chart data"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT date,
                       SUM(CASE WHEN table_type = 'revenue' THEN amount ELSE 0 END) as revenue,
                       SUM(CASE WHEN table_type = 'expense' THEN amount ELSE 0 END) as expenses
                FROM (
                    SELECT date, amount, 'revenue' as table_type FROM accounting_revenue
                    UNION ALL
                    SELECT date, amount, 'expense' as table_type FROM accounting_expenses
                ) combined
                WHERE date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
                GROUP BY date
                ORDER BY date
            """)
            data = cursor.fetchall()
            
            # Group by month in Python
            from collections import defaultdict
            monthly = defaultdict(lambda: {'revenue': 0, 'expenses': 0})
            
            for row in data:
                month = row['date'].strftime('%Y-%m')
                monthly[month]['revenue'] += float(row['revenue'])
                monthly[month]['expenses'] += float(row['expenses'])
            
            # Sort by month
            sorted_months = sorted(monthly.keys())
            
            return jsonify({
                'months': sorted_months,
                'revenue': [monthly[m]['revenue'] for m in sorted_months],
                'expenses': [monthly[m]['expenses'] for m in sorted_months]
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/maintenance")
@login_required
@block_weighbridge_operator
def maintenance():
    """Maintenance management page"""
    return render_template("maintenance.html")


@app.route("/api/maintenance/alerts")
@login_required
def api_maintenance_alerts():
    """Get alert counts for dashboard"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            
            # Overdue tasks
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM maintenance_schedule ms
                JOIN equipment e ON ms.equipment_id = e.id
                WHERE ms.is_active = TRUE
                  AND e.status = 'active'
                  AND ms.next_due_date < CURDATE()
            """)
            overdue = cursor.fetchone()['count']
            
            # Due soon (next 7 days)
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM maintenance_schedule ms
                JOIN equipment e ON ms.equipment_id = e.id
                WHERE ms.is_active = TRUE
                  AND e.status = 'active'
                  AND ms.next_due_date >= CURDATE()
                  AND ms.next_due_date <= DATE_ADD(CURDATE(), INTERVAL 7 DAY)
            """)
            due_soon = cursor.fetchone()['count']
            
            # Upcoming (next 30 days)
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM maintenance_schedule ms
                JOIN equipment e ON ms.equipment_id = e.id
                WHERE ms.is_active = TRUE
                  AND e.status = 'active'
                  AND ms.next_due_date > DATE_ADD(CURDATE(), INTERVAL 7 DAY)
                  AND ms.next_due_date <= DATE_ADD(CURDATE(), INTERVAL 30 DAY)
            """)
            upcoming = cursor.fetchone()['count']
            
            # Low stock parts
            cursor.execute("""
                SELECT COUNT(*) as count
                FROM spare_parts
                WHERE quantity_in_stock <= minimum_stock_level
            """)
            low_stock = cursor.fetchone()['count']
            
            return jsonify({
                'overdue': overdue,
                'due_soon': due_soon,
                'upcoming': upcoming,
                'low_stock': low_stock
            })
    
    except Exception as e:
        print(f"Error getting maintenance alerts: {e}")
        return jsonify({'error': str(e)}), 500


@app.route("/api/maintenance/schedule")
@login_required
def api_maintenance_schedule():
    """Get maintenance schedule"""
    try:
        equipment_type = request.args.get('type', '')
        priority = request.args.get('priority', '')
        status = request.args.get('status', '')
        
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT 
                    ms.id,
                    ms.task_name,
                    ms.task_description,
                    ms.frequency_type,
                    ms.frequency_value,
                    ms.next_due_date,
                    ms.priority,
                    ms.estimated_duration_minutes,
                    e.equipment_code,
                    e.equipment_name,
                    e.equipment_type,
                    DATEDIFF(ms.next_due_date, CURDATE()) as days_until_due
                FROM maintenance_schedule ms
                JOIN equipment e ON ms.equipment_id = e.id
                WHERE ms.is_active = TRUE
                  AND e.status = 'active'
            """
            
            params = []
            
            if equipment_type:
                query += " AND e.equipment_type = %s"
                params.append(equipment_type)
            
            if priority:
                query += " AND ms.priority = %s"
                params.append(priority)
            
            if status == 'overdue':
                query += " AND ms.next_due_date < CURDATE()"
            elif status == 'due_soon':
                query += " AND ms.next_due_date >= CURDATE() AND ms.next_due_date <= DATE_ADD(CURDATE(), INTERVAL 7 DAY)"
            elif status == 'upcoming':
                query += " AND ms.next_due_date > DATE_ADD(CURDATE(), INTERVAL 7 DAY) AND ms.next_due_date <= DATE_ADD(CURDATE(), INTERVAL 30 DAY)"
            
            query += " ORDER BY ms.next_due_date ASC"
            
            cursor.execute(query, params)
            schedule = cursor.fetchall()
            
            # Format dates
            for item in schedule:
                if item['next_due_date']:
                    item['next_due_date'] = item['next_due_date'].strftime('%Y-%m-%d')
            
            return jsonify({'schedule': schedule})
    
    except Exception as e:
        print(f"Error getting maintenance schedule: {e}")
        return jsonify({'error': str(e)}), 500


@app.route("/api/maintenance/history")
@login_required
def api_maintenance_history():
    """Get maintenance logs"""
    try:
        start_date = request.args.get('start', datetime.now().strftime('%Y-%m-01'))
        end_date = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))
        log_type = request.args.get('type', '')
        
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            
            query = """
                SELECT 
                    ml.id,
                    ml.log_type,
                    ml.performed_date,
                    ml.performed_time,
                    ml.performed_by,
                    ml.task_description,
                    ml.parts_used,
                    ml.total_cost,
                    ml.downtime_minutes,
                    ml.status,
                    e.equipment_code,
                    e.equipment_name
                FROM maintenance_logs ml
                JOIN equipment e ON ml.equipment_id = e.id
                WHERE ml.performed_date BETWEEN %s AND %s
            """
            
            params = [start_date, end_date]
            
            if log_type:
                query += " AND ml.log_type = %s"
                params.append(log_type)
            
            query += " ORDER BY ml.performed_date DESC"
            
            cursor.execute(query, params)
            logs = cursor.fetchall()
            
            # Format dates
            for log in logs:
                log['performed_date'] = log['performed_date'].strftime('%Y-%m-%d')
                if log['performed_time']:
                    log['performed_time'] = str(log['performed_time'])
            
            return jsonify({'logs': logs})
    
    except Exception as e:
        print(f"Error getting maintenance history: {e}")
        return jsonify({'error': str(e)}), 500


@app.route("/api/maintenance/log", methods=["POST"])
@login_required
def api_add_maintenance_log():
    """Add new maintenance log"""
    try:
        data = request.get_json()
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO maintenance_logs 
                (equipment_id, log_type, performed_date, performed_by, 
                 task_description, parts_used, parts_cost, labor_hours, 
                 labor_cost, downtime_minutes, notes, created_by)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                data['equipment_id'],
                data['log_type'],
                data['performed_date'],
                data['performed_by'],
                data['task_description'],
                data.get('parts_used', ''),
                data.get('parts_cost', 0),
                data.get('labor_hours', 0),
                data.get('labor_cost', 0),
                data.get('downtime_minutes', 0),
                data.get('notes', ''),
                session.get('username')
            ))
            
            conn.commit()
            return jsonify({'success': True, 'id': cursor.lastrowid})
    
    except Exception as e:
        print(f"Error adding maintenance log: {e}")
        return jsonify({'error': str(e)}), 500


@app.route("/api/maintenance/equipment")
@login_required
def api_maintenance_equipment():
    """Get equipment list"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT 
                    id,
                    equipment_code,
                    equipment_name,
                    equipment_type,
                    location,
                    manufacturer,
                    model_number,
                    status,
                    installation_date
                FROM equipment
                ORDER BY equipment_code
            """)
            
            equipment = cursor.fetchall()
            
            # Format dates
            for eq in equipment:
                if eq['installation_date']:
                    eq['installation_date'] = eq['installation_date'].strftime('%Y-%m-%d')
            
            return jsonify({'equipment': equipment})
    
    except Exception as e:
        print(f"Error getting equipment: {e}")
        return jsonify({'error': str(e)}), 500


@app.route("/api/maintenance/parts")
@login_required
def api_maintenance_parts():
    """Get spare parts inventory"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT 
                    id,
                    part_code,
                    part_name,
                    part_category,
                    quantity_in_stock,
                    minimum_stock_level,
                    unit_cost,
                    supplier_name,
                    supplier_contact
                FROM spare_parts
                ORDER BY part_code
            """)
            
            parts = cursor.fetchall()
            
            return jsonify({'parts': parts})
    
    except Exception as e:
        print(f"Error getting spare parts: {e}")
        return jsonify({'error': str(e)}), 500


@app.route("/api/maintenance/parts/<int:part_id>/adjust", methods=["POST"])
@login_required
def api_adjust_part_stock(part_id):
    """Adjust spare part stock quantity"""
    try:
        data = request.get_json()
        adjustment = data.get('adjustment', 0)
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE spare_parts
                SET quantity_in_stock = quantity_in_stock + %s,
                    updated_at = NOW()
                WHERE id = %s
            """, (adjustment, part_id))
            
            conn.commit()
            return jsonify({'success': True})
    
    except Exception as e:
        print(f"Error adjusting stock: {e}")
        return jsonify({'error': str(e)}), 500


@app.route("/api/maintenance/equipment/<int:equipment_id>/details")
@login_required
def api_equipment_details(equipment_id):
    """Get detailed equipment information with maintenance history"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            
            # Equipment details
            cursor.execute("""
                SELECT * FROM equipment WHERE id = %s
            """, (equipment_id,))
            equipment = cursor.fetchone()
            
            # Recent maintenance
            cursor.execute("""
                SELECT * FROM maintenance_logs
                WHERE equipment_id = %s
                ORDER BY performed_date DESC
                LIMIT 10
            """, (equipment_id,))
            recent_maintenance = cursor.fetchall()
            
            # Upcoming schedule
            cursor.execute("""
                SELECT * FROM maintenance_schedule
                WHERE equipment_id = %s AND is_active = TRUE
                ORDER BY next_due_date
            """, (equipment_id,))
            upcoming_schedule = cursor.fetchall()
            
            # Total cost this year
            cursor.execute("""
                SELECT COALESCE(SUM(total_cost), 0) as total_cost
                FROM maintenance_logs
                WHERE equipment_id = %s
                  AND YEAR(performed_date) = YEAR(CURDATE())
            """, (equipment_id,))
            yearly_cost = cursor.fetchone()['total_cost']
            
            return jsonify({
                'equipment': equipment,
                'recent_maintenance': recent_maintenance,
                'upcoming_schedule': upcoming_schedule,
                'yearly_cost': float(yearly_cost)
            })
    
    except Exception as e:
        print(f"Error getting equipment details: {e}")
        return jsonify({'error': str(e)}), 500


@app.route("/api/maintenance/reports/summary")
@login_required
def api_maintenance_summary_report():
    """Generate maintenance summary report"""
    try:
        start_date = request.args.get('start', datetime.now().strftime('%Y-%m-01'))
        end_date = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))
        
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            
            # Total maintenance count
            cursor.execute("""
                SELECT COUNT(*) as total_count
                FROM maintenance_logs
                WHERE performed_date BETWEEN %s AND %s
            """, (start_date, end_date))
            total_count = cursor.fetchone()['total_count']
            
            # Total cost
            cursor.execute("""
                SELECT COALESCE(SUM(total_cost), 0) as total_cost
                FROM maintenance_logs
                WHERE performed_date BETWEEN %s AND %s
            """, (start_date, end_date))
            total_cost = cursor.fetchone()['total_cost']
            
            # Total downtime
            cursor.execute("""
                SELECT COALESCE(SUM(downtime_minutes), 0) as total_downtime
                FROM maintenance_logs
                WHERE performed_date BETWEEN %s AND %s
            """, (start_date, end_date))
            total_downtime = cursor.fetchone()['total_downtime']
            
            # By type
            cursor.execute("""
                SELECT 
                    log_type,
                    COUNT(*) as count,
                    SUM(total_cost) as cost
                FROM maintenance_logs
                WHERE performed_date BETWEEN %s AND %s
                GROUP BY log_type
            """, (start_date, end_date))
            by_type = cursor.fetchall()
            
            # Top equipment by cost
            cursor.execute("""
                SELECT 
                    e.equipment_name,
                    COUNT(ml.id) as maintenance_count,
                    SUM(ml.total_cost) as total_cost
                FROM maintenance_logs ml
                JOIN equipment e ON ml.equipment_id = e.id
                WHERE ml.performed_date BETWEEN %s AND %s
                GROUP BY e.id, e.equipment_name
                ORDER BY total_cost DESC
                LIMIT 5
            """, (start_date, end_date))
            top_equipment = cursor.fetchall()
            
            return jsonify({
                'summary': {
                    'total_count': total_count,
                    'total_cost': float(total_cost),
                    'total_downtime': total_downtime
                },
                'by_type': by_type,
                'top_equipment': top_equipment
            })
    
    except Exception as e:
        print(f"Error generating report: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/api/accounting/charts/profit")
@login_required
def api_charts_profit():
    """Get profit chart data"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT date,
                       SUM(CASE WHEN table_type = 'revenue' THEN amount ELSE -amount END) as profit
                FROM (
                    SELECT date, amount, 'revenue' as table_type FROM accounting_revenue
                    UNION ALL
                    SELECT date, amount, 'expense' as table_type FROM accounting_expenses
                ) combined
                WHERE date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
                GROUP BY date
                ORDER BY date
            """)
            data = cursor.fetchall()
            
            # Group by month in Python
            from collections import defaultdict
            monthly = defaultdict(float)
            
            for row in data:
                month = row['date'].strftime('%Y-%m')
                monthly[month] += float(row['profit'])
            
            # Sort by month
            sorted_months = sorted(monthly.keys())
            
            return jsonify({
                'months': sorted_months,
                'profit': [monthly[m] for m in sorted_months]
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/accounting/export/excel")
@login_required
def api_export_excel():
    """Export accounting data to Excel"""
    return jsonify({'message': 'Excel export coming soon!'})


# ============================================================================
# STOCK MANAGEMENT SYSTEM
# ============================================================================

@app.route("/stock")
@login_required
@block_weighbridge_operator
def stock():
    """Stock management page"""
    return render_template("stock.html")

@app.route("/api/stock/summary")
@login_required
def api_stock_summary():
    """Get stock summary for dashboard cards"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT COALESCE(SUM(quantity), 0) as total FROM stock_products WHERE category = 'flour'")
            total_flour = cursor.fetchone()['total']
            cursor.execute("SELECT COALESCE(SUM(quantity), 0) as total FROM stock_products WHERE category = 'bran'")
            total_bran = cursor.fetchone()['total']
            cursor.execute("SELECT COALESCE(SUM(quantity), 0) as total FROM stock_products WHERE category = 'bags'")
            total_bags = cursor.fetchone()['total']
            cursor.execute("SELECT COUNT(*) as count FROM stock_products WHERE quantity < min_level")
            low_stock_count = cursor.fetchone()['count']
            return jsonify({'total_flour': float(total_flour), 'total_bran': float(total_bran), 'total_bags': float(total_bags), 'low_stock_count': low_stock_count})
    except Exception as e:
        print(f"Error getting stock summary: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/api/stock")
@login_required
def api_stock():
    """Get stock products"""
    try:
        product_type = request.args.get('type', '')
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            query = "SELECT id, product_code, product_name, category, unit, quantity, min_level, max_level, unit_cost, location FROM stock_products WHERE 1=1"
            params = []
            if product_type:
                query += " AND category = %s"
                params.append(product_type)
            query += " ORDER BY product_code"
            cursor.execute(query, params)
            products = cursor.fetchall()
            return jsonify({'products': products})
    except Exception as e:
        print(f"Error getting stock: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/api/stock/movements")
@login_required
def api_stock_movements():
    """Get stock movements history"""
    try:
        start_date = request.args.get('start', datetime.now().strftime('%Y-%m-01'))
        end_date = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))
        movement_type = request.args.get('type', '')
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            query = """SELECT sm.id, sm.movement_type, sm.quantity, sm.balance_before, sm.balance_after,
                       sm.movement_date, sm.movement_time, sm.notes, sm.created_by,
                       sp.product_code, sp.product_name, sp.unit
                       FROM stock_movements sm JOIN stock_products sp ON sm.product_id = sp.id
                       WHERE sm.movement_date BETWEEN %s AND %s"""
            params = [start_date, end_date]
            if movement_type:
                query += " AND sm.movement_type = %s"
                params.append(movement_type)
            query += " ORDER BY sm.movement_date DESC, sm.id DESC"
            cursor.execute(query, params)
            movements = cursor.fetchall()
            for move in movements:
                move['movement_date'] = move['movement_date'].strftime('%Y-%m-%d')
                if move['movement_time']:
                    move['movement_time'] = str(move['movement_time'])
            return jsonify({'movements': movements})
    except Exception as e:
        print(f"Error getting stock movements: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/api/stock/alerts")
@login_required
def api_stock_alerts():
    """Get low stock alerts"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""SELECT id, product_code, product_name, category, quantity, unit, min_level,
                           (min_level - quantity) as deficit FROM stock_products
                           WHERE quantity < min_level ORDER BY (min_level - quantity) DESC""")
            alerts = cursor.fetchall()
            return jsonify({'alerts': alerts})
    except Exception as e:
        print(f"Error getting stock alerts: {e}")
        return jsonify({'error': str(e)}), 500

@app.route("/api/stock/adjust", methods=["POST"])
@login_required
def api_stock_adjust():
    """Adjust stock quantity"""
    try:
        data = request.get_json()
        product_id = int(data['product_id'])
        movement_type = data['movement_type']
        quantity = float(data['quantity'])
        notes = data.get('notes', '')
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("SELECT quantity FROM stock_products WHERE id = %s", (product_id,))
            result = cursor.fetchone()
            if not result:
                return jsonify({'error': 'Product not found'}), 404
            balance_before = float(result['quantity'])
            if movement_type == 'in':
                balance_after = balance_before + quantity
            elif movement_type == 'out':
                balance_after = balance_before - quantity
                if balance_after < 0:
                    return jsonify({'error': 'Insufficient stock'}), 400
            else:
                balance_after = quantity
            cursor.execute("""INSERT INTO stock_movements (product_id, movement_type, quantity, balance_before, balance_after,
                           movement_date, movement_time, notes, created_by)
                           VALUES (%s, %s, %s, %s, %s, CURDATE(), CURTIME(), %s, %s)""",
                           (product_id, movement_type, quantity, balance_before, balance_after, notes, session.get('username')))
            cursor.execute("UPDATE stock_products SET quantity = %s WHERE id = %s", (balance_after, product_id))
            conn.commit()
            return jsonify({'success': True, 'new_balance': balance_after})
    except Exception as e:
        print(f"Error adjusting stock: {e}")
        return jsonify({'error': str(e)}), 500

# ============================================================================
# BX-3 PACKING SCALE ROUTES
# ============================================================================

@app.route("/api/intake/today")
@login_required
def api_intake_today():
    """Get today's intake summary"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT 
                    COUNT(*) as truck_count,
                    SUM(net_weight) as total_weight
                FROM intake
                WHERE DATE(captured_at) = CURDATE()
            """)
            result = cursor.fetchone()
            
            return jsonify({
                'truck_count': result['truck_count'] or 0,
                'total_weight': float(result['total_weight'] or 0)
            })
    except Exception as e:
        print(f"Error getting intake summary: {e}")
        return jsonify({'truck_count': 0, 'total_weight': 0})

@app.route("/api/intake/last")
@login_required
def api_intake_last():
    """Get last truck info"""
    try:
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT truck_number, net_weight
                FROM wheat_intake
                ORDER BY date DESC, id DESC
                LIMIT 1
            """)
            result = cursor.fetchone()
            
            if result:
                return jsonify({
                    'truck_number': result['truck_number'],
                    'weight': float(result['net_weight'] or 0)
                })
            return jsonify({'truck_number': None, 'weight': 0})
    except Exception as e:
        print(f"Error getting last truck: {e}")
        return jsonify({'truck_number': None, 'weight': 0})

@app.route("/api/packing/status")
@login_required
def api_packing_status():
    """Get status from all 3 machines"""
    try:
        if not packing_manager:
            return jsonify({'error': 'Packing system not available'}), 503
        
        # Get status from all machines
        all_status = packing_manager.get_all_status()
        all_stats = packing_manager.get_all_stats()
        
        # Combine status and stats for each machine
        response = {}
        for machine_id in ['bran_40kg', 'flour_50kg_bxf3', 'flour_50kg_bx30']:
            status = all_status.get(machine_id, {})
            stats = all_stats.get(machine_id, {})
            
            response[machine_id] = {
                'online': status.get('online', False),
                'current_weight': status.get('current_weight', 0.0),
                'state': status.get('state', 'OFFLINE'),
                'bag_count': status.get('bag_count', 0),
                'last_bag_weight': status.get('last_bag_weight', 0.0),
                'total_weight': stats.get('total_weight', 0.0),
                'average_weight': stats.get('average_weight', 0.0),
                'name': status.get('name', machine_id),
                'port': status.get('port', 'Unknown'),
                'bag_size': status.get('bag_size', 0),
                'product': status.get('product', 'Unknown'),
                'detected_format': status.get('detected_format', None)
            }
        
        return jsonify(response)
    
    except Exception as e:
        print(f"Error getting packing status: {e}")
        return jsonify({'error': str(e)}), 500


@app.route("/api/packing/stats")
@login_required
def api_packing_stats():
    """Get production statistics"""
    try:
        if not bx3_scale:
            return jsonify({
                'total_bags': 0,
                'total_weight': 0.0,
                'average_weight': 0.0,
                'min_weight': 0.0,
                'max_weight': 0.0
            })
        
        stats = bx3_scale.get_session_stats()
        return jsonify(stats)
    
    except Exception as e:
        print(f"Error getting packing stats: {e}")
        return jsonify({'error': str(e)}), 500


@app.route("/api/packing/recent")
@login_required
def api_packing_recent():
    """Get recent bags from specific machine or all"""
    try:
        if not packing_manager:
            return jsonify({'bags': []})
        
        machine_id = request.args.get('machine', None)
        count = request.args.get('count', 10, type=int)
        
        if machine_id:
            # Get bags from specific machine
            recent = packing_manager.get_recent_bags(machine_id, count)
            bags = [{
                'bag_number': bag['bag_number'],
                'weight': bag['weight'],
                'timestamp': bag['timestamp'].strftime('%H:%M:%S'),
                'machine': machine_id
            } for bag in recent]
        else:
            # Get bags from all machines, combined and sorted
            all_bags = []
            for mid in ['bran_40kg', 'flour_50kg_bxf3', 'flour_50kg_bx30']:
                recent = packing_manager.get_recent_bags(mid, count)
                for bag in recent:
                    all_bags.append({
                        'bag_number': bag['bag_number'],
                        'weight': bag['weight'],
                        'timestamp': bag['timestamp'].strftime('%H:%M:%S'),
                        'time_obj': bag['timestamp'],
                        'machine': mid
                    })
            
            # Sort by timestamp
            all_bags.sort(key=lambda x: x['time_obj'], reverse=True)
            all_bags = all_bags[:count]
            
            # Remove time_obj (was only for sorting)
            bags = [{k: v for k, v in bag.items() if k != 'time_obj'} for bag in all_bags]
        
        return jsonify({'bags': bags})
    
    except Exception as e:
        print(f"Error getting recent bags: {e}")
        return jsonify({'error': str(e)}), 500


@app.route("/api/packing/reset", methods=["POST"])
@login_required
def api_packing_reset():
    """Reset session counters for specific machine or all"""
    try:
        if not packing_manager:
            return jsonify({'error': 'Packing system not available'}), 503
        
        data = request.get_json() or {}
        machine_id = data.get('machine', None)
        
        if machine_id:
            # Reset specific machine
            if packing_manager.reset_machine(machine_id):
                return jsonify({'success': True, 'message': f'{machine_id} reset'})
            else:
                return jsonify({'error': 'Machine not found'}), 404
        else:
            # Reset all machines
            packing_manager.reset_all()
            return jsonify({'success': True, 'message': 'All machines reset'})
    
    except Exception as e:
        print(f"Error resetting packing session: {e}")
        return jsonify({'error': str(e)}), 500


@app.route("/api/packing/record", methods=["POST"])
@login_required
def api_packing_record():
    """Record packing production to database"""
    try:
        if not bx3_scale:
            return jsonify({'error': 'BX-3 not available'}), 503
        
        data = request.get_json()
        stats = bx3_scale.get_session_stats()
        
        if stats['total_bags'] == 0:
            return jsonify({'error': 'No bags to record'}), 400
        
        with get_db() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO packing_production
                (production_date, product_type, bag_size, bag_count, 
                 total_weight, shift, operator, notes)
                VALUES (CURDATE(), %s, %s, %s, %s, %s, %s, %s)
            """, (
                data.get('product_type', 'Flour'),
                data.get('bag_size', 25),
                stats['total_bags'],
                stats['total_weight'],
                data.get('shift', 'Morning'),
                session.get('username'),
                data.get('notes', f"Auto-recorded from BX-3. Avg: {stats['average_weight']:.2f} kg")
            ))
            
            conn.commit()
        
        # Reset session after recording
        bx3_scale.reset_session()
        
        return jsonify({
            'success': True,
            'bags_recorded': stats['total_bags'],
            'total_weight': stats['total_weight']
        })
    
    except Exception as e:
        print(f"Error recording packing production: {e}")
        return jsonify({'error': str(e)}), 500

@app.errorhandler(404)
def not_found(e):
    return "404 - Page Not Found", 404

@app.errorhandler(500)
def internal_error(e):
    print(f"Error: {e}")
    return "500 - Internal Server Error", 500

# Note: BX-3 connection stays open for the lifetime of the app
# The background thread will keep monitoring continuously
# Connection closes automatically when app shuts down

# ============================================================================
# PACKING DATA API ENDPOINTS
# ============================================================================

@app.route("/api/packing/details/<date>")
@login_required
def api_packing_details(date):
    """
    Get detailed bag list for a specific date
    
    Args:
        date: YYYY-MM-DD
    
    Query params:
        machine_id: Optional machine filter
    """
    try:
        machine_id = request.args.get('machine_id')
        
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            
            if machine_id:
                cursor.execute("""
                    SELECT 
                        id,
                        machine_name,
                        bag_number,
                        weight_kg,
                        packed_at,
                        operator
                    FROM packing_data
                    WHERE machine_id = %s
                      AND packed_date = %s
                    ORDER BY bag_number
                """, (machine_id, date))
            else:
                cursor.execute("""
                    SELECT 
                        id,
                        machine_id,
                        machine_name,
                        bag_number,
                        weight_kg,
                        packed_at,
                        operator
                    FROM packing_data
                    WHERE packed_date = %s
                    ORDER BY machine_id, bag_number
                """, (date,))
            
            bags = cursor.fetchall()
            
            # Format results
            details = []
            for bag in bags:
                # Format time in Python instead of SQL
                time_str = ''
                if bag.get('packed_at'):
                    try:
                        time_str = bag['packed_at'].strftime('%H:%M:%S')
                    except:
                        time_str = str(bag['packed_at'])
                
                details.append({
                    'id': bag['id'],
                    'machine': bag['machine_name'],
                    'bag_number': bag['bag_number'],
                    'weight': float(bag['weight_kg']),
                    'time': time_str,
                    'operator': bag.get('operator', 'SYSTEM')
                })
            
            return jsonify({'date': date, 'bags': details})
    
    except Exception as e:
        print(f"Error in packing/details: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': str(e), 'bags': []}), 500


@app.route("/api/packing/history")
@login_required
def api_packing_history():
    """
    Get packing history for date range
    
    Query params:
        start: Start date (YYYY-MM-DD)
        end: End date (YYYY-MM-DD)
        machine_id: Optional machine filter
    """
    try:
        from datetime import datetime, timedelta
        
        # Get parameters
        start_date = request.args.get('start', (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d'))
        end_date = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))
        machine_id = request.args.get('machine_id')
        
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            
            if machine_id:
                # Specific machine
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
                # All machines
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
            
            # Format results
            history = []
            for row in results:
                history.append({
                    'date': row['packed_date'].strftime('%Y-%m-%d'),
                    'machine': row['machine_name'],
                    'bags': int(row['bag_count']),
                    'total_weight': float(row['total_weight']),
                    'avg_weight': float(row['avg_weight']),
                    'min_weight': float(row.get('min_weight', 0)) if row.get('min_weight') else None,
                    'max_weight': float(row.get('max_weight', 0)) if row.get('max_weight') else None
                })
            
            return jsonify({'history': history})
    
    except Exception as e:
        print(f"Error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route("/api/packing/stats/today")
@login_required
def api_packing_stats_today():
    """
    Get today's packing statistics for all machines
    """
    try:
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            
            cursor.execute("""
                SELECT 
                    machine_id,
                    machine_name,
                    COUNT(*) as bag_count,
                    SUM(weight_kg) as total_weight,
                    AVG(weight_kg) as avg_weight
                FROM packing_data
                WHERE packed_date = CURDATE()
                GROUP BY machine_id, machine_name
            """)
            
            results = cursor.fetchall()
            
            stats = {}
            for row in results:
                stats[row['machine_id']] = {
                    'name': row['machine_name'],
                    'bags': int(row['bag_count']),
                    'total_weight': float(row['total_weight']),
                    'avg_weight': float(row['avg_weight'])
                }
            
            return jsonify({'stats': stats})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "True") == "True"
    port = int(os.environ.get("PORT", 5000))
    print("=" * 60)
    print("Al Mohandes Modern Mills - Management System")
    print("=" * 60)
    print(f"Server: http://0.0.0.0:{port}")
    print(f"Debug: {debug_mode}")
    print(f"Weighbridge: {'Connected' if WEIGHBRIDGE_AVAILABLE else 'Demo Mode'}")
    
    # Show all packing machines status
    if packing_manager:
        all_status = packing_manager.get_all_status()
        online_machines = [s['name'] for s in all_status.values() if s.get('online', False)]
        if online_machines:
            print(f"Packing Machines: {', '.join(online_machines)}")
        else:
            print(f"Packing Machines: None online (Manual Entry Mode)")
    
    print("=" * 60)
    print("\n📝 Login: username='admin' password='admin123'\n")
    
    # CRITICAL: Disable reloader to prevent opening COM port twice
    # Flask's reloader starts the app twice, which causes PermissionError on COM10
    app.run(debug=debug_mode, host="0.0.0.0", port=port, use_reloader=False)
