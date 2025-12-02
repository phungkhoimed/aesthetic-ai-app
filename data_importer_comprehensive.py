from database_utils import get_connection, get_ingredient_id
import sqlite3

# ==============================================================================
# BỘ DỮ LIỆU "ACTIVE & BASE" - NHỮNG CHẤT PHỔ BIẾN NHẤT TRONG MỸ PHẨM
# ==============================================================================
COMPREHENSIVE_DATA = [
    # --- 1. DUNG MÔI & CẤP ẨM (SOLVENTS & HUMECTANTS) ---
    {"inci": "Water", "common": "Aqua, Nước tinh khiết", "cat": "Solvent", "safe": 1, "com": 0, "mech": "Dung môi hòa tan các chất khác."},
    {"inci": "Glycerin", "common": "Glycerol", "cat": "Humectant", "safe": 1, "com": 0, "mech": "Hút ẩm từ môi trường vào da, giúp da mềm mịn."},
    {"inci": "Butylene Glycol", "common": "BG", "cat": "Solvent", "safe": 1, "com": 1, "mech": "Giúp sản phẩm thấm nhanh, giảm độ nhờn rít."},
    {"inci": "Propylene Glycol", "common": "PG", "cat": "Humectant", "safe": 3, "com": 0, "mech": "Tăng cường thẩm thấu."},
    {"inci": "Propanediol", "common": "Propanediol", "cat": "Humectant", "safe": 1, "com": 0, "mech": "Dưỡng ẩm tự nhiên từ ngô, thay thế Propylene Glycol."},
    
    # --- 2. CỒN BÉO & CHẤT LÀM MỀM (EMOLLIENTS - TỐT CHO DA KHÔ) ---
    {"inci": "Cetyl Alcohol", "common": "Cồn béo", "cat": "Emollient", "safe": 1, "com": 2, "mech": "Làm mềm da, giữ nước (Khác cồn khô, không hại da)."},
    {"inci": "Stearyl Alcohol", "common": "Cồn béo", "cat": "Emollient", "safe": 1, "com": 2, "mech": "Chất làm đặc và làm mềm."},
    {"inci": "Cetearyl Alcohol", "common": "Cồn béo", "cat": "Emollient", "safe": 1, "com": 2, "mech": "Hỗn hợp của Cetyl và Stearyl Alcohol."},
    {"inci": "Caprylic/Capric Triglyceride", "common": "MCT Oil", "cat": "Emollient", "safe": 1, "com": 1, "mech": "Dầu nhẹ chiết xuất từ dừa, không gây nhờn."},
    {"inci": "Dimethicone", "common": "Silicone", "cat": "Occlusive", "safe": 3, "com": 1, "mech": "Tạo màng khóa ẩm, làm mượt da (Da quá nhiều mụn nên cân nhắc)."},
    
    # --- 3. DẦU TỰ NHIÊN (OILS - CẨN THẬN VỚI DA MỤN) ---
    {"inci": "Cocos Nucifera Oil", "common": "Dầu dừa", "cat": "Oil", "safe": 1, "com": 4, "mech": "Dưỡng ẩm sâu nhưng RẤT DỄ GÂY MỤN."},
    {"inci": "Oryza Sativa Bran Oil", "common": "Dầu cám gạo", "cat": "Oil", "safe": 1, "com": 2, "mech": "Làm sáng da, dưỡng ẩm."},
    {"inci": "Helianthus Annuus Seed Oil", "common": "Dầu hướng dương", "cat": "Oil", "safe": 1, "com": 0, "mech": "Lành tính, phục hồi hàng rào bảo vệ da."},
    {"inci": "Simmondsia Chinensis Seed Oil", "common": "Dầu Jojoba", "cat": "Oil", "safe": 1, "com": 2, "mech": "Cấu trúc giống dầu tự nhiên của người, thấm tốt."},
    {"inci": "Butyrospermum Parkii Butter", "common": "Shea Butter, Bơ hạt mỡ", "cat": "Occlusive", "safe": 1, "com": 0, "mech": "Dưỡng ẩm cực tốt cho da khô, khóa ẩm."},

    # --- 4. CHẤT NHŨ HÓA & TẠO ĐẶC (TEXTURE ENHANCERS) ---
    {"inci": "Glyceryl Stearate", "common": "Glyceryl Stearate", "cat": "Emulsifier", "safe": 1, "com": 1, "mech": "Giúp dầu và nước hòa tan vào nhau."},
    {"inci": "PEG-100 Stearate", "common": "PEG-100", "cat": "Emulsifier", "safe": 3, "com": 1, "mech": "Thường đi kèm Glyceryl Stearate để ổn định kem."},
    {"inci": "Xanthan Gum", "common": "Xanthan Gum", "cat": "Thickener", "safe": 1, "com": 0, "mech": "Tạo độ đặc cho serum/kem dưỡng (Lành tính)."},
    {"inci": "Carbomer", "common": "Carbomer", "cat": "Thickener", "safe": 1, "com": 0, "mech": "Tạo dạng gel trong suốt."},
    
    # --- 5. CHẤT BẢO QUẢN & HƯƠNG LIỆU (PRESERVATIVES) ---
    {"inci": "Phenoxyethanol", "common": "Phenoxyethanol", "cat": "Preservative", "safe": 4, "com": 0, "mech": "Chất bảo quản phổ biến nhất hiện nay."},
    {"inci": "Ethylhexylglycerin", "common": "Ethylhexylglycerin", "cat": "Preservative", "safe": 2, "com": 0, "mech": "Hỗ trợ bảo quản và dưỡng ẩm nhẹ."},
    {"inci": "Parfum", "common": "Fragrance, Hương liệu", "cat": "Perfume", "safe": 8, "com": 0, "mech": "Tạo mùi thơm. Dễ gây kích ứng cho da nhạy cảm."},
    {"inci": "Fragrance", "common": "Hương liệu", "cat": "Perfume", "safe": 8, "com": 0, "mech": "Tạo mùi thơm. Dễ gây kích ứng cho da nhạy cảm."},
    {"inci": "Disodium EDTA", "common": "EDTA", "cat": "Chelator", "safe": 1, "com": 0, "mech": "Khử ion kim loại, giúp sản phẩm ổn định lâu hơn."},
    
    # --- 6. HOẠT CHẤT ĐẶC TRỊ (ACTIVES - BỔ SUNG) ---
    {"inci": "Tocopherol", "common": "Vitamin E", "cat": "Antioxidant", "safe": 1, "com": 2, "mech": "Chống oxy hóa, bảo vệ da."},
    {"inci": "Panthenol", "common": "Vitamin B5", "cat": "Soothing", "safe": 1, "com": 0, "mech": "Phục hồi, làm dịu da."},
    {"inci": "Allantoin", "common": "Allantoin", "cat": "Soothing", "safe": 1, "com": 0, "mech": "Chống kích ứng, làm dịu."},
    {"inci": "Centella Asiatica Extract", "common": "Rau má", "cat": "Soothing", "safe": 1, "com": 0, "mech": "Làm dịu, trị mụn, phục hồi."},
    {"inci": "Camellia Sinensis Leaf Extract", "common": "Trà xanh", "cat": "Antioxidant", "safe": 1, "com": 0, "mech": "Chống oxy hóa, kháng viêm."},
    {"inci": "Aloe Barbadensis Leaf Juice", "common": "Lô hội", "cat": "Soothing", "safe": 1, "com": 0, "mech": "Cấp nước, làm dịu da cháy nắng."},
    
    # --- 7. CHỐNG NẮNG (SUNSCREENS) ---
    {"inci": "Titanium Dioxide", "common": "Titanium Dioxide", "cat": "Sunscreen", "safe": 2, "com": 0, "mech": "Chống nắng vật lý, an toàn cho da nhạy cảm."},
    {"inci": "Zinc Oxide", "common": "Zinc Oxide", "cat": "Sunscreen", "safe": 2, "com": 1, "mech": "Chống nắng vật lý, kháng viêm."},
    {"inci": "Ethylhexyl Methoxycinnamate", "common": "Octinoxate", "cat": "Sunscreen", "safe": 5, "com": 0, "mech": "Chống nắng hóa học (UVB). Cẩn thận với bà bầu."}
]

