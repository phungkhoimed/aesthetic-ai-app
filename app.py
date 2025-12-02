import streamlit as st
from database_utils import get_connection, get_ingredient_details
from services import SkinAnalyzer
from chat_service import AIChatbot
from PIL import Image
import google.generativeai as genai
import pandas as pd
import plotly.express as px

# =====================================================
# 1. CẤU HÌNH & STYLE
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

# CSS TÙY CHỈNH (QUAN TRỌNG CHO GIAO DIỆN ĐẸP)
st.markdown("""
<style>
    /* Chỉnh font và padding */
    .block-container { padding-top: 2rem; }
    
    /* Style cho các metric card */
    div[data-testid="stMetric"] {
        background-color: #f9f9f9;
        border: 1px solid #e0e0e0;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
    }
    
    /* Style cho Chat message */
    .stChatMessage { 
        background-color: #ffffff; 
        border: 1px solid #f0f0f0;
        border-radius: 15px; 
        padding: 15px; 
        margin-bottom: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    
    /* Ẩn bớt decoration của Tab */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        height: 40px;
        white-space: pre-wrap;
        background-color: #ffffff;
        border-radius: 5px;
        padding: 5px 15px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #eef2ff;
        color: #4f46e5;
        border-bottom: 2px solid #4f46e5;
    }
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
    
    st.info(f"Đang phân tích cho da: **{skin_code}**")
    if is_pregnant: st.warning("⚠️ Chế độ thai kỳ: BẬT")

    st.markdown("---")
    st.header("⚙️ Cấu hình AI")
    
    system_api_key = st.secrets.get("GOOGLE_API_KEY", None)
    active_key = None
    is_ai_ready = False
    best_model_name = 'gemini-1.5-flash'

    if system_api_key:
        st.success("✅ Đã kích hoạt AI Pro")
        active_key = system_api_key
        with st.expander("🔑 Dùng Key cá nhân"):
            custom_key = st.text_input("Nhập Key mới:", type="password")
            if custom_key: active_key = custom_key
    else:
        active_key = st.text_input("Nhập Google API Key:", type="password")

    if active_key:
        try:
            genai.configure(api_key=active_key)
            # Auto-detect logic rút gọn
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
        Extract chemical ingredient names from skincare label.
        Standardize to INCI format.
        Return ONLY comma-separated list. No text.
        """
        with st.spinner('✨ AI đang đọc dữ liệu...'):
            response = model.generate_content([prompt, img])
        text = response.text.strip()
        return [x.strip() for x in text.split(',')] if text else []
    except: return []

# =====================================================
# 4. MAIN UI
# =====================================================
st.title("✨ Trợ lý Da liễu AI")
st.caption("Phân tích thành phần mỹ phẩm chuẩn y khoa & cá nhân hóa")
st.markdown("---")

ingredients_list = get_all_ingredients()
id_to_name = {item['ingredient_id']: item['inci_name'] for item in ingredients_list}
name_to_id = {item['inci_name'].lower(): item['ingredient_id'] for item in ingredients_list}

if not ingredients_list:
    st.error("⚠️ Database trống! Vui lòng chạy `data_importer_full.py`.")
    st.stop()

tab1, tab2 = st.tabs(["🔍 **Tra cứu Nhanh**", "📊 **Phân tích Hình ảnh (Pro)**"])

# --- TAB 1 (Giữ nguyên logic, tinh chỉnh UI) ---
with tab1:
    c1, c2 = st.columns(2)
    with c1: i_a = st.selectbox("🧪 Hoạt chất 1:", list(id_to_name.keys()), format_func=lambda x:id_to_name[x], key="ma")
    with c2: i_b = st.selectbox("🧪 Hoạt chất 2:", list(id_to_name.keys()), format_func=lambda x:id_to_name[x], index=1, key="mb")
    
    if st.button("Kiểm tra tương tác", use_container_width=True, type="primary"):
        with st.container(border=True):
            st.markdown("### 📋 Kết quả phân tích")
            inter = analyzer.check_interaction(i_a, i_b)
            risk_a, m_a = analyzer.check_safety_for_user(i_a)
            risk_b, m_b = analyzer.check_safety_for_user(i_b)
            
            if inter:
                t, l, a = inter
                color = "red" if t=='CONFLICT' else "green" if t=='SYNERGY' else "orange"
                st.markdown(f":{color}[**{t} ({l}):** {a}]")
            else: st.success("✅ Hai chất này an toàn khi dùng chung.")
            
            st.divider()
            c_ra, c_rb = st.columns(2)
            with c_ra: 
                st.caption(f"Đánh giá: {id_to_name[i_a]}")
                if risk_a == 'DANGER': st.error(m_a)
                elif risk_a == 'WARNING': st.warning(m_a)
                else: st.success(m_a)
            with c_rb:
                st.caption(f"Đánh giá: {id_to_name[i_b]}")
                if risk_b == 'DANGER': st.error(m_b)
                elif risk_b == 'WARNING': st.warning(m_b)
                else: st.success(m_b)

# --- TAB 2: VISION PRO (GIAO DIỆN MỚI) ---
with tab2:
    if not is_ai_ready:
        st.warning("🔒 Vui lòng nhập Key.")
    else:
        col_img, col_res = st.columns([1, 2.5], gap="large")
        
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
                            st.session_state.chat_history = [{"role": "assistant", "content": f"Tôi đã phân tích xong **{len(detected)}** thành phần. Dưới đây là báo cáo chi tiết cho bạn."}]
                    else:
                        st.error("Không đọc được chữ.")

        with col_res:
            if st.session_state.scan_done:
                # 1. XỬ LÝ DỮ LIỆU
                analysis_data = []
                safe_count = 0
                risk_count = 0
                warning_count = 0
                
                for name in st.session_state.detected_ingredients:
                    found = False
                    for db_name, db_id in name_to_id.items():
                        if db_name in name.lower():
                            details = get_ingredient_details(db_id) 
                            if details:
                                # Logic phân loại màu sắc đơn giản hóa
                                safe_lv = details['safety_rating']
                                status = "Nguy cơ" if safe_lv >= 5 else ("Cảnh báo" if safe_lv >=3 else "An toàn")
                                
                                if status == "An toàn": safe_count += 1
                                elif status == "Cảnh báo": warning_count += 1
                                else: risk_count += 1
                                
                                analysis_data.append({
                                    "Tên chất": details['inci_name'],
                                    "Chức năng": details['function_category'],
                                    "Đánh giá": status,
                                    "Gây mụn": details['comedogenic_rating']
                                })
                                found = True
                            break
                    if not found:
                        analysis_data.append({"Tên chất": name, "Chức năng": "Chưa rõ", "Đánh giá": "Không xác định", "Gây mụn": "-"})

                # 2. HIỂN THỊ METRICS (THẺ TÓM TẮT)
                total = len(st.session_state.detected_ingredients)
                known = len([d for d in analysis_data if d["Đánh giá"] != "Không xác định"])
                
                # Container cho Metrics
                with st.container(border=True):
                    m1, m2, m3 = st.columns(3)
                    m1.metric("Tổng thành phần", f"{total} chất", help="Số lượng chất tìm thấy trên nhãn")
                    m2.metric("Đã nhận diện", f"{known}/{total}", help="Số chất có trong Database của chúng ta")
                    
                    # Logic đánh giá tổng quan
                    if risk_count > 0:
                        m3.metric("Đánh giá an toàn", "RỦI RO", f"-{risk_count} chất", delta_color="inverse")
                    elif warning_count > 0:
                        m3.metric("Đánh giá an toàn", "CẦN LƯU Ý", f"-{warning_count} chất", delta_color="off")
                    else:
                        m3.metric("Đánh giá an toàn", "TỐT", "An toàn", delta_color="normal")

                st.write("") # Spacer

                # 3. BIỂU ĐỒ TRỰC QUAN (ĐÃ ĐƠN GIẢN HÓA)
                if known > 0:
                    df = pd.DataFrame(analysis_data)
                    df_known = df[df["Đánh giá"] != "Không xác định"]
                    
                    c_chart1, c_chart2 = st.columns([1, 1])
                    
                    with c_chart1:
                        st.caption("📊 **Tỷ lệ An toàn**")
                        # Biểu đồ Donut (Tròn rỗng ruột) nhìn sang hơn
                        fig_safe = px.pie(df_known, names='Đánh giá', color='Đánh giá', 
                                          color_discrete_map={"An toàn":"#4CAF50", "Cảnh báo":"#FFC107", "Nguy cơ":"#F44336"},
                                          hole=0.5)
                        fig_safe.update_layout(showlegend=True, margin=dict(t=0, b=0, l=0, r=0), height=220, 
                                               legend=dict(orientation="h", y=-0.1))
                        st.plotly_chart(fig_safe, use_container_width=True, config={'displayModeBar': False})

                    with c_chart2:
                        st.caption("🧬 **Nhóm chức năng chính**")
                        # Nhóm lại các category ít xuất hiện thành "Khác" cho gọn
                        top_cats = df_known['Chức năng'].value_counts().nlargest(5)
                        df_cat = df_known[df_known['Chức năng'].isin(top_cats.index)]
                        
                        fig_cat = px.bar(df_cat, y='Chức năng', x='Tên chất', orientation='h', color='Chức năng',
                                         color_discrete_sequence=px.colors.qualitative.Pastel)
                        fig_cat.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0), height=220,
                                              xaxis=dict(showgrid=False, showticklabels=False),
                                              yaxis=dict(title=None))
                        st.plotly_chart(fig_cat, use_container_width=True, config={'displayModeBar': False})
                
                # 4. BẢNG CHI TIẾT (NẰM GỌN TRONG EXPANDER)
                with st.expander("🔍 Xem chi tiết từng thành phần"):
                    st.dataframe(
                        pd.DataFrame(analysis_data),
                        column_config={
                            "Đánh giá": st.column_config.TextColumn(
                                "Đánh giá",
                                help="Dựa trên thang điểm EWG",
                                width="medium",
                            ),
                            "Gây mụn": st.column_config.NumberColumn(
                                "Gây mụn (0-5)",
                                format="%d ⭐",
                            ),
                        },
                        use_container_width=True,
                        hide_index=True
                    )

                st.divider()
                
                # 5. CÁ NHÂN HÓA (ROUTINE CHECK) - Gọn hơn
                st.markdown("##### 🛡️ Đối chiếu an toàn")
                routine_name = st.selectbox("Chọn chất đang dùng kèm:", ["(Không dùng kèm)"] + list(id_to_name.values()), key="v_s")
                
                if routine_name != "(Không dùng kèm)":
                    # Logic kiểm tra (Rút gọn hiển thị)
                    id_routine = None
                    for iid, name in id_to_name.items():
                        if name == routine_name: id_routine = iid; break
                    
                    found_issue = False
                    for row in analysis_data:
                        if row['Đánh giá'] != "Không xác định":
                            db_id = name_to_id.get(row['Tên chất'].lower())
                            if db_id and id_routine and db_id != id_routine:
                                inter = analyzer.check_interaction(db_id, id_routine)
                                if inter:
                                    t, l, a = inter
                                    found_issue = True
                                    if t == 'CONFLICT': st.error(f"❌ **{row['Tên chất']}** kỵ **{routine_name}**\n\n_{a}_")
                                    elif t == 'CAUTION': st.warning(f"⚠️ **{row['Tên chất']}** cần thận trọng với **{routine_name}**\n\n_{a}_")
                    
                    if not found_issue:
                        st.success(f"✅ Không tìm thấy xung đột với **{routine_name}**.")

                st.divider()
                
                # 6. CHATBOT (GIAO DIỆN SẠCH)
                st.subheader("💬 Trợ lý Bác sĩ AI")
                chat_container = st.container(height=300, border=True)
                for msg in st.session_state.chat_history:
                    with chat_container.chat_message(msg["role"]):
                        st.markdown(msg["content"])
                
                if prompt := st.chat_input("Hỏi chi tiết về sản phẩm này..."):
                    st.session_state.chat_history.append({"role": "user", "content": prompt})
                    with chat_container.chat_message("user"): st.markdown(prompt)
                    with chat_container.chat_message("assistant"):
                        with st.spinner("Thinking..."):
                            response = st.session_state.chatbot_instance.send_message(prompt)
                            st.markdown(response)
                    st.session_state.chat_history.append({"role": "assistant", "content": response})

            else:
                # Màn hình chờ (Placeholder)
                st.info("👈 Tải ảnh lên để bắt đầu phân tích.")
                st.caption("Hỗ trợ định dạng: JPG, PNG. Dung lượng tối đa 200MB.")
