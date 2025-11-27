import streamlit as st
import google.generativeai as genai
from PIL import Image
import io
import sys
import os
import time
from collections import deque 

# --- 0. 基础设置与核心库引入 ---
sys.path.append(os.path.abspath('.'))

# 1. 尝试导入 auth (如果不存在则跳过，不影响核心功能)
try:
    import auth
    HAS_AUTH = True
except ImportError:
    HAS_AUTH = False

# 2. 尝试导入核心工具 (核心依赖，如果失败则使用备用)
try:
    from core_utils import AITranslator, process_image_for_download, create_preview_thumbnail, HistoryManager, show_preview_modal
except ImportError:
    # 备用类定义 (防止报错)
    class AITranslator:
        def to_english(self, t): return t
        def to_chinese(self, t): return t
    class HistoryManager:
        def add(self, a, b, c): pass
        def render_sidebar(self): pass
    
    # 修复：备用函数必须接收 format 参数
    def process_image_for_download(b, format="PNG"): return b, "image/png"
    
    # 修复：备用函数必须接收 max_width 参数 (这是之前报错的根源)
    def create_preview_thumbnail(b, max_width=800): return b
    
    def show_preview_modal(b, c): pass

st.set_page_config(page_title="Fashion AI Core", page_icon="🧬", layout="wide")

# 门禁检查 (仅在 auth 存在时启用)
if HAS_AUTH and 'auth' in sys.modules:
    if not auth.check_password():
        st.stop()

# API Key 检查
if "GOOGLE_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GOOGLE_API_KEY"])
else:
    st.error("❌ 错误：未找到 GOOGLE_API_KEY")
    st.stop()

# --- 初始化核心组件 ---
if "translator" not in st.session_state:
    st.session_state.translator = AITranslator()
if "history_manager" not in st.session_state:
    st.session_state.history_manager = HistoryManager()

# --- 样式优化 ---
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
    .stTextArea { margin-bottom: 0px; }
    .stAlert { padding: 10px; }
