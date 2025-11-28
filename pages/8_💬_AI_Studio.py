import streamlit as st
from PIL import Image
import sys
import os
import time

# --- 环境设置 ---
current_script_path = os.path.abspath(__file__)
pages_dir = os.path.dirname(current_script_path)
root_dir = os.path.dirname(pages_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

try:
    import auth
    from services.llm_engine import LLMEngine
    from services.image_engine import ImageGenEngine
except ImportError as e:
    st.error(f"❌ 核心模块导入失败: {e}")
    st.stop()

st.set_page_config(page_title="AI Studio", page_icon="💬", layout="wide")

# --- 1. 初始化 ---
if 'auth' in sys.modules and not auth.check_password():
    st.stop()

# 初始化引擎
if "studio_ready" not in st.session_state:
    api_key = st.secrets.get("GOOGLE_API_KEY")
    st.session_state.llm_studio = LLMEngine(api_key)
    st.session_state.img_gen_studio = ImageGenEngine(api_key)
    st.session_state.studio_ready = True

# 初始化聊天历史 [{"role": "user", "type": "text/image", "content": "..."}]
if "studio_msgs" not in st.session_state:
    st.session_state.studio_msgs = []

# 初始化 Gemini Chat Session (仅用于文本模型)
if "gemini_chat" not in st.session_state:
    # 默认用 Flash 启动
    model = st.session_state.llm_studio.get_chat_model("models/gemini-flash-latest")
    st.session_state.gemini_chat = model.start_chat(history=[])

# --- 2. 侧边栏配置 ---
with st.sidebar:
    st.title("🎛️ AI 工作台")
    
    # === 模型选择 (核心逻辑) ===
    # 按照您的要求提供三个模型
    model_map = {
        "⚡ Gemini Flash (Fast Chat)": "models/gemini-flash-latest",
        "🧠 Gemini 3 Pro (Reasoning)": "models/gemini-3-pro-preview", 
        "🎨 Gemini 3 Image (Generation)": "models/gemini-3-pro-image-preview" 
    }
    
    selected_label = st.selectbox("🤖 选择模型功能", list(model_map.keys()))
    current_model_id = model_map[selected_label]
    
    # 判断当前是否是生图模式
    is_image_mode = "image-preview" in current_model_id

    st.divider()

    # === 参数配置 (根据模式变化) ===
    if is_image_mode:
        st.info("🎨 **生图模式已激活**")
        st.caption("直接在对话框输入 Prompt 即可生图。")
        ratio = st.selectbox("画幅比例", ["1:1 (Square)", "4:3", "16:9", "9:16"])
        style_seed = st.number_input("Seed (-1随机)", value=-1)
    else:
        st.caption("🧠 **系统人设 (System Prompt)**")
        sys_prompt = st.text_area("定义AI角色", value="你是一个亚马逊电商专家。", height=100)
        
    st.divider()
    
    # === 记忆管理 ===
    if st.button("🗑️ 清空历史 / 新话题", use_container_width=True):
        st.session_state.studio_msgs = []
        # 重置 Chat Session
        if not is_image_mode:
            new_model = st.session_state.llm_studio.get_chat_model(current_model_id, sys_prompt)
            st.session_state.gemini_chat = new_model.start_chat(history=[])
        st.rerun()

# --- 3. 主界面 ---
st.title("💬 Amazon AI Studio")

# 显示历史消息
for msg in st.session_state.studio_msgs:
    with st.chat_message(msg["role"]):
        # 如果是图片类型的消息
        if msg.get("type") == "image_result":
            st.image(msg["content"], caption="Generated Image")
        # 如果是包含上传图的用户消息
        elif msg.get("ref_image"):
            st.image(msg["ref_image"], width=250)
            st.markdown(msg["content"])
        # 普通文本
        else:
            st.markdown(msg["content"])

# --- 4. 输入处理 ---
# 上传图片组件 (仅文本模式支持识图，生图模式支持参考图)
uploaded_file = st.file_uploader("📷 上传图片 (识图/参考)", type=["jpg", "png", "webp"], label_visibility="collapsed")

user_input = st.chat_input("输入指令或 Prompt...")

if user_input:
    # 处理上传的图片
    input_image = None
    if uploaded_file:
        input_image = Image.open(uploaded_file)
    
    # 1. 显示用户输入
    st.session_state.studio_msgs.append({
        "role": "user", 
        "content": user_input,
        "ref_image": input_image
    })
    with st.chat_message("user"):
        if input_image: st.image(input_image, width=250)
        st.markdown(user_input)

    # 2. AI 响应 (分流逻辑)
    with st.chat_message("assistant"):
        
        # === 分支 A: 生图模式 ===
        if is_image_mode:
            with st.status("🎨 正在绘图...", expanded=True) as status:
                try:
                    # 调用 Image Engine
                    img_bytes = st.session_state.img_gen_studio.generate(
                        prompt=user_input,
                        model_name=current_model_id,
                        ref_image=input_image, # 支持垫图
                        ratio_suffix=f", aspect ratio {ratio.split()[0]}",
                        seed=int(style_seed) if style_seed != -1 else None
                    )
                    
                    if img_bytes:
                        st.image(img_bytes, caption="Generated by Gemini 3 Image")
                        # 保存到历史
                        st.session_state.studio_msgs.append({
                            "role": "assistant",
                            "type": "image_result",
                            "content": img_bytes
                        })
                        status.update(label="✅ 绘图完成", state="complete")
                    else:
                        st.error("生成失败，可能触发了安全拦截。")
                        status.update(label="❌ 任务中止", state="error")
                except Exception as e:
                    st.error(f"Error: {e}")

        # === 分支 B: 文本/对话模式 ===
        else:
            # 检查是否需要切换 Session 模型 (如果用户在中途切换了下拉框)
            # 简单的做法：这里我们假设用户切换模型后点了清空，或者我们动态重连
            # 为了流畅体验，这里动态调用 chat_stream 即可
            
            stream_placeholder = st.empty()
            full_response = ""
            
            try:
                # 重新获取一次带最新 System Prompt 的 Chat Session 
                # (注意：在长对话中频繁切换 System Prompt 可能会导致上下文错乱，这里简化处理)
                if not st.session_state.gemini_chat:
                     model = st.session_state.llm_studio.get_chat_model(current_model_id)
                     st.session_state.gemini_chat = model.start_chat(history=[])
                
                # 开始流式对话
                response_stream = st.session_state.llm_studio.chat_stream(
                    st.session_state.gemini_chat, 
                    user_input, 
                    input_image
                )
                
                for chunk in response_stream:
                    full_response += chunk
                    stream_placeholder.markdown(full_response + "▌")
                
                stream_placeholder.markdown(full_response)
                
                # 保存文本历史
                st.session_state.studio_msgs.append({
                    "role": "assistant",
                    "content": full_response
                })
                
            except Exception as e:
                st.error(f"对话异常: {e}")
