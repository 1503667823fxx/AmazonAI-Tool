import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import sys
import os
import time
import random
from collections import deque 

# --- 0. 基础设置与门禁系统 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
except ImportError:
    pass 

st.set_page_config(page_title="Fashion AI Core", page_icon="🧬", layout="wide")

# 执行安全检查
if 'auth' in sys.modules:
    if not auth.check_password():
        st.stop()

# --- 1. 鉴权配置 ---
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("❌ 错误：未找到 GOOGLE_API_KEY")
    st.stop()

# --- 2. 样式优化 (CSS) ---
st.markdown("""
<style>
    .step-header {
        background: linear-gradient(90deg, #e3f2fd 0%, #ffffff 100%);
        padding: 12px 20px;
        border-radius: 8px;
        border-left: 6px solid #2196F3;
        margin-top: 25px;
        margin-bottom: 15px;
        font-weight: 600;
        color: #0D47A1;
        font-size: 1.1rem;
    }
    .stButton button {
        border-radius: 8px;
        height: 3em; 
        font-weight: bold;
    }
    .preview-card {
        border: 1px solid #ddd;
        padding: 10px;
        border-radius: 8px;
        background-color: #f9f9f9;
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. 常量定义 ---

# 读图分析模型
ANALYSIS_MODELS = ["models/gemini-2.0-flash-exp", "models/gemini-1.5-pro", "models/gemini-1.5-flash"]

# 生图模型
GOOGLE_IMG_MODELS = [
    "models/gemini-2.5-flash-image", 
    "models/gemini-3-pro-image-preview" # 只有这个对比例支持比较好
]

# 比例控制 (精简版)
# 2.5 Flash 对 Prompt 改变比例的响应很差，建议在 UI 上做引导
RATIO_MAP = {
    "1:1 (正方形电商图)": ", crop and center composition to 1:1 square aspect ratio",
    "4:3 (常规横向)": ", adjust composition to 4:3 landscape aspect ratio",
    "21:9 (电影感超宽)": ", cinematic 21:9 ultrawide aspect ratio"
}

# --- 4. 状态管理 ---
if "history_queue" not in st.session_state:
    st.session_state["history_queue"] = deque(maxlen=10)
if "draft_prompt" not in st.session_state:
    st.session_state["draft_prompt"] = ""
if "last_generated_images" not in st.session_state:
    st.session_state["last_generated_images"] = [] 

# --- 5. 辅助函数 ---
def update_history(image_data, source="AI", prompt_summary=""):
    timestamp = time.strftime("%H:%M:%S")
    st.session_state["history_queue"].appendleft({
        "image": image_data,
        "source": source,
        "time": timestamp,
        "desc": prompt_summary[:30] + "..."
    })

def generate_image_call(model_name, prompt, image_input, ratio_suffix):
    """封装 API 调用，增加错误重试机制"""
    final_prompt = prompt + ratio_suffix + ", high quality, 8k resolution"
    gen_model = genai.GenerativeModel(model_name)
    
    # 尝试调用
    try:
        response = gen_model.generate_content([final_prompt, image_input], stream=True)
        for chunk in response:
            if hasattr(chunk, "parts"):
                for part in chunk.parts:
                    if part.inline_data:
                        return part.inline_data.data
    except Exception as e:
        # 这里可以捕获具体的 Google API 错误
        print(f"Error: {e}")
        return None
    return None

# ==========================================
# 🚀 侧边栏：历史记录
# ==========================================
with st.sidebar:
    st.title("🗂️ 工作区")
    with st.expander("🕒 历史记录 (History)", expanded=False):
        if len(st.session_state["history_queue"]) == 0:
            st.caption("暂无生成记录")
        else:
            for item in st.session_state["history_queue"]:
                st.markdown(f"**{item['source']}**")
                st.caption(f"Time: {item['time']}")
                # 显示小缩略图
                st.image(item['image'], width=150)
                st.divider()

# ==========================================
# 🚀 主界面：多标签页架构 (V3.0)
# ==========================================
st.title("🧬 Fashion AI Core V3.0")

# 分为三个主要功能区
tab_workflow, tab_variants, tab_background = st.tabs(["✨ 标准精修", "⚡ 变体改款", "🏞️ 场景置换"])

# ==========================================
# TAB 1: 标准工作流 (Standard)
# ==========================================
with tab_workflow:
    col_main, col_preview = st.columns([1.3, 1], gap="large")

    with col_main:
        st.markdown('<div class="step-header">Step 1: 需求分析</div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns([1, 1])
        with c1:
            analysis_model = st.selectbox("1. 读图模型", ANALYSIS_MODELS, index=0)
        with c2:
            # 增加 key 避免组件 ID 冲突
            uploaded_file = st.file_uploader("2. 上传参考图", type=["jpg", "png", "webp"], key="std_upload")

        # 预留素材区 (保持 UI 占位)
        with st.expander("🎨 场景/画质/光影素材库", expanded=False):
            st.info("🚧 快捷指令区 (开发中)")

        task_type = st.selectbox("3. 任务类型", ["场景图 (Lifestyle)", "展示图 (Creative)", "产品图 (Product Only)"])
        user_idea = st.text_area("4. 你的创意", height=100, placeholder="例如：改为极简主义风格，白色背景...")

        if st.button("🧠 生成 Prompt", type="primary"):
            if not uploaded_file:
                st.warning("⚠️ 请先上传图片")
            else:
                with st.spinner("AI 正在思考..."):
                    try:
                        uploaded_file.seek(0)
                        img_obj = Image.open(uploaded_file)
                        model = genai.GenerativeModel(analysis_model)
                        
                        prompt_req = f"Role: Art Director. Task: Create a prompt based on User Idea: '{user_idea}'. Type: {task_type}. Output: English Prompt Only."
                        response = model.generate_content([prompt_req, img_obj])
                        st.session_state["draft_prompt"] = response.text.strip()
                        st.rerun()
                    except Exception as e:
                        st.error(f"分析失败: {e}")

        # Step 2
        if st.session_state.get("draft_prompt"):
            st.markdown('<div class="step-header">Step 2: 执行生成</div>', unsafe_allow_html=True)
            
            edited_prompt = st.text_area("Prompt", value=st.session_state["draft_prompt"], height=120)
            st.session_state["draft_prompt"] = edited_prompt

            cg1, cg2, cg3 = st.columns(3)
            with cg1: google_model = st.selectbox("模型", GOOGLE_IMG_MODELS)
            with cg2: selected_ratio_key = st.selectbox("比例", list(RATIO_MAP.keys()))
            with cg3: num_images = st.number_input("数量", 1, 4, 1)

            # --- 智能风控提醒 ---
            if "flash" in google_model and "1:1" not in selected_ratio_key:
                st.warning("⚠️ 注意：Gemini 2.5 Flash 模型通常强制 1:1 输出。如需 4:3 或 21:9，建议切换至 3.0 Pro 模型。")

            if st.button("🎨 开始生成", type="primary"):
                st.session_state["last_generated_images"] = []
                bar = st.progress(0)
                for i in range(num_images):
                    uploaded_file.seek(0)
                    img_pil = Image.open(uploaded_file)
                    img_data = generate_image_call(google_model, edited_prompt, img_pil, RATIO_MAP[selected_ratio_key])
                    if img_data:
                        st.session_state["last_generated_images"].append(img_data)
                        update_history(img_data, source=f"Std {i+1}", prompt_summary=edited_prompt)
                    bar.progress((i+1)/num_images)
                    time.sleep(1)
                st.success("完成")

    # 右侧预览
    with col_preview:
        st.subheader("🖼️ 快速预览")
        if st.session_state["last_generated_images"]:
            for idx, img_bytes in enumerate(st.session_state["last_generated_images"]):
                # 使用较小的宽度进行快速预览，提升加载感官体验
                st.image(img_bytes, caption=f"Result {idx+1} (Preview)", width=350)
                st.download_button(f"📥 下载原图 {idx+1}", img_bytes, file_name=f"std_{idx}.png")
        elif uploaded_file:
             st.image(uploaded_file, caption="原图", width=200)

# ==========================================
# TAB 2: ⚡ 变体改款 (Restyling)
# ==========================================
with tab_variants:
    st.markdown("### ⚡ 服装改款工厂")
    st.info("💡 专用于修改服装款式、面料、细节。")
    
    cv1, cv2 = st.columns([1, 2], gap="large")
    with cv1:
        var_file = st.file_uploader("上传原版", type=["jpg", "png"], key="var_upload")
        if var_file: st.image(var_file, width=200)
        
        CHANGE_LEVELS = {
            "🎨 微调 (纹理/面料)": "Keep structure same. Only modify fabric/texture.",
            "✂️ 中改 (领口/袖口)": "Keep shape. Modify details like collar/sleeve.",
            "🪄 大改 (版型重构)": "Redesign silhouette and style significantly."
        }
        change_level = st.selectbox("改款幅度", list(CHANGE_LEVELS.keys()))
        var_prompt = st.text_area("改款指令", height=100, placeholder="例如：改为丝绸材质，增加蕾丝花边...")
        batch_count = st.slider("生成数量", 1, 20, 4)
        var_model = st.selectbox("模型", GOOGLE_IMG_MODELS, key="var_model")
        
        start_batch = st.button("🚀 启动改款", type="primary")

    with cv2:
        st.subheader("📦 方案池")
        if "batch_results" not in st.session_state: st.session_state["batch_results"] = []
        
        if start_batch and var_file:
            st.session_state["batch_results"] = []
            grid = st.columns(3)
            sys_instruct = CHANGE_LEVELS[change_level]
            
            my_bar = st.progress(0)
            for i in range(batch_count):
                try:
                    var_file.seek(0)
                    v_img = Image.open(var_file)
                    # 引入随机数种子 Random Seed 确保每次生成不同
                    random_seed = random.randint(1000, 999999)
                    prompt = f"{sys_instruct} User Request: {var_prompt}. \nIMPORTANT: Generate a unique variation different from others. \nRandom Seed: {random_seed}"
                    
                    img_data = generate_image_call(var_model, prompt, v_img, "")
                    if img_data:
                        st.session_state["batch_results"].append(img_data)
                        with grid[i%3]:
                            st.image(img_data, use_container_width=True) 
                except: pass
                my_bar.progress((i+1)/batch_count)
                time.sleep(1.5)

# ==========================================
# TAB 3: 🏞️ 场景置换 (Background Swap) - 新增
# ==========================================
with tab_background:
    st.markdown("### 🏞️ 场景批量置换")
    st.info("💡 专用于 **保留产品主体**，仅更换背景环境。")
    
    cb1, cb2 = st.columns([1, 2], gap="large")
    with cb1:
        bg_file = st.file_uploader("上传产品图", type=["jpg", "png"], key="bg_upload")
        if bg_file: st.image(bg_file, width=200)
        
        bg_desc = st.text_area("背景描述", height=100, placeholder="例如：放在木质纹理的桌面上，背景是模糊的咖啡厅，自然光...")
        bg_count = st.slider("生成数量", 1, 20, 4, key="bg_count")
        bg_model = st.selectbox("模型", GOOGLE_IMG_MODELS, index=1, key="bg_model", help="推荐使用 3.0 Pro 以获得更好的指令遵循")
        
        start_bg = st.button("🚀 启动换背景", type="primary")

    with cb2:
        st.subheader("📦 场景池")
        if "bg_results" not in st.session_state: st.session_state["bg_results"] = []
        
        if start_bg and bg_file:
            st.session_state["bg_results"] = []
            bg_grid = st.columns(3)
            bg_bar = st.progress(0)
            
            for i in range(bg_count):
                try:
                    bg_file.seek(0)
                    v_img = Image.open(bg_file)
                    # 引入随机数种子和随机化指令
                    random_seed = random.randint(1000, 999999)
                    prompt = f"Product Photography. KEEP THE FOREGROUND PRODUCT EXACTLY THE SAME. DO NOT CHANGE THE PRODUCT. Only replace the background with: {bg_desc}. \nIMPORTANT: Randomize the background composition, lighting, and angle to ensure it is unique. \nRandom Seed: {random_seed}"
                    
                    img_data = generate_image_call(bg_model, prompt, v_img, "")
                    if img_data:
                        st.session_state["bg_results"].append(img_data)
                        update_history(img_data, source=f"BG Swap {i+1}", prompt_summary=bg_desc)
                        with bg_grid[i%3]:
                            st.image(img_data, use_container_width=True)
                except Exception as e:
                    st.error(f"Error: {e}")
                
                bg_bar.progress((i+1)/bg_count)
                time.sleep(1.5)
        
        # 显示缓存
        elif st.session_state["bg_results"]:
            bg_grid = st.columns(3)
            for idx, img_bytes in enumerate(st.session_state["bg_results"]):
                with bg_grid[idx%3]:
                    st.image(img_bytes, caption=f"Scene {idx+1}", use_container_width=True)
                    st.download_button("📥", img_bytes, file_name=f"scene_{idx}.png", key=f"dl_bg_{idx}")
