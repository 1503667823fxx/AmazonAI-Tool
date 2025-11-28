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

# --- CSS 样式 ---
st.markdown("""
<style>
    .block-container { padding-top: 1rem; padding-bottom: 8rem; }
    
    .stChatMessage {
        background-color: transparent;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        border: 1px solid rgba(255, 255, 255, 0.1);
    }
    .stChatMessage:hover {
        border-color: rgba(128, 128, 128, 0.3);
        background-color: rgba(240, 242, 246, 0.1);
    }

    /* 紧凑的操作栏 */
    .msg-actions {
        display: flex;
        gap: 12px;
        margin-top: 8px;
        opacity: 0.5;
        font-size: 0.85rem;
    }
    .stChatMessage:hover .msg-actions { opacity: 1; }
    
    /* 图片网格 */
    .img-grid {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        margin-bottom: 10px;
    }
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

# 消息结构更新: ref_image -> ref_images (list)
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
    """
    将图片转为 Bytes，兼容 PIL Image 和 bytes 类型。
    修复：如果输入已经是 bytes，则直接返回，避免 AttributeError。
    """
    if isinstance(img, bytes):
        return img
    
    # 如果是 PIL Image 对象，则进行转换
    buf = io.BytesIO()
    try:
        img.save(buf, format=format, quality=80)
    except Exception:
        # 兜底：如果 img 既不是 bytes 也不是 PIL，可能是 numpy array 等，尝试强制转换
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
    """构建 Gemini 历史，支持多图"""
    history = []
    for m in msgs:
        if m["type"] == "text" or m.get("ref_images"):
            parts = []
            # 添加多张图片
            if m.get("ref_images"):
                parts.extend(m["ref_images"])
            # 添加文本
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

# --- 4. 渲染消息流 ---
for idx, msg in enumerate(st.session_state.studio_msgs):
    is_editing = (st.session_state.editing_state and st.session_state.editing_state["idx"] == idx)
    
    with st.chat_message(msg["role"]):
        
        # === 编辑模式 ===
        if is_editing:
            new_val = st.text_area("Edit:", value=msg["content"], height=100)
            c1, c2 = st.columns([1, 6])
            if c1.button("Save", key=f"s_{msg['id']}"): save_edit(idx, new_val)
            if c2.button("Cancel", key=f"c_{msg['id']}"): cancel_edit()
        
        # === 浏览模式 ===
        else:
            # 1. 多图显示逻辑 (用户上传的参考图)
            if msg.get("ref_images"):
                cols = st.columns(len(msg["ref_images"]))
                for i, img in enumerate(msg["ref_images"]):
                    with cols[i]:
                        st.image(img, use_container_width=True)
            
            # 2. 内容显示
            if msg["type"] == "image_result":
                # 直接显示缩略图
                st.image(msg["content"], width=400)
                
                # 操作区
                act_cols = st.columns([1, 1, 4])
                with act_cols[0]:
                    # 🔍 优化点：放大预览不再请求 HD Data，而是直接用当前缩略图转 Bytes
                    # 这样就是秒开，只有模糊预览，符合您的要求
                    if st.button("🔍 Zoom", key=f"z_{msg['id']}"):
                        preview_bytes = pil_to_bytes(msg["content"]) # 将缩略图转为二进制
                        show_image_modal(preview_bytes, f"Preview-{msg['id']}")
                        
                with act_cols[1]:
                    # 📥 只有这里才下载高清原图
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
                # 文本内容
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

st.markdown("<div style='height: 120px;'></div>", unsafe_allow_html=True)

# --- 5. AI 推理逻辑 ---
if st.session_state.get("trigger_inference", False):
    st.session_state.trigger_inference = False
    
    if not st.session_state.studio_msgs: st.stop()
    last_msg = st.session_state.studio_msgs[-1]
    
    if last_msg["role"] == "user":
        with st.chat_message("model"):
            
            # A. 生图模式 (Image Gen)
            if is_image_mode:
                with st.status("🎨 Rendering...", expanded=True):
                    try:
                        # 生图通常只取第一张参考图 (多图控制较为复杂，暂取首张)
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

            # B. 文本/对话模式 (Text Chat)
            else:
                try:
                    placeholder = st.empty()
                    full_resp = ""
                    
                    # 构建历史
                    past_msgs = st.session_state.studio_msgs[:-1]
                    gemini_history = build_gemini_history(past_msgs)
                    
                    model = st.session_state.llm_studio.get_chat_model(current_model_id, sys_prompt)
                    chat = model.start_chat(history=gemini_history)
                    
                    # 构建当前多模态输入 [text, img1, img2, ...]
                    current_payload = []
                    if last_msg["content"]:
                        current_payload.append(last_msg["content"])
                    if last_msg.get("ref_images"):
                        current_payload.extend(last_msg["ref_images"])
                    
                    # 发送请求
                    response = chat.send_message(current_payload, stream=True)
                    
                    for chunk in response:
                        if chunk.text:
                            full_resp += chunk.text
                            placeholder.markdown(full_resp + "▌")
                    placeholder.markdown(full_resp)
                    
                    st.session_state.studio_msgs.append({
                        "role": "model", "type": "text",
                        "content": full_resp, "id": get_uid()
                    })
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

# --- 6. 底部输入区 (集成多文件上传) ---
if not st.session_state.get("trigger_inference", False):
    
    bottom_container = st.container()
    
    with bottom_container:
        # 使用 Popover 包装上传器，并改为 accept_multiple_files=True
        with st.popover("📎 添加附件", use_container_width=False):
            uploaded_files = st.file_uploader(
                "上传图片 (支持多选)", 
                type=["jpg", "png", "webp"], 
                accept_multiple_files=True, # 关键修改
                key="chat_uploader"
            )
            if uploaded_files:
                st.caption(f"✅ 已选择 {len(uploaded_files)} 张图片")

        user_input = st.chat_input("Message...")

    if user_input:
        # 处理多图
        img_list = []
        if uploaded_files:
            for uf in uploaded_files:
                img_list.append(Image.open(uf))
        
        st.session_state.studio_msgs.append({
            "role": "user",
            "type": "text",
            "content": user_input,
            "ref_images": img_list, # 存为列表
            "id": get_uid()
        })
        st.session_state.trigger_inference = True
        st.rerun()
