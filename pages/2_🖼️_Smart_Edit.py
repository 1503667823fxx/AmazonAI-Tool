import streamlit as st
from PIL import Image
import sys
import os
# 在 Smart_Edit.py 顶部添加：
from services.styles import PRESETS

# --- 路径修复 ---
current_script_path = os.path.abspath(__file__)
pages_dir = os.path.dirname(current_script_path)
root_dir = os.path.dirname(pages_dir)
if root_dir not in sys.path:
    sys.path.append(root_dir)

try:
    import auth
    # 👇 引入纯逻辑
    from app_utils.history_manager import HistoryManager
    # 👇 引入纯 UI 组件
    from app_utils.ui_components import render_history_sidebar, show_image_modal
    from app_utils.image_processing import create_preview_thumbnail
    
    from services.llm_engine import LLMEngine
    from services.image_engine import ImageGenEngine
except ImportError as e:
    st.error(f"❌ 模块导入失败: {e}")
    st.stop()

# --- 1. 页面配置 ---
st.set_page_config(page_title="Fashion AI Core", page_icon="🧬", layout="wide")

# --- 2. 初始化 ---
if 'auth' in sys.modules and not auth.check_password():
    st.stop()

if "services_ready" not in st.session_state:
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("❌ 未找到 GOOGLE_API_KEY")
        st.stop()
    st.session_state.llm = LLMEngine(api_key)
    st.session_state.img_gen = ImageGenEngine(api_key)
    st.session_state.history = HistoryManager()
    st.session_state.services_ready = True

llm = st.session_state.llm
img_gen = st.session_state.img_gen
history = st.session_state.history

