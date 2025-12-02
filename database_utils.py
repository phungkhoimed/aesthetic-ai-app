import sqlite3
import os
from datetime import datetime

# CẤU HÌNH CHUNG
DB_NAME = 'Aesthetic_DB.db'

def get_db_path():
    """Tự động tìm đường dẫn file DB dù chạy ở đâu"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, DB_NAME)

def get_connection():
    """Tạo kết nối đến Database và tự động khởi tạo bảng Lịch sử nếu chưa có"""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        
        # --- CƠ CHẾ MIGRATION TỰ ĐỘNG ---
        # Tạo bảng History nếu chưa tồn tại (Không ảnh hưởng bảng cũ)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS Scan_History (
                scan_id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_name TEXT DEFAULT 'Sản phẩm chưa đặt tên',
                ingredients_detected TEXT,  -- Lưu danh sách chất cách nhau dấu phẩy
                risk_summary TEXT,          -- Lưu kết quả 'An toàn' hay 'Rủi ro'
                scan_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        
        return conn
    except Exception as e:
        print(f"❌ Lỗi kết nối Database (Fatal Error): {e}")
        return None

def get_ingredient_id(cursor, name):
    """Hàm tiện ích: Tìm ID từ Tên chất"""
    try:
        clean_name = name.strip()
        cursor.execute("SELECT ingredient_id FROM Ingredients WHERE inci_name = ? COLLATE NOCASE", (clean_name,))
        result = cursor.fetchone()
        if result:
            return result['ingredient_id']
        return None
    except Exception as e:
        print(f"⚠️ Lỗi khi tìm ID cho {name}: {e}")
        return None

def get_ingredient_details(id):
    """Lấy chi tiết hoạt chất"""
    conn = get_connection()
    if not conn: return None
    cursor = conn.cursor()
    
    query = """
        SELECT inci_name, function_category, safety_rating, comedogenic_rating, pregnancy_safe, mechanism_of_action
        FROM Ingredients
        WHERE ingredient_id = ?
    """
    cursor.execute(query, (id,))
    row = cursor.fetchone()
    conn.close()
    
    if row: return dict(row)
    return None

# --- CÁC HÀM MỚI CHO LỊCH SỬ ---

def save_scan_result(ingredients_list, risk_status):
    """Lưu kết quả quét vào lịch sử"""
    conn = get_connection()
    if not conn: return
    try:
        cursor = conn.cursor()
        # Chuyển list thành chuỗi "A, B, C" để lưu vào 1 ô
        ing_str = ", ".join(ingredients_list)
        
        sql = """INSERT INTO Scan_History (ingredients_detected, risk_summary) VALUES (?, ?)"""
        cursor.execute(sql, (ing_str, risk_status))
        conn.commit()
    except Exception as e:
        print(f"Lỗi lưu lịch sử: {e}")
    finally:
        conn.close()

def get_recent_history(limit=10):
    """Lấy danh sách 10 lần quét gần nhất"""
    conn = get_connection()
    if not conn: return []
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM Scan_History ORDER BY scan_id DESC LIMIT ?", (limit,))
        return cursor.fetchall()
    except:
        return []
    finally:
        conn.close()
