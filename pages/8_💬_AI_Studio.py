import streamlit as st
from PIL import Image
import sys
import os
import google.generativeai as genai

# --- 路径环境设置 ---
current_script_path = os.path.abspath(__file__)
pages_dir = os.path.dirname(current_script_path)
root_dir = os.path.dirname(pages_dir)
if root_dir not in sys.path: sys.path.append(root_dir)

try:
    import auth
    from services.llm_engine import LLMEngine
    from services.image_engine import ImageGenEngine
    # 引入我们刚才拆分出来的 UI 组件
    from app_utils.ui_components import inject_chat_css, render_chat_message
    from app_utils.image_processing import create_preview_thumbnail
except ImportError as e:
    st.error(f"❌ 模块缺失: {e}")
    st.stop()

st.set_page_config(page_title="Amazon AI Studio", page_icon="🧪", layout="wide")
inject_chat_css() # 注入样式

# --- 核心逻辑函数 ---

def build_gemini_history(msgs):
    """
    ✅ 解决上下文问题：
    将 Session State 中的消息格式化为 Gemini API 需要的 chat history 格式。
    注意：不包含最后一条正在发送的消息。
    """
    history = []
    for m in msgs:
        # 只处理文本类型的历史，忽略纯生图结果（Gemini 聊天模型看不懂生图结果的 bytes）
        if m["type"] == "text" or m.get("ref_images"):
            parts = []
            # 1. 放入图片 (如果有)
            if m.get("ref_images"):
                parts.extend(m["ref_images"])
            # 2. 放入文本
            if m["content"]:
                parts.append(m["content"])
            
            if parts:
                history.append({"role": m["role"], "parts": parts})
    return history

def delete_msg_callback(idx):
    if 0 <= idx < len(st.session_state.studio_msgs):
        st.session_state.studio_msgs.pop(idx)
        st.rerun()

def regenerate_callback(idx):
    # 删除这一条 AI 回复，并触发重新推理
    if st.session_state.studio_msgs[idx]["role"] == "model":
        st.session_state.studio_msgs.pop(idx)
        st.session_state.trigger_inference = True
        st.rerun()

# --- 初始化与鉴权 ---
if 'auth' in sys.modules and not auth.check_password(): st.stop()

# ✅ 修复点：独立检查每个关键变量，防止旧状态导致的 AttributeError
if "studio_msgs" not in st.session_state:
    st.session_state.studio_msgs = []

if "msg_uid" not in st.session_state:
    st.session_state.msg_uid = 0

if "uploader_key_id" not in st.session_state:
    st.session_state.uploader_key_id = 0

if "studio_ready" not in st.session_state:
    api_key = st.secrets.get("GOOGLE_API_KEY")
    st.session_state.llm_studio = LLMEngine(api_key)
    st.session_state.img_gen_studio = ImageGenEngine(api_key)
    st.session_state.studio_ready = True

# --- 侧边栏 ---
with st.sidebar:
    st.title("🧪 AI Workbench")
    model_map = {
        "🧠 Gemini 3 Pro (Reasoning)": "models/gemini-3-pro-preview", 
        "⚡ Gemini Flash (Fast)": "models/gemini-flash-latest",
        "🎨 Gemini 3 Image (Image Gen)": "models/gemini-3-pro-image-preview" 
    }
    selected_label = st.selectbox("Model", list(model_map.keys()))
    current_model_id = model_map[selected_label]
    is_image_mode = "image-preview" in current_model_id

    if st.button("🗑️ 清空对话", use_container_width=True):
        st.session_state.studio_msgs = []
        st.session_state.uploader_key_id += 1 # 同时清空文件选择器
        st.rerun()

# --- 消息渲染循环 ---
# 使用拆分后的 render_chat_message，主代码极其清爽
for idx, msg in enumerate(st.session_state.studio_msgs):
    render_chat_message(idx, msg, delete_msg_callback, regenerate_callback)

# --- 推理逻辑 (后端) ---
if st.session_state.get("trigger_inference", False):
    st.session_state.trigger_inference = False
    
    # 再次检查是否有消息，防止空指针
    if not st.session_state.studio_msgs:
        st.rerun()

    last_msg = st.session_state.studio_msgs[-1]
    
    if last_msg["role"] == "user":
        with st.chat_message("model"):
            # === A. 生图模式 ===
            if is_image_mode:
                with st.status("🎨 正在绘图...", expanded=True):
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
                            st.error("生成被拦截或失败")
                    except Exception as e:
                        st.error(f"Error: {e}")

            # === B. 对话模式 (带记忆) ===
            else:
                placeholder = st.empty()
                full_resp = ""
                try:
                    # 1. 构建历史 (不包含刚才发的这条)
                    past_history = build_gemini_history(st.session_state.studio_msgs[:-1])
                    
                    # 2. 启动聊天会话 (直接调用 SDK，最稳妥)
                    chat_session = genai.GenerativeModel(current_model_id).start_chat(history=past_history)
                    
                    # 3. 准备当前消息 Payload
                    current_payload = []
                    if last_msg.get("ref_images"): current_payload.extend(last_msg["ref_images"])
                    if last_msg["content"]: current_payload.append(last_msg["content"])
                    
                    # 4. 发送并流式接收
                    response = chat_session.send_message(current_payload, stream=True)
                    for chunk in response:
                        if chunk.text:
                            full_resp += chunk.text
                            placeholder.markdown(full_resp + "▌")
                    placeholder.markdown(full_resp)
                    
                    # 5. 保存记忆
                    st.session_state.msg_uid += 1
                    st.session_state.studio_msgs.append({
                        "role": "model", "type": "text", 
                        "content": full_resp, "id": st.session_state.msg_uid
                    })
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"对话出错: {e}")

# --- 底部输入区 ---
if not st.session_state.get("trigger_inference", False):
    
    # ✅ 解决附件重复问题：动态 Key
    upload_key = f"uploader_{st.session_state.uploader_key_id}"
    
    with st.popover("📎", use_container_width=False):
        uploaded_files = st.file_uploader(
            "添加参考图", 
            type=["jpg", "png", "webp"], 
            accept_multiple_files=True,
            key=upload_key 
        )
        if uploaded_files:
            st.info(f"已选择 {len(uploaded_files)} 张图片 (发送后将清除)")

    user_input = st.chat_input("输入指令...")

    if user_input:
        # 1. 处理图片
        img_list = []
        if uploaded_files:
            for uf in uploaded_files:
                img_list.append(Image.open(uf))
        
        # 2. 存入消息队列
        st.session_state.msg_uid += 1
        st.session_state.studio_msgs.append({
            "role": "user",
            "type": "text",
            "content": user_input,
            "ref_images": img_list, # 图片只绑定在这一条消息上
            "id": st.session_state.msg_uid
        })
        
        # 3. 强制重置上传控件
        st.session_state.uploader_key_id += 1
        
        # 4. 触发推理
        st.session_state.trigger_inference = True
        st.rerun()