# --- 3. 样式 ---
st.markdown("""
<style>
    .step-header {
        background: linear-gradient(90deg, #e3f2fd 0%, #ffffff 100%);
        padding: 10px 15px; border-radius: 8px; border-left: 5px solid #2196F3;
        margin: 20px 0 10px 0; font-weight: 600; color: #0D47A1;
    }
    .stButton button { border-radius: 8px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

ANALYSIS_MODELS = ["models/gemini-flash-latest", "models/gemini-3-pro-preview"]
GOOGLE_IMG_MODELS = ["models/gemini-2.5-flash-image", "models/gemini-3-pro-image-preview"]
RATIO_MAP = {
    "1:1 (Square)": ", crop to 1:1 aspect ratio",
    "4:3 (Landscape)": ", 4:3 landscape aspect ratio",
    "21:9 (Cinematic)": ", cinematic 21:9 ultrawide"
}

# --- 4. 侧边栏 ---
with st.sidebar:
    st.title("🗂️ 工作区")
    # 👇 使用新分离出来的 UI 组件
    render_history_sidebar(history) 
    download_format = st.radio("📥 下载格式", ["PNG", "JPEG"], horizontal=True)

# --- 5. 主界面 ---
st.title("🧬 Fashion AI Core V6.1 (Modular UI)")
tab_workflow, tab_variants, tab_background = st.tabs(["✨ 标准精修", "⚡ 变体改款", "🏞️ 场景置换"])

# ... (后面的 Tab 代码逻辑保持不变，不需要动) ...

# ==========================================
# TAB 1: 标准工作流 (Prompt 引擎升级版)
# ==========================================
with tab_workflow:
    if "std_prompts" not in st.session_state: st.session_state.std_prompts = []
    if "std_results" not in st.session_state: st.session_state.std_results = []

    c_main, c_view = st.columns([1.5, 1], gap="large")
    
    with c_main:
        st.markdown('<div class="step-header">Step 1: 需求配置</div>', unsafe_allow_html=True)
        
        # 1. 图片与任务
        uploaded_files = st.file_uploader("上传参考图", type=["jpg","png","webp"], accept_multiple_files=True)
        active_file = None
        if uploaded_files:
            target_name = st.selectbox("当前处理", [f.name for f in uploaded_files]) if len(uploaded_files) > 1 else uploaded_files[0].name
            active_file = next((f for f in uploaded_files if f.name == target_name), None)

        col_t1, col_t2 = st.columns(2)
        task_type = col_t1.selectbox("任务类型", ["展示图 (Creative)", "场景图 (Lifestyle)", "产品图 (Product Only)"])
        # ✨ 新增：风格选择器
        selected_style = col_t2.selectbox("🎨 风格预设", list(PRESETS.keys()), index=0)

        # 2. 创意与权重
        user_idea = st.text_area("你的创意 Prompt", height=80, placeholder="描述你的画面...")
        
        # ✨ 新增：语法提示
        st.caption("💡 **高级语法提示**：使用 `(keyword)` 增加权重，`[keyword]` 减小权重。例如：`(red dress), [blue sky]`")
        
        # ✨ 权重条 (已存在，逻辑已在 LLM 中强化)
        user_weight = st.slider("⚖️ AI 参考权重 (User vs Image)", 0.0, 1.0, 0.6, help="0.0: 完全听图片的; 1.0: 完全听你的 Prompt; 0.6: 平衡")
        
        # ✨ 新增：负向提示词
        neg_prompt = st.text_input("🚫 负向提示词 (Negative Prompt)", placeholder="例如：low quality, deformed, messy background")
        
        enable_split = st.checkbox("🧩 启用多任务拆分", value=False)

        # 🧠 生成 Prompt (AI 思考过程)
        if st.button("🧠 AI 思考并生成 Prompt", type="primary"):
            if not active_file: st.warning("请先上传图片")
            else:
                with st.spinner(f"AI 正在运用【{selected_style}】风格进行构图思考..."):
                    active_file.seek(0)
                    img_obj = Image.open(active_file)
                    
                    # 调用 LLM 服务 (传入了 style_key)
                    prompts = llm.optimize_art_director_prompt(
                        user_idea, task_type, user_weight, selected_style, img_obj, enable_split
                    )
                    
                    st.session_state.std_prompts = []
                    for p_en in prompts:
                        p_zh = llm.translate(p_en, "Simplified Chinese")
                        st.session_state.std_prompts.append({"en": p_en, "zh": p_zh})
                    st.rerun()

# ... (Step 2 之前的代码保持不变) ...

        # 🎨 执行生成 (Step 2 UI 更新)
        if st.session_state.std_prompts:
            st.markdown('<div class="step-header">Step 2: 任务执行</div>', unsafe_allow_html=True)
            
            # (Prompt 显示区域代码保持不变，省略...)
            for i, p_data in enumerate(st.session_state.std_prompts):
                with st.expander(f"任务 {i+1} 指令", expanded=True):
                    # ... (这部分代码保持你原来的样子) ...
                    col_zh, col_en = st.columns(2)
                    new_zh = col_zh.text_area("中文", p_data["zh"], key=f"p_zh_{i}", height=80)
                    if new_zh != p_data["zh"]: 
                        st.session_state.std_prompts[i]["zh"] = new_zh
                        st.session_state.std_prompts[i]["en"] = llm.translate(new_zh, "English")
                        st.rerun()
                    col_en.text_area("English", st.session_state.std_prompts[i]["en"], disabled=True, height=80)

            # --- ✨ 核心新增：高级控制面板 ---
            with st.container(border=True):
                st.caption("⚙️ **高级生成参数 (Advanced Controls)**")
                
                # 第一行：模型与比例
                cg1, cg2 = st.columns(2)
                model_name = cg1.selectbox("🤖 基础模型", GOOGLE_IMG_MODELS)
                ratio_key = cg2.selectbox("📐 画幅比例", list(RATIO_MAP.keys()))
                
                # 第二行：安全与创意
                cg3, cg4 = st.columns(2)
                safety_level = cg3.selectbox(
                    "🛡️ 安全过滤等级 (Safety Filter)", 
                    ["Standard (标准)", "Permissive (宽松 - 适合内衣/泳装)", "Strict (严格)"],
                    index=0,
                    help="【真实生效】如果生成内衣或泳装模特时提示错误，请选择'宽松'模式。这将降低 Google 的 NSFW 拦截阈值。"
                )
                creativity = cg4.slider(
                    "🎨 创意度 (Temperature)", 0.0, 1.0, 0.5,
                    help="【真实生效】0.0: 严谨、更忠实于原图构图; 1.0: 狂野、更多随机细节。"
                )

                # 第三行：Seed 控制
                cg5, cg6 = st.columns([0.8, 0.2], gap="small", vertical_alignment="bottom")
                seed_input = cg5.number_input(
                    "🎲 随机种子 (Seed)", value=-1, step=1,
                    help="【尝试生效】输入固定数字(如 42)可尝试固定画面特征。输入 -1 代表完全随机。"
                )
                if cg6.button("🎲", help="随机生成一个 Seed"):
                    # 这是一个小技巧：通过 rerun 来刷新 number_input 的默认值比较麻烦
                    # 我们这里简单提示用户手动改，或者配合 session state 做（为保持简单暂不展开）
                    pass
                
                real_seed = None if seed_input == -1 else int(seed_input)

            # --- 生成按钮 ---
            btn_col1, btn_col2 = st.columns([3, 1])
            with btn_col1:
                start_btn = st.button("🚀 开始生成图片 (Batch Run)", type="primary", use_container_width=True)
            
            if start_btn:
                st.session_state.std_results = []
                img_pil = Image.open(active_file) if active_file else None
                
                bar = st.progress(0)
                total = len(st.session_state.std_prompts)
                
                for idx, task in enumerate(st.session_state.std_prompts):
                    with st.spinner(f"生成中 ({idx+1}/{total}) | 🛡️安全: {safety_level.split()[0]} | 🎲Seed: {real_seed if real_seed else 'Random'}..."):
                        
                        # ✨ 调用升级版 generate 接口
                        res_bytes = img_gen.generate(
                            prompt=task["en"], 
                            model_name=model_name, 
                            ref_image=img_pil, 
                            ratio_suffix=RATIO_MAP[ratio_key], 
                            negative_prompt=neg_prompt, # 记得确保 neg_prompt 变量在上面定义了(Tab 1 Step 1里)
                            seed=real_seed,
                            creativity=creativity,
                            safety_level=safety_level.split()[0] # 传入 'Permissive' 等关键词
                        )
                        
                        if res_bytes:
                            st.session_state.std_results.append(res_bytes)
                            history.add(res_bytes, f"Task {idx+1}", task["zh"]) 
                        else:
                            st.error(f"任务 {idx+1} 生成失败，已自动重试。请检查 Prompt 是否违规。")
                            
                    bar.progress((idx + 1) / total)
                st.success("🎉 队列执行完毕！")

        # ... (后续预览代码不变) ...

    with c_view:
        if st.session_state.std_results:
            st.subheader("结果预览")
            for b in st.session_state.std_results:
                st.image(create_preview_thumbnail(b, 400))

# ==========================================
# TAB 2: 变体改款 (重构版)
# ==========================================
with tab_variants:
    st.markdown("### ⚡ 服装改款")
    if "var_en" not in st.session_state: st.session_state.var_en = ""
    
    var_file = st.file_uploader("上传原图", type=["jpg","png"], key="var_up")
    if var_file and st.button("👁️ 分析特征"):
        with st.spinner("正在提取特征..."):
            var_file.seek(0)
            # 调用 LLM 分析
            desc = llm.analyze_image_style(Image.open(var_file), "Describe fashion details: Silhouette, Fabric, Color.")
            st.session_state.var_en = desc
            st.session_state.var_zh = llm.translate(desc, "Chinese")
            st.success("特征已提取")

    if st.session_state.var_en:
        c1, c2 = st.columns(2)
        base_desc = c1.text_area("基础特征", st.session_state.var_zh, height=100)
        mod_req = c2.text_area("改款需求", placeholder="例如：把袖子改成蕾丝材质...", height=100)
        
        if st.button("⚡ 生成变体"):
            full_prompt = f"Base: {llm.translate(base_desc, 'English')}. Modification: {llm.translate(mod_req, 'English')}. Keep main silhouette."
            with st.spinner("生成中..."):
                var_file.seek(0)
                res = img_gen.generate(full_prompt, GOOGLE_IMG_MODELS[0], Image.open(var_file), "")
                if res:
                    st.image(res, caption="变体结果")
                    history.add(res, "Variant", mod_req)

# ==========================================
# TAB 3: 场景置换 (重构版 - 极简逻辑)
# ==========================================
with tab_background:
    st.markdown("### 🏞️ 场景置换")
    bg_file = st.file_uploader("上传产品", key="bg_up")
    bg_desc = st.text_area("新背景描述", placeholder="例如：放在海边沙滩上")
    
    if st.button("🏞️ 换背景") and bg_file:
        with st.spinner("正在置换..."):
            bg_file.seek(0)
            # 1. 简单分析 (可选)
            # 2. 直接生成
            prompt = f"Product Photography. Place this product in background: {llm.translate(bg_desc, 'English')}. Perfect lighting."
            res = img_gen.generate(prompt, GOOGLE_IMG_MODELS[1], Image.open(bg_file), "")
            if res:
                st.image(res, caption="新场景")
                history.add(res, "BG Swap", bg_desc)