# LUẬT TƯƠNG TÁC BỔ SUNG (Quan trọng cho Vision)
NEW_INTERACTIONS = [
    # Hương liệu vs Da nhạy cảm (Cảnh báo chung)
    {"a": "Fragrance", "b": "Retinol", "type": "CAUTION", "level": "MEDIUM", "advice": "Cả hai đều có nguy cơ kích ứng. Nếu da nhạy cảm nên tránh dùng chung."},
    # Vitamin C vs Niacinamide (Giải oan)
    {"a": "Niacinamide", "b": "Ascorbic Acid", "type": "SYNERGY", "level": "LOW", "advice": "Có thể dùng chung nếu da khỏe. Giúp sáng da mờ thâm hiệu quả gấp đôi."},
    # Dầu dừa vs Da mụn
    {"a": "Cocos Nucifera Oil", "b": "Salicylic Acid", "type": "CONFLICT", "level": "MEDIUM", "advice": "Dầu dừa dễ gây mụn (Comedogenic 4/5), trong khi BHA trị mụn. Dùng chung có thể làm giảm hiệu quả trị mụn."},
]

def run_import():
    conn = get_connection()
    cursor = conn.cursor()
    print(f"🚀 Đang nạp {len(COMPREHENSIVE_DATA)} chất phổ biến vào Database...")
    
    count_new = 0
    count_update = 0
    
    for item in COMPREHENSIVE_DATA:
        try:
            # Dùng INSERT OR REPLACE để cập nhật nếu đã có
            sql = """
            INSERT OR REPLACE INTO Ingredients 
            (ingredient_id, inci_name, common_names, function_category, safety_rating, comedogenic_rating, mechanism_of_action)
            VALUES (
                (SELECT ingredient_id FROM Ingredients WHERE inci_name = ?),
                ?, ?, ?, ?, ?, ?
            )
            """
            # Tham số đầu tiên (SELECT...) dùng để giữ nguyên ID cũ nếu đã có, hoặc tạo mới nếu chưa
            cursor.execute(sql, (
                item["inci"], 
                item["inci"], item["common"], item["cat"], item["safe"], item.get("com", 0), item["mech"]
            ))
            count_new += 1
        except Exception as e:
            print(f"❌ Lỗi {item['inci']}: {e}")

    conn.commit()
    print(f"✅ Đã xử lý {count_new} hoạt chất.")
    
    print("\n🔗 Đang nạp luật tương tác bổ sung...")
    for item in NEW_INTERACTIONS:
        id_a = get_ingredient_id(cursor, item['a'])
        id_b = get_ingredient_id(cursor, item['b'])
        if id_a and id_b:
            try:
                # Kiểm tra trùng trước khi thêm
                cursor.execute("SELECT 1 FROM Ingredient_Interactions WHERE ingredient_a_id=? AND ingredient_b_id=?", (id_a, id_b))
                if not cursor.fetchone():
                    sql = """INSERT INTO Ingredient_Interactions (ingredient_a_id, ingredient_b_id, interaction_type, severity_level, advice_vn)
                             VALUES (?, ?, ?, ?, ?)"""
                    cursor.execute(sql, (id_a, id_b, item['type'], item['level'], item['advice']))
                    print(f"   + Đã nối: {item['a']} <-> {item['b']}")
            except: pass

    conn.commit()
    conn.close()
    print("🎉 HOÀN TẤT! Database của bạn giờ đã 'thông thái' hơn rất nhiều.")

if __name__ == "__main__":
    run_import()
