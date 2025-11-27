import streamlit as st
import sys
import os

# 基础设置
sys.path.append(os.path.abspath('.'))

# 尝试导入核心库和子模块
try:
    import auth
    from core_utils import AITranslator, HistoryManager
    from tab4_workflow import render_tab1
    from tab2_restyling import render_tab2
    from tab3_background import render_tab3
    HAS_IMPORTS = True
except ImportError as e:
    st.error(f"核心模块导入失败: {e}")
    HAS_IMPORTS = False

# 页面配置
st.set_page_config(page_title="Fashion AI Core", page_icon="🧬", layout="wide")

# 门禁
if HAS_IMPORTS and 'auth' in sys.modules and not auth.check_password(): st.stop()

# API Key 检查
if "GOOGLE_API_KEY" in st.secrets:
    import google.generativeai as genai
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("❌ 未找到 GOOGLE_API_KEY"); st.stop()

# 初始化
if "translator" not in st.session_state and HAS_IMPORTS: 
    st.session_state.translator = AITranslator()
if "history_manager" not in st.session_state and HAS_IMPORTS: 
    st.session_state.history_manager = HistoryManager()

# 状态初始化
for key in ["std_prompt_data", "std_images", "batch_results", "bg_results"]:
    if key not in st.session_state: st.session_state[key] = []
for key in ["var_prompt_en", "var_prompt_zh", "bg_prompt_en", "bg_prompt_zh"]:
    if key not in st.session_state: st.session_state[key] = ""

# CSS
st.markdown("""
<style>
    .step-header { background: #f0f8ff; padding: 10px; border-left: 5px solid #2196F3; margin: 20px 0; font-weight: bold; }
    .stButton button { font-weight: bold; }
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] { height: 38px; white-space: pre-wrap; font-size: 14px; }
</style>
""", unsafe_allow_html=True)

# 常量
ANALYSIS_MODELS = ["models/gemini-flash-latest", "models/gemini-2.5-pro", "models/gemini-3-pro-preview"]
GOOGLE_IMG_MODELS = ["models/gemini-2.5-flash-image", "models/gemini-3-pro-image-preview"]
RATIO_MAP = {
    "1:1 (正方形)": ", crop 1:1 square ratio",
    "4:3 (横向)": ", 4:3 landscape ratio",
    "21:9 (宽屏)": ", 21:9 ultrawide ratio"
}

# --- Sidebar ---
with st.sidebar:
    st.title("🗂️ 工作区")
    dl_fmt = st.radio("📥 格式", ["PNG", "JPEG"], horizontal=True)
    if HAS_IMPORTS:
        st.session_state.history_manager.render_sidebar()

# --- Main ---
st.title("🧬 Fashion AI Core V5.6")

if HAS_IMPORTS:
    t1, t2, t3 = st.tabs(["✨ 标准精修", "⚡ 变体改款", "🏞️ 场景置换"])
    
    with t1:
        render_tab1(ANALYSIS_MODELS, GOOGLE_IMG_MODELS, RATIO_MAP, dl_fmt)
    
    with t2:
        render_tab2(ANALYSIS_MODELS, GOOGLE_IMG_MODELS, dl_fmt)
        
    with t3:
        render_tab3(ANALYSIS_MODELS, GOOGLE_IMG_MODELS, dl_fmt)
else:
    st.warning("系统模块加载不完整，请检查文件结构。")
