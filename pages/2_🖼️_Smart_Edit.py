import streamlit as st
from PIL import Image
import sys
import os
import time
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
# TAB 1: 标准工作流 (最终优化版)
# ==========================================
with tab_workflow:
    # 状态初始化
    if "std_prompts" not in st.session_state: st.session_state.std_prompts = []
    if "std_results" not in st.session_state: st.session_state.std_results = []

    c_main, c_view = st.columns([1.5, 1], gap="large")
    
    # --- 左侧：配置区 ---
    with c_main:
        st.markdown('<div class="step-header">Step 1: 需求配置</div>', unsafe_allow_html=True)
        
        # 1. 图片上传与原图预览 (优化点 1)
        uploaded_files = st.file_uploader("上传参考图", type=["jpg","png","webp"], accept_multiple_files=True)
        active_file = None
        
        if uploaded_files:
            # 多图选择逻辑
            target_name = st.selectbox("当前处理", [f.name for f in uploaded_files]) if len(uploaded_files) > 1 else uploaded_files[0].name
            active_file = next((f for f in uploaded_files if f.name == target_name), None)
            
            # ✨ 新增：原图预览区
            if active_file:
                with st.expander("🖼️ 查看当前参考原图", expanded=False):
                    st.image(active_file, width=300)

        col_t1, col_t2 = st.columns(2)
        task_type = col_t1.selectbox(
            "任务类型", 
            ["展示图 (Creative)", "场景图 (Lifestyle)", "产品图 (Product Only)"],
            help="Creative: 艺术感强的广告图; Lifestyle: 带生活场景的实拍感; Product Only: 纯白底或干净背景的产品特写。"
        )
        selected_style = col_t2.selectbox(
            "🎨 风格预设", 
            list(PRESETS.keys()), 
            index=0,
            help="选择预设风格，AI 会自动添加对应的光影、质感描述词。"
        )

        # 2. 创意输入
        user_idea = st.text_area(
            "你的创意 Prompt", 
            height=80, 
            placeholder="描述你的画面，例如：'放在木质桌面上，阳光洒在产品上'...",
            help="在这里输入你想要画面呈现的具体内容。支持中英文。"
        )
        st.caption("💡 **高级语法**：`(keyword)` 增加权重，`[keyword]` 减小权重。")
        
        # 3. 参数控制
        user_weight = st.slider(
            "⚖️ AI 参考权重", 0.0, 1.0, 0.6,
            help="0.0 = 完全听图片的（可能会忽略你的文字）；1.0 = 完全听文字的（可能会忽略原图结构）。推荐 0.6。"
        )
        neg_prompt = st.text_input(
            "🚫 负向提示词", 
            placeholder="low quality, deformed, messy",
            help="你【不希望】画面中出现的东西，比如 'blur' (模糊), 'dark' (太暗)。"
        )
        enable_split = st.checkbox(
            "🧩 启用多任务拆分", 
            value=False,
            help="勾选后，如果你的创意里包含多个不同的场景（用逗号隔开），AI 会尝试把它拆解成多张图分别生成。"
        )

        # 🧠 生成 Prompt 按钮
        if st.button("🧠 AI 思考并生成 Prompt", type="primary"):
            if not active_file: 
                st.toast("⚠️ 请先上传参考图片", icon="🚨")
            else:
                with st.status("🤖 AI 正在进行思维链思考...", expanded=True) as status:
                    st.write("👀 正在分析图片视觉特征...")
                    active_file.seek(0)
                    img_obj = Image.open(active_file)
                    time.sleep(0.5)
                    
                    st.write(f"🎨 正在融合【{selected_style}】风格与光影...")
                    prompts = llm.optimize_art_director_prompt(
                        user_idea, task_type, user_weight, selected_style, img_obj, enable_split
                    )
                    
                    st.write("📝 正在撰写最终 Prompt 并翻译...")
                    st.session_state.std_prompts = []
                    for p_en in prompts:
                        p_zh = llm.translate(p_en, "Simplified Chinese")
                        st.session_state.std_prompts.append({"en": p_en, "zh": p_zh})
                    
                    status.update(label="✅ Prompt 生成完毕！", state="complete", expanded=False)
                    st.toast("Prompt 已生成！", icon="✨")
                    st.rerun()

        # 🎨 执行生成区域
        if st.session_state.std_prompts:
            st.markdown('<div class="step-header">Step 2: 任务执行</div>', unsafe_allow_html=True)
            
            # Prompt 编辑区
            for i, p_data in enumerate(st.session_state.std_prompts):
                with st.expander(f"任务 {i+1} 指令", expanded=True):
                    col_zh, col_en = st.columns(2)
                    new_zh = col_zh.text_area("中文", p_data["zh"], key=f"p_zh_{i}", height=80)
                    if new_zh != p_data["zh"]: 
                        st.session_state.std_prompts[i]["zh"] = new_zh
                        st.session_state.std_prompts[i]["en"] = llm.translate(new_zh, "English")
                        st.rerun()
                    col_en.text_area("English", st.session_state.std_prompts[i]["en"], disabled=True, height=80)

            # 高级面板
            with st.container(border=True):
                st.caption("⚙️ **高级生成参数**")
                cg1, cg2 = st.columns(2)
                model_name = cg1.selectbox("🤖 基础模型", GOOGLE_IMG_MODELS, help="Flash 速度快但细节少；Pro 质量最高。")
                ratio_key = cg2.selectbox("📐 画幅比例", list(RATIO_MAP.keys()))
                
                # ✨ 优化点 4: Flash 模型比例警告
                if "flash" in model_name.lower() and "1:1" not in ratio_key:
                    st.warning("⚠️ 注意：Flash 模型通常强制输出 1:1 方图。如需宽/长图，建议切换到 Pro 模型。", icon="⚠️")

                cg3, cg4 = st.columns(2)
                safety_level = cg3.selectbox("🛡️ 安全过滤", ["Standard (标准)", "Permissive (宽松 - 适合内衣/泳装)", "Strict (严格)"], help="如果生成被拦截，请选'宽松'。")
                creativity = cg4.slider("🎨 创意度", 0.0, 1.0, 0.5, help="值越高，AI 发挥的随机性越大。")
                
                cg5, cg6 = st.columns([0.8, 0.2], vertical_alignment="bottom")
                seed_input = cg5.number_input("🎲 Seed", value=-1, step=1, help="-1 为随机。输入固定数字可复现结果。")
                real_seed = None if seed_input == -1 else int(seed_input)

            # 生成按钮
            if st.button("🚀 开始生成图片", type="primary", use_container_width=True):
                st.session_state.std_results = []
                img_pil = Image.open(active_file) if active_file else None
                
                bar = st.progress(0)
                total = len(st.session_state.std_prompts)
                
                with st.status("🎨 正在绘制中...", expanded=True) as status:
                    for idx, task in enumerate(st.session_state.std_prompts):
                        st.write(f"正在执行任务 {idx+1}/{total}...")
                        
                        res_bytes = img_gen.generate(
                            task["en"], model_name, img_pil, RATIO_MAP[ratio_key], 
                            negative_prompt=neg_prompt,
                            seed=real_seed, creativity=creativity, safety_level=safety_level.split()[0]
                        )
                        
                        if res_bytes:
                            st.session_state.std_results.append(res_bytes)
                            history.add(res_bytes, f"Task {idx+1}", task["zh"])
                        else:
                            st.error(f"任务 {idx+1} 生成失败")
                            
                        bar.progress((idx + 1) / total)
                    
                    status.update(label="🎉 执行完毕！", state="complete", expanded=False)
                    st.toast("图片生成完成！", icon="🖼️")

    # --- 右侧：结果预览区 (优化点 2) ---
    with c_view:
        if st.session_state.std_results:
            st.subheader("🖼️ 结果预览")
            for idx, img_bytes in enumerate(st.session_state.std_results):
                with st.container(border=True):
                    # 显示图片
                    thumb = create_preview_thumbnail(img_bytes, 400)
                    st.image(thumb, use_container_width=True, caption=f"Result {idx+1}")
                    
                    # ✨ 新增：快速操作按钮行
                    b_col1, b_col2 = st.columns(2)
                    with b_col1:
                        if st.button("🔍 放大", key=f"v_zoom_{idx}", use_container_width=True):
                            show_image_modal(img_bytes, f"Result {idx+1}")
                    with b_col2:
                        final_bytes, mime = process_image_for_download(img_bytes, format="JPEG")
                        st.download_button(
                            "📥 下载", 
                            data=final_bytes, 
                            file_name=f"result_{idx+1}.jpg", 
                            mime=mime, 
                            key=f"v_dl_{idx}", 
                            use_container_width=True
                        )
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