</style>
""", unsafe_allow_html=True)

# --- 常量 ---
ANALYSIS_MODELS = ["models/gemini-flash-latest", "models/gemini-2.5-pro", "models/gemini-3-pro-preview"]
GOOGLE_IMG_MODELS = ["models/gemini-2.5-flash-image", "models/gemini-3-pro-image-preview"]
RATIO_MAP = {
    "1:1 (正方形电商图)": ", crop and center composition to 1:1 square aspect ratio",
    "4:3 (常规横向)": ", adjust composition to 4:3 landscape aspect ratio",
    "21:9 (电影感超宽)": ", cinematic 21:9 ultrawide aspect ratio"
}

# --- 状态管理 ---
# Tab 1: 标准工作流
if "std_prompt_data" not in st.session_state: st.session_state["std_prompt_data"] = [] 
if "std_images" not in st.session_state: st.session_state["std_images"] = []

# Tab 2: 改款
if "var_prompt_en" not in st.session_state: st.session_state["var_prompt_en"] = ""
if "var_prompt_zh" not in st.session_state: st.session_state["var_prompt_zh"] = ""
if "batch_results" not in st.session_state: st.session_state["batch_results"] = []

# Tab 3: 换背景
if "bg_prompt_en" not in st.session_state: st.session_state["bg_prompt_en"] = ""
if "bg_prompt_zh" not in st.session_state: st.session_state["bg_prompt_zh"] = ""
if "bg_results" not in st.session_state: st.session_state["bg_results"] = []

# --- 辅助函数 ---
def generate_image_call(model_name, prompt, image_input, ratio_suffix):
    # 净化 Prompt
    clean_prompt = prompt.replace("16:9", "").replace("4:3", "").replace("1:1", "").replace("Aspect Ratio", "")
    final_prompt = clean_prompt + ratio_suffix + ", high quality, 8k resolution, photorealistic, commercial lighting"
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

# --- 侧边栏 ---
with st.sidebar:
    st.title("🗂️ 工作区")
    download_format = st.radio("📥 下载格式", ["PNG", "JPEG"], horizontal=True)
    # 渲染历史记录
    st.session_state.history_manager.render_sidebar()

# ==========================================
# 🚀 主界面
# ==========================================
st.title("🧬 Fashion AI Core V5.6")
tab_workflow, tab_variants, tab_background = st.tabs(["✨ 标准精修 (Workstation)", "⚡ 变体改款", "🏞️ 场景置换"])

# ==========================================
# TAB 1: 标准工作流 (支持多图上传 + 可选拆分 + 权重控制)
# ==========================================
with tab_workflow:
    col_main, col_preview = st.columns([1.5, 1], gap="large")

    with col_main:
        st.markdown('<div class="step-header">Step 1: 需求分析</div>', unsafe_allow_html=True)
        
        c1, c2 = st.columns([1, 1])
        with c1: analysis_model = st.selectbox("1. 读图模型", ANALYSIS_MODELS, index=0)
        with c2: 
            uploaded_files = st.file_uploader("2. 上传参考图 (支持多选)", type=["jpg", "png", "webp"], key="std_upload", accept_multiple_files=True)

        active_file = None
        if uploaded_files:
            if len(uploaded_files) > 1:
                file_names = [f.name for f in uploaded_files]
                selected_name = st.selectbox("👉 选择当前要处理的图片:", file_names)
                for f in uploaded_files:
                    if f.name == selected_name:
                        active_file = f
                        break
            else:
                active_file = uploaded_files[0]
        
        task_type = st.selectbox("3. 任务类型", ["场景图 (Lifestyle)", "展示图 (Creative)", "产品图 (Product Only)"])
        user_idea = st.text_area("4. 你的创意", height=80, placeholder="例如：改为极简主义风格，白色背景...")

        # 创意权重滑块
        user_weight = st.slider(
            "5. 创意权重 (User Influence)", 
            0.0, 1.0, 0.6, step=0.1, 
            help="0.0 = 完全听AI的(忠实原图); 1.0 = 完全听你的(忠实文字); 0.6 = 平衡模式"
        )

        # 拆分任务开关
        enable_split = st.checkbox("🧩 启用智能任务拆分 (多任务模式)", value=False, help="勾选后，AI 会尝试将复杂需求(如'一张上衣，一张裤子')拆解为多个独立的生图任务。")

        if st.button("🧠 生成 Prompt", type="primary"):
            if not active_file: st.warning("⚠️ 请先上传或选择图片")
            else:
                with st.spinner(f"AI 正在分析 (权重: {user_weight})..."):
                    try:
                        active_file.seek(0)
                        img_obj = Image.open(active_file)
                        model = genai.GenerativeModel(analysis_model)
                        
                        # 注入高质量摄影指令
                        special_instruction = ""
                        if "Product Only" in task_type:
                            special_instruction = """
                            SPECIAL INSTRUCTION FOR PRODUCT PHOTOGRAPHY:
                            1. **Layout**: If user implies 'flat lay' or 'break down', use "Knolling photography", "Neatly arranged".
                            2. **Realism**: Use "Contact shadows", "Ambient occlusion" to avoid floating look.
                            3. **Texture**: Emphasize "fabric texture", "material details".
                            """
                        
                        # 核心权重逻辑注入
                        weight_instruction = f"""
                        WEIGHT CONTROL INSTRUCTION (Important):
                        The user has set an influence weight of {user_weight} (Range 0.0 to 1.0).
                        - If weight > 0.7: Prioritize the User's Idea ('{user_idea}') over the visual analysis of the image. Even if it conflicts with the image, follow the text.
                        - If weight < 0.3: Prioritize the Visual Analysis of the image. Use the User's Idea only as a subtle suggestion.
                        - If weight is 0.4-0.6: Balance both equally.
                        """

                        if enable_split:
                            prompt_req = f"""
                            Role: Art Director. 
                            Task: Create detailed prompts based on User Idea and Image. Type: {task_type}.
                            {weight_instruction}
                            {special_instruction}
                            IMPORTANT LOGIC: Split distinct outputs into separate prompts using "|||".
                            STRICT OUTPUT FORMAT: Separate prompts with "|||". NO Markdown.
                            User Idea: {user_idea}
                            Output: English Prompts Only.
                            """
                        else:
                            prompt_req = f"""
                            Role: Art Director. 
                            Task: Create ONE single, high-quality prompt based on User Idea and Image. Type: {task_type}.
                            {weight_instruction}
                            {special_instruction}
                            STRICT OUTPUT FORMAT: Provide ONE unified prompt. NO "|||". NO Markdown.
                            User Idea: {user_idea}
                            Output: English Prompt Only.
                            """

                        response = model.generate_content([prompt_req, img_obj])
                        raw_text = response.text.strip()
                        
                        prompt_list = raw_text.split("|||")
                        
                        st.session_state["std_prompt_data"] = []
                        for p in prompt_list:
                            p_en = p.strip()
                            if p_en:
                                p_zh = st.session_state.translator.to_chinese(p_en)
                                st.session_state["std_prompt_data"].append({"en": p_en, "zh": p_zh})
                        st.rerun()
                    except Exception as e: st.error(f"分析失败: {e}")

        # Step 2: 任务渲染区
        if st.session_state["std_prompt_data"]:
            st.markdown('<div class="step-header">Step 2: 任务执行</div>', unsafe_allow_html=True)
            
            for i, p_data in enumerate(st.session_state["std_prompt_data"]):
                expander_label = f"📝 任务 {i+1}" if len(st.session_state["std_prompt_data"]) > 1 else "📝 生成指令微调"
                
                with st.expander(expander_label, expanded=True):
                    col_zh, col_en = st.columns(2)
                    with col_zh:
                        key_zh = f"std_zh_{i}"
                        if key_zh not in st.session_state: st.session_state[key_zh] = p_data["zh"]
                        # TAB 1 的同步逻辑：更新列表中的数据
                        def update_en(idx=i):
                            new_zh = st.session_state[f"std_zh_{idx}"]
                            new_en = st.session_state.translator.to_english(new_zh)
                            st.session_state["std_prompt_data"][idx]["zh"] = new_zh
                            st.session_state["std_prompt_data"][idx]["en"] = new_en
                        st.text_area("中文指令 (可编辑)", key=key_zh, height=100, on_change=update_en)
                    with col_en:
                        st.text_area("English Prompt (只读)", value=st.session_state["std_prompt_data"][i]["en"], height=100, disabled=True, key=f"std_en_view_{i}")

            cg1, cg2, cg3 = st.columns(3)
            with cg1: google_model = st.selectbox("模型", GOOGLE_IMG_MODELS)
            with cg2: selected_ratio_key = st.selectbox("比例", list(RATIO_MAP.keys()))
            with cg3: num_images = st.number_input("单任务生成数量", 1, 4, 1)

            if "flash" in google_model and "1:1" not in selected_ratio_key:
                st.warning("⚠️ 警告：Gemini 2.5 Flash 强制 1:1 输出。")

            if st.button("🎨 开始生成", type="primary"):
                st.session_state["std_images"] = []
                total_tasks = len(st.session_state["std_prompt_data"]) * num_images
                current_progress = 0
                bar = st.progress(0)
                
                if active_file:
                    active_file.seek(0)
                    img_pil = Image.open(active_file)
                    for task_idx, task_data in enumerate(st.session_state["std_prompt_data"]):
                        prompt_en = task_data["en"]
                        prompt_zh = task_data["zh"]
                        for n in range(num_images):
                            with st.spinner(f"执行任务 {task_idx+1} (第 {n+1} 张)..."):
                                active_file.seek(0)
                                # 再次确认读取，防止指针问题
                                img_pil = Image.open(active_file)
                                img_data = generate_image_call(google_model, prompt_en, img_pil, RATIO_MAP[selected_ratio_key])
                                if img_data:
                                    st.session_state["std_images"].append(img_data)
                                    st.session_state.history_manager.add(img_data, f"Task {task_idx+1}", prompt_zh)
                                current_progress += 1
                                bar.progress(current_progress / total_tasks)
                                time.sleep(1)
                    st.success("🎉 执行完毕！")

    # 右侧预览 (TAB 1)
    with col_preview:
        st.subheader("🖼️ 结果预览")
        if active_file:
            with st.expander("🔍 当前参考图", expanded=True):
                active_file.seek(0)
                st.image(Image.open(active_file), use_container_width=True)

        if st.session_state["std_images"]:
            st.divider()
            for idx, img_bytes in enumerate(st.session_state["std_images"]):
                thumb = create_preview_thumbnail(img_bytes, max_width=400)
                st.image(thumb, caption=f"Result {idx+1}", width=350)
                
                c_btn1, c_btn2 = st.columns([1.5, 1])
                with c_btn1:
                    final_bytes, mime = process_image_for_download(img_bytes, format=download_format)
                    st.download_button(f"📥 下载", data=final_bytes, file_name=f"std_{idx}.{download_format.lower()}", mime=mime, use_container_width=True)
                with c_btn2:
                    if st.button(f"🔍 放大", key=f"zoom_std_{idx}", use_container_width=True):
                        show_preview_modal(img_bytes, f"Result {idx+1}")

# ==========================================
# TAB 2: ⚡ 变体改款 (Restyling) - 优化版
# ==========================================
with tab_variants:
    st.markdown("### ⚡ 服装改款工厂")
    
    cv_left, cv_right = st.columns([1.5, 1], gap="large")

    # TAB 2 的同步逻辑：更新全局变量 var_prompt_en
    def update_var_en():
        val = st.session_state.var_prompt_zh
        if val:
            st.session_state.var_prompt_en = st.session_state.translator.to_english(val)
    
    with cv_left:
        st.markdown("#### Step 1: AI 读取产品特征")
        var_file = st.file_uploader("上传原版图片", type=["jpg", "png"], key="var_upload")
        var_ana_model = st.selectbox("分析模型", ANALYSIS_MODELS, index=0, key="var_ana_model")
        
        if st.button("👁️ AI 读图", key="btn_var_ana"):
            if not var_file: st.warning("请先上传")
            else:
                with st.spinner("提取中..."):
                    try:
                        var_file.seek(0)
                        v_img = Image.open(var_file)
                        model = genai.GenerativeModel(var_ana_model)
                        prompt = "Describe the main fashion product details: Silhouette, Fabric, Color, Pattern. Output pure text."
                        resp = model.generate_content([prompt, v_img])
                        
                        en_text = resp.text.strip()
                        st.session_state["var_prompt_en"] = en_text
                        st.session_state["var_prompt_zh"] = st.session_state.translator.to_chinese(en_text)
                        st.success("成功")
                    except Exception as e: st.error(f"失败: {e}")

        # Step 2: 改款设置
        st.markdown("#### Step 2: 改款设置")
        
        vp_col1, vp_col2 = st.columns(2)
        with vp_col1:
            # 绑定 on_change 事件到同步函数
            st.text_area("🇨🇳 特征描述 (中文 - 可编辑)", key="var_prompt_zh", height=100, on_change=update_var_en)
        with vp_col2:
            st.text_area("🇺🇸 Feature Desc (English - Auto)", key="var_prompt_en", height=100, disabled=True)

        CHANGE_LEVELS = {
            "🎨 微调 (纹理/面料)": "Keep silhouette exactly same. Only modify fabric.",
            "✂️ 中改 (领口/袖口)": "Keep fit. Modify details like collar/sleeves.",
            "🪄 大改 (版型重构)": "Redesign silhouette based on vibe."
        }
        change_level = st.selectbox("改款幅度", list(CHANGE_LEVELS.keys()))
        user_mod = st.text_area("改款指令", height=60)
        
        batch_count = st.slider("数量", 1, 20, 4, key="var_batch")
        var_model = st.selectbox("模型", GOOGLE_IMG_MODELS, key="var_gen_model")
        start_batch = st.button("🚀 启动批量改款", type="primary")

    with cv_right:
        st.subheader("🖼️ 结果预览")
        
        if var_file:
            with st.expander("🔍 原图预览", expanded=True):
                var_file.seek(0)
                st.image(Image.open(var_file), use_container_width=True)

        if start_batch and var_file and st.session_state["var_prompt_en"]:
            st.session_state["batch_results"] = []
            st.divider()
            grid = st.columns(2)
            sys_instruct = CHANGE_LEVELS[change_level]
            my_bar = st.progress(0)
            
            for i in range(batch_count):
                try:
                    var_file.seek(0)
                    v_img = Image.open(var_file)
                    # AI 读取的是 session_state['var_prompt_en']，它已经被同步函数更新了
                    prompt = f"Task: Restyling. Base: {st.session_state['var_prompt_en']}. Constraint: {sys_instruct}. Mod Request: {user_mod}. Var ID: {i}"
                    img_data = generate_image_call(var_model, prompt, v_img, "")
                    if img_data:
                        st.session_state["batch_results"].append(img_data)
                        st.session_state.history_manager.add(img_data, f"Restyle {i+1}", user_mod)
                        
                        with grid[i%2]:
                            thumb = create_preview_thumbnail(img_data, max_width=300)
                            st.image(thumb, use_container_width=True)
                            if st.button("🔍", key=f"zoom_var_{i}"):
                                show_preview_modal(img_data, f"Var {i+1}")
                except Exception as e: print(f"VarGen Error: {e}")
                my_bar.progress((i+1)/batch_count)
                time.sleep(1)
        
        if st.session_state["batch_results"]:
            st.divider()
            for idx, img_bytes in enumerate(st.session_state["batch_results"]):
                final_bytes, mime = process_image_for_download(img_bytes, format=download_format)
                st.download_button(f"📥 下载 {idx+1}", final_bytes, file_name=f"var_{idx}.{download_format.lower()}", mime=mime)

# ==========================================
# TAB 3: 🏞️ 场景置换 (Scene Swap) - 优化版
# ==========================================
with tab_background:
    st.markdown("### 🏞️ 场景批量置换")
    
    cb_left, cb_right = st.columns([1.5, 1], gap="large")

    # TAB 3 的同步逻辑：更新全局变量 bg_prompt_en
    def update_bg_en():
        val = st.session_state.bg_prompt_zh
        if val:
            st.session_state.bg_prompt_en = st.session_state.translator.to_english(val)

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

        # Step 2: 换背景设置
        st.markdown("#### Step 2: 换背景设置")
        bp_col1, bp_col2 = st.columns(2)
        with bp_col1:
            # 绑定 on_change 事件到同步函数
            st.text_area("🇨🇳 产品特征 (中文 - 可编辑)", key="bg_prompt_zh", height=100, on_change=update_bg_en)
        with bp_col2:
            st.text_area("🇺🇸 Product Features (English - Auto)", key="bg_prompt_en", height=100, disabled=True)
        
        bg_desc = st.text_area("新背景描述", height=60, placeholder="例如：放在木质纹理的桌面上...")
        bg_count = st.slider("数量", 1, 20, 4, key="bg_count")
        bg_model = st.selectbox("模型", GOOGLE_IMG_MODELS, index=1, key="bg_gen_model")
        start_bg = st.button("🚀 启动换背景", type="primary")

    with cb_right:
        st.subheader("🖼️ 结果预览")

        if bg_file:
            with st.expander("🔍 原图预览", expanded=True):
                bg_file.seek(0)
                st.image(Image.open(bg_file), use_container_width=True)

        if start_bg and bg_file and st.session_state["bg_prompt_en"]:
            st.session_state["bg_results"] = []
            st.divider()
            bg_grid = st.columns(2)
            bg_bar = st.progress(0)
            
            for i in range(bg_count):
                try:
                    bg_file.seek(0)
                    v_img = Image.open(bg_file)
                    # AI 读取的是 session_state['bg_prompt_en']
                    prompt = f"Product BG Swap. Product: {st.session_state['bg_prompt_en']}. New BG: {bg_desc}. Constraint: KEEP PRODUCT SAME. Var ID: {i}"
                    img_data = generate_image_call(bg_model, prompt, v_img, "")
                    if img_data:
                        st.session_state["bg_results"].append(img_data)
                        st.session_state.history_manager.add(img_data, f"BG Swap {i+1}", bg_desc)
                        
                        with bg_grid[i%2]:
                            thumb = create_preview_thumbnail(img_data, max_width=300)
                            st.image(thumb, use_container_width=True)
                            if st.button("🔍", key=f"zoom_bg_{i}"):
                                show_preview_modal(img_data, f"Scene {i+1}")
                except Exception as e: print(f"BGGen Error: {e}")
                bg_bar.progress((i+1)/bg_count)
                time.sleep(1)
        
        if st.session_state["bg_results"]:
            st.divider()
            for idx, img_bytes in enumerate(st.session_state["bg_results"]):
                final_bytes, mime = process_image_for_download(img_bytes, format=download_format)
                st.download_button(f"📥 下载 {idx+1}", final_bytes, file_name=f"scene_{idx}.{download_format.lower()}", mime=mime)
