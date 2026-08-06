from flask import Flask, render_template, request, redirect, session, url_for, jsonify, flash
import mysql.connector
from functools import wraps
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os
from contextlib import contextmanager

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "CHANGE_THIS_IN_PRODUCTION_" + os.urandom(24).hex())

# DATABASE CONFIG - Matches YOUR schema
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
try:
    from weighbridge import WeighbridgeReader
    import time
    
    port = os.environ.get("WEIGHBRIDGE_PORT", "COM10" if os.name == 'nt' else "/dev/ttyUSB0")
    baudrate = int(os.environ.get("WEIGHBRIDGE_BAUD", "2400"))
    
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

# PACKING SCALE INTEGRATION
try:
    from packing_scale import PackingScaleReader
    import time
    
    packing_port = os.environ.get("PACKING_PORT", "COM3" if os.name == 'nt' else "/dev/ttyUSB1")
    packing_baud = int(os.environ.get("PACKING_BAUD", "9600"))
    
    packing_scale = PackingScaleReader(port=packing_port, baudrate=packing_baud)
    
    # Wait for scale to initialize
    print(f"✅ Packing scale initialized on {packing_port} @ {packing_baud} baud")
    time.sleep(0.5)
    
    if packing_scale.is_online():
        print(f"   ✅ Packing scale ONLINE")
    else:
        print(f"   ⚠️  Packing scale offline (will work when data arrives)")
    
    PACKING_SCALE_AVAILABLE = True
except Exception as e:
    packing_scale = None
    PACKING_SCALE_AVAILABLE = False
    print(f"⚠️  Packing scale not available: {e}")

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
        "customer": "Customer", "invoice_number": "Invoice Number"
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
        "customer": "العميل", "invoice_number": "رقم الفاتورة"
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
            impurities_weight = int(request.form.get("impurities_weight", 51))
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
    """Get live packing scale data"""
    if PACKING_SCALE_AVAILABLE and packing_scale:
        data = packing_scale.get_data()
        data['timestamp'] = datetime.now().isoformat()
        return jsonify(data)
    
    # Demo mode
    import random
    return jsonify({
        "bag_weight": random.choice([25, 50]) if random.random() > 0.5 else 0,
        "bag_count": random.randint(0, 100) if random.random() > 0.5 else 0,
        "total_weight": 0,
        "online": False,
        "demo_mode": True,
        "timestamp": datetime.now().isoformat()
    })


# Packing page
@app.route("/packing")
@login_required
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
                        # Plain text comparison (insecure, but works with your SQL)
                        password_valid = (stored_password == pw)
                    
                    if password_valid:
                        session["user"] = row["username"]
                        session["role"] = row["role"]
                        session.permanent = True
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
    except:
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
    except:
        return render_template("conditioning.html", intakes=[])

@app.route("/conditioning/history")
@login_required
def conditioning_history():
    try:
        with get_db() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("""SELECT * FROM conditioning 
                        ORDER BY captured_at DESC LIMIT 100""")
            records = cur.fetchall() or []
        return render_template("conditioning_history.html", records=records)
    except:
        return render_template("conditioning_history.html", records=[])

@app.route("/vendors", methods=["GET", "POST"])
@login_required
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
    except:
        return render_template("vendors.html", vendors=[])


@app.route("/stock")
@login_required
def stock():
    try:
        with get_db() as conn:
            cur = conn.cursor(dictionary=True)
            # YOUR schema: product is ENUM, quantity_kg
            cur.execute("SELECT product, quantity_kg as qty FROM stock ORDER BY product")
            stock = cur.fetchall() or []
        return render_template("stock.html", stock=stock)
    except:
        return render_template("stock.html", stock=[])

@app.route("/reports")
@login_required
def reports():
    return render_template("reports.html")

@app.route("/admin")
@login_required
@admin_required
def admin():
    try:
        with get_db() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id, username, role FROM users ORDER BY id")
            users = cur.fetchall() or []
        return render_template("admin.html", users=users)
    except:
        return render_template("admin.html", users=[])

@app.route("/admin/vendors")
@login_required
@admin_required
def admin_vendors():
    try:
        with get_db() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT * FROM vendors ORDER BY name")
            vendors = cur.fetchall() or []
        return render_template("admin_vendors.html", vendors=vendors)
    except:
        return render_template("admin_vendors.html", vendors=[])

@app.route("/admin/stock", methods=["GET", "POST"])
@login_required
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
        except:
            flash("Error updating stock", "danger")
    
    try:
        with get_db() as conn:
            cur = conn.cursor(dictionary=True)
            cur.execute("SELECT id, product, quantity_kg as quantity FROM stock")
            stock = cur.fetchall() or []
        return render_template("admin_stock.html", stock=stock)
    except:
        return render_template("admin_stock.html", stock=[])


# ============================================================================
# ACCOUNTING SYSTEM - TOLL MILLING
# ============================================================================

@app.route("/accounting")
@login_required
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
                FROM intake WHERE DATE(created_at) = CURDATE()
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

