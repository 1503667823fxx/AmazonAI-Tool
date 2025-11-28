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
    # 引入核心UI组件
    from app_utils.image_processing import create_preview_thumbnail
    from app_utils.ui_components import show_image_modal
except ImportError as e:
    st.error(f"❌ 核心模块导入失败: {e}")
    st.stop()

# --- 页面配置 ---
st.set_page_config(
    page_title="Amazon AI Studio",
    page_icon="💬",
    layout="wide"
)

# --- CSS 深度优化 ---
st.markdown("""
<style>
    /* 1. 解决滚动回弹: 移除多余的padding，让内容自然流式排列 */
    .block-container { padding-top: 1rem; padding-bottom: 8rem; }
    
    /* 2. 消息气泡美化 */
    .stChatMessage {
        background-color: transparent;
        padding: 1rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
    }
    .stChatMessage:hover {
        background-color: rgba(240, 242, 246, 0.5); /* 鼠标悬停微高亮 */
    }

    /* 3. 操作栏样式 */
    .msg-actions {
        display: flex;
        gap: 8px;
        margin-top: 5px;
        opacity: 0.4;
        transition: opacity 0.2s;
    }
    .stChatMessage:hover .msg-actions { opacity: 1; }
    
    /* 4. 图片容器限制 */
    .preview-img {
        border-radius: 8px;
        border: 1px solid #ddd;
    }
</style>
""", unsafe_allow_html=True)

# --- 1. 初始化 State ---
if 'auth' in sys.modules and not auth.check_password():
    st.stop()

if "studio_ready" not in st.session_state:
    api_key = st.secrets.get("GOOGLE_API_KEY")
    st.session_state.llm_studio = LLMEngine(api_key)
    st.session_state.img_gen_studio = ImageGenEngine(api_key)
    st.session_state.studio_ready = True

# 消息历史
if "studio_msgs" not in st.session_state:
    st.session_state.studio_msgs = []

# 编辑状态
if "editing_state" not in st.session_state:
    st.session_state.editing_state = None

# ID 计数器
if "msg_uid" not in st.session_state:
    st.session_state.msg_uid = 0

def get_uid():
    st.session_state.msg_uid += 1
    return st.session_state.msg_uid

# --- 2. 逻辑函数 ---

def delete_msg(idx):
    if 0 <= idx < len(st.session_state.studio_msgs):
        st.session_state.studio_msgs.pop(idx)
        st.rerun()

def start_edit(idx, content):
    st.session_state.editing_state = {"idx": idx, "content": content}
    st.rerun()

def save_edit(idx, new_content):
    st.session_state.studio_msgs[idx]["content"] = new_content
    # 截断后续
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
    history = []
    for m in msgs:
        if m["type"] == "text" or m.get("ref_image"):
            parts = []
            if m.get("ref_image"): parts.append(m["ref_image"])
            if m["content"]: parts.append(m["content"])
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
    
    selected_label = st.selectbox("Select Model", list(model_map.keys()), label_visibility="collapsed")
    current_model_id = model_map[selected_label]
    is_image_mode = "image-preview" in current_model_id

    st.divider()

    if is_image_mode:
        st.caption("🎨 Image Settings")
        ratio = st.selectbox("Aspect Ratio", ["1:1 (Square)", "4:3", "3:4", "16:9", "9:16"])
        seed_val = st.number_input("Seed (-1 Random)", value=-1)
    else:
        st.caption("🧠 Persona")
        sys_prompt = st.text_area("System Prompt", value="You are a helpful Amazon assistant.", height=150)

    st.divider()
    if st.button("🗑️ New Chat", use_container_width=True):
        st.session_state.studio_msgs = []
        st.rerun()

# --- 4. 主消息区 (移除 st.container 以解决滚动 Bug) ---

