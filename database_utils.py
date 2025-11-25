import sqlite3
import os

# CẤU HÌNH CHUNG
DB_NAME = 'Aesthetic_DB.db'

def get_db_path():
    """Tự động tìm đường dẫn file DB dù chạy ở đâu"""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(current_dir, DB_NAME)

def get_connection():
    """Tạo kết nối đến Database"""
    try:
        db_path = get_db_path()
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row # Để truy cập cột bằng tên (row['name'])
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
    """Lấy toàn bộ thông tin chi tiết của một hoạt chất theo ID"""
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
    
    # Chuyển đổi Row object thành Dictionary để dễ xử lý ở tầng trên
    if row:
        return dict(row)
    return None