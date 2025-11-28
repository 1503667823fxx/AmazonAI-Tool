import streamlit as st
from PIL import Image
import sys
import os

# --- 路径环境设置 ---
current_script_path = os.path.abspath(__file__)
pages_dir = os.path.dirname(current_script_path)
root_dir = os.path.dirname(pages_dir)
if root_dir not in sys.path: sys.path.append(root_dir)

try:
    import auth
    from services.image_engine import ImageGenEngine
    # ✅ 引入新的逻辑链管理器
    from app_utils.chat_manager import ChatSessionManager 
    from app_utils.ui_components import render_chat_message, inject_chat_css
    from app_utils.image_processing import create_preview_thumbnail
except ImportError as e:
    st.error(f"❌ 模块缺失: {e}")
    st.stop()

st.set_page_config(page_title="Amazon AI Studio", page_icon="🧪", layout="wide")

# 1. 注入 CSS (保持您之前的样式)
inject_chat_css()
st.markdown("""
<style>
    /* 强制上传按钮在左下角 */
    section.main [data-testid="stPopover"] {
        position: fixed !important; bottom: 25px !important; left: 20px !important; z-index: 99999 !important;
        width: 45px !important; height: 45px !important;
    }
    section.main [data-testid="stPopover"] > div > button {
        border-radius: 50% !important; width: 45px !important; height: 45px !important;
        background-color: #fff !important; box-shadow: 0 4px 10px rgba(0,0,0,0.1) !important;
    } 
</style>
""", unsafe_allow_html=True)

# --- Session 初始化 ---
if 'auth' in sys.modules and not auth.check_password(): st.stop()

# 基础状态
if "studio_msgs" not in st.session_state: st.session_state.studio_msgs = []
if "msg_uid" not in st.session_state: st.session_state.msg_uid = 0
if "uploader_key_id" not in st.session_state: st.session_state.uploader_key_id = 0
if "system_prompt_val" not in st.session_state: 
    st.session_state.system_prompt_val = "You are a helpful AI assistant for Amazon E-commerce sellers. Analyze images and text professionally."

# API 初始化
api_key = st.secrets.get("GOOGLE_API_KEY")
if not api_key:
    st.error("请配置 GOOGLE_API_KEY")
    st.stop()

if "img_gen_studio" not in st.session_state:
    st.session_state.img_gen_studio = ImageGenEngine(api_key)

# --- 侧边栏 ---
with st.sidebar:
    st.title("🧪 AI Workbench")
    
    # A. 模型选择
    model_map = {
        "🧠 Gemini 3 Pro (Reasoning)": "models/gemini-3-pro-preview", 
        "⚡ Gemini Flash (Fast)": "models/gemini-flash-latest",
        "🎨 Gemini 3 Image (Image Gen)": "models/gemini-3-pro-image-preview" 
    }
    selected_label = st.selectbox("Core Model", list(model_map.keys()))
    current_model_id = model_map[selected_label]
    is_image_mode = "image-preview" in current_model_id

    st.divider()

    # B. 系统设定 (System Prompt) - 这才是对话的灵魂
    if not is_image_mode:
        st.caption("🎭 System Persona")
        new_sys_prompt = st.text_area(
            "System Instruction", 
            value=st.session_state.system_prompt_val,
            height=100,
            help="定义 AI 的身份，例如：'你是一个资深时尚买手' 或 '你是一个Python代码专家'。"
        )
        # 保存 System Prompt 变动
        if new_sys_prompt != st.session_state.system_prompt_val:
            st.session_state.system_prompt_val = new_sys_prompt
            # System Prompt 变了，最好清空历史，或者让用户知道上下文变了
            st.toast("System Prompt Updated!", icon="💾")

    st.divider()
    
    # C. 操作区
    col_k1, col_k2 = st.columns(2)
    with col_k1:
        if st.button("🧹 Clear", use_container_width=True):
            st.session_state.studio_msgs = []
            st.session_state.uploader_key_id += 1 
            st.rerun()
    with col_k2:
        if st.button("↩️ Undo", use_container_width=True):
            if st.session_state.studio_msgs:
                st.session_state.studio_msgs.pop() # 删掉 Model 回复
                if st.session_state.studio_msgs and st.session_state.studio_msgs[-1]["role"] == "user":
                   st.session_state.studio_msgs.pop() # 也删掉 User 提问，彻底回退一步
                st.rerun()

