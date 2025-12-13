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
    from app_utils.ai_studio.state_manager import init_session_state, clear_history, undo_last_turn
    from app_utils.ai_studio.css_injector import inject_studio_css
    from app_utils.ai_studio.message_renderer import show_image_modal, render_studio_message
    from app_utils.ai_studio.tools import create_preview_thumbnail
    from services.ai_studio.vision_service import StudioVisionService
    from services.ai_studio.chat_service import StudioChatService
except ImportError as e:
    st.error(f"❌ 模块缺失: {e}")
    st.stop()

st.set_page_config(page_title="Amazon AI Studio", page_icon="🧪", layout="wide")
inject_studio_css()

# --- 1. 初始化 ---
if 'auth' in sys.modules and not auth.check_password(): st.stop()
init_session_state()

api_key = st.secrets.get("GOOGLE_API_KEY")

# --- 2. 侧边栏配置 ---
with st.sidebar:
    st.title("🧪 AI Workbench")
    
    model_map = {
        "⚡ Gemini Flash (Fast)": "models/gemini-flash-latest",
        "🎨 Gemini 3 Image (Image Gen)": "models/gemini-3-pro-image-preview", 
        "🧠 Gemini 3 Pro (Reasoning)": "models/gemini-3-pro-preview", 
    }
    selected_label = st.selectbox("Core Model", list(model_map.keys()))
    current_model_id = model_map[selected_label]
    is_image_mode = "image-preview" in current_model_id

    st.divider()

    if not is_image_mode:
        st.caption("🎭 System Persona")
        new_sys_prompt = st.text_area("Instruction", st.session_state.system_prompt_val, height=100)
        if new_sys_prompt != st.session_state.system_prompt_val:
            st.session_state.system_prompt_val = new_sys_prompt
            st.toast("System Prompt Updated!")

    c1, c2 = st.columns(2)
    if c1.button("🧹 Clear"): clear_history()
    if c2.button("↩️ Undo"): undo_last_turn()

# --- 3. 消息渲染与回调 ---
def delete_callback(idx):
    st.session_state.studio_msgs.pop(idx)
    st.rerun()

def regen_callback(idx):
    if st.session_state.studio_msgs[idx]["role"] == "model":
        st.session_state.studio_msgs.pop(idx)
        st.session_state.trigger_inference = True
        st.rerun()

if not st.session_state.studio_msgs:
    st.info("👋 开始你的创作。上传图片或输入指令...")
else:
    for idx, msg in enumerate(st.session_state.studio_msgs):
        render_studio_message(idx, msg, delete_callback, regen_callback)

# --- 4. 核心推理循环 ---
if st.session_state.get("trigger_inference", False):
    st.session_state.trigger_inference = False
    if not st.session_state.studio_msgs: st.rerun()

    last_msg = st.session_state.studio_msgs[-1]
    
    if last_msg["role"] == "user":
        with st.chat_message("model"):
            
            if is_image_mode:
                # === 视觉模式 ===
                with st.status("🎨 正在绘制...", expanded=True):
                    vision_svc = st.session_state.studio_vision_svc
                    
                    target_ref_img, info_text = vision_svc.resolve_reference_image(last_msg, st.session_state.studio_msgs)
                    if info_text: st.write(info_text)

                    hd_bytes = vision_svc.generate_image(
                        prompt=last_msg["content"],
                        model_name=current_model_id,
                        ref_image=target_ref_img
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
            else:
                # === 对话模式 ===
                placeholder = st.empty()
                full_resp = ""
                try:
                    chat_svc = StudioChatService(
                        api_key=api_key,
                        model_name=current_model_id, 
                        system_instruction=st.session_state.system_prompt_val
                    )
                    
                    history_msgs = st.session_state.studio_msgs[:-1]
                    chat_session = chat_svc.create_chat_session(history_msgs)
                    
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

# --- 5. 输入区 ---
if not st.session_state.get("trigger_inference", False):
    
    upload_key = f"uploader_{st.session_state.uploader_key_id}"
    
    with st.popover("📎", use_container_width=False):
        uploaded_files = st.file_uploader("参考图", type=["jpg", "png", "webp"], accept_multiple_files=True, key=upload_key)
        if uploaded_files: st.caption(f"已选 {len(uploaded_files)} 张")

    user_input = st.chat_input("输入指令...")

    if user_input:
        img_list = []
        if uploaded_files:
            for uf in uploaded_files:
                img_list.append(Image.open(uf))
        
        st.session_state.msg_uid += 1
        st.session_state.studio_msgs.append({
            "role": "user", "type": "text",
            "content": user_input, "ref_images": img_list,
            "id": st.session_state.msg_uid
        })
        
        st.session_state.uploader_key_id += 1
        st.session_state.trigger_inference = True
        st.rerun()
