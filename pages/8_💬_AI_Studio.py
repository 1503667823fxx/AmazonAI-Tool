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

# --- CSS 样式 (暴力修复版) ---
st.markdown("""
<style>
    /* 1. 滚动条修复：给底部留足空间 */
    .block-container { 
        padding-top: 1rem; 
        padding-bottom: 120px !important; 
    }
    
    /* 2. 暴力固定附件按钮 */
    /* 排除侧边栏，只针对主区域的 Popover */
    .stApp > header + div [data-testid="stPopover"] {
        position: fixed !important;
        bottom: 80px !important; /* 距离底部 80px */
        left: 20px !important;   /* 距离左侧 20px */
        z-index: 2147483647 !important; /* 最高层级 */
        width: 50px !important;
        height: 50px !important;
        background: transparent !important;
    }
    
    /* 针对按钮本身的样式 */
    .stApp > header + div [data-testid="stPopover"] > div > button {
        border-radius: 50% !important; /* 圆形 */
        width: 50px !important;
        height: 50px !important;
        padding: 0 !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
        background-color: white !important;
        color: #333 !important;
        border: 1px solid #ddd !important;
        font-size: 1.2rem !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    
    /* 暗黑模式适配 */
    @media (prefers-color-scheme: dark) {
        .stApp > header + div [data-testid="stPopover"] > div > button {
            background-color: #262730 !important;
            color: white !important;
            border: 1px solid #464b5d !important;
        }
    }

    /* 3. 消息气泡美化 */
    .stChatMessage {
        background-color: transparent;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        border: 1px solid rgba(128, 128, 128, 0.1);
    }
    
    /* 操作栏 */
    .msg-actions {
        display: flex;
        gap: 12px;
        margin-top: 8px;
        opacity: 0.5;
        font-size: 0.85rem;
    }
    .stChatMessage:hover .msg-actions { opacity: 1; }
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

# 数据结构初始化
if "studio_msgs" not in st.session_state:
    st.session_state.studio_msgs = []

if "editing_state" not in st.session_state:
    st.session_state.editing_state = None

if "msg_uid" not in st.session_state:
    st.session_state.msg_uid = 0

def get_uid():
    st.session_state.msg_uid += 1
    return st.session_state.msg_uid

# --- 2. 辅助工具 ---

def pil_to_bytes(img, format="JPEG"):
    """兼容 Bytes 和 PIL 的转换"""
    if isinstance(img, bytes):
        return img
    if img is None:
        return None
    
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
    """构建 Gemini 历史"""
    history = []
    for m in msgs:
        if m["type"] == "text" or m.get("ref_images"):
            parts = []
            if m.get("ref_images"):
                parts.extend(m["ref_images"])
            if m["content"]:
                parts.append(m["content"])
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

# --- 4. 消息渲染区 ---
for idx, msg in enumerate(st.session_state.studio_msgs):
    is_editing = (st.session_state.editing_state and st.session_state.editing_state["idx"] == idx)
    
    with st.chat_message(msg["role"]):
        
        # === A. 编辑模式 ===
        if is_editing:
            new_val = st.text_area("Edit:", value=msg["content"], height=100)
            c1, c2 = st.columns([1, 6])
            if c1.button("Save", key=f"s_{msg['id']}"): save_edit(idx, new_val)
            if c2.button("Cancel", key=f"c_{msg['id']}"): cancel_edit()
        
        # === B. 浏览模式 ===
        else:
            # 1. 垫图显示
            if msg.get("ref_images"):
                cols = st.columns(min(len(msg["ref_images"]), 4))
                for i, img in enumerate(msg["ref_images"]):
                    with cols[i]:
                        st.image(img, use_container_width=True)
            
            # 2. 内容显示
            if msg["type"] == "image_result":
                # 显示缩略图
                st.image(msg["content"], width=400)
                
                # 操作区
                act_cols = st.columns([1, 1, 4])
                with act_cols[0]:
                    # 快速放大预览
                    if st.button("🔍 Zoom", key=f"z_{msg['id']}"):
                        preview_bytes = pil_to_bytes(msg["content"])
                        if preview_bytes:
                            show_image_modal(preview_bytes, f"Preview-{msg['id']}")
                with act_cols[1]:
                    # 高清下载
                    st.download_button(
                        "📥", 
                        data=msg["hd_data"], 
                        file_name=f"gen_{msg['id']}.jpg", 
                        mime="image/jpeg", 
                        key=f"dl_{msg['id']}"
                    )
                with act_cols[2]:
                     if st.button("🗑️", key=f"del_{msg['id']}"): delete_msg(idx)

            else:
                st.markdown(msg["content"])
                
                # 文本操作栏
                st.markdown('<div class="msg-actions">', unsafe_allow_html=True)
                ac1, ac2, _ = st.columns([2, 1, 6])
                
                with ac1:
                    if msg["role"] == "user":
                        if st.button("✏️ Edit", key=f"ed_{msg['id']}"): start_edit(idx, msg["content"])
                    elif msg["role"] == "model":
                        if st.button("🔄 Regen", key=f"rg_{msg['id']}"): regenerate(idx)
                
                with ac2:
                    if st.button("🗑️ Del", key=f"dl_t_{msg['id']}"): delete_msg(idx)
                
                st.markdown('</div>', unsafe_allow_html=True)

# --- 5. AI 推理逻辑 ---
if st.session_state.get("trigger_inference", False):
    st.session_state.trigger_inference = False
    
    if not st.session_state.studio_msgs: st.stop()
    last_msg = st.session_state.studio_msgs[-1]
    
    if last_msg["role"] == "user":
        with st.chat_message("model"):
            
            # Image Gen
            if is_image_mode:
                with st.status("🎨 Rendering...", expanded=True):
                    try:
                        ref_img = last_msg["ref_images"][0] if last_msg.get("ref_images") else None
                        hd_bytes = st.session_state.img_gen_studio.generate(
                            prompt=last_msg["content"],
                            model_name=current_model_id,
                            ref_image=ref_img, 
                            ratio_suffix=f", aspect ratio {ratio.split()[0]}",
                            seed=int(seed_val) if seed_val != -1 else None
                        )
                        if hd_bytes:
                            thumb = create_preview_thumbnail(hd_bytes, 800)
                            st.session_state.studio_msgs.append({
                                "role": "model", "type": "image_result",
                                "content": thumb, "hd_data": hd_bytes, "id": get_uid()
                            })
                            st.rerun()
                        else:
                            st.error("⚠️ Filtered / Error")
                    except Exception as e:
                        st.error(f"Error: {e}")

            # Text Chat
            else:
                try:
                    placeholder = st.empty()
                    full_resp = ""
                    
                    past_msgs = st.session_state.studio_msgs[:-1]
                    gemini_history = build_gemini_history(past_msgs)
                    
                    model = st.session_state.llm_studio.get_chat_model(current_model_id, sys_prompt)
                    chat = model.start_chat(history=gemini_history)
                    
                    current_payload = []
                    if last_msg["content"]: current_payload.append(last_msg["content"])
                    if last_msg.get("ref_images"): current_payload.extend(last_msg["ref_images"])
                    
                    response = chat.send_message(current_payload, stream=True)
                    
                    for chunk in response:
