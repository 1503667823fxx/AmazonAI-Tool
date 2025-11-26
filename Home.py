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

# --- 2. 自定义 CSS (打造高级感) ---
st.markdown("""
<style>
    /* 全局背景微调 */
    .main {
        background-color: #f8f9fa;
    }
    /* 卡片样式 */
    .dashboard-card {
        background-color: #ffffff;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #e0e0e0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        height: 100%;
        transition: all 0.3s ease;
    }
    .dashboard-card:hover {
        box-shadow: 0 8px 15px rgba(0,0,0,0.1);
        transform: translateY(-2px);
        border-color: #2196F3;
    }
    /* 标题样式 */
    h3 {
        color: #1a1a1a;
        font-weight: 700;
    }
    /* 状态标签 */
    .badge {
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 12px;
        font-weight: bold;
        color: white;
    }
    .badge-green {background-color: #28a745;}
    .badge-blue {background-color: #007bff;}
    .badge-purple {background-color: #6f42c1;}
    .badge-orange {background-color: #fd7e14;}
    
    /* 欢迎语 */
    .welcome-header {
        font-size: 2.5rem;
        font-weight: 800;
        background: -webkit-linear-gradient(45deg, #090979, #00d4ff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 安全检查 ---
if 'auth' in sys.modules:
    if not auth.check_password():
        st.stop()

# --- 4. 侧边栏：系统状态 ---
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/commons/a/a9/Amazon_logo.svg", width=120)
    st.markdown("### 🖥️ 系统状态")
    st.success("🟢 API 服务在线")
    st.info(f"📅 日期: {datetime.date.today()}")
    
    st.markdown("---")
    st.markdown("### 🔑 核心引擎")
    st.caption("🧠 Gemini 2.5/3.0 Pro")
    st.caption("🎨 FLUX.1 Pro")
    st.caption("🎬 Minimax / SVD")

# --- 5. 主页头部 ---
col_header, col_logo = st.columns([3, 1])
with col_header:
    st.markdown('<div class="welcome-header">Amazon 全能智造工作台</div>', unsafe_allow_html=True)
    st.markdown("##### 🚀 Your All-in-One AI Operation System")
    st.markdown("欢迎回来，运营官。请从下方或左侧菜单选择您的工作站。")

st.markdown("---")

# --- 6. 核心功能矩阵 (2x2 布局) ---

# === 第一行：基础生产力 ===
c1, c2 = st.columns(2, gap="medium")

with c1:
    st.markdown("""
    <div class="dashboard-card">
        <h3>✍️ 1. Listing 智能文案</h3>
        <span class="badge badge-green">V2.5 Stable</span>
        <p style="margin-top:10px; color:#666;">
            <b>核心任务：</b> 亚马逊 SEO 文案撰写、五点描述、关键词埋词。<br>
            <b>引擎：</b> Gemini 3.0 Pro<br>
            <b>功能：</b> 
            <br>• 2025 新规合规性检查
            <br>• 竞品分析与反写
            <br>• 多语言自动适配
        </p>
    </div>
    """, unsafe_allow_html=True)

with c2:
    st.markdown("""
    <div class="dashboard-card">
        <h3>🖼️ 2. Google 智造核心 (Smart Edit)</h3>
        <span class="badge badge-blue">V2.0 Core</span>
        <p style="margin-top:10px; color:#666;">
            <b>核心任务：</b> 原生图生图、创意构思、变体批量生产。<br>
            <b>引擎：</b> Gemini 2.5/3.0 Multimodal<br>
            <b>功能：</b> 
            <br>• <b>Workstation:</b> 读图、写 Prompt、原生生图
            <br>• <b>Batch Factory:</b> 20+ 变体批量生成
            <br>• 电商比例自动控制
        </p>
    </div>
    """, unsafe_allow_html=True)

# === 第二行：高级工坊 ===
st.write("") # 增加一点垂直间距
c3, c4 = st.columns(2, gap="medium")

with c3:
    st.markdown("""
    <div class="dashboard-card">
        <h3>🎨 3. Flux 视觉精修 (Visual Studio)</h3>
        <span class="badge badge-purple">Coming Soon</span>
        <p style="margin-top:10px; color:#666;">
            <b>核心任务：</b> 局部重绘、扩图、超清修复。<br>
            <b>引擎：</b> FLUX.1 Pro / ControlNet<br>
            <b>功能：</b> 
            <br>• <b>Inpainting:</b> 局部换装、换模特
            <br>• <b>Upscale:</b> 4K 级画质增强
            <br>• <b>Outpainting:</b> 图片尺寸无损扩展
        </p>
    </div>
    """, unsafe_allow_html=True)

with c4:
    st.markdown("""
    <div class="dashboard-card">
        <h3>🎬 4. 视频工场 (Video Studio)</h3>
        <span class="badge badge-orange">Beta</span>
        <p style="margin-top:10px; color:#666;">
            <b>核心任务：</b> 电商短视频生成、动效制作。<br>
            <b>引擎：</b> Minimax / SVD<br>
            <b>功能：</b> 
            <br>• 图生视频 (Image-to-Video)
            <br>• 5s 商业展示短片
            <br>• 运镜控制 (Zoom/Pan)
        </p>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# --- 7. 系统日志 ---
with st.expander("📢 系统更新日志 (System Changelog)", expanded=False):
    st.markdown("""
    * **2025-05-27 (Architecture Update):**
        * 🏗️ **架构重组**: 正式确立 `1-文案`, `2-谷歌核心`, `3-Flux精修`, `4-视频` 的四步工作流。
        * 🖼️ **Smart Edit 上线**: 谷歌原生工作台 (Page 2) 升级为 V2.0，支持批量变体。
    * **2025-05-26:**
        * ✨ **视频模块**: Video Studio (Page 4) 进入公测。
        * 🔒 **安全**: 全站 API 密钥与门禁系统升级。
    """)

st.caption("© 2025 Amazon AI Operation Team | Design by Streamlit")
