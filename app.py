import streamlit as st
from database_utils import get_connection
from services import SkinAnalyzer
from PIL import Image
import google.generativeai as genai
import os

# =====================================================
# 1. CẤU HÌNH HỆ THỐNG & TRẠNG THÁI
# =====================================================
st.set_page_config(page_title="Aesthetic AI Pro", page_icon="✨", layout="wide")

if 'detected_ingredients' not in st.session_state:
    st.session_state.detected_ingredients = []
if 'scan_done' not in st.session_state:
    st.session_state.scan_done = False

# CSS tùy chỉnh
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { padding-top: 10px; padding-bottom: 10px; }
    div[data-testid="stExpander"] details summary p { font-weight: 600; font-size: 1rem; }
    .stAlert { padding: 10px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# =====================================================
# 2. SIDEBAR: CẤU HÌNH THÔNG MINH (AUTO-KEY)
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
    
    # --- LOGIC XỬ LÝ API KEY TỰ ĐỘNG ---
    system_api_key = None
    
    # 1. Kiểm tra xem trong "Két sắt" (Secrets) có Key chưa
    if "GOOGLE_API_KEY" in st.secrets:
        system_api_key = st.secrets["GOOGLE_API_KEY"]
    
    # 2. Giao diện hiển thị trạng thái
    api_key_input = ""
    is_ai_ready = False
    best_model_name = None

    if system_api_key:
        st.success("✅ Đã kích hoạt AI bản quyền (Miễn phí)")
        active_key = system_api_key
        
        # Cho phép người dùng nhập Key riêng nếu muốn (Ẩn trong Expander)
        with st.expander("Cấu hình nâng cao (Dùng Key riêng)"):
            custom_key = st.text_input("Nhập Key cá nhân (Ghi đè):", type="password")
            if custom_key:
                active_key = custom_key
                st.info("Đang sử dụng Key cá nhân của bạn.")
    else:
        st.warning("⚠️ Hệ thống chưa có Key mặc định.")
        active_key = st.text_input("Vui lòng nhập Google API Key để tiếp tục:", type="password")

    # 3. KẾT NỐI VỚI KEY ĐÃ CHỌN
    if active_key:
        try:
            genai.configure(api_key=active_key)
            try:
                all_models = [m.name for m in genai.list_models()]
                if 'models/gemini-2.5-flash' in all_models: best_model_name = 'gemini-2.5-flash'
                elif 'models/gemini-1.5-flash' in all_models: best_model_name = 'gemini-1.5-flash'
                else: best_model_name = 'gemini-pro'
            except:
                best_model_name = 'gemini-1.5-flash'
            
            is_ai_ready = True
            st.caption(f"Engine: `{best_model_name}`")
        except: 
            st.error("Kết nối AI thất bại. Kiểm tra lại Key.")

# =====================================================
# 3. CÁC HÀM HỖ TRỢ
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
        if not model_name: model_name = 'gemini-1.5-flash'
        model = genai.GenerativeModel(model_name)
        img = Image.open(image_file)
        
        prompt = """
        Extract all chemical ingredient names from this skincare product label image.
        Standardize names to INCI format (e.g., Vitamin B3 -> Niacinamide).
        Return ONLY a comma-separated list. No other text.
        """
        with st.spinner(f'✨ AI đang đọc bảng thành phần...'):
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
    st.error("⚠️ Database đang trống! Vui lòng chạy file `data_importer_full.py`.")
    st.stop()

tab1, tab2 = st.tabs(["🔍 **Tra cứu Thủ công**", "📸 **Soi da & AI Vision**"])

# --- TAB 1 ---
with tab1:
    c1, c2 = st.columns(2)
    with c1: 
        i_a = st.selectbox("🧪 Hoạt chất 1:", list(id_to_name.keys()), format_func=lambda x:id_to_name[x], key="m_a")
    with c2: 
        i_b = st.selectbox("🧪 Hoạt chất 2:", list(id_to_name.keys()), format_func=lambda x:id_to_name[x], index=1, key="m_b")
    
    if st.button("⚡ Phân tích toàn diện", type="primary", use_container_width=True):
        st.divider()
        interaction = analyzer.check_interaction(i_a, i_b)
        risk_a, msg_a = analyzer.check_safety_for_user(i_a)
        risk_b, msg_b = analyzer.check_safety_for_user(i_b)
        
        st.subheader("1. Tương tác hoạt chất")
        if interaction:
            t, l, a = interaction
            if t=='CONFLICT': st.error(f"❌ **XUNG ĐỘT ({l})**: {a}")
            elif t=='SYNERGY': st.success(f"✅ **HỢP NHAU ({l})**: {a}")
            else: st.warning(f"⚠️ **THẬN TRỌNG ({l})**: {a}")
        else:
            st.info("✅ Hai chất này phối hợp an toàn.")
            
        st.subheader("2. Độ phù hợp với bạn")
        col_ra, col_rb = st.columns(2)
        with col_ra:
            st.markdown(f"**{id_to_name[i_a]}**")
            if risk_a == 'DANGER': st.error(msg_a)
            elif risk_a == 'WARNING': st.warning(msg_a)
            else: st.success(msg_a)
        with col_rb:
            st.markdown(f"**{id_to_name[i_b]}**")
            if risk_b == 'DANGER': st.error(msg_b)
            elif risk_b == 'WARNING': st.warning(msg_b)
            else: st.success(msg_b)

# --- TAB 2 ---
with tab2:
    # Nếu chưa có Key (cả hệ thống lẫn cá nhân) thì chặn
    if not is_ai_ready:
        st.warning("🔒 Vui lòng nhập API Key (hoặc liên hệ Admin) để mở khóa.")
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
                    else:
                        st.error("Không đọc được chữ nào.")

        with col_res:
            if st.session_state.scan_done and st.session_state.detected_ingredients:
                with st.expander(f"✅ AI tìm thấy {len(st.session_state.detected_ingredients)} chất", expanded=False):
                    st.write(", ".join([f"`{x}`" for x in st.session_state.detected_ingredients]))
                
                st.write("")
                st.markdown("##### 🛡️ Đối chiếu với Routine tại nhà")
                routine_name = st.selectbox("Bạn đang dùng chất gì ở nhà?", ["(Chọn chất)"] + list(id_to_name.values()), key="v_s")
                
                if routine_name != "(Chọn chất)":
                    st.divider()
                    st.write("📝 **Kết quả phân tích chi tiết:**")
                    
                    matched_count = 0
                    personal_risks = []
                    interaction_risks = []
                    
                    id_routine = None
                    for iid, name in id_to_name.items():
                        if name == routine_name: id_routine = iid; break
                    
                    for d_name in st.session_state.detected_ingredients:
                        for db_name_l, db_id in name_to_id.items():
                            if db_name_l in d_name.lower():
                                matched_count += 1
                                db_name_real = id_to_name[db_id]
                                p_risk, p_msg = analyzer.check_safety_for_user(db_id)
                                if p_risk in ['DANGER', 'WARNING']:
                                    personal_risks.append((db_name_real, p_risk, p_msg))
                                if id_routine and db_id != id_routine:
                                    inter = analyzer.check_interaction(db_id, id_routine)
                                    if inter:
                                        t, l, a = inter
                                        if t == 'CONFLICT': interaction_risks.append((f"❌ **XUNG ĐỘT**: {db_name_real} kỵ {routine_name}", a))
                                        elif t == 'CAUTION': interaction_risks.append((f"⚠️ **THẬN TRỌNG**: {db_name_real} và {routine_name}", a))
                                break
                    
                    if matched_count > 0:
                        if personal_risks:
                            st.error(f"🚫 **RỦI RO CHO DA {skin_code.upper()}:**")
                            for name, risk, msg in personal_risks:
                                if risk == 'DANGER': st.error(f"**{name}**: {msg}")
                                else: st.warning(f"**{name}**: {msg}")
                        
                        if interaction_risks:
                            st.warning(f"⚡ **LƯU Ý KHI DÙNG VỚI {routine_name}:**")
                            for title, desc in interaction_risks:
                                st.markdown(f"{title}\n> *{desc}*")
                        
                        if not personal_risks and not interaction_risks:
                            st.success(f"🎉 **AN TOÀN TUYỆT ĐỐI!**")
                            st.caption(f"(Đã kiểm tra {matched_count} chất)")
                    else:
                        st.info("⚠️ Chưa có dữ liệu khớp trong Database.")
            else:
                st.info("👈 Tải ảnh lên để bắt đầu.")
