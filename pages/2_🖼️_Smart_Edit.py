import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import sys
import os
import time
from collections import deque 

# --- 0. 基础设置与门禁系统 ---
sys.path.append(os.path.abspath('.'))
try:
    import auth
    # 尝试引入翻译模块，如果失败则定义一个哑类防止报错
    from translator import AITranslator 
except ImportError:
    class AITranslator:
        def to_english(self, text): return text
        def to_chinese(self, text): return text
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

# 初始化翻译器 (使用 Session State 防止重复初始化)
if "translator" not in st.session_state:
    st.session_state.translator = AITranslator()

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
    /* 紧凑布局 */
    .stTextArea { margin-bottom: 0px; }
    
    /* 警告框样式微调 */
    .stAlert { padding: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 3. 常量定义 ---
ANALYSIS_MODELS = ["models/gemini-flash-latest", "models/gemini-2.5-pro", "models/gemini-3-pro-preview"]
GOOGLE_IMG_MODELS = ["models/gemini-2.5-flash-image", "models/gemini-3-pro-image-preview"]

RATIO_MAP = {
    "1:1 (正方形电商图)": ", crop and center composition to 1:1 square aspect ratio",
    "4:3 (常规横向)": ", adjust composition to 4:3 landscape aspect ratio",
    "21:9 (电影感超宽)": ", cinematic 21:9 ultrawide aspect ratio"
}

# --- 4. 状态管理 ---
if "history_queue" not in st.session_state: st.session_state["history_queue"] = deque(maxlen=10)

# Tab 1 States
if "std_prompt_en" not in st.session_state: st.session_state["std_prompt_en"] = ""
if "std_prompt_zh" not in st.session_state: st.session_state["std_prompt_zh"] = "" 
if "std_images" not in st.session_state: st.session_state["std_images"] = []

# Tab 2 States
if "var_prompt_en" not in st.session_state: st.session_state["var_prompt_en"] = ""
if "var_prompt_zh" not in st.session_state: st.session_state["var_prompt_zh"] = ""
if "batch_results" not in st.session_state: st.session_state["batch_results"] = []

# Tab 3 States
if "bg_prompt_en" not in st.session_state: st.session_state["bg_prompt_en"] = ""
if "bg_prompt_zh" not in st.session_state: st.session_state["bg_prompt_zh"] = ""
if "bg_results" not in st.session_state: st.session_state["bg_results"] = []

# --- 5. 辅助函数 ---
def update_history(image_data, source="AI", prompt_summary=""):
    timestamp = time.strftime("%H:%M:%S")
    st.session_state["history_queue"].appendleft({
        "image": image_data, "source": source, "time": timestamp, "desc": prompt_summary[:30] + "..."
    })

@st.cache_data(show_spinner=False)
def convert_image_format(image_bytes, format="PNG"):
    try:
        image = Image.open(io.BytesIO(image_bytes))
        buf = io.BytesIO()
        if format.upper() == "JPEG":
            if image.mode in ("RGBA", "P"): image = image.convert("RGB")
        image.save(buf, format=format, quality=95)
        return buf.getvalue(), f"image/{format.lower()}"
    except Exception as e:
        return image_bytes, "image/png"

def generate_image_call(model_name, prompt, image_input, ratio_suffix):
    # 强制清理 prompt，移除可能的冲突指令
    clean_prompt = prompt.replace("16:9", "").replace("4:3", "").replace("1:1", "").replace("Aspect Ratio", "")
    final_prompt = clean_prompt + ratio_suffix + ", high quality, 8k resolution, photorealistic"
    
    gen_model = genai.GenerativeModel(model_name)
    try:
        response = gen_model.generate_content([final_prompt, image_input], stream=True)
        for chunk in response:
            if hasattr(chunk, "parts"):
                for part in chunk.parts:
                    if part.inline_data:
                        return part.inline_data.data
    except Exception as e:
        print(f"Error: {e}")
        return None
    return None

# --- 双语同步回调 ---
def sync_std_zh_to_en():
    val = st.session_state.std_prompt_zh
    if val: st.session_state.std_prompt_en = st.session_state.translator.to_english(val)

def sync_var_zh_to_en():
    val = st.session_state.var_prompt_zh
    if val: st.session_state.var_prompt_en = st.session_state.translator.to_english(val)

def sync_bg_zh_to_en():
    val = st.session_state.bg_prompt_zh
    if val: st.session_state.bg_prompt_en = st.session_state.translator.to_english(val)

# --- 弹窗预览函数 (支持 st.dialog) ---
# 检查 Streamlit 版本是否支持 dialog，不支持则回退
if hasattr(st, "dialog"):
    @st.dialog("高清大图预览", width="large")
    def show_hd_image(image_bytes, caption):
        st.image(image_bytes, caption=caption, use_container_width=True)
else:
    # 兼容旧版本的回退方案
    def show_hd_image(image_bytes, caption):
        with st.expander("🔍 高清大图 (点击展开)", expanded=True):
            st.image(image_bytes, caption=caption, use_container_width=True)

# ==========================================
# 🚀 侧边栏
# ==========================================
with st.sidebar:
    st.title("🗂️ 工作区")
    download_format = st.radio("📥 下载格式", ["PNG", "JPEG"], horizontal=True)
    with st.expander("🕒 历史记录", expanded=False):
        if not st.session_state["history_queue"]:
            st.caption("暂无记录")
        else:
            for item in st.session_state["history_queue"]:
                st.markdown(f"**{item['source']}**")
                st.image(item['image'], width=150)
                st.divider()

# ==========================================
# 🚀 主界面
# ==========================================
st.title("🧬 Fashion AI Core V5.2")
tab_workflow, tab_variants, tab_background = st.tabs(["✨ 标准精修", "⚡ 变体改款", "🏞️ 场景置换"])

# ==========================================
# TAB 1: 标准工作流 (Standard)
# ==========================================
with tab_workflow:
    col_main, col_preview = st.columns([1.5, 1], gap="large")

    with col_main:
        st.markdown('<div class="step-header">Step 1: 需求分析</div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns([1, 1])
        with c1: analysis_model = st.selectbox("1. 读图模型", ANALYSIS_MODELS, index=0)
        with c2: uploaded_file = st.file_uploader("2. 上传参考图", type=["jpg", "png", "webp"], key="std_upload")

        task_type = st.selectbox("3. 任务类型", ["场景图 (Lifestyle)", "展示图 (Creative)", "产品图 (Product Only)"])
        user_idea = st.text_area("4. 你的创意", height=80, placeholder="例如：改为极简主义风格，白色背景...")

        if st.button("🧠 生成 Prompt", type="primary"):
            if not uploaded_file: st.warning("⚠️ 请先上传图片")
            else:
                with st.spinner("AI 正在构思 (双语同步中)..."):
                    try:
                        uploaded_file.seek(0)
                        img_obj = Image.open(uploaded_file)
                        model = genai.GenerativeModel(analysis_model)
                        
                        # 核心修改：增加负面约束，防止输出比例和Markdown
                        prompt_req = f"""
                        Role: Art Director. 
                        Task: Create a prompt based on User Idea: '{user_idea}'. Type: {task_type}.
                        
                        STRICT CONSTRAINTS:
                        1. Output ONLY the visual description keywords (comma separated or sentences).
                        2. DO NOT mention aspect ratios (e.g. 16:9, 4:3).
                        3. DO NOT use markdown, asterisks (**), or headers.
                        4. DO NOT mention resolution numbers like '4096x2048'.
                        
                        Output: English Prompt Only.
                        """
                        response = model.generate_content([prompt_req, img_obj])
                        
                        en_text = response.text.strip()
                        # 翻译成中文
                        zh_text = st.session_state.translator.to_chinese(en_text)
                        
                        st.session_state["std_prompt_en"] = en_text
                        st.session_state["std_prompt_zh"] = zh_text
                        st.rerun()
                    except Exception as e: st.error(f"分析失败: {e}")

        # Step 2: 双语编辑区
        if st.session_state.get("std_prompt_en"):
            st.markdown('<div class="step-header">Step 2: 指令微调 (双语同步)</div>', unsafe_allow_html=True)
            
            p_col1, p_col2 = st.columns(2)
            with p_col1:
                st.text_area(
                    "🇨🇳 中文指令 (在此编辑)", 
                    key="std_prompt_zh", 
                    height=150,
                    on_change=sync_std_zh_to_en 
                )
            with p_col2:
                st.text_area(
                    "🇺🇸 English Prompt (AI 读取只读)", 
                    key="std_prompt_en", 
                    height=150,
                    disabled=True 
                )

            cg1, cg2, cg3 = st.columns(3)
            with cg1: google_model = st.selectbox("模型", GOOGLE_IMG_MODELS)
            with cg2: selected_ratio_key = st.selectbox("比例", list(RATIO_MAP.keys()))
            with cg3: num_images = st.number_input("数量", 1, 4, 1)

            # 【修复】补回 Flash 模型比例警告
            if "flash" in google_model and "1:1" not in selected_ratio_key:
                st.warning("⚠️ 警告：Gemini 2.5 Flash 模型强制 1:1 输出，忽略比例设置。如需宽屏/竖屏，请切换至 3.0 Pro 模型。")

            if st.button("🎨 开始生成", type="primary"):
                st.session_state["std_images"] = []
                bar = st.progress(0)
                for i in range(num_images):
                    uploaded_file.seek(0)
                    img_pil = Image.open(uploaded_file)
                    img_data = generate_image_call(google_model, st.session_state["std_prompt_en"], img_pil, RATIO_MAP[selected_ratio_key])
                    if img_data:
                        st.session_state["std_images"].append(img_data)
                        update_history(img_data, source=f"Std {i+1}", prompt_summary=st.session_state["std_prompt_zh"])
                    bar.progress((i+1)/num_images)
                    time.sleep(1)
                st.success("完成")

    # 右侧预览区
    with col_preview:
        st.subheader("🖼️ 结果预览")
        
        if uploaded_file:
            with st.expander("🔍 原始参考图", expanded=True):
                st.image(uploaded_file, use_container_width=True)

        if st.session_state["std_images"]:
            st.divider()
            st.markdown("#### ✨ 生成结果")
            for idx, img_bytes in enumerate(st.session_state["std_images"]):
                # 预览图 (350px 宽度，快速加载)
                st.image(img_bytes, caption=f"Result {idx+1}", width=350)
                
                # 功能按钮行
                c_btn1, c_btn2 = st.columns([1.5, 1])
                with c_btn1:
                    final_bytes, mime = convert_image_format(img_bytes, download_format)
                    st.download_button(
                        f"📥 下载 ({download_format})", 
                        data=final_bytes, 
                        file_name=f"std_{idx}.{download_format.lower()}", 
                        mime=mime,
                        use_container_width=True
                    )
                with c_btn2:
                    # 【优化】使用 st.dialog 弹出模态框预览
                    if st.button(f"🔍 放大", key=f"zoom_std_{idx}", use_container_width=True):
                        show_hd_image(img_bytes, f"Result {idx+1}")

# ==========================================
# TAB 2: ⚡ 变体改款 (Restyling)
# ==========================================
with tab_variants:
    st.markdown("### ⚡ 服装改款工厂")
    
    cv_left, cv_right = st.columns([1.5, 1], gap="large")
    with cv_left:
        st.markdown("#### Step 1: AI 读取产品特征")
        var_file = st.file_uploader("上传原版图片", type=["jpg", "png"], key="var_upload")
        var_ana_model = st.selectbox("分析模型", ANALYSIS_MODELS, index=0, key="var_ana_model")
        
        if st.button("👁️ AI 读图提取特征", key="btn_var_ana"):
            if not var_file: st.warning("请先上传图片")
            else:
                with st.spinner("提取中..."):
                    try:
                        var_file.seek(0)
                        v_img = Image.open(var_file)
                        model = genai.GenerativeModel(var_ana_model)
                        prompt = "Describe the main fashion product details: Silhouette, Fabric, Color, Pattern. Output pure text, no markdown."
                        resp = model.generate_content([prompt, v_img])
                        
                        en_text = resp.text.strip()
                        st.session_state["var_prompt_en"] = en_text
                        st.session_state["var_prompt_zh"] = st.session_state.translator.to_chinese(en_text)
                        st.success("特征提取成功")
                    except Exception as e: st.error(f"读取失败: {e}")

        # Step 2
        st.markdown("#### Step 2: 改款设置")
        
        vp_col1, vp_col2 = st.columns(2)
        with vp_col1:
            st.text_area("🇨🇳 特征描述 (中文 - 可编辑)", key="var_prompt_zh", height=100, on_change=sync_var_zh_to_en)
        with vp_col2:
            st.text_area("🇺🇸 Feature Desc (English)", key="var_prompt_en", height=100, disabled=True)

        CHANGE_LEVELS = {
            "🎨 微调 (纹理/面料)": "Keep the main silhouette and structure EXACTLY the same. Only modify fabric texture.",
            "✂️ 中改 (领口/袖口)": "Keep the overall fit. Modify specific details like collar/sleeves.",
            "🪄 大改 (版型重构)": "Redesign silhouette and style significantly based on vibe."
        }
        change_level = st.selectbox("改款幅度", list(CHANGE_LEVELS.keys()))
        user_mod = st.text_area("改款指令 (例如: 改为丝绸材质)", height=60)
        
        batch_count = st.slider("数量", 1, 20, 4, key="var_batch")
        var_model = st.selectbox("模型", GOOGLE_IMG_MODELS, key="var_gen_model")
        start_batch = st.button("🚀 启动批量改款", type="primary")

    with cv_right:
        st.subheader("📦 方案预览")
        if start_batch and var_file and st.session_state["var_prompt_en"]:
            st.session_state["batch_results"] = []
            grid = st.columns(2)
            sys_instruct = CHANGE_LEVELS[change_level]
            my_bar = st.progress(0)
            
            for i in range(batch_count):
                try:
                    var_file.seek(0)
                    v_img = Image.open(var_file)
                    prompt = f"Task: Restyling. Base: {st.session_state['var_prompt_en']}. Constraint: {sys_instruct}. Mod Request: {user_mod}. Var ID: {i}"
                    img_data = generate_image_call(var_model, prompt, v_img, "")
                    if img_data:
                        st.session_state["batch_results"].append(img_data)
                        with grid[i%2]:
                            st.image(img_data, use_container_width=True)
                            if st.button("🔍", key=f"zoom_var_{i}"):
                                show_hd_image(img_data, f"Var {i+1}")
                except: pass
                my_bar.progress((i+1)/batch_count)
                time.sleep(1)
        
        if st.session_state["batch_results"]:
            st.divider()
            for idx, img_bytes in enumerate(st.session_state["batch_results"]):
                final_bytes, mime = convert_image_format(img_bytes, download_format)
                st.download_button(f"📥 下载方案 {idx+1}", final_bytes, file_name=f"var_{idx}.{download_format.lower()}", mime=mime)

# ==========================================
# TAB 3: 🏞️ 场景置换 (Background)
# ==========================================
with tab_background:
    st.markdown("### 🏞️ 场景批量置换")
    
    cb_left, cb_right = st.columns([1.5, 1], gap="large")
    with cb_left:
        st.markdown("#### Step 1: AI 锁定产品")
        bg_file = st.file_uploader("上传产品图", type=["jpg", "png"], key="bg_upload")
        bg_ana_model = st.selectbox("分析模型", ANALYSIS_MODELS, index=0, key="bg_ana_model")
        
        if st.button("🔒 锁定产品特征", key="btn_bg_ana"):
            if not bg_file: st.warning("请先上传")
            else:
                with st.spinner("锁定中..."):
                    try:
                        bg_file.seek(0)
                        v_img = Image.open(bg_file)
                        model = genai.GenerativeModel(bg_ana_model)
                        prompt = "Describe FOREGROUND PRODUCT ONLY in detail. Ignore background. Output pure text."
                        resp = model.generate_content([prompt, v_img])
                        
                        en_text = resp.text.strip()
                        st.session_state["bg_prompt_en"] = en_text
                        st.session_state["bg_prompt_zh"] = st.session_state.translator.to_chinese(en_text)
                        st.success("锁定成功")
                    except Exception as e: st.error(f"失败: {e}")

        # Step 2: 双语编辑
        st.markdown("#### Step 2: 换背景设置")
        bp_col1, bp_col2 = st.columns(2)
        with bp_col1:
            st.text_area("🇨🇳 产品特征 (中文)", key="bg_prompt_zh", height=100, on_change=sync_bg_zh_to_en)
        with bp_col2:
            st.text_area("🇺🇸 Product Features (English)", key="bg_prompt_en", height=100, disabled=True)
        
        bg_desc = st.text_area("新背景描述", height=60, placeholder="例如：木质桌面，自然光...")
        bg_count = st.slider("数量", 1, 20, 4, key="bg_count")
        bg_model = st.selectbox("模型", GOOGLE_IMG_MODELS, index=1, key="bg_gen_model")
        start_bg = st.button("🚀 启动换背景", type="primary")

    with cb_right:
        st.subheader("📦 场景预览")
        if start_bg and bg_file and st.session_state["bg_prompt_en"]:
            st.session_state["bg_results"] = []
            bg_grid = st.columns(2)
            bg_bar = st.progress(0)
            
            for i in range(bg_count):
                try:
                    bg_file.seek(0)
                    v_img = Image.open(bg_file)
                    prompt = f"Product BG Swap. Product: {st.session_state['bg_prompt_en']}. New BG: {bg_desc}. Constraint: KEEP PRODUCT SAME. Var ID: {i}"
                    img_data = generate_image_call(bg_model, prompt, v_img, "")
                    if img_data:
                        st.session_state["bg_results"].append(img_data)
                        with bg_grid[i%2]:
                            st.image(img_data, use_container_width=True)
                            if st.button("🔍", key=f"zoom_bg_{i}"):
                                show_hd_image(img_data, f"Scene {i+1}")
                except: pass
                bg_bar.progress((i+1)/bg_count)
                time.sleep(1)
        
        if st.session_state["bg_results"]:
            st.divider()
            for idx, img_bytes in enumerate(st.session_state["bg_results"]):
                final_bytes, mime = convert_image_format(img_bytes, download_format)
                st.download_button(f"📥 下载 {idx+1}", final_bytes, file_name=f"scene_{idx}.{download_format.lower()}", mime=mime)
