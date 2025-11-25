from database_utils import get_connection, get_ingredient_id
import sqlite3

INTERACTIONS_DATA = [
    {"a": "Retinol", "b": "Ascorbic Acid", "type": "CONFLICT", "level": "HIGH", 
     "advice": "Retinol (pH 6) kỵ Vitamin C (pH 3.5). Dùng chung gây kích ứng. Nên chia sáng/tối.", "ref": "Dermatology Times"},
    
    {"a": "Salicylic Acid", "b": "Retinol", "type": "CAUTION", "level": "MEDIUM", 
     "advice": "Cả hai đều gây bong tróc. Dùng cách ngày để tránh vỡ màng bảo vệ da.", "ref": "AAD"},
    
    {"a": "Hyaluronic Acid", "b": "Retinol", "type": "SYNERGY", "level": "LOW", 
     "advice": "HA cấp nước giúp giảm khô rát do Retinol. Combo hoàn hảo.", "ref": "NCBI"},
     
    {"a": "Niacinamide", "b": "Salicylic Acid", "type": "SYNERGY", "level": "LOW", 
     "advice": "Niacinamide kháng viêm giúp làm dịu da sau khi BHA tẩy tế bào chết.", "ref": "Cosmetic Review"}
]

def import_interactions():
    conn = get_connection()
    if not conn: return
    cursor = conn.cursor()

    print("\n🧠 Bắt đầu liên kết Tương tác (Interactions)...")
    count = 0

    for item in INTERACTIONS_DATA:
        # Tái sử dụng hàm tìm ID chuẩn
        id_a = get_ingredient_id(cursor, item['a'])
        id_b = get_ingredient_id(cursor, item['b'])

        if id_a and id_b:
            try:
                # Kiểm tra xem cặp này đã có chưa để tránh trùng lặp
                check_sql = "SELECT 1 FROM Ingredient_Interactions WHERE ingredient_a_id=? AND ingredient_b_id=?"
                cursor.execute(check_sql, (id_a, id_b))
                if cursor.fetchone():
                    print(f"   ⏩ Đã có: {item['a']} - {item['b']}")
                    continue

                sql = """
                INSERT INTO Ingredient_Interactions 
                (ingredient_a_id, ingredient_b_id, interaction_type, severity_level, advice_vn, scientific_ref)
                VALUES (?, ?, ?, ?, ?, ?)
                """
                cursor.execute(sql, (id_a, id_b, item['type'], item['level'], item['advice'], item['ref']))
                count += 1
                print(f"   🔗 Đã nối: {item['a']} <-> {item['b']} ({item['type']})")
            except Exception as e:
                print(f"   ❌ Lỗi: {e}")
        else:
            print(f"   ⚠️ Thiếu dữ liệu gốc cho cặp: {item['a']} - {item['b']}")

    conn.commit()
    conn.close()
    print(f"🎉 Hoàn tất liên kết {count} quy tắc mới.\n")

if __name__ == "__main__":
    import_interactions()