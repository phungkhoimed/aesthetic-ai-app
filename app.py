import streamlit as st
from database_utils import get_connection
from services import SkinAnalyzer # Gọi "Bộ não" xử lý logic từ file services.py
from PIL import Image
import google.generativeai as genai

# =====================================================
# 1. CẤU HÌNH HỆ THỐNG & TRẠNG THÁI (STATE)
# =====================================================
st.set_page_config(page_title="Aesthetic AI Pro", page_icon="✨", layout="wide")

# Khởi tạo bộ nhớ tạm (Session State) để lưu kết quả AI khi web reload
if 'detected_ingredients' not in st.session_state:
    st.session_state.detected_ingredients = []
if 'scan_done' not in st.session_state:
    st.session_state.scan_done = False

# CSS tùy chỉnh cho giao diện đẹp hơn
st.markdown("""
<style>
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { padding-top: 10px; padding-bottom: 10px; }
    div[data-testid="stExpander"] details summary p { font-weight: 600; font-size: 1rem; }
    .stAlert { padding: 10px; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

# =====================================================
# 2. SIDEBAR: CẤU HÌNH & HỒ SƠ NGƯỜI DÙNG
# =====================================================
with st.sidebar:
    st.header("👤 Hồ sơ Da liễu")
    
    # 2.1 Thu thập thông tin cá nhân hóa
    skin_type = st.selectbox("Loại da của bạn:", 
                             ["Normal (Thường)", "Oily (Dầu)", "Dry (Khô)", "Sensitive (Nhạy cảm)", "Acne-Prone (Dễ nổi mụn)"])
    is_pregnant = st.checkbox("Đang mang thai / Cho con bú? 🤰")
    
    # Mapping tên loại da cho khớp với logic trong services.py
    skin_code = skin_type.split(" ")[0] # Lấy chữ "Oily", "Dry"...
    
    # KHỞI TẠO "BỘ NÃO" ANALYZER
    # Đây là bước quan trọng: Truyền hồ sơ vào service để xử lý logic
    user_profile = {"skin_type": skin_code, "is_pregnant": is_pregnant}
    analyzer = SkinAnalyzer(user_profile)
    
    # Hiển thị trạng thái hồ sơ
    st.info(f"Chế độ phân tích: **{skin_code}**")
    if is_pregnant: 
        st.warning("⚠️ Chế độ an toàn thai kỳ: BẬT")

    st.markdown("---")
    st.header("⚙️ Cấu hình AI")
    api_key_input = st.text_input("Google API Key:", type="password")
    
    is_ai_ready = False
    best_model_name = None

    # 2.2 Kết nối Google Gemini (Auto-Detect Model)
    if api_key_input:
        try:
            genai.configure(api_key=api_key_input)
            try:
                all_models = [m.name for m in genai.list_models()]
                # Ưu tiên các model mới nhất
                if 'models/gemini-2.5-flash' in all_models: best_model_name = 'gemini-2.5-flash'
                elif 'models/gemini-1.5-flash' in all_models: best_model_name = 'gemini-1.5-flash'
                else: best_model_name = 'gemini-pro'
            except:
                best_model_name = 'gemini-1.5-flash' # Fallback an toàn
            
            st.success(f"AI đã sẵn sàng 🟢")
            is_ai_ready = True
        except: 
            st.error("Key không hợp lệ")
    else: 
        st.warning("Vui lòng nhập API Key")
        
    st.caption(f"Engine: `{best_model_name or '---'}`")

# =====================================================
# 3. CÁC HÀM HỖ TRỢ (HELPER FUNCTIONS)
# =====================================================
def get_all_ingredients():
    """Lấy danh sách tên hoạt chất từ Database để đổ vào ô chọn"""
    conn = get_connection()
    if not conn: return []
    cursor = conn.cursor()
    cursor.execute("SELECT ingredient_id, inci_name FROM Ingredients ORDER BY inci_name")
    data = cursor.fetchall()
    conn.close()
    return data

def analyze_image_with_gemini(image_file, model_name):
    """Gửi ảnh lên Google AI để trích xuất văn bản (OCR)"""
    try:
        if not model_name: model_name = 'gemini-1.5-flash'
        model = genai.GenerativeModel(model_name)
        img = Image.open(image_file)
        
        prompt = """
        Extract all chemical ingredient names from this skincare product label image.
        Standardize names to INCI format (e.g., Vitamin B3 -> Niacinamide).
        Return ONLY a comma-separated list. No other text.
        Example output: Water, Glycerin, Retinol, Salicylic Acid
        """
        
        with st.spinner(f'✨ AI đang đọc bảng thành phần...'):
            response = model.generate_content([prompt, img])
        text = response.text.strip()
        
        if text:
            return [x.strip() for x in text.split(',')]
        return []
    except Exception as e:
        st.error(f"Lỗi kết nối AI: {e}")
        return []

# =====================================================
# 4. GIAO DIỆN CHÍNH (MAIN UI)
# =====================================================
st.title("✨ Trợ lý Da liễu AI (Pro)")
st.markdown(f"#### *Cá nhân hóa cho làn da: {skin_type}*")
st.markdown("---")

# Load dữ liệu nền
ingredients_list = get_all_ingredients()
# Tạo từ điển tra cứu: ID -> Tên và Tên -> ID
id_to_name = {item['ingredient_id']: item['inci_name'] for item in ingredients_list}
name_to_id = {item['inci_name'].lower(): item['ingredient_id'] for item in ingredients_list}

if not ingredients_list:
    st.error("⚠️ Database đang trống! Vui lòng chạy file `data_importer_full.py` để nạp dữ liệu.")
    st.stop() # Dừng chương trình nếu không có dữ liệu

# Chia Tab chức năng
tab1, tab2 = st.tabs(["🔍 **Tra cứu Thủ công**", "📸 **Soi da & AI Vision**"])

# -----------------------------------------------------
# TAB 1: TRA CỨU THỦ CÔNG (MANUAL CHECK)
# -----------------------------------------------------
with tab1:
    c1, c2 = st.columns(2)
    with c1: 
        i_a = st.selectbox("🧪 Hoạt chất 1:", list(id_to_name.keys()), format_func=lambda x:id_to_name[x], key="m_a")
    with c2: 
        i_b = st.selectbox("🧪 Hoạt chất 2:", list(id_to_name.keys()), format_func=lambda x:id_to_name[x], index=1, key="m_b")
    
    if st.button("⚡ Phân tích toàn diện", type="primary", use_container_width=True):
        st.divider()
        
        # 1. GỌI SERVICE: Kiểm tra Tương tác (Interaction)
        interaction = analyzer.check_interaction(i_a, i_b)
        
        # 2. GỌI SERVICE: Kiểm tra An toàn Cá nhân (Personal Safety)
        risk_a, msg_a = analyzer.check_safety_for_user(i_a)
        risk_b, msg_b = analyzer.check_safety_for_user(i_b)
        
        # Hiển thị Kết quả Tương tác
        st.subheader("1. Tương tác hoạt chất")
        if interaction:
            t, l, a = interaction
            if t=='CONFLICT': st.error(f"❌ **XUNG ĐỘT ({l})**: {a}")
            elif t=='SYNERGY': st.success(f"✅ **HỢP NHAU ({l})**: {a}")
            else: st.warning(f"⚠️ **THẬN TRỌNG ({l})**: {a}")
        else:
            st.info("✅ Hai chất này phối hợp an toàn với nhau.")
            
        # Hiển thị Kết quả Cá nhân hóa
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

# -----------------------------------------------------
# TAB 2: AI VISION (IMAGE ANALYSIS)
# -----------------------------------------------------
with tab2:
    if not is_ai_ready:
        st.warning("🔒 Vui lòng nhập API Key ở thanh bên trái để mở khóa tính năng này.")
    else:
        # Bố cục chia cột: Ảnh (Nhỏ) | Kết quả (To)
        col_img, col_res = st.columns([1, 2], gap="medium")
        
        with col_img:
            st.caption("Tải ảnh bảng thành phần:")
            uploaded_file = st.file_uploader("", type=['jpg', 'png', 'jpeg'], label_visibility="collapsed")
            
            if uploaded_file:
                st.image(uploaded_file, caption="Ảnh sản phẩm", use_container_width=True)
                
                # Nút bấm gọi AI
                if st.button("🚀 Quét ngay", type="primary", use_container_width=True):
                    detected = analyze_image_with_gemini(uploaded_file, best_model_name)
                    if detected:
                        # Lưu vào Session State để không bị mất khi reload
                        st.session_state.detected_ingredients = detected
                        st.session_state.scan_done = True
                    else:
                        st.error("Không đọc được chữ nào từ ảnh.")

        with col_res:
            # Chỉ hiển thị khi đã quét xong
            if st.session_state.scan_done and st.session_state.detected_ingredients:
                
                # 1. Danh sách chất tìm thấy (Thu gọn)
                with st.expander(f"✅ AI tìm thấy {len(st.session_state.detected_ingredients)} chất (Bấm để xem)", expanded=False):
                    st.write(", ".join([f"`{x}`" for x in st.session_state.detected_ingredients]))
                
                st.write("")
                # 2. Chọn Routine để đối chiếu
                st.markdown("##### 🛡️ Đối chiếu với Routine tại nhà")
                routine_name = st.selectbox("Bạn đang dùng chất gì ở nhà?", ["(Chọn chất)"] + list(id_to_name.values()), key="v_s")
                
                if routine_name != "(Chọn chất)":
                    st.divider()
                    st.write("📝 **Kết quả phân tích chi tiết:**")
                    
                    # --- LOGIC PHÂN TÍCH TỔNG HỢP ---
                    matched_count = 0
                    personal_risks = []     # Rủi ro cá nhân (Da dầu, Bầu bí)
                    interaction_risks = []  # Rủi ro tương tác (Kỵ nhau)
                    
                    # Lấy ID của chất Routine đang chọn
                    id_routine = None
                    for iid, name in id_to_name.items():
                        if name == routine_name: id_routine = iid; break
                    
                    # Vòng lặp quét từng chất AI tìm thấy
                    for d_name in st.session_state.detected_ingredients:
                        # Tìm kiếm mờ (Fuzzy search) trong Database
                        for db_name_l, db_id in name_to_id.items():
                            if db_name_l in d_name.lower(): # Nếu tìm thấy trong DB
                                matched_count += 1
                                db_name_real = id_to_name[db_id]
                                
                                # A. GỌI SERVICE: Check Cá nhân hóa
                                p_risk, p_msg = analyzer.check_safety_for_user(db_id)
                                if p_risk in ['DANGER', 'WARNING']:
                                    personal_risks.append((db_name_real, p_risk, p_msg))
                                
                                # B. GỌI SERVICE: Check Tương tác với Routine
                                if id_routine and db_id != id_routine:
                                    inter = analyzer.check_interaction(db_id, id_routine)
                                    if inter:
                                        t, l, a = inter
                                        if t == 'CONFLICT':
                                            interaction_risks.append((f"❌ **XUNG ĐỘT**: {db_name_real} kỵ {routine_name}", a))
                                        elif t == 'CAUTION':
                                            interaction_risks.append((f"⚠️ **THẬN TRỌNG**: {db_name_real} và {routine_name}", a))
                                break # Đã tìm thấy match, thoát vòng lặp tên DB
                    
                    # --- HIỂN THỊ KẾT QUẢ ---
                    if matched_count > 0:
                        # 1. Hiển thị rủi ro cá nhân trước (Ưu tiên cao nhất)
                        if personal_risks:
                            st.error(f"🚫 **PHÁT HIỆN RỦI RO CHO DA {skin_code.upper()}:**")
                            for name, risk, msg in personal_risks:
                                if risk == 'DANGER': st.error(f"**{name}**: {msg}")
                                else: st.warning(f"**{name}**: {msg}")
                        
                        # 2. Hiển thị rủi ro tương tác
                        if interaction_risks:
                            st.warning(f"⚡ **LƯU Ý KHI DÙNG CHUNG VỚI {routine_name}:**")
                            for title, desc in interaction_risks:
                                st.markdown(f"{title}\n> *{desc}*")
                        
                        # 3. Nếu an toàn
                        if not personal_risks and not interaction_risks:
                            st.success(f"🎉 **AN TOÀN TUYỆT ĐỐI!**\nSản phẩm này phù hợp với da **{skin_code}** và dùng tốt với **{routine_name}**.")
                            st.caption(f"(Hệ thống đã kiểm tra trên {matched_count} hoạt chất được nhận diện trong DB)")
                    else:
                        st.info("⚠️ AI đọc được chữ, nhưng các chất này chưa có trong Database của bạn (Hãy nạp thêm dữ liệu).")
            else:
                st.info("👈 Hãy tải ảnh lên để bắt đầu.")