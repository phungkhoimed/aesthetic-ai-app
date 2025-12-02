import streamlit as st
from database_utils import get_connection, get_ingredient_details
from services import SkinAnalyzer
from chat_service import AIChatbot
from PIL import Image
import google.generativeai as genai
import pandas as pd
import plotly.express as px

# =====================================================
# 1. CẤU HÌNH & TRẠNG THÁI
# =====================================================
st.set_page_config(page_title="Aesthetic AI Pro", page_icon="✨", layout="wide")

if 'detected_ingredients' not in st.session_state:
    st.session_state.detected_ingredients = []
if 'scan_done' not in st.session_state:
    st.session_state.scan_done = False
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []
if 'chatbot_instance' not in st.session_state:
    st.session_state.chatbot_instance = None

# CSS
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { padding-top: 10px; padding-bottom: 10px; }
    .stChatMessage { background-color: #f0f2f6; border-radius: 10px; padding: 10px; margin-bottom: 10px;}
</style>
""", unsafe_allow_html=True)

# =====================================================
# 2. SIDEBAR
# =====================================================
with st.sidebar:
    st.header("👤 Hồ sơ Da liễu")
    skin_type = st.selectbox("Loại da của bạn:", 
                             ["Normal (Thường)", "Oily (Dầu)", "Dry (Khô)", "Sensitive (Nhạy cảm)", "Acne-Prone (Dễ nổi mụn)"])
    is_pregnant = st.checkbox("Đang mang thai / Cho con bú? 🤰")
    skin_code = skin_type.split(" ")[0]
    
    user_profile = {"skin_type": skin_code, "is_pregnant": is_pregnant}
    analyzer = SkinAnalyzer(user_profile)
    
    st.info(f"Chế độ phân tích: **{skin_code}**")
    if is_pregnant: st.warning("⚠️ Chế độ an toàn thai kỳ: BẬT")

    st.markdown("---")
    st.header("⚙️ Cấu hình AI")
    
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

    if active_key:
        try:
            genai.configure(api_key=active_key)
            try:
                all_models = [m.name for m in genai.list_models()]
                if 'models/gemini-2.5-flash' in all_models: best_model_name = 'gemini-2.5-flash'
                elif 'models/gemini-1.5-flash' in all_models: best_model_name = 'gemini-1.5-flash'
                else: best_model_name = 'gemini-pro'
            except: pass
            
            is_ai_ready = True
            if st.session_state.chatbot_instance is None:
                st.session_state.chatbot_instance = AIChatbot(active_key, best_model_name)
        except: st.error("Key lỗi")
    
    if is_ai_ready: st.caption(f"Engine: `{best_model_name}`")
    else: st.warning("Vui lòng nhập Key.")

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
    except: return []

# =====================================================
# 4. MAIN UI
# =====================================================
st.title("✨ Trợ lý Da liễu AI (Pro)")
st.markdown(f"#### *Cá nhân hóa cho làn da: {skin_type}*")
st.markdown("---")

ingredients_list = get_all_ingredients()
id_to_name = {item['ingredient_id']: item['inci_name'] for item in ingredients_list}
name_to_id = {item['inci_name'].lower(): item['ingredient_id'] for item in ingredients_list}

if not ingredients_list:
    st.error("⚠️ Database trống! Vui lòng chạy `data_importer_full.py`.")
    st.stop()

tab1, tab2 = st.tabs(["🔍 **Tra cứu Thủ công**", "📊 **Phân tích AI Vision (Mới)**"])

# --- TAB 1 (Giữ nguyên) ---
with tab1:
    c1, c2 = st.columns(2)
    with c1: i_a = st.selectbox("🧪 Hoạt chất 1:", list(id_to_name.keys()), format_func=lambda x:id_to_name[x], key="ma")
    with c2: i_b = st.selectbox("🧪 Hoạt chất 2:", list(id_to_name.keys()), format_func=lambda x:id_to_name[x], index=1, key="mb")
    
    if st.button("⚡ Phân tích", use_container_width=True):
        inter = analyzer.check_interaction(i_a, i_b)
        risk_a, m_a = analyzer.check_safety_for_user(i_a)
        risk_b, m_b = analyzer.check_safety_for_user(i_b)
        
        st.subheader("1. Kết quả Tương tác")
        if inter:
            t, l, a = inter
            if t=='CONFLICT': st.error(f"❌ **XUNG ĐỘT ({l})**: {a}")
            else: st.success(f"✅ **HỢP NHAU ({l})**: {a}")
        else: st.info("✅ An toàn.")
        
        c_ra, c_rb = st.columns(2)
        with c_ra: 
            if risk_a == 'DANGER': st.error(m_a)
            else: st.success(m_a)
        with c_rb:
            if risk_b == 'DANGER': st.error(m_b)
            else: st.success(m_b)

# --- TAB 2: DASHBOARD TRỰC QUAN HÓA ---
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
                        if st.session_state.chatbot_instance:
                            profile_str = f"Da {skin_type}, Bầu: {is_pregnant}"
                            st.session_state.chatbot_instance.start_new_session(detected, profile_str)
                            st.session_state.chat_history = [{"role": "assistant", "content": "Tôi đã phân tích xong dữ liệu. Bạn cần xem biểu đồ hay hỏi gì thêm?"}]
                    else:
                        st.error("Không đọc được chữ.")

        with col_res:
            if st.session_state.scan_done:
                # --- PHẦN PHÂN TÍCH DỮ LIỆU (NEW) ---
                
                # 1. Thu thập dữ liệu chi tiết từ DB
                analysis_data = []
                unknown_count = 0
                
                for name in st.session_state.detected_ingredients:
                    found = False
                    for db_name, db_id in name_to_id.items():
                        if db_name in name.lower():
                            # Lấy chi tiết từ hàm trong database_utils
                            details = get_ingredient_details(db_id) 
                            if details:
                                analysis_data.append({
                                    "Name": details['inci_name'],
                                    "Category": details['function_category'],
                                    "Safety": "Nguy cơ cao" if details['safety_rating'] >= 5 else ("Trung bình" if details['safety_rating'] >=3 else "An toàn"),
                                    "Comedogenic": details['comedogenic_rating']
                                })
                                found = True
                            break
                    if not found:
                        unknown_count += 1

                # 2. Hiển thị Dashboard
                if analysis_data:
                    df = pd.DataFrame(analysis_data)
                    
                    st.success(f"✅ Đã nhận diện {len(df)}/{len(st.session_state.detected_ingredients)} thành phần trong Database.")
                    
                    # BIỂU ĐỒ 1: MỨC ĐỘ AN TOÀN (PIE CHART)
                    c_chart1, c_chart2 = st.columns(2)
                    with c_chart1:
                        st.caption("📊 Mức độ an toàn")
                        fig_safe = px.pie(df, names='Safety', color='Safety', 
                                          color_discrete_map={"An toàn":"#00CC96", "Trung bình":"#FFA15A", "Nguy cơ cao":"#EF553B"},
                                          hole=0.4)
                        fig_safe.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=200)
                        st.plotly_chart(fig_safe, use_container_width=True)

                    # BIỂU ĐỒ 2: PHÂN BỐ CHỨC NĂNG (BAR CHART)
                    with c_chart2:
                        st.caption("🧬 Nhóm chức năng")
                        fig_cat = px.bar(df, y='Category', x='Name', orientation='h', color='Category')
                        fig_cat.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=200, xaxis_title=None, yaxis_title=None)
                        st.plotly_chart(fig_cat, use_container_width=True)
                    
                    # BẢNG CHI TIẾT
                    with st.expander("Xem bảng chi tiết từng chất"):
                        st.dataframe(df[['Name', 'Category', 'Safety', 'Comedogenic']], use_container_width=True)

                else:
                    st.warning("⚠️ Chưa có dữ liệu khớp trong Database để vẽ biểu đồ.")

                st.divider()
                
                # --- PHẦN LOGIC CÁ NHÂN HÓA (GIỮ NGUYÊN) ---
                routine_name = st.selectbox("Đối chiếu với Routine:", ["(Chọn chất)"] + list(id_to_name.values()), key="v_s")
                if routine_name != "(Chọn chất)":
                    matched_count = 0
                    personal_risks = []
                    interaction_risks = []
                    id_routine = None
                    for iid, name in id_to_name.items():
                        if name == routine_name: id_routine = iid; break
                    
                    for row in analysis_data: # Dùng data đã xử lý cho nhanh
                        matched_count += 1
                        # Tìm lại ID
                        db_id = name_to_id.get(row['Name'].lower())
                        if db_id:
                            p_risk, p_msg = analyzer.check_safety_for_user(db_id)
                            if p_risk in ['DANGER', 'WARNING']:
                                personal_risks.append((row['Name'], p_risk, p_msg))
                            if id_routine and db_id != id_routine:
                                inter = analyzer.check_interaction(db_id, id_routine)
                                if inter:
                                    t, l, a = inter
                                    if t == 'CONFLICT': interaction_risks.append((f"❌ **XUNG ĐỘT**: {row['Name']} kỵ {routine_name}", a))
                    
                    if personal_risks:
                        st.error(f"🚫 **RỦI RO CHO DA {skin_code.upper()}:**")
                        for name, risk, msg in personal_risks:
                            st.write(f"- **{name}**: {msg}")
                    
                    if not personal_risks and not interaction_risks:
                        st.success(f"🎉 **AN TOÀN TUYỆT ĐỐI!**")

                st.divider()
                # --- PHẦN CHAT (GIỮ NGUYÊN) ---
                st.subheader("💬 Hỏi đáp chuyên sâu")
                chat_container = st.container(height=300)
                for msg in st.session_state.chat_history:
                    with chat_container.chat_message(msg["role"]):
                        st.markdown(msg["content"])
                if prompt := st.chat_input("Hỏi gì đó..."):
                    st.session_state.chat_history.append({"role": "user", "content": prompt})
                    with chat_container.chat_message("user"): st.markdown(prompt)
                    with chat_container.chat_message("assistant"):
                        with st.spinner("..."):
                            response = st.session_state.chatbot_instance.send_message(prompt)
                            st.markdown(response)
                    st.session_state.chat_history.append({"role": "assistant", "content": response})

            else:
                st.info("👈 Tải ảnh lên để bắt đầu.")