@app.route("/api/accounting/revenue")
@login_required
def api_accounting_revenue():
    """Get revenue breakdown"""
    try:
        start_date = request.args.get('start', datetime.now().strftime('%Y-%m-01'))
        end_date = request.args.get('end', datetime.now().strftime('%Y-%m-%d'))
        
        with get_db() as conn:
            cursor = conn.cursor(dictionary=True)
            cursor.execute("""
                SELECT source_type, SUM(quantity) as total_quantity,
                       AVG(rate) as avg_rate, SUM(amount) as total_amount
                FROM accounting_revenue
                WHERE date BETWEEN %s AND %s
                GROUP BY source_type
            """, (start_date, end_date))
            
            revenue_data = cursor.fetchall()
            total = sum(r['total_amount'] for r in revenue_data)
            
            source_names = {
                'milling': 'Milling Fee Revenue' if session.get('lang') != 'ar' else 'إيرادات رسوم الطحن',
                'bran': 'Coarse Bran Revenue' if session.get('lang') != 'ar' else 'إيرادات النخالة الخشنة',
                'weighbridge': 'Weighbridge Revenue' if session.get('lang') != 'ar' else 'إيرادات الميزان',
                'other': 'Other Revenue' if session.get('lang') != 'ar' else 'إيرادات أخرى'
            }
            
            sources = []
            for row in revenue_data:
                sources.append({
                    'name': source_names.get(row['source_type'], row['source_type']),
                    'quantity': f"{float(row['total_quantity']):.2f}",
                    'rate': f"LE {float(row['avg_rate']):,.2f}",
                    'amount': float(row['total_amount']),
                    'percentage': f"{(float(row['total_amount']) / total * 100):.1f}" if total > 0 else "0.0"
                })
            
            return jsonify({'sources': sources})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/accounting/revenue", methods=["POST"])
@login_required
def api_add_revenue():
    """Add other revenue"""
    try:
        data = request.get_json()
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO accounting_revenue 
                (date, source_type, description, amount, notes, created_by)
                VALUES (%s, 'other', %s, %s, %s, %s)
            """, (data['date'], data['description'], data['amount'],
                  data.get('notes', ''), session.get('username')))
            conn.commit()
            return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/accounting/expenses")
@login_required
def api_accounting_expenses():
    """Get expenses"""
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

@app.route("/api/accounting/expenses", methods=["POST"])
@login_required
def api_add_expense():
    """Add expense"""
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
                SELECT DATE_FORMAT(date, '%Y-%m') as month,
                       SUM(CASE WHEN table_type = 'revenue' THEN amount ELSE 0 END) as revenue,
                       SUM(CASE WHEN table_type = 'expense' THEN amount ELSE 0 END) as expenses
                FROM (
                    SELECT date, amount, 'revenue' as table_type FROM accounting_revenue
                    UNION ALL
                    SELECT date, amount, 'expense' as table_type FROM accounting_expenses
                ) combined
                WHERE date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
                GROUP BY DATE_FORMAT(date, '%Y-%m')
                ORDER BY month
            """)
            data = cursor.fetchall()
            return jsonify({
                'months': [row['month'] for row in data],
                'revenue': [float(row['revenue']) for row in data],
                'expenses': [float(row['expenses']) for row in data]
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/maintenance")
@login_required
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
                SELECT DATE_FORMAT(date, '%Y-%m') as month,
                       SUM(CASE WHEN table_type = 'revenue' THEN amount ELSE -amount END) as profit
                FROM (
                    SELECT date, amount, 'revenue' as table_type FROM accounting_revenue
                    UNION ALL
                    SELECT date, amount, 'expense' as table_type FROM accounting_expenses
                ) combined
                WHERE date >= DATE_SUB(CURDATE(), INTERVAL 6 MONTH)
                GROUP BY DATE_FORMAT(date, '%Y-%m')
                ORDER BY month
            """)
            data = cursor.fetchall()
            return jsonify({
                'months': [row['month'] for row in data],
                'profit': [float(row['profit']) for row in data]
            })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/api/accounting/export/excel")
@login_required
def api_export_excel():
    """Export accounting data to Excel"""
    return jsonify({'message': 'Excel export coming soon!'})

@app.errorhandler(404)
def not_found(e):
    return "404 - Page Not Found", 404

@app.errorhandler(500)
def internal_error(e):
    print(f"Error: {e}")
    return "500 - Internal Server Error", 500

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG", "True") == "True"
    port = int(os.environ.get("PORT", 5000))
    print("=" * 60)
    print("Al Mohandes Modern Mills - Management System")
    print("=" * 60)
    print(f"Server: http://0.0.0.0:{port}")
    print(f"Debug: {debug_mode}")
    print(f"Weighbridge: {'Connected' if WEIGHBRIDGE_AVAILABLE else 'Demo Mode'}")
    print("=" * 60)
    print("\n📝 Login: username='admin' password='admin123'\n")
    
    # CRITICAL: Disable reloader to prevent opening COM port twice
    # Flask's reloader starts the app twice, which causes PermissionError on COM10
    app.run(debug=debug_mode, host="0.0.0.0", port=port, use_reloader=False)
