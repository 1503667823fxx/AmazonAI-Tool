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
    from app_utils.image_processing import create_preview_thumbnail, process_image_for_download
    
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
# TAB 1: 标准工作流 (多图融合升级版)
# ==========================================
with tab_workflow:
    # 状态初始化
    if "std_prompts" not in st.session_state: st.session_state.std_prompts = []
    if "std_results" not in st.session_state: st.session_state.std_results = []
    if "prompt_ver" not in st.session_state: st.session_state.prompt_ver = 0

    c_main, c_view = st.columns([1.5, 1], gap="large")
    
    # --- 左侧：配置区 ---
    with c_main:
        st.markdown('<div class="step-header">Step 1: 需求配置</div>', unsafe_allow_html=True)
        
        # 1. 上传与模式选择
        uploaded_files = st.file_uploader("上传参考图", type=["jpg","png","webp"], accept_multiple_files=True)
        
        # ✨ 新增：处理模式开关 (关键逻辑)
        proc_mode = st.radio(
            "⚙️ 处理模式", 
            ["🔄 单图批量 (Batch Loop)", "🧩 多图融合 (Composite)"], 
            horizontal=True,
            help="单图批量：上传5张图，分别生成5次；\n多图融合：上传5张图（如人+场景），AI 读取所有内容生成 1 个融合后的 Prompt。"
        )

        active_img_input = None # 将要传给 LLM 的图片对象（单图或列表）
        active_ref_for_gen = None # 将要传给 ImageGen 的参考图

        if uploaded_files:
            if proc_mode == "🔄 单图批量 (Batch Loop)":
                # 旧逻辑：选一张作为当前主图
                file_names = [f.name for f in uploaded_files]
                target_name = st.selectbox("👉 选择当前要处理的原图", file_names)
                active_file = next((f for f in uploaded_files if f.name == target_name), None)
                
                if active_file:
                    with st.expander(f"🖼️ 查看原图: {target_name}", expanded=True):
                        st.image(active_file, width=300)
                    active_img_input = Image.open(active_file)
                    active_ref_for_gen = active_img_input # 生图时参考这张

            else: # 🧩 多图融合 (Composite)
                st.info(f"已选中 {len(uploaded_files)} 张图片进行融合分析 (例如：人物 + 背景)")
                # 展示所有图的小缩略图
                cols = st.columns(len(uploaded_files))
                img_list = []
                for idx, f in enumerate(uploaded_files):
                    img = Image.open(f)
                    img_list.append(img)
                    with cols[idx]:
                        st.image(img, use_container_width=True, caption=f"Img {idx+1}")
                
                active_img_input = img_list # 传给 LLM 一个列表
                # 注意：多图融合时，生图阶段通常很难同时参考多张图的结构（除非用ControlNet）。
                # 策略：生图时我们不传 reference image，而是完全依赖 LLM 融合后写出的详细 Prompt。
                # 或者，你可以选择其中一张作为结构参考（这里暂定为 None，全靠 Prompt）
                active_ref_for_gen = None 
        else:
            st.info("👆 请先上传图片")

        col_t1, col_t2 = st.columns(2)
        task_type = col_t1.selectbox(
            "任务类型", 
            ["展示图 (Creative)", "场景图 (Lifestyle)", "产品图 (Product Only)"],
            help="Creative: 艺术感强的广告图; Lifestyle: 带生活场景的实拍感; Product Only: 纯白底或干净背景的产品特写。"
        )
        selected_style = col_t2.selectbox(
            "🎨 风格预设", 
            list(PRESETS.keys()), 
            index=0
        )

        # 2. 创意输入
        user_idea = st.text_area(
            "你的创意 Prompt", 
            height=80, 
            placeholder="描述你的画面，例如：'把图1的模特放进图2的背景里'...",
            help="在融合模式下，请明确告诉 AI 哪张图是干嘛的。"
        )
        st.caption("💡 **高级语法**：`(keyword)` 增加权重，`[keyword]` 减小权重。")
        
        # 3. 参数控制
        user_weight = st.slider("⚖️ AI 参考权重", 0.0, 1.0, 0.6)
        neg_prompt = st.text_input("🚫 负向提示词", placeholder="low quality, deformed, messy")
        enable_split = st.checkbox("🧩 启用多任务拆分", value=False)

        # 🧠 生成 Prompt 按钮
        if st.button("🧠 AI 思考并生成 Prompt", type="primary"):
            if not uploaded_files: 
                st.toast("⚠️ 请先上传图片", icon="🚨")
            else:
                with st.status("🤖 AI 正在进行思维链思考...", expanded=True) as status:
                    st.write("👀 正在阅读图片内容...")
                    
                    # 如果是多图，可能需要重新 seek(0)
                    if isinstance(active_img_input, list):
                        for img in active_img_input:
                            if hasattr(img, 'seek'): img.seek(0)
                    elif hasattr(active_img_input, 'seek'):
                        active_img_input.seek(0)

                    time.sleep(0.5)
                    
                    st.write(f"🎨 正在融合【{selected_style}】风格与光影...")
                    
                    # ✨ 调用升级版 LLM 接口 (支持传入列表)
                    prompts = llm.optimize_art_director_prompt(
                        user_idea, task_type, user_weight, selected_style, active_img_input, enable_split
                    )
                    
                    st.write("📝 正在撰写最终 Prompt 并翻译...")
                    st.session_state.std_prompts = []
                    for p_en in prompts:
                        p_zh = llm.translate(p_en, "Simplified Chinese")
                        st.session_state.std_prompts.append({"en": p_en, "zh": p_zh})
                    
                    st.session_state.prompt_ver += 1
                    status.update(label="✅ Prompt 生成完毕！", state="complete", expanded=False)
                    st.toast("Prompt 已生成！", icon="✨")
                    st.rerun()

        # 🎨 执行生成区域
        if st.session_state.std_prompts:
            st.markdown('<div class="step-header">Step 2: 任务执行</div>', unsafe_allow_html=True)
            
            for i, p_data in enumerate(st.session_state.std_prompts):
                with st.container(border=True):
                    st.markdown(f"**任务 {i+1}**")
                    tab_zh, tab_en = st.tabs(["🇨🇳 中文编辑 (默认)", "🇺🇸 English Prompt"])
                    
                    with tab_zh:
                        new_zh = st.text_area(
                            "中文指令", 
                            p_data["zh"], 
                            key=f"p_zh_{i}_v{st.session_state.prompt_ver}", 
                            height=100, label_visibility="collapsed"
                        )
                        if new_zh != p_data["zh"]: 
                            st.session_state.std_prompts[i]["zh"] = new_zh
                            st.session_state.std_prompts[i]["en"] = llm.translate(new_zh, "English")
                    
                    with tab_en:
                        st.text_area("English Source", st.session_state.std_prompts[i]["en"], disabled=True, height=100, key=f"p_en_{i}_v{st.session_state.prompt_ver}")

            # 高级面板
            with st.container(border=True):
                st.caption("⚙️ **高级生成参数**")
                cg1, cg2 = st.columns(2)
                model_name = cg1.selectbox("🤖 基础模型", GOOGLE_IMG_MODELS)
                ratio_key = cg2.selectbox("📐 画幅比例", list(RATIO_MAP.keys()))
                
                if "flash" in model_name.lower() and "1:1" not in ratio_key:
                    st.warning("⚠️ Flash 模型仅支持 1:1。", icon="⚠️")

                cg3, cg4 = st.columns(2)
                safety_level = cg3.selectbox("🛡️ 安全过滤", ["Standard (标准)", "Permissive (宽松)", "Strict (严格)"])
                creativity = cg4.slider("🎨 创意度", 0.0, 1.0, 0.5)
                
                cg5, cg6 = st.columns([0.8, 0.2], vertical_alignment="bottom")
                seed_input = cg5.number_input("🎲 Seed", value=-1, step=1)
                real_seed = None if seed_input == -1 else int(seed_input)

            # 生成按钮
            if st.button("🚀 开始生成图片", type="primary", use_container_width=True):
                st.session_state.std_results = []
                
                bar = st.progress(0)
                total = len(st.session_state.std_prompts)
                
                with st.status("🎨 正在绘制中...", expanded=True) as status:
                    for idx, task in enumerate(st.session_state.std_prompts):
                        st.write(f"正在执行任务 {idx+1}/{total}...")
                        
                        # ✨ 注意：融合模式下 active_ref_for_gen 通常为 None
                        # 因为 Image Gen 模型一次只能吃一张参考图，融合主要靠 Prompt 描述
                        res_bytes = img_gen.generate(
                            task["en"], model_name, active_ref_for_gen, RATIO_MAP[ratio_key], 
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

    # --- 右侧：结果预览区 ---
    with c_view:
        if st.session_state.std_results:
            st.subheader("🖼️ 结果预览")
            for idx, img_bytes in enumerate(st.session_state.std_results):
                with st.container(border=True):
                    thumb = create_preview_thumbnail(img_bytes, 400)
                    st.image(thumb, use_container_width=True, caption=f"Result {idx+1}")
                    
                    b_col1, b_col2 = st.columns(2)
                    with b_col1:
                        if "show_image_modal" in globals():
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
