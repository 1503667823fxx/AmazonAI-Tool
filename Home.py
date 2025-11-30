import streamlit as st
import sys
import os
import datetime

# --- 0. 基础设置与路径 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
except ImportError:
    pass

# --- 1. 页面配置 (默认收起侧边栏) ---
st.set_page_config(
    page_title="Amazon AI Hub",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="collapsed" # 默认收起
)

# --- 2. 深度样式定制 (CSS) ---
st.markdown("""
<style>
    /* 1. 隐藏 Home 页面的侧边栏导航，防止冲突 */
    [data-testid="stSidebarNav"] {
        display: none !important;
    }
    [data-testid="stSidebar"] {
        display: none !important;
    }
    
    /* 2. 全局字体与背景优化 */
    .main {
        background-color: #f8f9fa; /* 浅灰背景，提升层次感 */
    }
    
    /* 3. 标题样式 */
    .hero-title {
        font-size: 2.5rem;
        font-weight: 800;
        background: linear-gradient(120deg, #232F3E, #FF9900); /* Amazon 配色渐变 */
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .hero-subtitle {
        font-size: 1.1rem;
        color: #555;
        margin-bottom: 2rem;
    }

    /* 4. 卡片容器样式 */
    .tool-card {
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        transition: transform 0.2s, box-shadow 0.2s;
        height: 100%;
    }
    .tool-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 8px 15px rgba(0,0,0,0.1);
        border-color: #FF9900;
    }

    /* 5. 状态徽章样式 */
    .badge {
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        margin-left: 8px;
        vertical-align: middle;
    }
    .badge-stable { background-color: #e6fffa; color: #047857; border: 1px solid #047857; }
    .badge-beta { background-color: #fffaf0; color: #dd6b20; border: 1px solid #dd6b20; }
    .badge-dev { background-color: #f7fafc; color: #718096; border: 1px solid #718096; }
    
    /* 6. 分割线 */
    .section-header {
        font-size: 1.4rem;
        font-weight: 700;
        color: #232F3E;
        margin-top: 30px;
        margin-bottom: 15px;
        border-left: 5px solid #FF9900;
        padding-left: 10px;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 安全门禁 ---
if 'auth' in sys.modules:
    if not auth.check_password():
        st.stop()

# --- 4. 欢迎头部 ---
col_logo, col_text = st.columns([1, 8])
with col_logo:
    st.image("https://upload.wikimedia.org/wikipedia/commons/4/4a/Amazon_icon.svg", width=60) # 示例Logo，可换本地
with col_text:
    st.markdown('<div class="hero-title">Amazon AI Operation Hub</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-subtitle">全能智造工作台 · 高效赋能运营 | 当前状态: <span style="color:green">● System Online</span></div>', unsafe_allow_html=True)

# --- 5. 功能模块配置 ---
# 这是一个配置字典，方便统一管理状态
tools = {
    # 核心创作 - Stable
    "copywriter": {"path": "pages/1_✍️_Listing_Copywriter.py", "status": "Stable", "icon": "✍️", "title": "Listing 智能文案", "desc": "SEO 文案、五点描述、关键词优化 (V2.5)"},
    "visual": {"path": "pages/6_🎨_Visual_Studio.py", "status": "Stable", "icon": "🎨", "title": "Visual Studio 文生图", "desc": "产品海报生成、场景图绘制 (Flux 引擎)"},
    "smart_edit": {"path": "pages/2_🖼️_Smart_Edit.py", "status": "Stable", "icon": "🖼️", "title": "Smart Edit 图生图", "desc": "改款变体、场景置换、参考图生成"},
    
    # 视觉后期与工具 - Stable
    "batch": {"path": "pages/7_🔄_Batch_Variant.py", "status": "Stable", "icon": "🔄", "title": "批量变体工厂", "desc": "SKU 矩阵批量生产与处理"},
    "upscale": {"path": "pages/9_🔍_HD_Upscale.py", "status": "Stable", "icon": "🔍", "title": "HD Upscale 高清化", "desc": "图片无损放大、画质增强修复"},
    "resizer": {"path": "pages/10_📐_Smart_Resizer.py", "status": "Stable", "icon": "📐", "title": "Smart Resizer", "desc": "智能画幅调整、多平台尺寸适配"},

    # AI 实验室 - Beta/Dev
    "chat": {"path": "pages/8_💬_AI_Studio.py", "status": "Beta", "icon": "💬", "title": "AI 助手 (Chat)", "desc": "运营知识库问答、自由对话 (待优化)"},
    "canvas": {"path": "pages/3_🖌️_Magic_Canvas.py", "status": "Dev", "icon": "🖌️", "title": "Magic Canvas", "desc": "局部重绘与扩展 (开发攻坚中)"},

    # 规划中 - Roadmap
    "video": {"path": "pages/4_🎬_Video_Studio.py", "status": "Plan", "icon": "🎬", "title": "Video Studio", "desc": "电商短视频生成 (即将到来)"},
    "aplus": {"path": "pages/5_🧩_APlus_Studio.py", "status": "Plan", "icon": "🧩", "title": "A+ 创意工场", "desc": "A+ 页面长图拼接与切片 (概念阶段)"}
}

# 辅助函数：渲染徽章
def get_badge(status):
    if status == "Stable": return '<span class="badge badge-stable">✅ 稳定版</span>'
    if status == "Beta": return '<span class="badge badge-beta">🚧 公测版</span>'
    return '<span class="badge badge-dev">🛠️ 开发中</span>'

# --- 6. 核心创作区 (Tier 1: 高频使用) ---
st.markdown('<div class="section-header">🚀 核心创作 (Core Creative)</div>', unsafe_allow_html=True)
c1, c2, c3 = st.columns(3)

with c1:
    t = tools["copywriter"]
    with st.container(border=True):
        st.markdown(f"### {t['icon']} {t['title']} {get_badge(t['status'])}", unsafe_allow_html=True)
        st.caption(t['desc'])
        st.page_link(t['path'], label="开始撰写文案", icon="🚀", use_container_width=True)

with c2:
    t = tools["visual"]
    with st.container(border=True):
        st.markdown(f"### {t['icon']} {t['title']} {get_badge(t['status'])}", unsafe_allow_html=True)
        st.caption(t['desc'])
        st.page_link(t['path'], label="开始生成海报", icon="🎨", use_container_width=True)

with c3:
    t = tools["smart_edit"]
    with st.container(border=True):
        st.markdown(f"### {t['icon']} {t['title']} {get_badge(t['status'])}", unsafe_allow_html=True)
        st.caption(t['desc'])
        st.page_link(t['path'], label="进入修图中心", icon="🖼️", use_container_width=True)

# --- 7. 生产力工具箱 (Tier 2: 实用工具) ---
st.markdown('<div class="section-header">🛠️ 视觉后期与工具 (Utilities)</div>', unsafe_allow_html=True)
c4, c5, c6 = st.columns(3)

with c4:
    t = tools["batch"]
    with st.container(border=True):
        st.markdown(f"**{t['title']}** {get_badge(t['status'])}", unsafe_allow_html=True)
        st.caption(t['desc'])
        st.page_link(t['path'], label="进入批量任务", icon="⚡", use_container_width=True)

with c5:
    t = tools["upscale"]
    with st.container(border=True):
        st.markdown(f"**{t['title']}** {get_badge(t['status'])}", unsafe_allow_html=True)
        st.caption(t['desc'])
        st.page_link(t['path'], label="图片高清化", icon="🔍", use_container_width=True)

with c6:
    t = tools["resizer"]
    with st.container(border=True):
        st.markdown(f"**{t['title']}** {get_badge(t['status'])}", unsafe_allow_html=True)
        st.caption(t['desc'])
        st.page_link(t['path'], label="调整尺寸", icon="📐", use_container_width=True)

# --- 8. 实验室与规划 (Tier 3: Beta & Roadmap) ---
st.markdown('<div class="section-header">🧪 实验室与未来规划 (Labs & Roadmap)</div>', unsafe_allow_html=True)
c7, c8, c9, c10 = st.columns(4)

with c7:
    t = tools["chat"]
    with st.container(border=True):
        st.markdown(f"**{t['title']}** {get_badge(t['status'])}", unsafe_allow_html=True)
        st.caption(t['desc'])
        st.page_link(t['path'], label="进入对话", icon="💬", use_container_width=True)

with c8:
    t = tools["canvas"]
    with st.container(border=True):
        st.markdown(f"**{t['title']}**", unsafe_allow_html=True) # Dev状态不强调Badge，或手动置灰
        st.caption(f"状态: 🔴 维护中 | {t['desc']}")
        st.button("暂不可用", key="btn_canvas", disabled=True, use_container_width=True)

with c9:
    t = tools["video"]
    with st.container(border=True):
        st.markdown(f"**{t['title']}**", unsafe_allow_html=True)
        st.caption("状态: ⚪ 规划中 | 视频生成引擎")
        st.button("敬请期待", key="btn_video", disabled=True, use_container_width=True)

with c10:
    t = tools["aplus"]
    with st.container(border=True):
        st.markdown(f"**{t['title']}**", unsafe_allow_html=True)
        st.caption("状态: ⚪ 规划中 | A+ 拼图工具")
        st.button("待开发", key="btn_aplus", disabled=True, use_container_width=True)

# --- 9. 底部状态栏 ---
st.divider()
st.caption("© 2025 Amazon AI Team | Build 2.0.1 | Powered by Gemini & Flux")

