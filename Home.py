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
        min-height: 60px; /* 保证卡片高度对齐 */
    }
    /* 让按钮更显眼 */
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
    if st.button("🔒 退出登录 (Logout)"):
        st.session_state["authenticated"] = False
        st.rerun()

# --- 5. 欢迎区 ---
st.markdown('<div class="welcome-header">Amazon 全能智造工作台</div>', unsafe_allow_html=True)
st.markdown("👋 欢迎回来，运营官。请选择下方的工作模块开始任务。")
st.divider()

# --- 6. 功能导航区 (核心修改点) ---
# 使用 Streamlit 原生容器 + Page Link 实现跳转

# === 第一行 ===
c1, c2 = st.columns(2, gap="medium")

with c1:
    # 使用带边框的容器模拟卡片
    with st.container(border=True):
        st.markdown('<div class="card-title">✍️ 1. Listing 智能文案</div>', unsafe_allow_html=True)
        st.caption("✅ V2.5 Stable | 引擎: Gemini 3.0 Pro")
        st.markdown('<div class="card-desc">亚马逊 SEO 文案撰写、五点描述、关键词埋词。支持新规合规性检查。</div>', unsafe_allow_html=True)
        
        # 🚀 关键：跳转按钮
        # 请确保这里的字符串和你 pages 文件夹里的文件名一模一样！
        st.page_link("pages/1_✍️_Listing_Copywriter.py", label="进入文案工作室", icon="🚀", use_container_width=True)

with c2:
    with st.container(border=True):
        st.markdown('<div class="card-title">🖼️ 2. Google 智造核心</div>', unsafe_allow_html=True)
        st.caption("✅ V2.0 Core | 引擎: Gemini Multimodal")
        st.markdown('<div class="card-desc">原生图生图、创意构思、变体批量生产。支持电商比例控制与批量工厂。</div>', unsafe_allow_html=True)
        
        # 🚀 关键：跳转按钮
        # 如果你刚才把文件改名成了 Fashion_AI_Google_Core.py，这里要改成对应的名字
        # 这里假设你还是用截图里的名字 2_🖼️_Smart_Edit.py
        # 如果不对，请手动修改下面这行引号里的字
        st.page_link("pages/2_🖼️_Smart_Edit.py", label="进入 Google 智造台", icon="🎨", use_container_width=True)

# === 第二行 ===
st.write("") # 留白
c3, c4 = st.columns(2, gap="medium")

with c3:
    with st.container(border=True):
        st.markdown('<div class="card-title">🎨 3. Visual Studio (Flux)</div>', unsafe_allow_html=True)
        st.caption("🚧 Coming Soon | 引擎: FLUX.1 Pro")
        st.markdown('<div class="card-desc">视觉精修工作台。支持局部重绘 (Inpainting)、扩图 (Outpainting) 及 4K 增强。</div>', unsafe_allow_html=True)
        
        # 假设文件名是 3_🎨_Visual_Studio.py
        st.page_link("pages/3_🎨_Visual_Studio.py", label="进入视觉精修", icon="🛠️", use_container_width=True)

with c4:
    with st.container(border=True):
        st.markdown('<div class="card-title">🎬 4. Video Studio</div>', unsafe_allow_html=True)
        st.caption("🚀 Beta | 引擎: Minimax / SVD")
        st.markdown('<div class="card-desc">电商短视频生成。支持图生视频 (Img2Vid) 及运镜控制。</div>', unsafe_allow_html=True)
        
        # 假设文件名是 4_🎬_Video_Studio.py
        st.page_link("pages/4_🎬_Video_Studio.py", label="进入视频工场", icon="🎥", use_container_width=True)

# --- 7. 底部 ---
st.divider()
st.caption("© 2025 Amazon AI Operation Team")
