import streamlit as st
from PIL import Image
import sys
import os
import io

# --- 路径环境设置 ---
current_script_path = os.path.abspath(__file__)
pages_dir = os.path.dirname(current_script_path)
root_dir = os.path.dirname(pages_dir)
if root_dir not in sys.path: sys.path.append(root_dir)

try:
    import auth
    from services.image_engine import ImageGenEngine
    from app_utils.chat_manager import ChatSessionManager 
    from app_utils.ui_components import render_chat_message, inject_chat_css
    from app_utils.image_processing import create_preview_thumbnail
except ImportError as e:
    st.error(f"❌ 模块缺失: {e}")
    st.stop()

st.set_page_config(page_title="Amazon AI Studio", page_icon="🧪", layout="wide")

# ==========================================
# 🎨 CSS 修复：确保上传按钮像钉子一样钉在左下角
# ==========================================
inject_chat_css()
st.markdown("""
<style>
    /* 1. 调整底部内边距，给输入框留位 */
    .block-container {
        padding-bottom: 120px !important;
    }

    /* 2. 强力定位上传按钮 */
    /* 使用 [data-testid="stPopover"] 定位，覆盖所有层级 */
    div[data-testid="stPopover"] {
        position: fixed !important;
        bottom: 75px !important; /* 位于 chat_input 上方一点点，避免被遮挡 */
        left: 30px !important;   /* 钉在左侧 */
        z-index: 2147483647 !important; /*以此确保在最顶层*/
        width: 45px !important;
        height: 45px !important;
    }

    /* 3. 按钮样式美化 */
    div[data-testid="stPopover"] > div > button {
        border-radius: 50% !important;
        width: 45px !important;
        height: 45px !important;
        background-color: white !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15) !important;
        border: 1px solid #eee !important;
        color: #444 !important;
        font-size: 1.2rem !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
    }
    
    /* 悬停微动 */
    div[data-testid="stPopover"] > div > button:hover {
        transform: scale(1.1);
        color: #000 !important;
        border-color: #ccc !important;
    }

    /* 隐藏 footer 以免干扰 */
    footer {visibility: hidden;}
    
</style>
""", unsafe_allow_html=True)

# --- Session 初始化 ---
if 'auth' in sys.modules and not auth.check_password(): st.stop()

if "studio_msgs" not in st.session_state: st.session_state.studio_msgs = []
if "msg_uid" not in st.session_state: st.session_state.msg_uid = 0
if "uploader_key_id" not in st.session_state: st.session_state.uploader_key_id = 0
if "system_prompt_val" not in st.session_state: 
    st.session_state.system_prompt_val = "You are a helpful AI assistant for Amazon E-commerce sellers."

api_key = st.secrets.get("GOOGLE_API_KEY")
if "img_gen_studio" not in st.session_state:
    st.session_state.img_gen_studio = ImageGenEngine(api_key)

# --- 侧边栏 ---
with st.sidebar:
    st.title("🧪 AI Workbench")
    
    # 模型选择
    model_map = {
        "🧠 Gemini 3 Pro (Reasoning)": "models/gemini-3-pro-preview", 
        "⚡ Gemini Flash (Fast)": "models/gemini-flash-latest",
        "🎨 Gemini 3 Image (Image Gen)": "models/gemini-3-pro-image-preview" 
    }
    selected_label = st.selectbox("Core Model", list(model_map.keys()))
    current_model_id = model_map[selected_label]
    is_image_mode = "image-preview" in current_model_id

    st.divider()

    # System Prompt (仅 Chat 模式有效)
    if not is_image_mode:
        st.caption("🎭 System Persona")
        new_sys_prompt = st.text_area("Instruction", st.session_state.system_prompt_val, height=100)
        if new_sys_prompt != st.session_state.system_prompt_val:
            st.session_state.system_prompt_val = new_sys_prompt
            st.toast("System Prompt Updated!")

    # 清空 / 撤回
    c1, c2 = st.columns(2)
    if c1.button("🧹 Clear"):
        st.session_state.studio_msgs = []
        st.session_state.uploader_key_id += 1
        st.rerun()
    if c2.button("↩️ Undo"):
        if st.session_state.studio_msgs:
            st.session_state.studio_msgs.pop() # Del AI
            if st.session_state.studio_msgs and st.session_state.studio_msgs[-1]["role"] == "user":
                st.session_state.studio_msgs.pop() # Del User
            st.rerun()

# --- 消息渲染 ---
def delete_msg_callback(idx):
    st.session_state.studio_msgs.pop(idx)
    st.rerun()

def regenerate_callback(idx):
    if st.session_state.studio_msgs[idx]["role"] == "model":
        st.session_state.studio_msgs.pop(idx)
        st.session_state.trigger_inference = True
        st.rerun()

if not st.session_state.studio_msgs:
    st.info("👋 开始你的创作。上传图片或输入指令...")
