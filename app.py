import streamlit as st
from database_utils import get_connection
from services import SkinAnalyzer
from chat_service import AIChatbot  # Module Chat thông minh
from PIL import Image
import google.generativeai as genai

# =====================================================
# 1. CẤU HÌNH & TRẠNG THÁI (STATE)
# =====================================================
st.set_page_config(page_title="Aesthetic AI Pro", page_icon="✨", layout="wide")

# Khởi tạo bộ nhớ tạm
if 'detected_ingredients' not in st.session_state:
    st.session_state.detected_ingredients = []
if 'scan_done' not in st.session_state:
    st.session_state.scan_done = False
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'chatbot_instance' not in st.session_state:
    st.session_state.chatbot_instance = None

# CSS tùy chỉnh
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { padding-top: 10px; padding-bottom: 10px; }
    .stChatMessage { background-color: #f0f2f6; border-radius: 10px; padding: 10px; margin-bottom: 10px;}
</style>
""", unsafe_allow_html=True)

# =====================================================
# 2. SIDEBAR: CẤU HÌNH & HỒ SƠ
# =====================================================
with st.sidebar:
    st.header("👤 Hồ sơ Da liễu")
    
    # Thu thập thông tin cá nhân
    skin_type = st.selectbox("Loại da của bạn:", 
                             ["Normal (Thường)", "Oily (Dầu)", "Dry (Khô)", "Sensitive (Nhạy cảm)", "Acne-Prone (Dễ nổi mụn)"])
    is_pregnant = st.checkbox("Đang mang thai / Cho con bú? 🤰")
    
    skin_code = skin_type.split(" ")[0]
    
    # Khởi tạo Analyzer (Logic kiểm tra an toàn)
    user_profile = {"skin_type": skin_code, "is_pregnant": is_pregnant}
    analyzer = SkinAnalyzer(user_profile)
    
    st.info(f"Chế độ phân tích: **{skin_code}**")
    if is_pregnant: st.warning("⚠️ Chế độ an toàn thai kỳ: BẬT")

    st.markdown("---")
    st.header("⚙️ Cấu hình AI")
    
    # --- LOGIC API KEY THÔNG MINH (SECRETS + INPUT) ---
    system_api_key = st.secrets.get("GOOGLE_API_KEY", None)
    active_key = None
    is_ai_ready = False
    best_model_name = 'gemini-1.5-flash'

    if system_api_key:
        st.success("✅ Đã kích hoạt AI bản quyền")
        active_key = system_api_key
        with st.expander("Dùng Key riêng (Nâng cao)"):
            custom_key = st.text_input("Nhập Key mới:", type="password")
            if custom_key: active_key = custom_key
    else:
        active_key = st.text_input("Nhập Google API Key:", type="password")

    # Kết nối AI & Khởi tạo Chatbot
    if active_key:
        try:
            genai.configure(api_key=active_key)
            # Auto-detect Model
            try:
                all_models = [m.name for m in genai.list_models()]
                if 'models/gemini-2.5-flash' in all_models: best_model_name = 'gemini-2.5-flash'
                elif 'models/gemini-1.5-flash' in all_models: best_model_name = 'gemini-1.5-flash'
                else: best_model_name = 'gemini-pro'
            except: pass
            
            is_ai_ready = True
            
            # Khởi tạo Chatbot Service (Chỉ 1 lần)
            if st.session_state.chatbot_instance is None:
                st.session_state.chatbot_instance = AIChatbot(active_key, best_model_name)
                
        except: st.error("Key lỗi")
    
    if is_ai_ready:
        st.caption(f"Engine: `{best_model_name}`")
    else:
        st.warning("Vui lòng nhập Key để dùng.")

# =====================================================
# 3. HELPER FUNCTIONS
# =====================================================
def get_all_ingredients():
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor()
    cursor.execute("SELECT ingredient_id, inci_name FROM Ingredients ORDER BY inci_name")
    data = cursor.fetchall()
    conn.close()
    return data

def analyze_image_with_gemini(image_file, model_name):
    try:
        model = genai.GenerativeModel(model_name)
        img = Image.open(image_file)
        prompt = """
        Extract all chemical ingredient names from this skincare product label image.
        Standardize names to INCI format (e.g., Vitamin B3 -> Niacinamide).
        Return ONLY a comma-separated list. No other text.
        """
        with st.spinner('✨ AI đang đọc bảng thành phần...'):
            response = model.generate_content([prompt, img])
        text = response.text.strip()
        return [x.strip() for x in text.split(',')] if text else []
    except Exception as e:
        st.error(f"Lỗi AI: {e}")
        return []

# =====================================================
# 4. GIAO DIỆN CHÍNH
# =====================================================
st.title("✨ Trợ lý Da liễu AI (Pro)")
st.markdown(f"#### *Cá nhân hóa cho làn da: {skin_type}*")
st.markdown("---")

ingredients_list = get_all_ingredients()
id_to_name = {item['ingredient_id']: item['inci_name'] for item in ingredients_list}
name_to_id = {item['inci_name'].lower(): item['ingredient_id'] for item in ingredients_list}

if not ingredients_list:
    st.error("⚠️ Database đang trống! Vui lòng chạy `data_importer_full.py`.")
    st.stop()

tab1, tab2 = st.tabs(["🔍 **Tra cứu Thủ công**", "📸 **Soi da & Chat AI**"])

# --- TAB 1: TRA CỨU ---
with tab1:
    c1, c2 = st.columns(2)
    with c1: i_a = st.selectbox("🧪 Hoạt chất 1:", list(id_to_name.keys()), format_func=lambda x:id_to_name[x], key="ma")
    with c2: i_b = st.selectbox("🧪 Hoạt chất 2:", list(id_to_name.keys()), format_func=lambda x:id_to_name[x], index=1, key="mb")
    
    if st.button("⚡ Phân tích", use_container_width=True):
        st.divider()
        inter = analyzer.check_interaction(i_a, i_b)
        risk_a, m_a = analyzer.check_safety_for_user(i_a)
        risk_b, m_b = analyzer.check_safety_for_user(i_b)
        
        st.subheader("1. Kết quả Tương tác")
        if inter:
            t, l, a = inter
            if t=='CONFLICT': st.error(f"❌ **XUNG ĐỘT ({l})**: {a}")
            elif t=='SYNERGY': st.success(f"✅ **HỢP NHAU ({l})**: {a}")
            else: st.warning(f"⚠️ **THẬN TRỌNG ({l})**: {a}")
        else: st.info("✅ An toàn.")
        
        st.subheader("2. Độ phù hợp với bạn")
        c_ra, c_rb = st.columns(2)
        with c_ra: 
            st.markdown(f"**{id_to_name[i_a]}**")
            if risk_a == 'DANGER': st.error(m_a)
            elif risk_a == 'WARNING': st.warning(m_a)
            else: st.success(m_a)
        with c_rb:
            st.markdown(f"**{id_to_name[i_b]}**")
            if risk_b == 'DANGER': st.error(m_b)
            elif risk_b == 'WARNING': st.warning(m_b)
            else: st.success(m_b)

# --- TAB 2: VISION + CHATBOT ---
with tab2:
    if not is_ai_ready:
        st.warning("🔒 Vui lòng nhập Key.")
    else:
        col_img, col_res = st.columns([1, 2], gap="medium")
        
        with col_img:
            uploaded_file = st.file_uploader("", type=['jpg', 'png', 'jpeg'], label_visibility="collapsed")
            if uploaded_file:
                st.image(uploaded_file, caption="Ảnh sản phẩm", use_container_width=True)
                if st.button("🚀 Quét ngay", type="primary", use_container_width=True):
                    detected = analyze_image_with_gemini(uploaded_file, best_model_name)
                    if detected:
                        st.session_state.detected_ingredients = detected
                        st.session_state.scan_done = True
                        
                        # --- KÍCH HOẠT PHIÊN CHAT MỚI ---
                        if st.session_state.chatbot_instance:
                            profile_str = f"Da {skin_type}, Bầu bì: {'Có' if is_pregnant else 'Không'}"
                            st.session_state.chatbot_instance.start_new_session(detected, profile_str)
                            st.session_state.chat_history = [] 
                            st.session_state.chat_history.append({"role": "assistant", "content": f"👋 Chào bạn! Tôi đã phân tích xong **{len(detected)}** thành phần trong ảnh. Bạn cần tôi tư vấn gì về sản phẩm này không?"})
                    else:
                        st.error("Không đọc được chữ.")

        with col_res:
            if st.session_state.scan_done:
                # PHẦN 1: KẾT QUẢ PHÂN TÍCH CỨNG
                with st.expander("📊 Xem chi tiết thành phần & Cảnh báo", expanded=True):
                    st.write(f"**Thành phần:** {', '.join(st.session_state.detected_ingredients)}")
                    st.write("")
                    
                    # Logic check DB nhanh
                    matched = 0
                    for name in st.session_state.detected_ingredients:
                        for db_name, db_id in name_to_id.items():
                            if db_name in name.lower():
                                matched += 1
                                risk, msg = analyzer.check_safety_for_user(db_id)
                                if risk in ['DANGER', 'WARNING']:
                                    if risk == 'DANGER': st.error(f"**{id_to_name[db_id]}**: {msg}")
                                    else: st.warning(f"**{id_to_name[db_id]}**: {msg}")
                                break
                    if matched == 0: st.caption("⚠️ Các chất này chưa có trong Database nên chưa thể cảnh báo tự động.")

                st.divider()
                
                # PHẦN 2: CHAT VỚI BÁC SĨ AI
                st.subheader("💬 Chat với Bác sĩ AI")
                
                # Khung chat cuộn được
                chat_container = st.container(height=300)
                for msg in st.session_state.chat_history:
                    with chat_container.chat_message(msg["role"]):
                        st.markdown(msg["content"])

                # Ô nhập liệu
                if prompt := st.chat_input("Hỏi gì đó (VD: Dùng sáng hay tối?)..."):
                    st.session_state.chat_history.append({"role": "user", "content": prompt})
                    with chat_container.chat_message("user"):
                        st.markdown(prompt)

                    with chat_container.chat_message("assistant"):
                        with st.spinner("Đang trả lời..."):
                            response = st.session_state.chatbot_instance.send_message(prompt)
                            st.markdown(response)
                            
                    st.session_state.chat_history.append({"role": "assistant", "content": response})

            else:
                st.info("👈 Tải ảnh lên để bắt đầu soi da & chat.")
