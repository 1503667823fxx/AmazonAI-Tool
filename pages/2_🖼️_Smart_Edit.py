import streamlit as st
from PIL import Image
import sys
import os
import time

# --- 核心：修改引用路径 ---
# 不再引用通用的 services.llm_engine
try:
    import auth
    # 1. 引用通用基座 (鉴权)
    from services.core_base import BaseService
    
    # 2. 引用 [Smart Edit 专属] 服务
    from services.vision.prompt_manager import SmartEditPrompter
    from services.vision.generator import SmartEditGenerator
    from services.vision.styles_config import PRESETS
    
    # 3. 引用 [Smart Edit 专属] 工具
    from app_utils.vision_utils.media_tools import create_thumbnail, prepare_download
    from app_utils.vision_utils.ui_widgets import render_vision_sidebar
    
    # 4. 历史记录管理器暂时复用通用的，因为它不含业务逻辑 (或者你也想复制一份到 vision_utils?)
    from app_utils.history_manager import HistoryManager 

except ImportError as e:
    st.error(f"❌ 模块缺失: {e}")
    st.stop()

# --- 页面配置 ---
st.set_page_config(page_title="Smart Edit (Modular)", page_icon="🎨", layout="wide")

# CSS 样式 (保持不变)
st.markdown("""
    <style>
    [data-testid="stHorizontalBlock"] > [data-testid="column"]:nth-of-type(2) {
        position: sticky; top: 60px; height: 90vh; overflow-y: auto;
    }
    </style>
""", unsafe_allow_html=True)

# --- 初始化与鉴权 ---
if 'auth' in sys.modules and not auth.check_password(): st.stop()

if "vision_ctx" not in st.session_state:
    # 使用 BaseService 获取 Key，但用专属类实例化
    base = BaseService()
    if not base.is_valid:
        st.error("API Key 无效")
        st.stop()
        
    st.session_state.prompter = SmartEditPrompter(base.api_key)
    st.session_state.generator = SmartEditGenerator(base.api_key)
    st.session_state.history = HistoryManager(key="smart_edit_history") # 独立 Key 防止冲突
    st.session_state.vision_ctx = True
    
    # 临时数据容器
    st.session_state.edit_prompts = [] 
    st.session_state.edit_results = []

prompter = st.session_state.prompter
generator = st.session_state.generator
history = st.session_state.history

# --- 侧边栏 ---
render_vision_sidebar(history)

# --- 主界面逻辑 ---
st.title("🎨 Smart Edit (独立架构版)")

c_conf, c_view = st.columns([1.2, 1], gap="large")

# === 左侧：配置 ===
with c_conf:
    uploaded_files = st.file_uploader("上传参考图", type=["jpg","png","webp"], accept_multiple_files=True)
    
    active_ref = None
    if uploaded_files:
        imgs = [Image.open(f) for f in uploaded_files]
        active_ref = imgs[0] # 简化逻辑，取第一张作为主要参考
        st.image(active_ref, width=150, caption="当前参考图")

    user_req = st.text_area("创意描述", height=80, placeholder="例如：换成赛博朋克风格背景")
    
    col_s1, col_s2 = st.columns(2)
    style_key = col_s1.selectbox("风格", list(PRESETS.keys()))
    task_type = col_s2.selectbox("任务", ["展示图", "产品图"])

    # 1. 生成 Prompt
    if st.button("🧠 1. AI 优化指令", type="primary"):
        with st.spinner("思考中..."):
            res = prompter.optimize_prompt(user_req, task_type, style_key, active_ref)
            # 自动翻译并存入 state
            p_zh = user_req # 简单起见，或者调用 translate
            st.session_state.edit_prompts = [{"en": res[0], "zh": p_zh}]
            st.rerun()

    # 2. 编辑 Prompt
    if st.session_state.edit_prompts:
        p_data = st.session_state.edit_prompts[0]
        st.info(f"🇺🇸 Prompt: {p_data['en']}")
        
        # 3. 执行生成
        st.divider()
        model_name = st.selectbox("模型", ["models/gemini-3-pro-image-preview", "models/gemini-1.5-flash"])
        if st.button("🚀 2. 开始生成"):
            with st.spinner("绘制中..."):
                img_bytes = generator.generate_image(
                    prompt=p_data['en'],
                    model_name=model_name,
                    ref_image=active_ref
                )
                if img_bytes:
                    st.session_state.edit_results.append(img_bytes)
                    history.add(img_bytes, "Smart Edit", p_data['en'][:20])
                    st.toast("完成！")
                else:
                    st.error("生成失败")

# === 右侧：预览 ===
with c_view:
    st.subheader("🖼️ 结果")
    for img_data in st.session_state.edit_results:
        st.image(img_data, use_container_width=True)
        # 下载
        dl, mime = prepare_download(img_data)
        if dl:
            st.download_button("下载", dl, f"gen_{int(time.time())}.jpg", mime=mime)