else:
    for idx, msg in enumerate(st.session_state.studio_msgs):
        render_chat_message(idx, msg, delete_msg_callback, regenerate_callback)

# --- 核心推理逻辑 (Visual Logic Chain) ---
if st.session_state.get("trigger_inference", False):
    st.session_state.trigger_inference = False
    if not st.session_state.studio_msgs: st.rerun()

    last_msg = st.session_state.studio_msgs[-1]
    
    if last_msg["role"] == "user":
        with st.chat_message("model"):
            
            # === 模式 A: 生图 (支持连续编辑流) ===
            if is_image_mode:
                with st.status("🎨 正在绘制...", expanded=True):
                    try:
                        # 1. 确定参考图 (Reference Image)
                        target_ref_img = None
                        
                        # [优先级 1] 用户这一轮新上传了图
                        if last_msg.get("ref_images"):
                            target_ref_img = last_msg["ref_images"][0]
                            st.write("📸 使用本次上传的图片作为参考")
                        
                        # [优先级 2] 用户没传图，但上一轮 AI 生成了图 -> 视觉接力 (Visual Carry-over)
                        # 这就是解决你问题的关键逻辑
                        elif len(st.session_state.studio_msgs) >= 2:
                            prev_ai_msg = st.session_state.studio_msgs[-2]
                            # 检查上一条是不是 AI 发的，且是不是生图结果
                            if prev_ai_msg["role"] == "model" and prev_ai_msg.get("type") == "image_result" and prev_ai_msg.get("hd_data"):
                                # 将上一轮生成的 Bytes 转回 PIL Image
                                prev_bytes = prev_ai_msg["hd_data"]
                                target_ref_img = Image.open(io.BytesIO(prev_bytes))
                                st.write("🔗 自动引用上一张生成图作为底图 (连续编辑模式)")

                        # 2. 调用生图引擎
                        hd_bytes = st.session_state.img_gen_studio.generate(
                            prompt=last_msg["content"],
                            model_name=current_model_id,
                            ref_image=target_ref_img # 传入接力后的图片
                        )
                        
                        if hd_bytes:
                            thumb = create_preview_thumbnail(hd_bytes, 800)
                            st.session_state.studio_msgs.append({
                                "role": "model", "type": "image_result",
                                "content": thumb, "hd_data": hd_bytes, 
                                "id": st.session_state.msg_uid
                            })
                            st.rerun()
                        else:
                            st.error("生成失败或被拦截")
                            
                    except Exception as e:
                        st.error(f"Error: {e}")

            # === 模式 B: 聊天 (调用 Chat Manager) ===
            else:
                placeholder = st.empty()
                full_resp = ""
                try:
                    chat_manager = ChatSessionManager(
                        model_name=current_model_id, 
                        api_key=api_key,
                        system_instruction=st.session_state.system_prompt_val
                    )
                    
                    history_msgs = st.session_state.studio_msgs[:-1]
                    chat_session = chat_manager.start_chat_session(history_msgs)
                    
                    current_payload = []
                    if last_msg.get("ref_images"): current_payload.extend(last_msg["ref_images"])
                    if last_msg["content"]: current_payload.append(last_msg["content"])
                    
                    response = chat_session.send_message(current_payload, stream=True)
                    
                    for chunk in response:
                        if chunk.text:
                            full_resp += chunk.text
                            placeholder.markdown(full_resp + "▌")
                    placeholder.markdown(full_resp)
                    
                    st.session_state.msg_uid += 1
                    st.session_state.studio_msgs.append({
                        "role": "model", "type": "text", 
                        "content": full_resp, "id": st.session_state.msg_uid
                    })
                    st.rerun()
                except Exception as e:
                    st.error(f"Chat Error: {e}")

# --- 底部输入区 ---
if not st.session_state.get("trigger_inference", False):
    
    upload_key = f"uploader_{st.session_state.uploader_key_id}"
    
    # 悬浮按钮 (CSS 已强制固定)
    with st.popover("📎", use_container_width=False):
        uploaded_files = st.file_uploader(
            "参考图", 
            type=["jpg", "png", "webp"], 
            accept_multiple_files=True,
            key=upload_key
        )
        if uploaded_files:
            st.caption(f"已选 {len(uploaded_files)} 张")

    user_input = st.chat_input("输入指令...")

    if user_input:
        img_list = []
        if uploaded_files:
            for uf in uploaded_files:
                img_list.append(Image.open(uf))
        
        st.session_state.msg_uid += 1
        st.session_state.studio_msgs.append({
            "role": "user",
            "type": "text",
            "content": user_input,
            "ref_images": img_list,
            "id": st.session_state.msg_uid
        })
        
        st.session_state.uploader_key_id += 1
        st.session_state.trigger_inference = True
        st.rerun()
