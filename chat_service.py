import google.generativeai as genai
import streamlit as st

class AIChatbot:
    """
    Class quản lý hội thoại thông minh với Gemini.
    Nhiệm vụ: Nhớ ngữ cảnh (Context) về sản phẩm và Hồ sơ người dùng.
    """
    
    def __init__(self, api_key, model_name='gemini-1.5-flash'):
        if api_key:
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel(model_name)
            self.chat_session = None
        else:
            self.model = None

    def start_new_session(self, ingredients_list, skin_profile):
        """
        Khởi tạo phiên chat với kỹ thuật 'Context Injection'.
        Truyền toàn bộ dữ liệu thành phần và hồ sơ da vào não AI trước.
        """
        if not self.model: return
        
        # --- BÍ MẬT CÔNG NGHỆ: SYSTEM PROMPT ---
        # Đây là nơi chúng ta dạy AI cách cư xử
        context_prompt = f"""
        Bạn là một Bác sĩ Da liễu AI chuyên nghiệp (Dermatologist AI).
        
        DỮ LIỆU ĐẦU VÀO:
        1. Sản phẩm khách hàng đang cầm trên tay chứa: {', '.join(ingredients_list)}.
        2. HỒ SƠ KHÁCH HÀNG (QUAN TRỌNG): {skin_profile}.
        
        NGUYÊN TẮC TƯ VẤN:
        1. ƯU TIÊN SỐ 1: Kiểm tra an toàn cho đối tượng nhạy cảm (Bà bầu/Cho con bú). Nếu sản phẩm chứa Retinol, BHA, Hydroquinone... phải cảnh báo ngay lập tức.
        2. CÁ NHÂN HÓA: 
           - Nếu da Dầu: Cảnh báo các chất gây bít tắc (Comedogenic) như Dầu dừa, Shea Butter.
           - Nếu da Khô: Khen ngợi các chất cấp ẩm (HA, Glycerin).
           - Nếu da Nhạy cảm: Cảnh báo hương liệu (Fragrance), cồn khô.
        3. PHONG CÁCH: Trả lời ngắn gọn, khoa học, đồng cảm. Không lan man.
        
        Hãy bắt đầu bằng việc chào khách hàng và nhận xét ngắn gọn về độ phù hợp của sản phẩm này với hồ sơ của họ.
        """
        
        # Khởi tạo lịch sử chat
        history = [
            {"role": "user", "parts": [context_prompt]},
            {"role": "model", "parts": [f"Chào bạn! Dựa trên hồ sơ {skin_profile}, tôi đã phân tích bảng thành phần. Bạn cần tôi tư vấn chi tiết điểm nào không?"]}
        ]
        
        self.chat_session = self.model.start_chat(history=history)
        return self.chat_session

    def send_message(self, user_message):
        """Gửi tin nhắn và nhận phản hồi"""
        if not self.chat_session:
            return "⚠️ Lỗi: Phiên chat chưa được khởi tạo. Hãy quét ảnh trước."
        
        try:
            response = self.chat_session.send_message(user_message)
            return response.text
        except Exception as e:
            return f"⚠️ Lỗi kết nối AI: {str(e)}"
