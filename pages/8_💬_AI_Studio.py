import streamlit as st
from PIL import Image
import sys
import os
import io

# --- 路径环境设置 ---
current_script_path = os.path.abspath(__file__)
pages_dir = os.path.dirname(current_script_path)
root_dir = os.path.dirname(pages_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

try:
    import auth
    from services.llm_engine import LLMEngine
    from services.image_engine import ImageGenEngine
    from app_utils.image_processing import create_preview_thumbnail
    from app_utils.ui_components import show_image_modal
except ImportError as e:
    st.error(f"❌ 核心模块导入失败: {e}")
    st.stop()

# --- 页面配置 ---
st.set_page_config(
    page_title="Amazon AI Studio",
    page_icon="🧪",
    layout="wide"
)

# --- CSS 终极优化 (Fixed UI & Smooth Scroll) ---
st.markdown("""
<style>
    /* 1. 全局滚动优化: 给底部留出巨大的缓冲空间，避免内容被遮挡 */
    .block-container { 
        padding-top: 1rem; 
        padding-bottom: 12rem; /* 增加到底部 12rem，给固定输入框留足位置 */
    }
    
    /* 2. 消息气泡样式 */
    .stChatMessage {
        background-color: transparent;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        border: 1px solid rgba(255, 255, 255, 0.05); /* 极淡的边框 */
    }
    .stChatMessage:hover {
        background-color: rgba(240, 242, 246, 0.1);
    }

    /* 3. 操作栏 */
    .msg-actions {
        display: flex;
        gap: 12px;
        margin-top: 8px;
        opacity: 0.4;
        font-size: 0.85rem;
        transition: opacity 0.2s;
    }
    .stChatMessage:hover .msg-actions { opacity: 1; }
    
    /* 4. [关键] 强制固定附件按钮的位置 */
    /* 这是一个 CSS Hack，将页面底部的 Popover 容器强制固定在屏幕下方 */
    div[data-testid="stPopover"] {
        position: fixed;
        bottom: 5rem; /* 位于 chat_input (约4rem高) 的上方 */
        z-index: 1000;
        /* 这里的 left/right 可能需要根据 Sidebar 状态微调，但在 wide 模式下通常没问题 */
    }
    
    /* 隐藏 Streamlit 自带的 footer */
    footer {visibility: hidden;}
    
</style>
""", unsafe_allow_html=True)

# --- 1. 初始化 ---
if 'auth' in sys.modules and not auth.check_password():
    st.stop()

if "studio_ready" not in st.session_state:
    api_key = st.secrets.get("GOOGLE_API_KEY")
    st.session_state.llm_studio = LLMEngine(api_key)
    st.session_state.img_gen_studio = ImageGenEngine(api_key)
    st.session_state.studio_ready = True

# 数据结构
if "studio_msgs" not in st.session_state:
    st.session_state.studio_msgs = []
if "editing_state" not in st.session_state:
    st.session_state.editing_state = None
if "msg_uid" not in st.session_state:
    st.session_state.msg_uid = 0

def get_uid():
    st.session_state.msg_uid += 1
    return st.session_state.msg_uid

# --- 2. 辅助工具 (含 Bug 修复) ---

def pil_to_bytes(img, format="JPEG"):
    """修复：兼容 bytes 和 PIL 对象"""
    if isinstance(img, bytes):
        return img
    buf = io.BytesIO()
    try:
        img.save(buf, format=format, quality=80)
    except Exception:
        return None 
    return buf.getvalue()

def delete_msg(idx):
    if 0 <= idx < len(st.session_state.studio_msgs):
        st.session_state.studio_msgs.pop(idx)
        st.rerun()

def start_edit(idx, content):
    st.session_state.editing_state = {"idx": idx, "content": content}
    st.rerun()

def save_edit(idx, new_content):
    st.session_state.studio_msgs[idx]["content"] = new_content
    st.session_state.studio_msgs = st.session_state.studio_msgs[:idx+1]
    st.session_state.editing_state = None
    st.session_state.trigger_inference = True
    st.rerun()

def cancel_edit():
    st.session_state.editing_state = None
    st.rerun()

def regenerate(idx):
    if st.session_state.studio_msgs[idx]["role"] == "model":
        st.session_state.studio_msgs.pop(idx)
        st.session_state.trigger_inference = True
        st.rerun()

def build_gemini_history(msgs):
    history = []
    for m in msgs:
        if m["type"] == "text" or m.get("ref_images"):
            parts = []
            if m.get("ref_images"): parts.extend(m["ref_images"])
            if m["content"]: parts.append(m["content"])
            if parts:
                history.append({"role": m["role"], "parts": parts})
    return history

# --- 3. 侧边栏 ---
with st.sidebar:
    st.title("🧪 AI Workbench")
    
    model_map = {
        "⚡ Gemini Flash (Fast)": "models/gemini-flash-latest",
        "🧠 Gemini 3 Pro (Reasoning)": "models/gemini-3-pro-preview", 
        "🎨 Gemini 3 Image (Image Gen)": "models/gemini-3-pro-image-preview" 
    }
    
    selected_label = st.selectbox("Model", list(model_map.keys()), label_visibility="collapsed")
    current_model_id = model_map[selected_label]
    is_image_mode = "image-preview" in current_model_id

    st.divider()

    if is_image_mode:
        st.caption("🎨 Image Config")
        ratio = st.selectbox("Ratio", ["1:1", "4:3", "3:4", "16:9"], index=0)
        seed_val = st.number_input("Seed", value=-1)
    else:
        st.caption("🧠 System Prompt")
        sys_prompt = st.text_area("System Instruction", value="You are a helpful Amazon assistant.", height=150)

    st.divider()
    if st.button("🗑️ New Chat", use_container_width=True):
        st.session_state.studio_msgs = []
        st.rerun()

# --- 4. 渲染消息流 ---
# 不使用 container 包裹，直接流式渲染，解决回弹问题
for idx, msg in enumerate(st.session_state.studio_msgs):
    is_editing = (st.session_state.editing_state and st.session_state.editing_state["idx"] == idx)
    
    with st.chat_message(msg["role"]):
        # 编辑模式
        if is_editing:
            new_val = st.text_area("Edit:", value=msg["content"], height=100)
            c1, c2 = st.columns([1, 6])
            if c1.button("Save", key=f"s_{msg['id']}"): save_edit(idx, new_val)
            if c2.button("Cancel", key=f"c_{msg['id']}"): cancel_edit()
        
        # 浏览模式
        else:
            # 多图预览
            if msg.get("ref_images"):
                # 限制预览大小，避免刷屏
                cols = st.columns(min(len(msg["ref_images"]), 4))
                for i, img in enumerate(msg["ref_images"]):
                    if i < 4:
                        with cols[i]: st.image(img, use_container_width=True)
            
            # 内容主体
            if msg["type"] == "image_result":
                st.image(msg["content"], width=400) # 默认显示缩略图
                
                # 图片操作栏
                act_cols = st.columns([1, 1, 4])
                with act_cols[0]:
                    # 快速放大 (使用 Bytes)
                    if st.button("🔍 Zoom", key=f"z_{msg['id']}"):
                        preview_bytes = pil_to_bytes(msg["content"])
                        if preview_bytes:
                            show_image_modal(preview_bytes, f"Preview-{msg['id']}")