# --- 消息渲染 ---
def delete_msg_callback(idx):
    if 0 <= idx < len(st.session_state.studio_msgs):
        st.session_state.studio_msgs.pop(idx)
        st.rerun()

def regenerate_callback(idx):
    # 重新生成逻辑：删掉当前的 AI 回复，触发重新推理
    if st.session_state.studio_msgs[idx]["role"] == "model":
        st.session_state.studio_msgs.pop(idx)
        st.session_state.trigger_inference = True
        st.rerun()

if not st.session_state.studio_msgs:
    st.info("👋 Ready via **Chat Manager**. Upload images or text to start.")
else:
    for idx, msg in enumerate(st.session_state.studio_msgs):
        render_chat_message(idx, msg, delete_msg_callback, regenerate_callback)

# --- 核心推理逻辑 (The Logical Chain) ---
if st.session_state.get("trigger_inference", False):
    st.session_state.trigger_inference = False
    if not st.session_state.studio_msgs: st.rerun()

    last_msg = st.session_state.studio_msgs[-1]
    
    # 只有当最后一条是用户发的消息时，才触发 AI 回复
    if last_msg["role"] == "user":
        with st.chat_message("model"):
            
            # === 分支 A: 生图模式 (无上下文逻辑，单次生成) ===
            if is_image_mode:
                with st.status("🎨 Rendering...", expanded=True):
                    try:
                        ref_img = last_msg["ref_images"][0] if last_msg.get("ref_images") else None
                        hd_bytes = st.session_state.img_gen_studio.generate(
                            prompt=last_msg["content"],
                            model_name=current_model_id,
                            ref_image=ref_img
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
                            st.error("Generation Failed / Blocked.")
                    except Exception as e:
                        st.error(f"Error: {e}")

            # === 分支 B: 智能对话模式 (调用 Chat Manager) ===
            else:
                placeholder = st.empty()
                full_resp = ""
                
                try:
                    # 1. 初始化逻辑大脑 (传入 System Prompt)
                    chat_manager = ChatSessionManager(
                        model_name=current_model_id, 
                        api_key=api_key,
                        system_instruction=st.session_state.system_prompt_val
                    )
                    
                    # 2. 构建历史上下文 (不包含当前的最后一条)
                    # 注意：我们把除最后一条之外的所有消息，交给 Manager 去清洗、合并
                    history_msgs = st.session_state.studio_msgs[:-1]
                    chat_session = chat_manager.start_chat_session(history_msgs)
                    
                    # 3. 准备当前发送的内容 (User Turn)
                    current_payload = []
                    # 附件 (图片)
                    if last_msg.get("ref_images"): 
                        current_payload.extend(last_msg["ref_images"])
                    # 文本
                    if last_msg["content"]: 
                        current_payload.append(last_msg["content"])
                    
                    # 4. 发送给 Gemini
                    # stream=True 让体验像真实对话一样流畅
                    response = chat_session.send_message(current_payload, stream=True)
                    
                    for chunk in response:
                        if chunk.text:
                            full_resp += chunk.text
                            placeholder.markdown(full_resp + "▌")
                    placeholder.markdown(full_resp)
                    
                    # 5. 记录回复
                    st.session_state.msg_uid += 1
                    st.session_state.studio_msgs.append({
                        "role": "model", "type": "text", 
                        "content": full_resp, "id": st.session_state.msg_uid
                    })
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Logic Chain Error: {e}")
                    # 调试用：显示具体的错误栈
                    # st.exception(e)

# --- 底部输入区 ---
if not st.session_state.get("trigger_inference", False):
    
    upload_key = f"uploader_{st.session_state.uploader_key_id}"
    
    # 附件按钮 (左下角)
    with st.popover("📎", use_container_width=False):
        uploaded_files = st.file_uploader(
            "Upload Context Images", 
            type=["jpg", "png", "webp"], 
            accept_multiple_files=True,
            key=upload_key
        )
        if uploaded_files:
            st.caption(f"{len(uploaded_files)} images selected")

    # 输入框
    user_input = st.chat_input("Type your message...")

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