# 直接在主流程渲染，让 Streamlit 自动处理滚动
for idx, msg in enumerate(st.session_state.studio_msgs):
    is_editing = (st.session_state.editing_state and st.session_state.editing_state["idx"] == idx)
    
    with st.chat_message(msg["role"]):
        
        # === 编辑模式 ===
        if is_editing:
            new_val = st.text_area("Edit prompt:", value=msg["content"], height=100)
            c1, c2 = st.columns([1, 4])
            if c1.button("Save", key=f"s_{msg['id']}"): save_edit(idx, new_val)
            if c2.button("Cancel", key=f"c_{msg['id']}"): cancel_edit()
        
        # === 浏览模式 ===
        else:
            # 1. 垫图显示
            if msg.get("ref_image"):
                st.image(msg["ref_image"], width=150, caption="Ref Image")
            
            # 2. 内容显示 (核心修改点：Smart Edit 风格预览)
            if msg["type"] == "image_result":
                # 显示缩略图 (快速)
                st.image(msg["content"], width=400)
                
                # 操作区 (放大 + 下载)
                act_cols = st.columns([1, 1, 4])
                with act_cols[0]:
                    # 模态框逻辑
                    if st.button("🔍 Zoom", key=f"zoom_{msg['id']}"):
                        show_image_modal(msg["hd_data"], f"Result-{msg['id']}")
                with act_cols[1]:
                    # 下载按钮
                    st.download_button(
                        "📥", 
                        data=msg["hd_data"], 
                        file_name=f"gen_{msg['id']}.jpg", 
                        mime="image/jpeg", 
                        key=f"dl_{msg['id']}"
                    )
                with act_cols[2]:
                     if st.button("🗑️", key=f"del_img_{msg['id']}"): delete_msg(idx)

            else:
                st.markdown(msg["content"])
                
                # 文本消息的操作栏
                # 使用 opacity CSS 实现鼠标悬停才显示
                st.markdown('<div class="msg-actions">', unsafe_allow_html=True)
                
                act_c1, act_c2, _ = st.columns([1, 1, 8])
                
                # 编辑按钮 (仅用户)
                if msg["role"] == "user":
                    with act_c1:
                        if st.button("✏️", key=f"edt_{msg['id']}"): start_edit(idx, msg["content"])
                
                # 重试按钮 (仅 AI)
                if msg["role"] == "model":
                    with act_c1:
                        if st.button("🔄", key=f"rgn_{msg['id']}"): regenerate(idx)
                
                # 删除按钮 (通用)
                with act_c2:
                    if st.button("🗑️", key=f"del_{msg['id']}"): delete_msg(idx)
                    
                st.markdown('</div>', unsafe_allow_html=True)

# 底部占位符，防止内容被输入框遮挡
st.markdown("<div style='height: 100px;'></div>", unsafe_allow_html=True)

# --- 5. 推理逻辑 ---
if st.session_state.get("trigger_inference", False):
    st.session_state.trigger_inference = False
    
    if not st.session_state.studio_msgs: st.stop()
    last_msg = st.session_state.studio_msgs[-1]
    
    if last_msg["role"] == "user":
        with st.chat_message("model"):
            if is_image_mode:
                with st.status("🎨 Rendering...", expanded=True):
                    try:
                        hd_bytes = st.session_state.img_gen_studio.generate(
                            prompt=last_msg["content"],
                            model_name=current_model_id,
                            ref_image=last_msg.get("ref_image"),
                            ratio_suffix=f", aspect ratio {ratio.split()[0]}",
                            seed=int(seed_val) if seed_val != -1 else None
                        )
                        if hd_bytes:
                            # 生成缩略图
                            thumb = create_preview_thumbnail(hd_bytes, 800)
                            st.session_state.studio_msgs.append({
                                "role": "model", "type": "image_result",
                                "content": thumb, "hd_data": hd_bytes, "id": get_uid()
                            })
                            st.rerun()
                        else:
                            st.error("Blocked by safety filters.")
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                # 文本逻辑 (同前)
                try:
                    placeholder = st.empty()
                    full_resp = ""
                    past_msgs = st.session_state.studio_msgs[:-1]
                    gemini_history = build_gemini_history(past_msgs)
                    model = st.session_state.llm_studio.get_chat_model(current_model_id, sys_prompt)
                    chat = model.start_chat(history=gemini_history)
                    
                    user_c = []
                    if last_msg.get("ref_image"): user_c.append(last_msg["ref_image"])
                    if last_msg["content"]: user_c.append(last_msg["content"])
                    
                    response = chat.send_message(user_c, stream=True)
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

# --- 6. 底部输入区 (优化版) ---
if not st.session_state.get("trigger_inference", False):
    
    # 布局优化：利用 Popover 实现类似“附件菜单”的效果
    # 这会显示在输入框的左上方，最接近 "旁边" 的效果
    
    # 定义底部容器，固定在下方
    bottom_container = st.container()
    
    with bottom_container:
        # 创建两列：左侧是附件按钮，右侧由于 chat_input 独占一行，其实这里主要是给附件腾位置
        
        # 使用 st.popover 创建一个折叠的菜单
        with st.popover("📎 添加图片", use_container_width=False):
            uploaded_file = st.file_uploader(
                "Upload Reference Image", 
                type=["jpg", "png", "webp"], 
                key="chat_uploader"
            )
            if uploaded_file:
                st.caption("✅ 图片已就绪，请在下方发送")

        # 紧接着是输入框
        user_input = st.chat_input("Message...")

    if user_input:
        img_obj = Image.open(uploaded_file) if uploaded_file else None
        
        st.session_state.studio_msgs.append({
            "role": "user",
            "type": "text",
            "content": user_input,
            "ref_image": img_obj,
            "id": get_uid()
        })
        st.session_state.trigger_inference = True
        st.rerun()
