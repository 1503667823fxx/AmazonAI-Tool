import streamlit as st
import sys
import os
import datetime

# --- 0. 基础设置与门禁 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
except ImportError:
    pass 

# --- 1. 页面配置 ---
st.set_page_config(
    page_title="Amazon AI Hub",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. 样式优化 ---
st.markdown("""
<style>
    .welcome-header {
        font-size: 2.2rem;
        font-weight: 700;
        background: -webkit-linear-gradient(45deg, #090979, #00d4ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 10px;
    }
    .card-title {
        font-size: 1.2rem;
        font-weight: 600;
        color: #333;
        margin-bottom: 5px;
    }
    .card-desc {
        font-size: 0.9rem;
        color: #666;
        margin-bottom: 15px;
        min-height: 60px; 
    }
    .stButton button {
        width: 100%;
        border-radius: 8px;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 安全检查 ---
if 'auth' in sys.modules:
    if not auth.check_password():
        st.stop()

# --- 4. 侧边栏 ---
with st.sidebar:
    st.markdown("### 🖥️ Amazon AI Hub")
    st.success("🟢 System Online")
    st.info(f"📅 {datetime.date.today()}")
    st.divider()
    if st.button("🔒 退出登录"):
        st.session_state["authenticated"] = False
        st.rerun()

# --- 5. 主页内容 ---
st.markdown('<div class="welcome-header">Amazon 全能智造工作台</div>', unsafe_allow_html=True)
st.markdown("👋 欢迎回来，运营官。请选择下方的工作模块开始任务。")
st.divider()

# --- 6. 功能导航区 ---

# Row 1: Core Workflow
c1, c2 = st.columns(2, gap="medium")
with c1:
    with st.container(border=True):
        st.markdown('<div class="card-title">✍️ 1. Listing 智能文案</div>', unsafe_allow_html=True)
        st.caption("✅ V2.5 Stable | 引擎: Gemini 3.0 Pro")
        st.markdown('<div class="card-desc">SEO 文案撰写、五点描述、关键词埋词。支持合规性检查与多语言适配。</div>', unsafe_allow_html=True)
        st.page_link("pages/1_✍️_Listing_Copywriter.py", label="进入文案工作室", icon="🚀", use_container_width=True)

with c2:
    with st.container(border=True):
        st.markdown('<div class="card-title">🖼️ 2. Google 智造核心</div>', unsafe_allow_html=True)
        st.caption("✅ V6.1 Core | 引擎: Gemini Multimodal")
        st.markdown('<div class="card-desc">原生图生图、改款变体、场景置换。支持多任务拆分与批量生产。</div>', unsafe_allow_html=True)
        st.page_link("pages/2_🖼️_Smart_Edit.py", label="进入 Google 智造台", icon="🎨", use_container_width=True)

st.write("") 

# Row 2: Advanced Visuals
c3, c4 = st.columns(2, gap="medium")
with c3:
    with st.container(border=True):
        st.markdown('<div class="card-title">🖌️ 3. Magic Canvas (魔术画布)</div>', unsafe_allow_html=True)
        st.caption("🚧 Beta | 引擎: FLUX Fill Pro")
        st.markdown('<div class="card-desc">交互式局部重绘 (Inpainting) 与智能画幅扩展 (Outpainting)。</div>', unsafe_allow_html=True)
        st.page_link("pages/3_🖌️_Magic_Canvas.py", label="进入魔术画布", icon="🖌️", use_container_width=True)

with c4:
    with st.container(border=True):
        st.markdown('<div class="card-title">🎬 4. Video Studio</div>', unsafe_allow_html=True)
        st.caption("🚀 Beta | 引擎: Minimax / SVD")
        st.markdown('<div class="card-desc">电商短视频生成。支持图生视频 (Img2Vid) 及运镜控制。</div>', unsafe_allow_html=True)
        st.page_link("pages/4_🎬_Video_Studio.py", label="进入视频工场", icon="🎥", use_container_width=True)

st.write("")

# Row 3: Special Tools
c5, c6 = st.columns(2, gap="medium")
with c5:
    with st.container(border=True):
        st.markdown('<div class="card-title">🧩 5. A+ 创意工场</div>', unsafe_allow_html=True)
        st.caption("✨ New | 工具: Slicer & GIF Maker")
        st.markdown('<div class="card-desc">A+ 页面专属工具。长图智能切片、无缝拼接预览、动态 GIF 制作。</div>', unsafe_allow_html=True)
        st.page_link("pages/5_🧩_APlus_Studio.py", label="进入 A+ 工场", icon="🧩", use_container_width=True)

with c6:
    # Visual Studio 现在主要作为补充工具
    with st.container(border=True):
        st.markdown('<div class="card-title">🎨 视觉基础工场</div>', unsafe_allow_html=True)
        st.caption("🛠️ Utility | 引擎: Flux & ESRGAN")
        st.markdown('<div class="card-desc">纯文生图 (Text-to-Image) 与 4K 画质增强 (Upscale) 中心。</div>', unsafe_allow_html=True)
        st.page_link("pages/3_🎨_Visual_Studio.py", label="进入视觉基础", icon="🔭", use_container_width=True)

# --- 7. 底部 ---
st.divider()
st.caption("© 2025 Amazon AI Operation Team")
