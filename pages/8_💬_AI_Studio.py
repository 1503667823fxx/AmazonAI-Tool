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
    # 复用你项目里的图片处理工具
    from app_utils.image_processing import create_preview_thumbnail
except ImportError as e:
    st.error(f"❌ 核心模块导入失败: {e}")
    st.stop()

# --- 页面配置 ---
st.set_page_config(
    page_title="AI Studio Workbench", 
    page_icon="🧪", 
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS 样式注入 (模仿 Google AI Studio) ---
st.markdown("""
<style>
    /* 隐藏顶部Padding */
    .block-container { padding-top: 2rem; }
    
    /* 消息气泡微调 */
    .stChatMessage { 
        background-color: transparent; 
        border-radius: 10px;
    }

    /* 操作按钮行样式 */
    .action-row {
        display: flex; 
        gap: 10px; 
        margin-top: -10px; 
        margin-bottom: 20px;
        opacity: 0.7;
    }
    .action-row:hover { opacity: 1; }
</style>
""", unsafe_allow_html=True)

# --- 1. 初始化与鉴权 ---
if 'auth' in sys.modules and not auth.check_password():
    st.stop()

if "studio_ready" not in st.session_state:
    api_key = st.secrets.get("GOOGLE_API_KEY")
    st.session_state.llm_studio = LLMEngine(api_key)
    st.session_state.img_gen_studio = ImageGenEngine(api_key)
    st.session_state.studio_ready = True

# 消息结构: [{"role": "user", "type": "text/image/gen_result", "content": "...", "hd_data": bytes, "id": 0}]
if "studio_msgs" not in st.session_state:
    st.session_state.studio_msgs = []

# 全局计数器用于生成唯一 Key
if "msg_counter" not in st.session_state:
    st.session_state.msg_counter = 0

# --- 2. 辅助函数 ---
def delete_message(index):
    """删除指定索引的消息"""
    if 0 <= index < len(st.session_state.studio_msgs):
        st.session_state.studio_msgs.pop(index)
        # 注意：这里仅删除了UI显示。
        # 如果需要同步删除 Gemini 后端记忆，需要重建 Chat Session，考虑到性能暂不做复杂处理。
        # 对于"生图"或"单轮问答"场景，UI删除已足够。

def add_message(role, content, msg_type="text", hd_data=None, ref_image=None):
    """统一添加消息到历史"""
    st.session_state.studio_msgs.append({
        "role": role,
        "type": msg_type,
        "content": content,     # 文本内容 或 缩略图对象
        "hd_data": hd_data,     # 原始高清数据 (仅生图结果有)
        "ref_image": ref_image, # 用户上传的垫图
        "id": st.session_state.msg_counter
    })
    st.session_state.msg_counter += 1

# --- 3. 侧边栏 (工作台设置) ---
with st.sidebar:
    st.title("🧪 AI Studio")
    
    # 模型选择
    model_map = {
        "⚡ Gemini Flash (Fast)": "models/gemini-flash-latest",
        "🧠 Gemini 3 Pro (Reasoning)": "models/gemini-3-pro-preview", 
        "🎨 Gemini 3 Image (Generation)": "models/gemini-3-pro-image-preview" 
    }
    
    selected_label = st.selectbox("Model", list(model_map.keys()), label_visibility="collapsed")
    current_model_id = model_map[selected_label]
    is_image_mode = "image-preview" in current_model_id

    st.divider()

    # 参数区
    if is_image_mode:
        st.caption("⚙️ Generation Params")
        ratio = st.selectbox("Aspect Ratio", ["1:1", "4:3", "3:4", "16:9"], index=0)
        seed_val = st.number_input("Seed", value=-1)
    else:
        st.caption("⚙️ System Instructions")
        sys_prompt = st.text_area("System Prompt", value="你是一个亚马逊电商专家。", height=150)

    st.divider()
    
    # 全局清空
    if st.button("🗑️ Clear Context", use_container_width=True):
        st.session_state.studio_msgs = []
        # 如果是文本对话，重置 Session
        if not is_image_mode:
             model = st.session_state.llm_studio.get_chat_model(current_model_id, sys_prompt)
             st.session_state.gemini_chat = model.start_chat(history=[])
        st.rerun()

# --- 4. 主工作区 (渲染历史消息) ---
# 使用 container 包裹，防止底部输入框跳动
chat_container = st.container()

with chat_container:
    # 遍历时需要 index 用于删除
    for idx, msg in enumerate(st.session_state.studio_msgs):
        
        # 1. 渲染消息主体
        with st.chat_message(msg["role"]):
            
            # Case A: 用户消息 (含垫图)
            if msg["role"] == "user":
                if msg.get("ref_image"):
                    # 显示上传图的缩略版本
                    st.image(msg["ref_image"], width=200)
                st.write(msg["content"])
            
            # Case B: AI 生图结果 (预览图 + 高清下载)
            elif msg["type"] == "image_result":
                # 显示预览图 (Content 存的是 PIL 或 缩略图)
                st.image(msg["content"], width=400, caption="Preview Version")
                
                # --- 操作栏 (Action Row) ---
                col_act1, col_act2, col_act3 = st.columns([1, 1, 3])
                with col_act1:
                    # 下载按钮 (使用高清数据)
                    if msg.get("hd_data"):
                        filename = f"studio_gen_{msg['id']}.jpg"
                        st.download_button(
                            label="📥 HD Download",
                            data=msg["hd_data"],
                            file_name=filename,
                            mime="image/jpeg",
                            key=f"dl_{msg['id']}"
                        )
                with col_act2:
                    # 删除按钮
                    if st.button("🗑️ Delete", key=f"del_btn_{msg['id']}"):
                        delete_message(idx)
                        st.rerun()

            # Case C: AI 文本回复
            else:
                st.write(msg["content"])
                # 文本消息也可以有删除按钮 (放在右下角或下方)
                if st.button("✕", key=f"del_txt_{msg['id']}", help="Remove this message"):
                    delete_message(idx)
                    st.rerun()

    st.write("") # Spacer

# --- 5. 底部输入区 ---
uploaded_file = st.file_uploader("Upload Image", type=["jpg", "png", "webp"], label_visibility="collapsed")
user_input = st.chat_input("Type your instructions here...")

if user_input:
    # 1. 处理用户输入
    input_image = None
    if uploaded_file:
        input_image = Image.open(uploaded_file)
    
    # 添加到 UI 历史
    add_message("user", user_input, ref_image=input_image)
    st.rerun() # 强制刷新以立即显示用户消息，然后开始 AI 思考

# --- 6. 异步处理 AI 响应 (利用 Session State 检测新消息) ---
# 逻辑：如果最后一条是用户消息，则触发 AI
if st.session_state.studio_msgs and st.session_state.studio_msgs[-1]["role"] == "user":
    last_msg = st.session_state.studio_msgs[-1]
    last_text = last_msg["content"]
    last_img = last_msg.get("ref_image")

    with st.chat_message("assistant"):
        
        # === 模式 A: 生图 ===
        if is_image_mode:
            with st.status("🎨 Generating Image...", expanded=True) as status:
                try:
                    # 获取高清 Byte 流
                    hd_bytes = st.session_state.img_gen_studio.generate(
                        prompt=last_text,
                        model_name=current_model_id,
                        ref_image=last_img,
                        ratio_suffix=f", aspect ratio {ratio.split()[0]}",
                        seed=int(seed_val) if seed_val != -1 else None
                    )
                    
                    if hd_bytes:
                        # 1. 生成预览缩略图 (加快渲染)
                        preview_img = create_preview_thumbnail(hd_bytes, size=800) 
                        
                        # 2. 存入历史
                        add_message(
                            "assistant", 
                            content=preview_img,  # 存预览图用于显示
                            msg_type="image_result",
                            hd_data=hd_bytes      # 存原始数据用于下载
                        )
                        status.update(label="Done!", state="complete")
                        st.rerun() # 刷新显示结果和按钮
                    else:
                        st.error("Generation blocked by safety filters.")
                        status.update(label="Failed", state="error")
                except Exception as e:
                    st.error(f"Error: {e}")

        # === 模式 B: 文本对话 ===
        else:
            stream_placeholder = st.empty()
            full_resp = ""
            
            try:
                # 确保 Session 存在
                if "gemini_chat" not in st.session_state or not st.session_state.gemini_chat:
                    model = st.session_state.llm_studio.get_chat_model(current_model_id, sys_prompt)
                    st.session_state.gemini_chat = model.start_chat(history=[])
                
                # 流式生成
                response_stream = st.session_state.llm_studio.chat_stream(
                    st.session_state.gemini_chat, 
                    last_text, 
                    last_img
                )
                
                for chunk in response_stream:
                    full_resp += chunk
                    stream_placeholder.markdown(full_resp + "▌")
                
                stream_placeholder.markdown(full_resp)
                
                # 存入历史
                add_message("assistant", full_resp)
                st.rerun() # 刷新以去除光标并显示删除按钮
                
            except Exception as e:
                st.error(f"Chat Error: {e}")
