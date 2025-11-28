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
    from app_utils.ui_components import render_chat_message
    from app_utils.image_processing import create_preview_thumbnail
except ImportError as e:
    st.error(f"❌ 模块缺失: {e}")
    st.stop()

st.set_page_config(page_title="Amazon AI Studio", page_icon="🧪", layout="wide")

# ==========================================
# 🎨 CSS 魔法区：把上传按钮钉在聊天框旁边
# ==========================================
st.markdown("""
<style>
    /* 1. 给底部留出空间，防止消息被输入框遮挡 */
    .block-container {
        padding-bottom: 120px;
    }

    /* 2. 定位上传按钮 (Popover) */
    /* 只针对主界面(section.main)里的 Popover，不影响侧边栏 */
    section.main [data-testid="stPopover"] {
        position: fixed !important;
        bottom: 25px !important; /* 距离底部 25px，正好在输入框左侧/右侧 */
        left: 20px !important;   /* 钉在屏幕左下角 */
        z-index: 99999 !important;
        width: 45px !important;
        height: 45px !important;
    }

    /* 3. 美化上传按钮：圆形、阴影、白色背景 */
    section.main [data-testid="stPopover"] > div > button {
        border-radius: 50% !important;
        width: 45px !important;
        height: 45px !important;
        background-color: #ffffff !important;
        color: #444 !important;
        border: 1px solid #e0e0e0 !important;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1) !important;
        padding: 0 !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        font-size: 1.2rem !important;
        transition: all 0.2s ease !important;
    }

    /* 悬停效果 */
    section.main [data-testid="stPopover"] > div > button:hover {
        transform: scale(1.1) !important;
        border-color: #aaa !important;
        color: #000 !important;
    }

    /* 暗黑模式适配 */
    @media (prefers-color-scheme: dark) {
        section.main [data-testid="stPopover"] > div > button {
            background-color: #262730 !important;
            color: #fff !important;
            border: 1px solid #4a4a4a !important;
        }
    }
    
    /* 隐藏 Streamlit 默认的 'Deploy' 按钮等干扰元素 (可选) */
    .stDeployButton {display:none;}
</style>
""", unsafe_allow_html=True)

# --- 核心逻辑函数 ---

def build_gemini_history(msgs):
    """构建符合 Gemini API 规范的历史记录"""
    history = []
    for m in msgs:
        # 过滤掉生图结果和错误信息，只保留文本和用户上传的图片
        if m["type"] == "text" or m.get("ref_images"):
            parts = []
            if m.get("ref_images"):
                parts.extend(m["ref_images"])
            if m["content"]:
                parts.append(m["content"])
            if parts:
                history.append({"role": m["role"], "parts": parts})
    return history

def delete_msg_callback(idx):
    """回调：删除单条消息"""
    if 0 <= idx < len(st.session_state.studio_msgs):
        st.session_state.studio_msgs.pop(idx)
        st.rerun()

def regenerate_callback(idx):
    """回调：重新生成"""
    if st.session_state.studio_msgs[idx]["role"] == "model":
        st.session_state.studio_msgs.pop(idx)
        st.session_state.trigger_inference = True
        st.rerun()

# --- 初始化 ---
if 'auth' in sys.modules and not auth.check_password(): st.stop()

# 安全初始化 Session State
if "studio_msgs" not in st.session_state: st.session_state.studio_msgs = []
if "msg_uid" not in st.session_state: st.session_state.msg_uid = 0
if "uploader_key_id" not in st.session_state: st.session_state.uploader_key_id = 0
if "studio_ready" not in st.session_state:
    api_key = st.secrets.get("GOOGLE_API_KEY")
    st.session_state.llm_studio = LLMEngine(api_key)
    st.session_state.img_gen_studio = ImageGenEngine(api_key)
    st.session_state.studio_ready = True

# --- 侧边栏配置 ---
with st.sidebar:
    st.title("🧪 AI Workbench")
    
    # 模型选择
    model_map = {
        "🧠 Gemini 3 Pro (Reasoning)": "models/gemini-3-pro-preview", 
        "⚡ Gemini Flash (Fast)": "models/gemini-flash-latest",
        "🎨 Gemini 3 Image (Image Gen)": "models/gemini-3-pro-image-preview" 
    }
    selected_label = st.selectbox("核心模型", list(model_map.keys()))
    current_model_id = model_map[selected_label]
    is_image_mode = "image-preview" in current_model_id
    
    st.divider()
    
    # 记忆管理区
    st.caption("🧠 记忆管理")
    col_k1, col_k2 = st.columns(2)
    with col_k1:
        if st.button("🧹 清空对话", use_container_width=True):
            st.session_state.studio_msgs = []
            st.session_state.uploader_key_id += 1 
            st.toast("记忆已清除", icon="🧹")
            st.rerun()
    with col_k2:
        if st.button("↩️ 撤回", use_container_width=True):
            if st.session_state.studio_msgs:
                st.session_state.studio_msgs.pop()
                st.rerun()

# --- 消息渲染 ---
if not st.session_state.studio_msgs:
    # 欢迎页
    st.markdown("""
    <div style="text-align: center; color: #888; margin-top: 100px;">
        <h3>👋 Welcome to AI Studio</h3>
        <p>上传图片、输入指令，开始你的创作。</p>
    </div>
    """, unsafe_allow_html=True)
else:
    for idx, msg in enumerate(st.session_state.studio_msgs):
        render_chat_message(idx, msg, delete_msg_callback, regenerate_callback)

# --- AI 推理逻辑 ---
if st.session_state.get("trigger_inference", False):
    st.session_state.trigger_inference = False
    
    if not st.session_state.studio_msgs: st.rerun()
    last_msg = st.session_state.studio_msgs[-1]
    
    if last_msg["role"] == "user":
        with st.chat_message("model"):
            # === 模式 A: 生图 ===
            if is_image_mode:
                with st.status("🎨 正在绘制...", expanded=True):
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
                            st.error("⚠️ 生成失败 (可能因安全策略拦截)")
                    except Exception as e:
                        st.error(f"Generate Error: {e}")

            # === 模式 B: 对话 ===
            else:
                placeholder = st.empty()
                full_resp = ""
                try:
                    past_history = build_gemini_history(st.session_state.studio_msgs[:-1])
                    chat_session = genai.GenerativeModel(current_model_id).start_chat(history=past_history)
                    
                    payload = []
                    if last_msg.get("ref_images"): payload.extend(last_msg["ref_images"])
                    if last_msg["content"]: payload.append(last_msg["content"])
                    
                    resp = chat_session.send_message(payload, stream=True)
                    for chunk in resp:
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

    # 1. 悬浮的附件按钮 (位置由顶部 CSS 控制，固定在左下角)
    # 使用动态 key 确保发完消息后清空文件
    upload_key = f"uploader_{st.session_state.uploader_key_id}"
    
    with st.popover("📎", use_container_width=False):
        uploaded_files = st.file_uploader(
            "添加参考图 / Add Images", 
            type=["jpg", "png", "webp"], 
            accept_multiple_files=True,
            key=upload_key
        )
        if uploaded_files:
            st.caption(f"已选中 {len(uploaded_files)} 张")

    # 2. 聊天输入框
    user_input = st.chat_input("输入指令 / Ask anything...")

    # 3. 发送处理
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
        
        # 强制更新 Key 以清空上传器
        st.session_state.uploader_key_id += 1
        st.session_state.trigger_inference = True
        st.rerun()
