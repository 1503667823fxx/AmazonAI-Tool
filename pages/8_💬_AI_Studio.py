import streamlit as st
from PIL import Image
import sys
import os
import io
import time
import google.generativeai as genai

# --- 环境配置 ---
current_script_path = os.path.abspath(__file__)
pages_dir = os.path.dirname(current_script_path)
root_dir = os.path.dirname(pages_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

try:
    import auth
    from services.llm_engine import LLMEngine
    from services.image_engine import ImageGenEngine
    # 修复引用
    from app_utils.image_processing import create_preview_thumbnail
except ImportError as e:
    st.error(f"❌ 核心模块导入失败: {e}")
    st.stop()

# --- 页面配置 ---
st.set_page_config(
    page_title="Amazon AI Studio",
    page_icon="🧪",
    layout="wide"
)

# --- CSS 样式优化 (对标 AI Studio) ---
st.markdown("""
<style>
    /* 隐藏默认头部 */
    .block-container { padding-top: 1.5rem; }
    
    /* 消息气泡样式 */
    .stChatMessage {
        background-color: transparent;
        border-bottom: 1px solid #f0f0f0;
        padding-bottom: 15px;
    }
    
    /* 操作按钮区 */
    .msg-actions {
        display: flex;
        gap: 0.5rem;
        font-size: 0.8rem;
        opacity: 0.6;
    }
    .msg-actions:hover { opacity: 1; }
    
    /* 隐藏部分Streamlit默认元素以更像App */
    div[data-testid="stToolbar"] { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# --- 1. 初始化 State ---
if 'auth' in sys.modules and not auth.check_password():
    st.stop()

# 核心服务
if "studio_ready" not in st.session_state:
    api_key = st.secrets.get("GOOGLE_API_KEY")
    st.session_state.llm_studio = LLMEngine(api_key)
    st.session_state.img_gen_studio = ImageGenEngine(api_key)
    st.session_state.studio_ready = True

# 消息列表：这是唯一的真理来源
# 结构: {"role": "user"/"model", "content": str/img, "type": "text"/"image_result", "hd_data": bytes, "id": int}
if "studio_msgs" not in st.session_state:
    st.session_state.studio_msgs = []

# 编辑状态追踪 {"idx": 3, "content": "..."}
if "editing_state" not in st.session_state:
    st.session_state.editing_state = None

# 计数器
if "msg_uid" not in st.session_state:
    st.session_state.msg_uid = 0

def get_uid():
    st.session_state.msg_uid += 1
    return st.session_state.msg_uid

# --- 2. 逻辑处理函数 ---

def delete_msg(idx):
    """删除某条消息，如果是中间删除，可能需要截断后续以保持逻辑连贯(可选)，这里选择仅删除该条"""
    if 0 <= idx < len(st.session_state.studio_msgs):
        st.session_state.studio_msgs.pop(idx)
        st.rerun()

def start_edit(idx, content):
    """进入编辑模式"""
    st.session_state.editing_state = {"idx": idx, "content": content}
    st.rerun()

def save_edit(idx, new_content):
    """保存编辑：通常意味着截断后续历史，重新生成"""
    # 1. 更新该条内容
    st.session_state.studio_msgs[idx]["content"] = new_content
    # 2. 截断：编辑了用户的 Prompt，通常意味着后面的 AI 回复作废
    st.session_state.studio_msgs = st.session_state.studio_msgs[:idx+1]
    # 3. 退出编辑
    st.session_state.editing_state = None
    # 4. 触发重新生成 (通过设置标记让主循环处理)
    st.session_state.trigger_inference = True
    st.rerun()

def cancel_edit():
    st.session_state.editing_state = None
    st.rerun()

def regenerate(idx):
    """重生成：删除这条 AI 回复，并触发上一条 User 消息的推理"""
    # 确保这条是 assistant 消息
    if st.session_state.studio_msgs[idx]["role"] == "model":
        # 删除当前条
        st.session_state.studio_msgs.pop(idx)
        # 触发推理
        st.session_state.trigger_inference = True
        st.rerun()

def build_gemini_history(msgs):
    """将 UI 消息转换为 Gemini API 格式"""
    history = []
    for m in msgs:
        if m["type"] == "text" or m.get("ref_image"):
            parts = []
            if m.get("ref_image"):
                parts.append(m["ref_image"])
            if m["content"]:
                parts.append(m["content"])
            
            if parts:
                history.append({
                    "role": m["role"],
                    "parts": parts
                })
    return history

# --- 3. 侧边栏 ---
with st.sidebar:
    st.title("🧪 AI Studio")
    
    # 模型选择
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
        st.caption("🎨 Generation Settings")
        ratio = st.selectbox("Aspect Ratio", ["1:1 (Square)", "4:3", "3:4", "16:9", "9:16"])
        seed_val = st.number_input("Seed (-1 Random)", value=-1)
    else:
        st.caption("🧠 System Instructions")
        sys_prompt = st.text_area("System Prompt", value="You are a helpful Amazon assistant.", height=150)

    st.divider()
    if st.button("🗑️ Clear All History", type="primary", use_container_width=True):
        st.session_state.studio_msgs = []
        st.rerun()

# --- 4. 主工作台 (历史消息渲染) ---
chat_container = st.container()

with chat_container:
    for idx, msg in enumerate(st.session_state.studio_msgs):
        
        # 判断是否正在编辑这条消息
        is_editing = (st.session_state.editing_state and st.session_state.editing_state["idx"] == idx)
        
        with st.chat_message(msg["role"]):
            
            # === 编辑模式视图 ===
            if is_editing:
                edit_col1, edit_col2 = st.columns([4, 1])
                with edit_col1:
                    new_val = st.text_area("Edit prompt:", value=msg["content"], label_visibility="collapsed")
                with edit_col2:
                    if st.button("Save & Run", key=f"save_{msg['id']}"):
                        save_edit(idx, new_val)
                    if st.button("Cancel", key=f"cancel_{msg['id']}"):
                        cancel_edit()
            
            # === 正常视图 ===
            else:
                # 1. 显示内容
                if msg.get("ref_image"):
                    st.image(msg["ref_image"], width=200)
                
                if msg["type"] == "image_result":
                    # 这里的 content 已经是缩略图了，直接显示
                    st.image(msg["content"], caption=f"Generated Image", width=400)
                else:
                    st.markdown(msg["content"])
                
                # 2. 操作栏 (Action Bar) - 模仿 Google AI Studio 放在消息下方
                # 使用 columns 布局操作按钮
                act_cols = st.columns([0.1, 0.1, 0.1, 0.1, 0.6])
                
                # 按钮A: 编辑 (仅用户)
                if msg["role"] == "user":
                    with act_cols[0]:
                        if st.button("✏️", key=f"edit_{msg['id']}", help="Edit prompt"):
                            start_edit(idx, msg["content"])
                
                # 按钮B: 重生成 (仅 AI)
                if msg["role"] == "model":
                    with act_cols[0]:
                        if st.button("🔄", key=f"regen_{msg['id']}", help="Regenerate"):
                            regenerate(idx)
                
                # 按钮C: 下载 (仅图片)
                if msg["type"] == "image_result" and msg.get("hd_data"):
                    with act_cols[1]:
                        st.download_button(
                            "⬇️", 
                            data=msg["hd_data"], 
                            file_name=f"gen_{msg['id']}.jpg", 
                            mime="image/jpeg", 
                            key=f"dl_{msg['id']}",
                            help="Download HD Image"
                        )
                
                # 按钮D: 删除 (通用)
                # 调整位置：如果是 AI 消息放在第二列，用户消息放在第二列
                del_col_idx = 2 if (msg["type"] == "image_result" or msg["role"]=="model") else 1
                with act_cols[del_col_idx]:
                    if st.button("🗑️", key=f"del_{msg['id']}", help="Delete this message"):
                        delete_msg(idx)

# --- 5. 推理逻辑 (Trigger Inference) ---
# 当用户输入、或点击"Save & Run"、或点击"Regenerate"时，trigger_inference 会被设为 True
if st.session_state.get("trigger_inference", False):
    # 立即复位标记
    st.session_state.trigger_inference = False
    
    # 获取上下文（最后一条通常是 User 的 Prompt）
    if not st.session_state.studio_msgs:
        st.stop()
        
    last_msg = st.session_state.studio_msgs[-1]
    
    # 必须保证最后一条是 User 发起的，才能让 AI 回复
    if last_msg["role"] == "user":
        
        with st.chat_message("model"):
            
            # === 生图模式 ===
            if is_image_mode:
                with st.status("🎨 Rendering...", expanded=True) as status:
                    try:
                        # 核心生图调用
                        hd_bytes = st.session_state.img_gen_studio.generate(
                            prompt=last_msg["content"],
                            model_name=current_model_id,
                            ref_image=last_msg.get("ref_image"),
                            ratio_suffix=f", aspect ratio {ratio.split()[0]}",
                            seed=int(seed_val) if seed_val != -1 else None
                        )
                        
                        if hd_bytes:
                            # 1. 修复的缩略图调用 (不使用关键字 size=)
                            thumb = create_preview_thumbnail(hd_bytes, 800)
                            
                            # 2. 追加到历史
                            st.session_state.studio_msgs.append({
                                "role": "model",
                                "type": "image_result",
                                "content": thumb,   # 预览图
                                "hd_data": hd_bytes, # 高清原图
                                "id": get_uid()
                            })
                            status.update(label="Complete", state="complete")
                            st.rerun()
                        else:
                            st.error("Safety filter triggered or error occurred.")
                            status.update(label="Failed", state="error")
                    except Exception as e:
                        st.error(f"Gen Error: {e}")

            # === 文本/对话模式 ===
            else:
                placeholder = st.empty()
                full_resp = ""
                
                try:
                    # 1. 动态重建历史 (Stateless 模式，保证上下文永远正确)
                    # 取出除了最后一条的所有历史作为 context
                    past_msgs = st.session_state.studio_msgs[:-1]
                    gemini_history = build_gemini_history(past_msgs)
                    
                    # 2. 初始化带 System Prompt 的模型
                    model = st.session_state.llm_studio.get_chat_model(current_model_id, sys_prompt)
                    chat = model.start_chat(history=gemini_history)
                    
                    # 3. 发送最后一条消息
                    user_content = []
                    if last_msg.get("ref_image"): user_content.append(last_msg["ref_image"])
                    if last_msg["content"]: user_content.append(last_msg["content"])
                    
                    response = chat.send_message(user_content, stream=True)
                    
                    for chunk in response:
                        if chunk.text:
                            full_resp += chunk.text
                            placeholder.markdown(full_resp + "▌")
                    
                    placeholder.markdown(full_resp)
                    
                    # 4. 追加结果
                    st.session_state.studio_msgs.append({
                        "role": "model",
                        "type": "text",
                        "content": full_resp,
                        "id": get_uid()
                    })
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Chat Error: {e}")

# --- 6. 底部输入框 ---
# 只有不在推理时才显示
if not st.session_state.get("trigger_inference", False):
    
    # 文件上传区
    with st.expander("📷 Add Image", expanded=False):
        uploaded_file = st.file_uploader("Upload", type=["jpg", "png", "webp"], label_visibility="collapsed")
    
    user_input = st.chat_input("Message Amazon AI Studio...")

    if user_input:
        img_obj = Image.open(uploaded_file) if uploaded_file else None
        
        # 存入历史
        st.session_state.studio_msgs.append({
            "role": "user",
            "type": "text",
            "content": user_input,
            "ref_image": img_obj,
            "id": get_uid()
        })
        
        # 设置标记，下一帧触发推理
        st.session_state.trigger_inference = True
        st.rerun()
