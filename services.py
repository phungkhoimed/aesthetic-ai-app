from database_utils import get_connection, get_ingredient_details

class SkinAnalyzer:
    """
    Class chịu trách nhiệm phân tích độ phù hợp của hoạt chất với người dùng.
    Áp dụng nguyên lý Single Responsibility (SRP).
    """
    
    def __init__(self, user_profile):
        # user_profile là dict: {'skin_type': 'Oily', 'is_pregnant': False, ...}
        self.profile = user_profile

    def check_safety_for_user(self, ingredient_id):
        """
        Phân tích một hoạt chất dựa trên hồ sơ người dùng.
        Trả về: (Mức độ nguy hiểm, Lời khuyên)
        Mức độ: 'SAFE', 'WARNING', 'DANGER'
        """
        details = get_ingredient_details(ingredient_id)
        if not details:
            return 'UNKNOWN', "Không có dữ liệu"

        name = details['inci_name']
        category = details['function_category']
        com_rating = details['comedogenic_rating'] or 0
        # safety_rating = details['safety_rating'] # Có thể dùng sau này

        messages = []
        risk_level = 'SAFE'

        # 1. KIỂM TRA CHO BÀ BẦU (Ưu tiên cao nhất)
        if self.profile.get('is_pregnant'):
            # Logic: Retinoid và BHA nồng độ cao, Hydroquinone là cấm kỵ
            if category == 'Retinoid':
                return 'DANGER', f"⛔ **TUYỆT ĐỐI TRÁNH:** {name} thuộc nhóm Retinoid, có nguy cơ gây dị tật thai nhi."
            if name == 'Salicylic Acid' or name == 'BHA':
                # Trong thực tế cần check nồng độ, nhưng an toàn thì cảnh báo luôn
                messages.append(f"⚠️ **Thận trọng:** BHA liều cao không tốt cho thai kỳ. Nên hỏi ý kiến bác sĩ.")
                risk_level = 'WARNING'

        # 2. KIỂM TRA LOẠI DA
        skin_type = self.profile.get('skin_type', 'Normal')

        # Logic cho Da Dầu / Mụn
        if skin_type in ['Oily', 'Acne-Prone']:
            if com_rating >= 3:
                messages.append(f"🚫 **Gây mụn:** Chỉ số bít tắc lỗ chân lông là {com_rating}/5. Rất dễ gây mụn cho da dầu.")
                if risk_level != 'DANGER': risk_level = 'DANGER'
            elif com_rating == 2:
                messages.append(f"⚠️ **Lưu ý:** Có khả năng gây mụn nhẹ (Chỉ số 2/5).")
                if risk_level == 'SAFE': risk_level = 'WARNING'
        
        # Logic cho Da Khô
        if skin_type == 'Dry':
            if category in ['Solvent', 'Surfactant'] and details['safety_rating'] >= 4:
                 messages.append(f"⚠️ **Gây khô da:** {name} có thể làm mất độ ẩm tự nhiên.")
                 if risk_level == 'SAFE': risk_level = 'WARNING'

        # Logic cho Da Nhạy Cảm
        if skin_type == 'Sensitive':
            if category in ['Perfume', 'Fragrance', 'Preservative'] and details['safety_rating'] >= 4:
                messages.append(f"❌ **Dễ kích ứng:** Da nhạy cảm nên tránh hương liệu/chất bảo quản mạnh như {name}.")
                if risk_level != 'DANGER': risk_level = 'WARNING'

        # Tổng hợp kết quả
        if not messages:
            return 'SAFE', f"✅ Phù hợp với hồ sơ {skin_type}."
        
        return risk_level, "\n".join(messages)

    def check_interaction(self, id_a, id_b):
        """Kiểm tra tương tác thuốc (Logic cũ chuyển vào đây)"""
        conn = get_connection()
        cursor = conn.cursor()
        query = """
        SELECT interaction_type, severity_level, advice_vn 
        FROM Ingredient_Interactions 
        WHERE (ingredient_a_id = ? AND ingredient_b_id = ?) 
           OR (ingredient_a_id = ? AND ingredient_b_id = ?)
        """
        cursor.execute(query, (id_a, id_b, id_b, id_a))
        result = cursor.fetchone()
        conn.close()
        return result