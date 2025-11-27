import google.generativeai as genai
import streamlit as st

class AIChatbot:
    """
    Class quản lý hội thoại thông minh với Gemini.
    Nhiệm vụ: Nhớ lịch sử chat và ngữ cảnh (Context) về sản phẩm đang soi.
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
        Bắt đầu cuộc trò chuyện mới với ngữ cảnh là danh sách thành phần vừa quét.
        Đây là kỹ thuật 'Context Injection' (Tiêm ngữ cảnh).
        """
        if not self.model: return
        
        # Tạo System Prompt (Lời nhắc hệ thống) để định hình tính cách AI
        context_prompt = f"""
        Bạn là một Bác sĩ Da liễu AI chuyên nghiệp, thân thiện.
        
        ĐÂY LÀ NGỮ CẢNH HIỆN TẠI:
        1. Người dùng vừa quét một sản phẩm có chứa các hoạt chất: {', '.join(ingredients_list)}.
        2. Hồ sơ da của người dùng: {skin_profile}.
        
        NHIỆM VỤ CỦA BẠN:
        - Trả lời các câu hỏi thắc mắc của người dùng liên quan đến sản phẩm này.
        - Tư vấn cách dùng, tần suất, và lưu ý dựa trên danh sách thành phần trên.
        - Nếu người dùng hỏi ngoài lề (không liên quan skincare), hãy khéo léo từ chối.
        - Trả lời ngắn gọn, súc tích, có định dạng Markdown đẹp mắt.
        """
        
        # Khởi tạo lịch sử chat
        history = [
            {"role": "user", "parts": [context_prompt]},
            {"role": "model", "parts": ["Đã hiểu. Tôi sẵn sàng tư vấn về sản phẩm này dựa trên hồ sơ da của bạn."]}
        ]
        
        self.chat_session = self.model.start_chat(history=history)
        return self.chat_session

    def send_message(self, user_message):
        """Gửi tin nhắn và nhận phản hồi"""
        if not self.chat_session:
            return "⚠️ Lỗi: Phiên chat chưa được khởi tạo."
        
        try:
            response = self.chat_session.send_message(user_message)
            return response.text
        except Exception as e:
            return f"⚠️ Lỗi kết nối AI: {str(e)}"
