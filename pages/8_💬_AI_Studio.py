import streamlit as st
from PIL import Image
import sys
import os

# 环境设置 (与之前一致)
current_script_path = os.path.abspath(__file__)
pages_dir = os.path.dirname(current_script_path)
root_dir = os.path.dirname(pages_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

try:
    import auth
    from services.llm_engine import LLMEngine
    from services.image_engine import ImageGenEngine # 如果你想在这里也支持生图
except ImportError as e:
    st.error(f"❌ 模块导入失败: {e}")
    st.stop()

st.set_page_config(page_title="Amazon AI Studio", page_icon="💬", layout="wide")

# --- 1. 初始化 ---
if 'auth' in sys.modules and not auth.check_password():
    st.stop()

if "llm_studio" not in st.session_state:
    api_key = st.secrets.get("GOOGLE_API_KEY")
    st.session_state.llm_studio = LLMEngine(api_key)

# 核心：管理聊天历史和会话对象
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = [] # 用于UI显示 [{"role": "user", "content": "hi", "image": img}, ...]

if "gemini_chat_session" not in st.session_state:
    # 初始化一个空的 Gemini 会话
    model = st.session_state.llm_studio.get_chat_model()
    st.session_state.gemini_chat_session = model.start_chat(history=[])

# --- 2. 侧边栏配置 (控制台风格) ---
with st.sidebar:
    st.title("🎛️ AI Studio 控制台")
    
    # A. 模型选择
    model_options = [
        "models/gemini-3-pro-preview", 
        "models/gemini-flash-latest",
        "models/gemini-flash-lite-latest"
    ]
    selected_model = st.selectbox("🤖 模型选择", model_options)
    
    # B. 系统指令 (System Prompt) - 这就是"人设"
    st.caption("🧠 系统指令 (System Instructions)")
    system_prompt = st.text_area(
        "定义 AI 的行为", 
        value="你是一个专业的亚马逊电商运营专家。回答要简洁、商业化，并善于分析产品卖点。",
        height=150,
        help="在这里告诉 AI 它是谁，比如'你是一个资深文案'或'你是一个Python代码助手'。"
    )
    
    st.divider()
    
    # C. 记忆管理 (核心需求)
    col_mem1, col_mem2 = st.columns([1, 3])
    with col_mem1:
        st.write("") # Spacer
    with col_mem2:
        if st.button("🗑️ 清除记忆 (Reset)", type="primary", use_container_width=True):
            # 1. 清空 UI 历史
            st.session_state.chat_messages = []
            # 2. 重置 Gemini 后端会话
            new_model = st.session_state.llm_studio.get_chat_model(selected_model, system_prompt)
            st.session_state.gemini_chat_session = new_model.start_chat(history=[])
            st.toast("记忆已清除，开启新话题！", icon="🧹")
            st.rerun()

    st.info("💡 **提示**: 你可以直接截图粘贴到对话框，或者点击回形针上传图片。")

# --- 3. 主对话区 ---
st.title("💬 Amazon AI Workbench")
st.caption("与 AI 自由对话，分析图片、撰写文案或构思创意。")

# 展示历史消息
for msg in st.session_state.chat_messages:
    with st.chat_message(msg["role"]):
        # 如果有图片先展示图片
        if "image" in msg and msg["image"]:
            st.image(msg["image"], width=300)
        st.markdown(msg["content"])

# --- 4. 输入处理 ---
# 上传图片的小挂件 (放在输入框上方或侧边比较难，Streamlit限制，通常用 expander 或 file_uploader)
with st.expander("📷 上传图片 (可选)", expanded=False):
    uploaded_img = st.file_uploader("添加图片到对话", type=["png", "jpg", "webp", "jpeg"], label_visibility="collapsed")

prompt = st.chat_input("输入你的指令...")

if prompt:
    # 1. 处理用户输入
    user_img = None
    if uploaded_img:
        user_img = Image.open(uploaded_img)
    
    # 更新 UI 历史
    st.session_state.chat_messages.append({
        "role": "user", 
        "content": prompt,
        "image": user_img
    })
    
    # 显示用户消息
    with st.chat_message("user"):
        if user_img:
            st.image(user_img, width=300)
        st.markdown(prompt)

    # 2. AI 回复
    with st.chat_message("assistant"):
        stream_placeholder = st.empty()
        full_response = ""
        
        # 确保模型与侧边栏配置同步 (如果系统指令变了，其实应该重置 session，但在简单模式下我们只更新 session 对象)
        # 注意：动态修改 System Prompt 在运行中的 Session 比较麻烦，通常建议修改后点"清除记忆"生效
        # 这里我们直接调用 chat_stream
        
        try:
            # 获取流式生成器
            response_stream = st.session_state.llm_studio.chat_stream(
                st.session_state.gemini_chat_session,
                prompt,
                user_img
            )
            
            for chunk in response_stream:
                full_response += chunk
                stream_placeholder.markdown(full_response + "▌")
            
            stream_placeholder.markdown(full_response)
            
            # 更新 UI 历史
            st.session_state.chat_messages.append({
                "role": "assistant", 
                "content": full_response
            })
            
        except Exception as e:
            st.error(f"对话出错: {e}")
            if "429" in str(e):
                st.warning("请求过快，请稍后重试。")
